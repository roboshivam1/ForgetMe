"""Offline tests for the interactive cards and privacy score. No network needed.

    python -m scripts.test_cards
"""
import asyncio
import json
import os

for key in ("ORCHESTRATOR", "BREACH_SCOUT", "RISK_RANKER", "ERASER", "FOLLOW_UP", "ACCOUNT_FINDER"):
    os.environ.setdefault(f"SEED_{key}", f"test-seed-{key.lower()}-for-cards")

from uagents_core.contrib.protocols.chat import ChatMessage, MetadataContent  # noqa: E402

from agents.orchestrator import agent as orch  # noqa: E402
from agents.orchestrator import cards, score  # noqa: E402
from agents.orchestrator.intent import classify  # noqa: E402
from agents.orchestrator.state import Sessions  # noqa: E402
from shared.models import (  # noqa: E402
    EraseAction, EraseRequest, EraseResult, FollowUpTask, ScanRequest, TriagedAccount, TriageResult,
)

PASSED = []


def check(name, condition):
    assert condition, f"FAILED: {name}"
    PASSED.append(name)
    print("ok  ", name)


def meta_of(message):
    blocks = [c for c in message.content if isinstance(c, MetadataContent)]
    return blocks[0].metadata if blocks else None


def test_cards_are_valid():
    s, p = score.privacy_score(cards.SAMPLE_ITEMS), score.projected_score(cards.SAMPLE_ITEMS)
    messages = {
        "welcome": cards.welcome_message("hi"),
        "report": cards.report_message("r", cards.SAMPLE_ITEMS, "**bold** headline", s, p),
        "plan": cards.plan_message("p", cards.SAMPLE_ACTIONS, "Asha"),
        "done": cards.done_message("d", cards.SAMPLE_ACTIONS, "24 November 2026", s, p),
    }
    for name, message in messages.items():
        meta = meta_of(message)
        check(f"{name}: has card metadata", meta is not None)
        check(f"{name}: required keys", meta["card_protocol_version"] == "1" and meta["requires_card_interaction"] == "true")
        check(f"{name}: metadata is dict[str,str]", all(isinstance(v, str) for v in meta.values()))
        check(f"{name}: payload valid", cards.validate_payload(meta["card_kind"], json.loads(meta["card_payload"])) is None)
        check(f"{name}: text kept as fallback", message.content[0].text)
    check("done is terminal", meta_of(messages["done"])["is_terminal"] == "true")
    check("plan with emails is interactive", "is_terminal" not in meta_of(messages["plan"]))
    check("headline markdown stripped", "**" not in meta_of(messages["report"])["card_payload"])
    check("report shows privacy score", "Privacy score" in meta_of(messages["report"])["card_payload"])


def test_score():
    s, p = score.privacy_score(cards.SAMPLE_ITEMS), score.projected_score(cards.SAMPLE_ITEMS)
    check("score in range", 5 <= s <= 100 and 5 <= p <= 100)
    check("projected beats current", p > s)
    check("empty list scores 100", score.privacy_score([]) == 100)
    check("bad score values ignored", score.privacy_score([{"verdict": "delete", "score": "x"}]) == 100)
    check("score line mentions both", f"{s}/100" in score.score_line(s, p) and f"{p}/100" in score.score_line(s, p))


def test_plan_without_emails_is_terminal_and_has_no_send():
    links_only = [{"service": "A", "method": "link", "deletion_url": "https://a.example/del"}]
    message = cards.plan_message("p", links_only)
    check("links-only plan terminal", meta_of(message)["is_terminal"] == "true")
    check("links-only plan has no send button", "Send" not in meta_of(message)["card_payload"])


def test_limits_and_fallback():
    many = [{"service": f"S{i}", "verdict": "delete", "reason": "x" * 300, "score": 90} for i in range(500)]
    payload = cards.build_report_payload(many, "", score.privacy_score(many), score.projected_score(many))
    check("500 accounts stay under size cap", cards.validate_payload("custom", payload) is None)
    check("report capped at MAX_ACCOUNTS", f"acc_{cards.MAX_ACCOUNTS + 1}" not in json.dumps(payload))
    bad = cards.build_card_message("hello", "custom", {"no_root": True})
    check("invalid card falls back to text only", meta_of(bad) is None and bad.content[0].text == "hello")
    check("tree depth within 8", cards._depth(cards.build_report_payload(cards.SAMPLE_ITEMS, "", 40, 80)["root"]) <= 8)


