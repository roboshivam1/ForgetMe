import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
env_path = root / ".env"
if not env_path.exists():
    env_path.write_text((root / ".env.example").read_text())

lines = []
for line in env_path.read_text().splitlines():
    if line.startswith("SEED_") and line.endswith("="):
        line = line + "forgetme-" + secrets.token_hex(24)
    lines.append(line)
env_path.write_text("\n".join(lines) + "\n")
print("Seeds written to .env. Now add ASI1_API_KEY, HIBP_API_KEY and SMTP details.")
