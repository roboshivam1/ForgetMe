"""Interactive cards for the ForgetMe orchestrator (ASI:One).

A card is one extra MetadataContent block on a normal ChatMessage, next to the
text. If ASI:One rejects a card it shows the text instead, so every builder
here takes the existing text reply (from views.py) and keeps it in the message.

Cards
    welcome  form    email field + "Scan"
    report   custom  privacy score, badge + reason + checkbox per account, bulk buttons
    plan     custom  link / email / manual rows, name field, Send / Cancel
    done     custom  summary + projected score, marked terminal

The plan is a custom card, not `review`, because the predefined review card
has no input field and the plan needs the user's name to sign the letters.

Clicks come back as chat text. card_intent() turns them into the same intent
dicts that intent.rule_intent() returns, so agent.py needs no new branches:
  - JSON text (direct @mention)      -> exact mapping
  - prose (ASI:One planner narrates) -> best-effort mapping, else None, and the
    normal rule/ASI1 classifier takes over.

Preview payloads without running agents:
    python -m agents.orchestrator.cards --dump ./docs/card_samples
Paste a file into https://asi1.ai/developer/card-playground with the card kind
shown in the file name (form_* -> form, custom_* -> custom).
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agents.orchestrator.score import grade

MAX_PAYLOAD_BYTES = 60 * 1024
MAX_DEPTH = 8
MAX_ACCOUNTS = 40
DRAWER_WIDTH_PX = "540"
CARD_KINDS = ("carousel", "detail", "form", "review", "custom")

ACTION_SCAN = "scan"
ACTION_DELETE_ALL_RED = "delete_all_red"
ACTION_DELETE_SELECTED = "delete_selected"
ACTION_SEND = "send"
ACTION_CANCEL = "cancel"

SELF_SERVE = ("link", "form", "app_only")

VERDICTS = {
    "delete": ("🔴 Delete", "warning"),
    "secure": ("🟡 Secure", "info"),
    "keep": ("🟢 Keep", "success"),
}


def _short(value: str, limit: int = 80) -> str:
    value = str(value or "")
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def plain(markdown_text: str) -> str:
    return (markdown_text or "").replace("**", "")


def emailable(action: Dict[str, Any]) -> bool:
    return bool(action.get("letter") and action.get("privacy_email"))


def has_link(action: Dict[str, Any]) -> bool:
    return action.get("method") in SELF_SERVE and bool(action.get("deletion_url"))


def _row(*children: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "group", "direction": "row", "gap": 8, "children": list(children)}


def _score_block(score: Optional[int], projected: Optional[int]) -> List[Dict[str, Any]]:
    if score is None:
        return []
    label, variant = grade(score)
    block: List[Dict[str, Any]] = [_row(
        {"type": "badge", "label": f"Privacy score {score}/100", "variant": variant},
        {"type": "text", "value": label, "style": "emphasis"},
    )]
    if projected is not None and projected > score:
        block.append({"type": "text", "style": "muted",
                      "value": f"Projected after cleanup: {projected}/100 once companies confirm."})
    return block


def build_welcome_payload() -> Dict[str, Any]:
    return {
        "title": "How exposed are you?",
        "fields": [{"name": "email", "kind": "email", "label": "Email address to check", "required": True}],
        "submit_cta": {"label": "Scan", "selection": {"action": ACTION_SCAN}},
    }


def build_report_payload(items: List[Dict[str, Any]], headline: str = "",
                         score: Optional[int] = None, projected: Optional[int] = None) -> Dict[str, Any]:
    shown = list(items)[:MAX_ACCOUNTS]
    red = sum(1 for i in shown if i.get("verdict") == "delete")

    rows: List[Dict[str, Any]] = []
    for number, item in enumerate(shown, start=1):
        label, variant = VERDICTS.get(item.get("verdict"), VERDICTS["keep"])
        detail: List[Dict[str, Any]] = [{"type": "badge", "label": label, "variant": variant}]
        if item.get("reason"):
            detail.append({"type": "text", "value": _short(item["reason"]), "style": "muted"})
        rows.append({
            "type": "group", "direction": "column", "gap": 4,
            "children": [
                {"type": "input", "name": f"acc_{number}", "kind": "checkbox",
                 "label": f"{number}. {item.get('service', 'Unknown')}"},
                _row(*detail),
            ],
        })

    buttons: List[Dict[str, Any]] = []
    if red:
        buttons.append({"type": "button", "label": f"Delete all red ({red})", "primary": True,
                        "action": {"selection": {"action": ACTION_DELETE_ALL_RED}}})
    buttons.append({"type": "button", "label": "Delete selected", "primary": not red,
                    "action": {"selection": {"action": ACTION_DELETE_SELECTED}}})

    children: List[Dict[str, Any]] = []
    if headline:
        children.append({"type": "text", "value": headline, "style": "emphasis"})
    children += _score_block(score, projected)
    children += rows + [{"type": "divider"}, _row(*buttons)]
    return {"root": {"type": "section", "title": "Your exposure report",
                     "subtitle": f"{_plural(len(shown), 'account')} · {red} marked delete",
                     "children": children}}


def build_plan_payload(actions: List[Dict[str, Any]], name: str = "") -> Dict[str, Any]:
    links = [a for a in actions if has_link(a)]
    emails = [a for a in actions if emailable(a)]
    manual = [a for a in actions if a not in links and a not in emails]

    rows: List[Dict[str, Any]] = []
    for a in links:
        extra = f" · {a['difficulty']}" if a.get("difficulty") else ""
        rows.append(_row({"type": "badge", "label": "Self-serve link", "variant": "success"},
                         {"type": "text", "value": _short(f"{a['service']}{extra}: {a['deletion_url']}", 110)}))
    for a in emails:
        rows.append(_row({"type": "badge", "label": "Email request", "variant": "info"},
                         {"type": "text", "value": _short(f"{a['service']} → {a['privacy_email']}", 110)}))
    for a in manual:
        reason = a.get("note") or a.get("error") or "No deletion route on file yet."
        rows.append(_row({"type": "badge", "label": "Manual step", "variant": "warning"},
                         {"type": "text", "value": _short(f"{a['service']}: {reason}", 110)}))

    children: List[Dict[str, Any]] = list(rows)
    if emails:
        children += [
            {"type": "divider"},
            {"type": "input", "name": "user_name", "kind": "text", "required": True,
             "label": "Your full name (signs the requests)", "placeholder": name or "Full name"},
            _row(
                {"type": "button", "label": f"Send {_plural(len(emails), 'request')}", "primary": True,
                 "action": {"selection": {"action": ACTION_SEND}}},
                {"type": "button", "label": "Cancel", "action": {"selection": {"action": ACTION_CANCEL}}},
            ),
        ]
    subtitle = "Nothing is sent until you press send." if emails else "Use the links below, then ask for a new scan."
    return {"root": {"type": "section", "title": "Deletion plan", "subtitle": subtitle, "children": children}}


def build_done_payload(actions: List[Dict[str, Any]], deadline: str = "",
                       score: Optional[int] = None, projected: Optional[int] = None) -> Dict[str, Any]:
    sent = [a for a in actions if a.get("sent")]
    failed = [a for a in actions if emailable(a) and not a.get("sent")]
    links = [a for a in actions if has_link(a)]

    children: List[Dict[str, Any]] = [
        {"type": "badge", "label": f"✓ {_plural(len(sent), 'request')} sent",
         "variant": "success" if sent else "warning"},
    ]
    if sent:
        children.append({"type": "text", "style": "muted",
                         "value": _short(", ".join(a["service"] for a in sent), 140)})
    if deadline and sent:
        children.append({"type": "text", "style": "emphasis",
                         "value": f"Companies should reply by {deadline}. I'll chase anyone who ignores you."})
    if failed:
        children.append({"type": "text", "value": _short("Not sent: " + ", ".join(a["service"] for a in failed), 140)})
    children += _score_block(score, projected)
    if links:
        children += [{"type": "divider"}, {"type": "heading", "value": "Delete these yourself", "level": 3}]
        children += [{"type": "text", "value": _short(f"{a['service']}: {a['deletion_url']}", 120)} for a in links]
    return {"root": {"type": "section", "title": "All done", "children": children}}


def _depth(node: Any) -> int:
    if not isinstance(node, dict):
        return 0
    kids: List[Any] = list(node.get("children") or []) + list(node.get("items") or [])
    return 1 + max((_depth(k) for k in kids), default=0)


def validate_payload(card_kind: str, payload: Dict[str, Any]) -> Optional[str]:
    if card_kind not in CARD_KINDS:
        return f"unknown card kind {card_kind}"
    try:
        size = len(json.dumps(payload).encode("utf-8"))
    except (TypeError, ValueError) as err:
        return f"payload is not JSON serializable: {err}"
    if size > MAX_PAYLOAD_BYTES:
        return f"payload too large ({size} bytes)"
    if card_kind == "custom":
        if "root" not in payload:
            return "custom payload needs a top-level 'root'"
        if _depth(payload["root"]) > MAX_DEPTH:
            return f"custom tree deeper than {MAX_DEPTH} levels"
    return None


def build_card_message(text: str, card_kind: str, payload: Dict[str, Any], terminal: bool = False):
    from uagents_core.contrib.protocols.chat import ChatMessage, MetadataContent, TextContent

    content: List[Any] = [TextContent(type="text", text=text)]
    if validate_payload(card_kind, payload) is None:
        meta = {
            "card_protocol_version": "1",
            "requires_card_interaction": "true",
            "card_kind": card_kind,
            "card_payload": json.dumps(payload),
            "preferred_drawer_width_px": DRAWER_WIDTH_PX,
        }
        if terminal:
            meta["is_terminal"] = "true"
        content.append(MetadataContent(type="metadata", metadata=meta))
    return ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=content)


def welcome_message(text: str):
    return build_card_message(text, "form", build_welcome_payload())


def report_message(text: str, items: List[Dict[str, Any]], headline: str = "",
                   score: Optional[int] = None, projected: Optional[int] = None):
    return build_card_message(text, "custom", build_report_payload(items, plain(headline), score, projected))


def plan_message(text: str, actions: List[Dict[str, Any]], name: str = ""):
    return build_card_message(text, "custom", build_plan_payload(actions, name),
                              terminal=not any(emailable(a) for a in actions))


def done_message(text: str, actions: List[Dict[str, Any]], deadline: str = "",
                 score: Optional[int] = None, projected: Optional[int] = None):
    return build_card_message(text, "custom", build_done_payload(actions, deadline, score, projected), terminal=True)


def parse_card_selection(text: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads((text or "").strip())
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _ticked(value: Any) -> bool:
    return value is True or str(value).lower() in ("true", "on", "1", "yes")


def selected_indexes(selection: Dict[str, Any], count: int) -> List[int]:
    picked = set()
    for key, value in selection.items():
        match = re.fullmatch(r"acc_(\d+)", str(key))
        if match and _ticked(value) and 1 <= int(match.group(1)) <= count:
            picked.add(int(match.group(1)) - 1)
    return sorted(picked)


def selection_to_intent(selection: Dict[str, Any], count: int) -> Optional[Dict[str, Any]]:
    action = selection.get("action")
    if action == ACTION_SCAN:
        return {"intent": "scan", "email": str(selection.get("email", "")).strip()}
    if action == ACTION_DELETE_ALL_RED:
        return {"intent": "select", "all_delete": True, "numbers": []}
    if action == ACTION_DELETE_SELECTED:
        return {"intent": "select", "all_delete": False, "numbers": selected_indexes(selection, count)}
    if action == ACTION_SEND:
        return {"intent": "confirm", "name": str(selection.get("user_name", "")).strip()[:60]}
    if action == ACTION_CANCEL:
        return {"intent": "cancel"}
    return None


def prose_intent(text: str, state: str, count: int) -> Optional[Dict[str, Any]]:
    t = text or ""
    if re.search(r"delete[ _]all[ _]red", t, re.I):
        return {"intent": "select", "all_delete": True, "numbers": []}
    numbers = sorted({int(n) - 1 for n in re.findall(r"\bacc_(\d+)\b", t) if 1 <= int(n) <= count})
    if numbers:
        return {"intent": "select", "all_delete": False, "numbers": numbers}
    if state == "confirm" and re.search(r"\buser_name\b|\baction\W{0,4}send\b|\bsend \d+ request", t, re.I):
        found = re.search(r"user_name\W{0,6}([A-Za-z][A-Za-z .'\-]{1,58}?)(?:[\"'.,;)]|\band\b|$)", t)
        return {"intent": "confirm", "name": found.group(1).strip() if found else ""}
    return None


def card_intent(text: str, state: str, count: int) -> Optional[Dict[str, Any]]:
    selection = parse_card_selection(text)
    if selection is not None:
        return selection_to_intent(selection, count)
    return prose_intent(text, state, count)


SAMPLE_ITEMS = [
    {"service": "Adobe", "verdict": "delete", "reason": "Breached 2013; passwords and hints leaked.", "score": 85},
    {"service": "Gawker", "verdict": "delete", "reason": "Breached 2010; the oldest exposure.", "score": 80},
    {"service": "Stratfor", "verdict": "delete", "reason": "Breached 2011; unsalted MD5 passwords.", "score": 75},
    {"service": "Canva", "verdict": "secure", "reason": "Still active; change the password, turn on 2FA.", "score": 45},
    {"service": "Spotify", "verdict": "keep", "reason": "No known breach and in regular use.", "score": 10},
]
SAMPLE_ACTIONS = [
    {"service": "Adobe", "method": "link", "deletion_url": "https://example.com/delete", "difficulty": "medium"},
    {"service": "Gawker", "method": "email", "privacy_email": "privacy@example.com", "letter": "Subject: x"},
    {"service": "Stratfor", "method": "email", "privacy_email": "privacy@example.com", "letter": "Subject: x"},
    {"service": "Old Forum", "method": "unknown", "note": "No deletion route on file yet."},
]


def _dump(directory: str) -> None:
    import os

    from agents.orchestrator.score import privacy_score, projected_score

    os.makedirs(directory, exist_ok=True)
    score, projected = privacy_score(SAMPLE_ITEMS), projected_score(SAMPLE_ITEMS)
    sent = [dict(a, sent=True) for a in SAMPLE_ACTIONS if emailable(a)] + [a for a in SAMPLE_ACTIONS if has_link(a)]
    samples = {
        "form_welcome": build_welcome_payload(),
        "custom_report": build_report_payload(SAMPLE_ITEMS, "you@example.com appears in 5 data breaches.", score, projected),
        "custom_plan": build_plan_payload(SAMPLE_ACTIONS, "Asha Rao"),
        "custom_done": build_done_payload(sent, "24 November 2026", score, projected),
    }
    for name, payload in samples.items():
        path = os.path.join(directory, f"{name}.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        print("wrote", path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--dump":
        _dump(sys.argv[2])
    else:
        print("usage: python -m agents.orchestrator.cards --dump ./docs/card_samples")
