import asyncio

from agents.orchestrator import views
from agents.orchestrator.intent import classify

breaches = [
    {"name": "LinkedIn", "breach_date": "2012-05-05", "data_classes": ["Email addresses", "Passwords"]},
    {"name": "Canva", "breach_date": "2019-05-24", "data_classes": ["Email addresses", "Passwords"]},
    {"name": "Spotify", "breach_date": "2020-11-01", "data_classes": ["Email addresses"]},
]
items = [
    {"service": "LinkedIn", "verdict": "delete", "reason": "Passwords leaked in 2012.", "score": 85},
    {"service": "Canva", "verdict": "delete", "reason": "Passwords and usernames leaked in 2019.", "score": 75},
    {"service": "Spotify", "verdict": "secure", "reason": "Only your email leaked in 2020.", "score": 40},
]
actions = [
    {"service": "LinkedIn", "method": "link", "deletion_url": "https://example.com/delete", "difficulty": "easy"},
    {"service": "Canva", "method": "email", "privacy_email": "privacy@example.com", "letter": "Subject: x"},
]

print(views.triage_report("you@example.com", breaches, items))
print("\n" + "-" * 60 + "\n")
print(views.erase_plan(actions, "Test User"))
print("\n" + "-" * 60 + "\n")

phrases = [
    ("idle", "check me@example.com please"),
    ("triaged", "delete all"),
    ("triaged", "delete 1 and 3"),
    ("triaged", "how do I protect the yellow ones?"),
    ("confirm", "send - Shivam Kapoor"),
    ("confirm", "yes"),
    ("idle", "what does GDPR article 17 mean?"),
]


async def main():
    for state, text in phrases:
        result = await classify(text, state, len(items))
        print(f"[{state:8}] {text!r:40} -> {result}")


asyncio.run(main())
