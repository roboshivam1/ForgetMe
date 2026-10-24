import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from agents.eraser.directory import lookup
from agents.eraser.letters import render_letter
from agents.eraser.mailer import MailError, send_email
from shared.models import EraseAction

SELF_SERVE = ("link", "form", "app_only")
RECEIPTS = Path(__file__).resolve().parents[2] / "data" / "receipts.json"


def make_receipt(to, subject, body):
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    digest = hashlib.sha256(f"{to}\n{subject}\n{body}\n{stamp}".encode("utf8")).hexdigest()
    return stamp, digest


def save_receipt(service, to, stamp, digest, mode="sent"):
    records = json.loads(RECEIPTS.read_text()) if RECEIPTS.exists() else []
    records.append({"service": service, "to": to, "sent_at": stamp, "sha256": digest, "mode": mode})
    RECEIPTS.write_text(json.dumps(records, indent=2))


async def build_action(account, user_name, user_email, send):
    entry = lookup(account.service, account.domain)
    data = {"service": account.service, "domain": account.domain}

    if not entry:
        subject, body = render_letter(account.service, user_name, user_email)
        data.update(
            method="unknown",
            note="Not in our directory yet. Check its account settings or privacy policy for a delete option.",
            letter=f"Subject: {subject}\n\n{body}",
        )
        return EraseAction(**data)

    method = (entry.get("method") or "unknown").strip().lower()
    data.update(
        method=method,
        deletion_url=entry.get("deletion_url", ""),
        privacy_email=entry.get("privacy_email", ""),
        difficulty=entry.get("difficulty", ""),
        note=entry.get("note", ""),
    )

    if method in SELF_SERVE and data["deletion_url"]:
        return EraseAction(**data)

    if not data["privacy_email"]:
        data["note"] = data["note"] or "No privacy email listed. Use the link or contact their support."
        return EraseAction(**data)

    subject, body = render_letter(account.service, user_name, user_email)
    data["letter"] = f"Subject: {subject}\n\n{body}"

    if send:
        try:
            outcome = await asyncio.to_thread(send_email, data["privacy_email"], subject, body, user_email)
            data["sent"] = outcome in ("sent", "redirected")
            if data["sent"]:
                stamp, digest = make_receipt(data["privacy_email"], subject, body)
                try:
                    save_receipt(account.service, data["privacy_email"], stamp, digest, outcome)
                except (OSError, ValueError):
                    pass  # the email already went out; never lose the result over a log file
                data["receipt"] = f"RCPT-{digest[:10].upper()}"
            if outcome == "dry_run":
                data["note"] = "Dry run: letter prepared but not sent."
            elif outcome == "redirected":
                data["note"] = "Demo mode: sent to the redirect inbox instead of the company."
        except MailError as err:
            data["error"] = str(err)

    return EraseAction(**data)
