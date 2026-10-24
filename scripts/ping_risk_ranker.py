import os

from uagents import Agent

from scripts.sample_data import SAMPLE_ACCOUNTS
from shared.agentkit import new_id
from shared.config import address_for
from shared.models import TriageRequest, TriageResult

target = address_for("risk_ranker")

client = Agent(
    name="ping-ranker-client",
    seed="forgetme-ping-ranker-client-seed",
    port=8098,
    endpoint=["http://127.0.0.1:8098/submit"],
)


@client.on_event("startup")
async def send_request(ctx):
    ctx.logger.info(f"Asking Risk Ranker {target} to triage {len(SAMPLE_ACCOUNTS)} sample accounts")
    await ctx.send(target, TriageRequest(request_id=new_id(), accounts=SAMPLE_ACCOUNTS))


@client.on_message(model=TriageResult)
async def got_result(ctx, sender, msg):
    if msg.error:
        print("\nRanker replied with an error:", msg.error)
    else:
        print(f"\n{'VERDICT':8} {'SCORE':5}  {'SERVICE':12} REASON")
        for item in msg.items:
            print(f"{item.verdict.upper():8} {item.score:<5}  {item.service:12} {item.reason}")
    os._exit(0)


@client.on_interval(period=60.0)
async def give_up(ctx):
    print("\nNo reply in 60 seconds. Is the ranker running with its mailbox connected?")
    os._exit(1)


if __name__ == "__main__":
    client.run()
