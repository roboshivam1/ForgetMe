import os
import sys
import time

from uagents import Agent

from shared.agentkit import new_id
from shared.config import address_for
from shared.models import BreachReport, ScanRequest

email = sys.argv[1] if len(sys.argv) > 1 else "multiple-breaches@hibp-integration-tests.com"
target = address_for("breach_scout")
TIMEOUT = 60
started = time.time()

client = Agent(
    name="ping-client",
    seed="forgetme-ping-client-seed",
    port=8099,
    mailbox=True,
)


@client.on_event("startup")
async def send_request(ctx):
    ctx.logger.info(f"Asking Breach Scout {target} about {email}")
    await ctx.send(target, ScanRequest(request_id=new_id(), email=email))


@client.on_message(model=BreachReport)
async def got_report(ctx, sender, msg):
    if msg.error:
        print("\nScout replied with an error:", msg.error)
    else:
        print(f"\nScout replied: {len(msg.breaches)} breaches")
        for b in msg.breaches:
            print(f"  {b.breach_date or '?':10}  {b.name:24} {', '.join(b.data_classes[:3])}")
    os._exit(0)


@client.on_interval(period=5.0)
async def give_up(ctx):
    if time.time() - started > TIMEOUT:
        print(f"\nNo reply in {TIMEOUT} seconds. Is the scout running with its mailbox connected?")
        os._exit(1)


if __name__ == "__main__":
    client.run()
