from datetime import datetime

from agents.follow_up.store import load

tasks = load()
if not tasks:
    print("No deletion requests are being tracked yet.")
for task in tasks.values():
    due = datetime.fromtimestamp(task.get("due_at", 0)).strftime("%d %b %H:%M")
    print(f"{task['service']:22} {task['contact']:32} sent {task['sent_on']}  due {due}  {task['status']}")
