from agents.risk_ranker.ranker import triage
from shared.agentkit import make_agent
from shared.models import TriageRequest, TriageResult

agent = make_agent("risk_ranker", "forgetme-risk-ranker")


@agent.on_event("startup")
async def started(ctx):
    ctx.logger.info(f"Risk Ranker ready at {agent.address}")


@agent.on_message(model=TriageRequest)
async def on_triage(ctx, sender, msg):
    ctx.logger.info(f"Triage {msg.request_id}: {len(msg.accounts)} accounts")
    try:
        items = await triage(msg.accounts)
        result = TriageResult(request_id=msg.request_id, items=items)
        counts = {v: sum(1 for i in items if i.verdict == v) for v in ("delete", "secure", "keep")}
        ctx.logger.info(f"Triage {msg.request_id} done: {counts}")
    except Exception as err:
        ctx.logger.exception(f"Triage {msg.request_id} crashed: {err}")
        result = TriageResult(
            request_id=msg.request_id,
            error="Something went wrong while ranking your accounts. Please try again.",
        )
    await ctx.send(sender, result)


if __name__ == "__main__":
    agent.run()
