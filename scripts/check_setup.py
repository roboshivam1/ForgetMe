import requests
from shared.config import AGENTS, address_for, env
from shared.asi1 import ask

print("Agent addresses (each must match that agent's startup log):")
for key in AGENTS:
    try:
        print(f"  {key:16} {address_for(key)}")
    except Exception as err:
        print(f"  {key:16} ERROR {err}")

print("\nASI1:")
try:
    print("  OK:", ask("Reply with one word only.", "Say ready.", max_tokens=200))
except Exception as err:
    print("  FAILED:", err)

print("\nHIBP:")
key = env("HIBP_API_KEY") or "0" * 32
try:
    r = requests.get(
        "https://haveibeenpwned.com/api/v3/breachedaccount/multiple-breaches@hibp-integration-tests.com",
        headers={"hibp-api-key": key, "user-agent": "forgetme-hackathon"},
        params={"truncateResponse": "false"},
        timeout=15,
    )
    print("  status", r.status_code, "| breaches:", [b["Name"] for b in r.json()] if r.ok else r.text[:120])
except Exception as err:
    print("  FAILED:", err)