def test_intent_mapping():
    check("scan", cards.card_intent('{"action":"scan","email":" a@b.co "}', "idle", 0) == {"intent": "scan", "email": "a@b.co"})
    check("delete all red", cards.card_intent('{"action":"delete_all_red"}', "triaged", 3)
          == {"intent": "select", "all_delete": True, "numbers": []})
    check("delete selected is 0-based", cards.card_intent('{"acc_1": true, "acc_3": "true", "acc_2": false, "action":"delete_selected"}', "triaged", 3)
          == {"intent": "select", "all_delete": False, "numbers": [0, 2]})
    check("out-of-range ticks ignored", cards.card_intent('{"acc_9": true, "action":"delete_selected"}', "triaged", 3)["numbers"] == [])
    check("send carries name", cards.card_intent('{"user_name":"Asha Rao","action":"send"}', "confirm", 3)
          == {"intent": "confirm", "name": "Asha Rao"})
    check("cancel", cards.card_intent('{"action":"cancel"}', "confirm", 3) == {"intent": "cancel"})
    check("unknown action -> None", cards.card_intent('{"action":"nope"}', "idle", 0) is None)
    check("plain chat -> None", cards.card_intent("delete all", "triaged", 3) is None)
    check("planner prose: acc ids", cards.card_intent("The user ticked acc_1 and acc_3 then chose Delete selected.", "triaged", 3)["numbers"] == [0, 2])
    check("planner prose: delete all red", cards.card_intent("User clicked delete_all_red", "triaged", 3)["all_delete"] is True)
    check("planner prose: send + name", cards.card_intent('The user entered user_name "Asha Rao" and clicked send.', "confirm", 3)
          == {"intent": "confirm", "name": "Asha Rao"})


async def test_classify_uses_cards_first():
    result = await classify('{"acc_2": true, "action":"delete_selected"}', "triaged", 3)
    check("classify reads card JSON before rules/ASI1", result["numbers"] == [1])
    result = await classify("delete 1 and 3", "triaged", 3)
    check("classify still handles typed text", result["numbers"] == [0, 2])


class FakeStorage(dict):
    def set(self, key, value):
        self[key] = value


class FakeCtx:
    def __init__(self):
        self.storage = FakeStorage()
        self.sent = []

        class Log:
            def info(self, *a, **k): pass
            warning = exception = info
        self.logger = Log()

    async def send(self, destination, message):
        self.sent.append((destination, message))


