import time
from datetime import date

from uagents import Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, chat_protocol_spec

from agents.eraser.letters import deadline_from
from agents.orchestrator import views
from agents.orchestrator.intent import classify
from agents.orchestrator.state import Sessions, to_dict
from shared.agentkit import make_agent
from shared.chat import ack_for, extract_text, text_message
from shared.config import address_for, env
from shared.models import (
    Account, BreachReport, EraseRequest, EraseResult, FollowUpAck, FollowUpTask,
    ScanRequest, TriagedAccount, TriageRequest, TriageResult,
)

agent = make_agent("orchestrator", "forgetme")
chat = Protocol(spec=chat_protocol_spec)

SCOUT = address_for("breach_scout")
RANKER = address_for("risk_ranker")
ERASER = address_for("eraser")
FOLLOW_UP = address_for("follow_up")
BUSY = ("scanning", "ranking", "planning", "sending")
STUCK_AFTER = 120


async def say(ctx, user, text):
    await ctx.send(user, text_message(text))


def emailable(action):
    return bool(action.get("letter") and action.get("privacy_email"))


def signer(session):
    return session.get("name") or env("USER_DISPLAY_NAME") or ""


def load(sessions, request_id):
    user = sessions.user_for(request_id)
    if not user:
        return None, None
    session = sessions.get(user)
    if not sessions.is_current(session, request_id):
        return None, None
    return user, session


def begin(sessions, user, session, state):
    session["since"] = time.time()
    return sessions.start_request(user, session, state)


@agent.on_event("startup")
async def started(ctx):
    ctx.logger.info(f"ForgetMe orchestrator ready at {agent.address}")


@chat.on_message(ChatMessage)
async def on_chat(ctx, sender, msg):
    await ctx.send(sender, ack_for(msg))
    text = extract_text(msg)
    sessions = Sessions(ctx.storage)
    session = sessions.get(sender)
    if not text:
        if session["state"] == "idle":
            await say(ctx, sender, views.welcome())
        return
    try:
        await handle(ctx, sender, sessions, session, text)
    except Exception as err:
        ctx.logger.exception(f"Chat handling failed: {err}")
        await say(ctx, sender, views.error("Something went wrong on my side."))


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx, sender, msg):
    pass


async def handle(ctx, user, sessions, session, text):
    state, items = session["state"], session["items"]
    intent = await classify(text, state, len(items))
    kind = intent.get("intent")
    ctx.logger.info(f"[{state}] intent={kind}")

    busy = state in BUSY and time.time() - session.get("since", 0) < STUCK_AFTER
    if busy and kind not in ("restart", "cancel", "help", "question"):
        await say(ctx, user, "Still working on your last request. One moment...")
        return

    if kind == "help":
        await say(ctx, user, views.help_text())

    elif kind in ("restart", "cancel"):
        sessions.reset(user)
        prefix = "Cancelled. " if kind == "cancel" else ""
        await say(ctx, user, prefix + views.welcome())

    elif kind == "scan":
        email = intent.get("email", "").strip()
        if not email:
            await say(ctx, user, "Which email address should I check?")
            return
        session = sessions.reset(user)
        session["email"] = email
        request_id = begin(sessions, user, session, "scanning")
        await say(ctx, user, views.scanning(email))
        await ctx.send(SCOUT, ScanRequest(request_id=request_id, email=email))

    elif kind == "select":
        if state not in ("triaged", "confirm", "done") or not items:
            await say(ctx, user, "First send me an email address to scan.")
            return
        picked = intent.get("numbers") or []
        if intent.get("all_delete"):
            picked = [i for i, item in enumerate(items) if item["verdict"] == "delete"]
        if not picked:
            await say(ctx, user, "I couldn't tell which accounts you meant. Try `delete 1, 3` or `delete all`.")
            return
        session["selected"], session["actions"] = picked, []
        request_id = begin(sessions, user, session, "planning")
        await say(ctx, user, f"Preparing a deletion plan for **{len(picked)}** account{'s' if len(picked) != 1 else ''}...")
        await ctx.send(ERASER, EraseRequest(
            request_id=request_id, user_name=signer(session), user_email=session["email"],
            accounts=[TriagedAccount(**items[i]) for i in picked], send=False,
        ))

    elif kind == "confirm":
        if state != "confirm":
            await say(ctx, user, "Nothing to send yet. Pick accounts first, e.g. `delete all`.")
            return
        if intent.get("name"):
            session["name"] = intent["name"]
        names = {a["service"] for a in session["actions"] if emailable(a)}
        targets = [items[i] for i in session["selected"] if items[i]["service"] in names]
        if not targets:
            await say(ctx, user, "None of the selected accounts need an email. Use the links in the plan.")
            return
        request_id = begin(sessions, user, session, "sending")
        await say(ctx, user, f"Sending **{len(targets)}** deletion request{'s' if len(targets) != 1 else ''}...")
        await ctx.send(ERASER, EraseRequest(
            request_id=request_id, user_name=signer(session), user_email=session["email"],
            accounts=[TriagedAccount(**t) for t in targets], send=True,
        ))

    elif kind == "secure":
        await say(ctx, user, views.secure_tips(items) if items else "Send me an email address to scan first.")

    else:
        answer = intent.get("answer") or ""
        if state == "idle":
            await say(ctx, user, (answer + "\n\n" if answer else "") + views.welcome())
        else:
            await say(ctx, user, answer or views.help_text())


