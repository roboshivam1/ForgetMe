ICON = {"delete": "🔴", "secure": "🟡", "keep": "🟢"}
ATTRIBUTION = "_Breach data: XposedOrNot and Have I Been Pwned (haveibeenpwned.com)._"
SELF_SERVE = ("link", "form", "app_only")


def welcome():
    return (
        "Hi, I'm **ForgetMe**. I find the online accounts where your data has leaked or been forgotten, "
        "tell you which ones matter, and file the deletion requests for you.\n\n"
        "Send me the **email address** you want to check. Nothing is sent to any company without your approval."
    )


def help_text():
    return (
        "Here's what I can do:\n"
        "- **Scan an email**: just send the address.\n"
        "- **Pick accounts to delete**: `delete all` (every 🔴), or numbers like `delete 1, 3-5`.\n"
        "- **Send the requests**: `send`, optionally with your name, e.g. `send - Asha Rao`.\n"
        "- **Protect accounts you keep**: `secure`.\n"
        "- **Start again**: `restart`."
    )


def scanning(email):
    return f"Checking **{email}** against known data breaches. This takes a few seconds..."


def ranking(count):
    return f"Found **{count}** breached accounts. Working out which ones matter most..."


def no_breaches(email):
    return (
        f"Good news: **{email}** doesn't appear in any known data breach. 🎉\n\n"
        "Send another email address to check it, or say `help`.\n\n" + ATTRIBUTION
    )


def error(message):
    return f"⚠️ {message}\n\nSay `restart` to try again."


def _headline(email, breaches):
    count = len(breaches)
    passwords = sum(1 for b in breaches if any(c.lower() == "passwords" for c in b.get("data_classes", [])))
    dated = [b for b in breaches if b.get("breach_date")]
    oldest = min(dated, key=lambda b: b["breach_date"]) if dated else None
    line = f"**{email}** appears in **{count} data breach{'es' if count != 1 else ''}**"
    facts = []
    if passwords:
        facts.append(f"**{passwords}** leaked a password")
    if oldest:
        facts.append(f"the oldest is **{oldest['name']}** from {oldest['breach_date'][:4]}")
    return line + (": " + "; ".join(facts) if facts else "") + "."


def triage_report(email, breaches, items):
    lines = [_headline(email, breaches), ""]
    for number, item in enumerate(items, start=1):
        icon = ICON.get(item["verdict"], "•")
        lines.append(f"{number}. {icon} **{item['service']}** ({item['verdict']}): {item['reason']}")
    counts = {v: sum(1 for i in items if i["verdict"] == v) for v in ICON}
    lines += [
        "",
        f"🔴 delete {counts['delete']} · 🟡 secure {counts['secure']} · 🟢 keep {counts['keep']}",
        "",
        "Reply `delete all` to remove every 🔴 account, or pick numbers like `delete 1, 3`. "
        "Say `secure` for how to protect the 🟡 ones.",
        "",
        ATTRIBUTION,
    ]
    return "\n".join(lines)


def erase_plan(actions, name):
    links = [a for a in actions if a["method"] in SELF_SERVE and a.get("deletion_url")]
    emails = [a for a in actions if a.get("letter") and a.get("privacy_email")]
    rest = [a for a in actions if a not in links and a not in emails]

    lines = [f"Here's the plan for **{len(actions)}** account{'s' if len(actions) != 1 else ''}:", ""]
    if links:
        lines.append("**Delete these yourself (fastest)**")
        for a in links:
            extra = f" · {a['difficulty']}" if a.get("difficulty") else ""
            note = f" ({a['note']})" if a.get("note") else ""
            lines.append(f"- {a['service']}: [delete account]({a['deletion_url']}){extra}{note}")
        lines.append("")
    if emails:
        lines.append("**Formal deletion requests I'll email for you**")
        for a in emails:
            lines.append(f"- {a['service']} → {a['privacy_email']}")
        lines.append("")
    if rest:
        lines.append("**Needs a manual step**")
        for a in rest:
            reason = a.get("note") or a.get("error") or "No deletion route on file yet."
            lines.append(f"- {a['service']}: {reason}")
        lines.append("")
    if emails:
        signer = f"signed as **{name}**" if name else "unsigned"
        lines.append(
            f"Reply `send` to email these **{len(emails)}** requests ({signer}). "
            "To sign with your name, reply like `send - Asha Rao`. Say `cancel` to stop."
        )
    else:
        lines.append("No emails needed. Use the links above, then say `restart` to check another address.")
    return "\n".join(lines)


def erase_done(actions, deadline):
    sent = [a for a in actions if a.get("sent")]
    failed = [a for a in actions if a.get("letter") and a.get("privacy_email") and not a.get("sent")]
    lines = []
    if sent:
        lines.append(f"✅ Sent **{len(sent)}** deletion request{'s' if len(sent) != 1 else ''}:")
        for a in sent:
            lines.append(f"- {a['service']} → {a['privacy_email']}")
        lines.append(f"\nCompanies should reply by **{deadline}**. I'll track that and chase anyone who ignores you.")
    if failed:
        lines.append("\n⚠️ Not sent:")
        for a in failed:
            lines.append(f"- {a['service']}: {a.get('error') or a.get('note') or 'unknown problem'}")
    demo = [a for a in sent if "Demo mode" in (a.get("note") or "")]
    if demo:
        lines.append("\n_Demo mode: requests went to the demo inbox instead of the companies._")
    lines.append("\nSay `restart` to check another email address.")
    return "\n".join(lines)


def secure_tips(items):
    targets = [i for i in items if i["verdict"] == "secure"]
    if not targets:
        return "Nothing is marked 🟡 secure right now. Pick accounts to delete, or say `restart`."
    names = ", ".join(f"**{i['service']}**" for i in targets)
    return (
        f"For {names}:\n"
        "1. Change the password, and change it anywhere else you reused it.\n"
        "2. Turn on two-factor authentication (an authenticator app beats SMS).\n"
        "3. Check the account's recent logins and connected apps for anything unfamiliar.\n"
        "4. Use a password manager so every account gets its own password.\n\n"
        "When you're ready, pick accounts to delete, e.g. `delete 1, 3`."
    )
