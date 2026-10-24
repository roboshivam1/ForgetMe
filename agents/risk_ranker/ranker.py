import asyncio
import json
import logging

from agents.risk_ranker.rules import CRYPTO_NOTE, fallback_reason, is_crypto, score_account, verdict_for
from shared.asi1 import aask_json
from shared.models import TriagedAccount

log = logging.getLogger("risk_ranker")

MAX_ACCOUNTS = 60
CHUNK = 20

SYSTEM = (
    "You are a privacy analyst reviewing a person's online accounts. "
    'Return JSON shaped exactly like {"items":[{"service":"<same name as input>","category_risk":<integer 0-10>,"reason":"<max 18 words>"}]}. '
    "category_risk rates how sensitive the TYPE of service is: 0-2 games, newsletters, forums; "
    "3-5 shopping, social, media; 6-8 email, cloud storage, jobs, education; 9-10 banking, health, government, dating. "
    "reason explains the exposure only, in plain English, strictly from the data given (what leaked and when). "
    "Never recommend actions. Never invent facts. If there is no breach, say what kind of service it is and why it matters."
)


def _compact(account):
    item = {"service": account.service, "domain": account.domain, "source": account.source}
    breach = account.breach
    if breach:
        item["breach_year"] = (breach.breach_date or "")[:4]
        item["leaked"] = breach.data_classes[:8]
    return item


async def _enrich_chunk(chunk):
    data = await aask_json(SYSTEM, json.dumps([_compact(a) for a in chunk]))
    rows = data.get("items", []) if isinstance(data, dict) else data
    found = {}
    for row in rows:
        name = str(row.get("service", "")).strip().lower()
        if not name:
            continue
        try:
            risk = max(0, min(10, int(row.get("category_risk", 0))))
        except (TypeError, ValueError):
            risk = 0
        found[name] = {"category_risk": risk, "reason": str(row.get("reason", "")).strip()[:160]}
    return found


async def enrich(accounts):
    chunks = [accounts[i:i + CHUNK] for i in range(0, len(accounts), CHUNK)]
    results = await asyncio.gather(*(_enrich_chunk(c) for c in chunks), return_exceptions=True)
    merged = {}
    for result in results:
        if isinstance(result, Exception):
            log.warning("ASI1 enrichment failed for a chunk: %s", result)
            continue
        merged.update(result)
    return merged


async def triage(accounts):
    accounts = list(accounts)[:MAX_ACCOUNTS]
    if not accounts:
        return []

    insights = await enrich(accounts)
    items = []
    for account in accounts:
        info = insights.get(account.service.strip().lower(), {})
        score, years, high_impact = score_account(account, info.get("category_risk", 0))
        reason = info.get("reason") or fallback_reason(account)
        if is_crypto(account):
            reason = f"{reason} {CRYPTO_NOTE}"
        items.append(
            TriagedAccount(
                service=account.service,
                domain=account.domain,
                verdict=verdict_for(score, years, high_impact),
                reason=reason,
                score=score,
            )
        )
    items.sort(key=lambda i: i.score, reverse=True)
    return items