@agent.on_message(model=BreachReport)
async def on_breaches(ctx, sender, msg):
    if sender != SCOUT:
        return
    sessions = Sessions(ctx.storage)
    user, session = load(sessions, msg.request_id)
    if not user:
        return
    if msg.error or not msg.breaches:
        session["state"] = "idle"
        sessions.save(user, session)
        await say(ctx, user, views.error(msg.error) if msg.error else views.no_breaches(session["email"]))
        return
    unique = {}
    for breach in msg.breaches:
        unique.setdefault(breach.name.lower(), breach)
    breaches = list(unique.values())
    session["breaches"] = [to_dict(b) for b in breaches]
    request_id = begin(sessions, user, session, "ranking")
    await say(ctx, user, views.ranking(len(breaches)))
    await ctx.send(RANKER, TriageRequest(
        request_id=request_id,
        accounts=[Account(service=b.name, domain=b.domain, breach=b) for b in breaches],
    ))


@agent.on_message(model=TriageResult)
async def on_triage(ctx, sender, msg):
    if sender != RANKER:
        return
    sessions = Sessions(ctx.storage)
    user, session = load(sessions, msg.request_id)
    if not user:
        return
    if msg.error or not msg.items:
        session["state"] = "idle"
        sessions.save(user, session)
        await say(ctx, user, views.error(msg.error or "I couldn't rank your accounts."))
        return
    session["items"] = [to_dict(i) for i in msg.items]
    session["state"] = "triaged"
    sessions.save(user, session)
    await say(ctx, user, views.triage_report(session["email"], session["breaches"], session["items"]))


@agent.on_message(model=EraseResult)
async def on_erase(ctx, sender, msg):
    if sender != ERASER:
        return
    sessions = Sessions(ctx.storage)
    user, session = load(sessions, msg.request_id)
    if not user:
        return
    actions = [to_dict(a) for a in msg.actions]

    if session["state"] == "planning":
        session["actions"] = actions
        session["state"] = "confirm" if any(emailable(a) for a in actions) else "done"
        sessions.save(user, session)
        await say(ctx, user, views.erase_plan(actions, signer(session)))
        return

    session["state"] = "done"
    sessions.save(user, session)
    due = deadline_from()
    await say(ctx, user, views.erase_done(actions, due.strftime("%d %B %Y")))
    for action in msg.actions:
        if action.sent:
            try:
                await ctx.send(FOLLOW_UP, FollowUpTask(
                    request_id=msg.request_id, user_email=session["email"], user_name=signer(session),
                    service=action.service, contact=action.privacy_email,
                    sent_on=date.today().isoformat(), due_on=due.isoformat(),
                ))
            except Exception as err:
                ctx.logger.warning(f"Follow-up not scheduled for {action.service}: {err}")


@agent.on_message(model=FollowUpAck)
async def on_followup_ack(ctx, sender, msg):
    ctx.logger.info(f"Follow-up tracking {msg.tracked} requests for {msg.request_id}")


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
