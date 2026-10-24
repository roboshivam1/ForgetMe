from agents.eraser.core import build_action
from shared.agentkit import make_agent
from shared.models import EraseAction, EraseRequest, EraseResult

agent = make_agent("eraser", "forgetme-eraser")


@agent.on_event("startup")
async def started(ctx):
    ctx.logger.info(f"Eraser ready at {agent.address}")


@agent.on_message(model=EraseRequest)
async def on_erase(ctx, sender, msg):
    ctx.logger.info(f"Erase {msg.request_id}: {len(msg.accounts)} accounts, send={msg.send}")
    actions = []
    for account in msg.accounts:
        try:
            actions.append(await build_action(account, msg.user_name, msg.user_email, msg.send))
        except Exception as err:
            ctx.logger.exception(f"Erase {msg.request_id} failed on {account.service}: {err}")
            actions.append(EraseAction(service=account.service, domain=account.domain,
                                       error="Couldn't prepare this one. Please try again."))
    sent = sum(1 for a in actions if a.sent)
    ctx.logger.info(f"Erase {msg.request_id} done: {len(actions)} actions, {sent} emails sent")
    await ctx.send(sender, EraseResult(request_id=msg.request_id, actions=actions))


if __name__ == "__main__":
    agent.run()