async def test_full_flow():
    ctx, user = FakeCtx(), "agent1quser"
    sessions = Sessions(ctx.storage)

    session = sessions.get(user)
    await orch.handle(ctx, user, sessions, session, '{"email": "demo@example.com", "action": "scan"}')
    to_scout = [m for d, m in ctx.sent if isinstance(m, ScanRequest)]
    check("flow: form click sends ScanRequest to Breach Scout", len(to_scout) == 1 and to_scout[0].email == "demo@example.com")

    session = sessions.get(user)
    session["breaches"] = [{"name": "Adobe", "breach_date": "2013-10-04", "data_classes": ["Passwords"]},
                           {"name": "Gawker", "breach_date": "2010-12-11", "data_classes": []}]
    request_id = orch.begin(sessions, user, session, "ranking")
    ctx.sent.clear()
    items = [TriagedAccount(service="Adobe", verdict="delete", reason="Passwords leaked.", score=85),
             TriagedAccount(service="Gawker", verdict="delete", reason="Oldest breach.", score=80),
             TriagedAccount(service="Canva", verdict="secure", reason="Still active.", score=45)]
    await orch.on_triage(ctx, orch.RANKER, TriageResult(request_id=request_id, items=items))
    report = ctx.sent[-1][1]
    check("flow: triage sends a ChatMessage with report card", isinstance(report, ChatMessage) and meta_of(report) is not None)
    check("flow: report card has 3 checkboxes", all(f'"acc_{i}"' in meta_of(report)["card_payload"] for i in (1, 2, 3)))
    check("flow: text report kept", "appears in" in report.content[0].text)
    check("flow: text report has privacy score", "Privacy score" in report.content[0].text)

    ctx.sent.clear()
    session = sessions.get(user)
    await orch.handle(ctx, user, sessions, session, '{"acc_1": true, "acc_3": true, "action": "delete_selected"}')
    erase = [m for d, m in ctx.sent if isinstance(m, EraseRequest)][0]
    check("flow: ticked boxes become the right accounts", [a.service for a in erase.accounts] == ["Adobe", "Canva"])
    check("flow: plan request does not send email", erase.send is False)

    ctx.sent.clear()
    plan_id = sessions.get(user)["request_id"]
    actions = [EraseAction(service="Adobe", method="link", deletion_url="https://example.com/del", difficulty="medium"),
               EraseAction(service="Canva", method="email", privacy_email="privacy@example.com", letter="Subject: x")]
    await orch.on_erase(ctx, orch.ERASER, EraseResult(request_id=plan_id, actions=actions))
    plan = ctx.sent[-1][1]
    check("flow: plan card shows Send 1 request", "Send 1 request" in meta_of(plan)["card_payload"])
    check("flow: state is confirm", sessions.get(user)["state"] == "confirm")

    ctx.sent.clear()
    session = sessions.get(user)
    await orch.handle(ctx, user, sessions, session, '{"user_name": "Asha Rao", "action": "send"}')
    send_req = [m for d, m in ctx.sent if isinstance(m, EraseRequest)][0]
    check("flow: send click emails only the emailable account", send_req.send is True and [a.service for a in send_req.accounts] == ["Canva"])
    check("flow: letters signed with the typed name", send_req.user_name == "Asha Rao")

    ctx.sent.clear()
    send_id = sessions.get(user)["request_id"]
    sent_actions = [EraseAction(service="Canva", method="email", privacy_email="privacy@example.com", letter="x", sent=True)]
    await orch.on_erase(ctx, orch.ERASER, EraseResult(request_id=send_id, actions=sent_actions))
    done = [m for d, m in ctx.sent if isinstance(m, ChatMessage)][0]
    check("flow: done card is terminal", meta_of(done)["is_terminal"] == "true")
    check("flow: done text shows score rising", "privacy score should rise" in done.content[0].text)
    check("flow: follow-up scheduled", any(isinstance(m, FollowUpTask) for d, m in ctx.sent))

    ctx.sent.clear()
    session = sessions.get(user)
    await orch.handle(ctx, user, sessions, session, '{"action": "cancel"}')
    check("flow: cancel returns the welcome form", meta_of(ctx.sent[-1][1])["card_kind"] == "form")


async def test_name_fallback():
    ctx, user = FakeCtx(), "agent1qplanner"
    sessions = Sessions(ctx.storage)
    session = sessions.get(user)
    session.update(state="triaged", email="demo@example.com",
                   items=[{"service": "Adobe", "verdict": "delete", "reason": "r", "score": 80},
                          {"service": "Canva", "verdict": "secure", "reason": "r", "score": 40}])
    sessions.save(user, session)

    async def planner_says_select(text, state, count):
        return {"intent": "select", "numbers": [], "all_delete": False}

    original = orch.classify
    orch.classify = planner_says_select
    try:
        await orch.handle(ctx, user, sessions, sessions.get(user),
                          "The user selected Canva on the card and clicked delete selected.")
    finally:
        orch.classify = original
    erase = [m for d, m in ctx.sent if isinstance(m, EraseRequest)]
    check("planner prose naming a service still selects it", erase and [a.service for a in erase[0].accounts] == ["Canva"])


async def main():
    test_cards_are_valid()
    test_score()
    test_plan_without_emails_is_terminal_and_has_no_send()
    test_limits_and_fallback()
    test_intent_mapping()
    await test_classify_uses_cards_first()
    await test_full_flow()
    await test_name_fallback()
    print(f"\nAll {len(PASSED)} checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
