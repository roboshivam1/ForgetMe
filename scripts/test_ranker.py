import asyncio

from agents.risk_ranker.ranker import triage
from scripts.sample_data import SAMPLE_ACCOUNTS

items = asyncio.run(triage(SAMPLE_ACCOUNTS))

print(f"\n{'VERDICT':8} {'SCORE':5}  {'SERVICE':12} REASON")
for item in items:
    print(f"{item.verdict.upper():8} {item.score:<5}  {item.service:12} {item.reason}")
