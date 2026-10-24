import asyncio

from agents.eraser.core import build_action
from agents.eraser.directory import load_directory
from shared.models import TriagedAccount

entries = load_directory()
print(f"Directory has {len(entries)} services")

accounts = [TriagedAccount(service=e["service"], domain=e.get("domain", ""), verdict="delete", reason="test")
            for e in entries[:3]]
accounts.append(TriagedAccount(service="Some Unknown Site", domain="unknown-site.example", verdict="delete", reason="test"))


async def main():
    for account in accounts:
        action = await build_action(account, "Test User", "test@example.com", send=False)
        print(f"\n{action.service}: method={action.method} difficulty={action.difficulty or '-'}")
        if action.deletion_url:
            print("  link:", action.deletion_url)
        if action.privacy_email:
            print("  email:", action.privacy_email)
        if action.note:
            print("  note:", action.note)
        if action.letter:
            print("  letter:", action.letter.splitlines()[0])


asyncio.run(main())
