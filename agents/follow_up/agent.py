import asyncio
import time
from datetime import date, datetime
from pathlib import Path

from agents.eraser.mailer import MailError, send_email
from agents.follow_up.store import load, save
from agents.orchestrator.state import to_dict
from shared.agentkit import make_agent
from shared.config import env
from shared.models import FollowUpAck, FollowUpTask

TEMPLATE = Path(__file__).resolve().parents[2] / "data" / "letters" / "escalation.txt"

agent = make_agent("follow_up", "forgetme-follow-up")


def due_timestamp(due_on):
    demo = int(env("FOLLOWUP_DEMO_SECONDS", "0") or 0)
    if demo > 0:
        return time.time() + demo
    try:
        return datetime.fromisoformat(due_on).timestamp()
    except ValueError:
        return time.time() + 30 * 86400


def render(task):
    text = TEMPLATE.read_text().format(
        service=task["service"],
        sent_on=task["sent_on"],
        user_email=task["user_email"],
        user_name=task.get("user_name") or "",
        date=date.today().strftime("%d %B %Y"),
    )
    first, _, body = text.partition("\n")
    return first[len("Subject:"):].strip(), body.strip()


@agent.on_event("startup")
async def started(ctx):
    waiting = sum(1 for t in load().values() if t.get("status") == "waiting")
    ctx.logger.info(f"Follow-up ready at {agent.address}, tracking {waiting} open requests")


@agent.on_message(model=FollowUpTask)
async def on_task(ctx, sender, msg):
    tasks = load()
    task = to_dict(msg)
    task.update(due_at=due_timestamp(msg.due_on), status="waiting")
    tasks[f"{msg.request_id}:{msg.service}"] = task
    save(tasks)
    tracked = sum(1 for k in tasks if k.startswith(f"{msg.request_id}:"))
    ctx.logger.info(f"Tracking {msg.service}, due {msg.due_on}")
    await ctx.send(sender, FollowUpAck(request_id=msg.request_id, tracked=tracked))


@agent.on_interval(period=30.0)
async def check_due(ctx):
    tasks = load()
    now = time.time()
    changed = False
    for task in tasks.values():
        if task.get("status") != "waiting" or now < task.get("due_at", now + 1):
            continue
        subject, body = render(task)
        try:
            outcome = await asyncio.to_thread(send_email, task["contact"], subject, body, task["user_email"])
            task["status"] = "escalated" if outcome in ("sent", "redirected") else "escalation_dry_run"
        except MailError as err:
            task["status"] = "escalation_failed"
            task["error"] = str(err)
        task["escalated_on"] = date.today().isoformat()
        changed = True
        ctx.logger.info(f"Escalated {task['service']}: {task['status']}")
    if changed:
        save(tasks)


if __name__ == "__main__":
    agent.run()
