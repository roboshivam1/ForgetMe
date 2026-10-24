from agents.risk_ranker.rules import is_crypto, score_account, verdict_for
from shared.models import Account, Breach

ledger = Account(service="Ledger", domain="ledger.com",
                 breach=Breach(name="Ledger", domain="ledger.com", breach_date="2020-06-25",
                               data_classes=["Email addresses", "Names", "Phone numbers", "Physical addresses"]))
forum = Account(service="Some Forum", domain="forum.example",
                breach=Breach(name="Some Forum", domain="forum.example", breach_date="2020-06-25",
                              data_classes=["Email addresses", "Names", "Phone numbers", "Physical addresses"]))

assert is_crypto(ledger) and not is_crypto(forum)
ledger_score = score_account(ledger)
forum_score = score_account(forum)
assert ledger_score[0] == min(forum_score[0] + 20, 100), (ledger_score, forum_score)
print("Ledger:", ledger_score[0], verdict_for(*ledger_score))
print("Forum: ", forum_score[0], verdict_for(*forum_score))
print("Crypto flag OK")

# ---- cards + receipts (offline)
import asyncio
import json
import pathlib
import tempfile

from agents.eraser import core
from agents.orchestrator import cards, views

items = [
    {"service": "Ledger", "verdict": "delete", "score": 75,
     "reason": "Breached in 2020: Email addresses, Names exposed. ⚠️ Crypto service: expect targeted phishing "
               "and fake support calls; never share your seed phrase."},
    {"service": "Some Forum", "verdict": "secure", "score": 55, "reason": "Breached in 2020."},
]
payload = cards.build_report_payload(items, "headline")
blob = json.dumps(payload, ensure_ascii=False)
assert "⚠️ Crypto" in blob and "seed phrase" in blob and "Crypto service" not in blob
assert cards.validate_payload("custom", payload) is None
assert "Crypto" not in json.dumps(cards.build_report_payload(items[1:], "h"))
assert "Crypto accounts found" in views.triage_report("a@b.c", [], items)

core.RECEIPTS = pathlib.Path(tempfile.mkdtemp()) / "receipts.json"
core.lookup = lambda service, domain: {"method": "email", "privacy_email": "privacy@ledger.com"}
for outcome, expect_receipt in (("sent", True), ("redirected", True), ("dry_run", False)):
    core.send_email = lambda *a, _o=outcome, **k: _o
    action = asyncio.run(core.build_action(Account(service="Ledger", domain="ledger.com"), "Asha", "a@b.c", True))
    assert bool(action.receipt) is expect_receipt, (outcome, action.receipt)
records = json.loads(core.RECEIPTS.read_text())
assert [r["mode"] for r in records] == ["sent", "redirected"], records

sent = [dict(action.dict(), sent=True, receipt="RCPT-ABC1234567")]
assert "RCPT-ABC1234567" in json.dumps(cards.build_done_payload(sent, "24 November 2026"))
assert "receipt `RCPT-ABC1234567`" in views.erase_done(sent, "24 November 2026")
print("Cards + receipts OK")

# a broken receipts file must not break a request that was already sent
core.RECEIPTS = pathlib.Path(tempfile.mkdtemp()) / "receipts.json"
core.RECEIPTS.write_text("{not json")
core.send_email = lambda *a, **k: "sent"
broken = asyncio.run(core.build_action(Account(service="Ledger", domain="ledger.com"), "Asha", "a@b.c", True))
assert broken.sent and broken.receipt, broken
print("Receipt failure is safe OK")
