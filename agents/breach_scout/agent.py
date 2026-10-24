import asyncio

from agents.breach_scout.hibp import HibpError, fetch_breaches, mask, valid_email
from shared.agentkit import make_agent
from shared.models import BreachReport, ScanRequest

agent = make_agent("breach_scout", "forgetme-breach-scout")


@agent.on_event("startup")
async def started(ctx):
    ctx.logger.info(f"Breach Scout ready at {agent.address}")


@agent.on_message(model=ScanRequest)
async def on_scan(ctx, sender, msg):
    ctx.logger.info(f"Scan {msg.request_id} for {mask(msg.email)}")

    if not valid_email(msg.email):
        await ctx.send(
            sender,
            BreachReport(
                request_id=msg.request_id,
                email=msg.email,
                error="That doesn't look like a valid email address.",
            ),
        )
        return

    try:
        breaches = await asyncio.to_thread(fetch_breaches, msg.email)
        report = BreachReport(request_id=msg.request_id, email=msg.email, breaches=breaches)
        ctx.logger.info(f"Scan {msg.request_id}: {len(breaches)} breaches")
    except HibpError as err:
        ctx.logger.warning(f"Scan {msg.request_id} failed: {err}")
        report = BreachReport(request_id=msg.request_id, email=msg.email, error=str(err))
    except Exception as err:
        ctx.logger.exception(f"Scan {msg.request_id} crashed: {err}")
        report = BreachReport(
            request_id=msg.request_id,
            email=msg.email,
            error="Something went wrong while checking breaches. Please try again.",
        )

    await ctx.send(sender, report)


if __name__ == "__main__":
    agent.run()
