import json
import re

from shared.asi1 import aask_json

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
YES_RE = re.compile(r"^(send|yes|y|yeah|yep|confirm|go|go ahead|do it|ok|okay|sure)\b", re.I)


def parse_numbers(text, count):
    picked = set()
    for start, end in re.findall(r"(\d+)\s*-\s*(\d+)", text):
        picked.update(range(int(start), int(end) + 1))
    text_wo_ranges = re.sub(r"\d+\s*-\s*\d+", " ", text)
    picked.update(int(n) for n in re.findall(r"\d+", text_wo_ranges))
    return sorted(i - 1 for i in picked if 1 <= i <= count)


def name_after_yes(text):
    rest = YES_RE.sub("", text.strip(), count=1)
    rest = re.sub(r"^[\s,:\-]*(as|signed|sign it|name)?[\s,:\-]*", "", rest, flags=re.I).strip(" .!")
    return rest[:60] if re.search(r"[A-Za-z]", rest) else ""


def rule_intent(text, state, count):
    t = text.strip().lower()
    email = EMAIL_RE.search(text)

    if t in ("help", "?", "menu", "what can you do", "what can you do?"):
        return {"intent": "help"}
    if re.match(r"^(restart|start over|reset|new scan|scan again)\b", t):
        return {"intent": "restart"}
    if re.match(r"^(cancel|stop|nope|no)\b", t):
        return {"intent": "cancel"}
    if email:
        return {"intent": "scan", "email": email.group(0)}
    if state == "confirm" and YES_RE.match(t):
        return {"intent": "confirm", "name": name_after_yes(text)}
    if state in ("triaged", "confirm"):
        if re.search(r"\b(all|every|everything)\b", t) and re.search(r"delete|remove|erase|all", t):
            return {"intent": "select", "all_delete": "everything" not in t and "every account" not in t,
                    "numbers": list(range(count)) if "everything" in t else []}
        numbers = parse_numbers(t, count)
        if numbers:
            return {"intent": "select", "numbers": numbers, "all_delete": False}
        if re.search(r"\b(secure|2fa|protect|password)\b", t):
            return {"intent": "secure"}
    return None


SYSTEM = (
    "You route chat messages for ForgetMe, an assistant that finds a person's breached or forgotten "
    "online accounts and files deletion requests. Classify the user's latest message. "
    'Return JSON: {"intent": "scan|select|confirm|cancel|restart|secure|help|question", '
    '"email": "", "numbers": [], "all_delete": false, "name": "", "answer": ""}. '
    "scan = they want an email checked (put it in email). select = they choose accounts (numbers are the "
    "1-based list numbers; all_delete=true means every account marked delete). confirm = they agree to send "
    "the deletion requests (name = the name they want to sign with, if given). secure = they want help "
    "protecting accounts. question = anything else; then write a short, accurate answer (max 60 words) "
    "about privacy, data breaches, account deletion or how ForgetMe works, and never invent facts about the user."
)


async def classify(text, state, count):
    found = rule_intent(text, state, count)
    if found:
        return found
    context = json.dumps({"current_step": state, "accounts_listed": count, "message": text})
    try:
        data = await aask_json(SYSTEM, context, max_tokens=600)
    except Exception:
        return {"intent": "question", "answer": ""}
    intent = str(data.get("intent", "question")).lower()
    numbers = []
    for n in data.get("numbers") or []:
        try:
            if 1 <= int(n) <= count:
                numbers.append(int(n) - 1)
        except (TypeError, ValueError):
            pass
    return {
        "intent": intent,
        "email": str(data.get("email") or ""),
        "numbers": sorted(set(numbers)),
        "all_delete": bool(data.get("all_delete")),
        "name": str(data.get("name") or "")[:60],
        "answer": str(data.get("answer") or "")[:600],
    }
