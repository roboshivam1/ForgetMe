#!/usr/bin/env bash
set -e

echo "ForgetMe batch 1: scaffold and contract"

mkdir -p shared scripts data agents/orchestrator agents/breach_scout agents/risk_ranker agents/eraser agents/follow_up agents/account_finder
touch shared/__init__.py scripts/__init__.py agents/__init__.py agents/orchestrator/__init__.py agents/breach_scout/__init__.py agents/risk_ranker/__init__.py agents/eraser/__init__.py agents/follow_up/__init__.py agents/account_finder/__init__.py

cat > requirements.txt << 'EOF'
uagents==0.25.5
openai
python-dotenv
requests
EOF

cat > .gitignore << 'EOF'
.venv/
.env
__pycache__/
*.pyc
*_data.json
data/followups.json
EOF

cat > .env.example << 'EOF'
ASI1_API_KEY=
ASI1_MODEL=asi1
HIBP_API_KEY=
USER_DISPLAY_NAME=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
EMAIL_DRY_RUN=true
SEED_ORCHESTRATOR=
SEED_BREACH_SCOUT=
SEED_RISK_RANKER=
SEED_ERASER=
SEED_FOLLOW_UP=
SEED_ACCOUNT_FINDER=
EOF

cat > scripts/init_env.py << 'EOF'
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
EOF

cat > shared/config.py << 'EOF'
import os
from dotenv import load_dotenv

try:
    from uagents_core.identity import Identity
except ImportError:
    from uagents.crypto import Identity

load_dotenv()

AGENTS = {
    "orchestrator": ("SEED_ORCHESTRATOR", 8001),
    "breach_scout": ("SEED_BREACH_SCOUT", 8002),
    "risk_ranker": ("SEED_RISK_RANKER", 8003),
    "eraser": ("SEED_ERASER", 8004),
    "follow_up": ("SEED_FOLLOW_UP", 8005),
    "account_finder": ("SEED_ACCOUNT_FINDER", 8006),
}


def env(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"{name} is missing. Add it to .env")
    return value


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def seed_for(key):
    return env(AGENTS[key][0], required=True)


def port_for(key):
    return AGENTS[key][1]


def address_for(key):
    return Identity.from_seed(seed_for(key), 0).address
EOF

cat > shared/models.py << 'EOF'
from typing import List, Optional
from uagents import Model


class Breach(Model):
    name: str
    domain: str = ""
    breach_date: str = ""
    data_classes: List[str] = []
    pwn_count: int = 0
    is_sensitive: bool = False


class ScanRequest(Model):
    request_id: str
    email: str


class BreachReport(Model):
    request_id: str
    email: str
    breaches: List[Breach] = []
    error: Optional[str] = None


class Account(Model):
    service: str
    domain: str = ""
    source: str = "breach"
    breach: Optional[Breach] = None


class TriageRequest(Model):
    request_id: str
    accounts: List[Account]


class TriagedAccount(Model):
    service: str
    domain: str = ""
    verdict: str
    reason: str
    score: int = 0


class TriageResult(Model):
    request_id: str
    items: List[TriagedAccount] = []
    error: Optional[str] = None


class EraseRequest(Model):
    request_id: str
    user_name: str
    user_email: str
    accounts: List[TriagedAccount]
    send: bool = False


class EraseAction(Model):
    service: str
    domain: str = ""
    method: str = "unknown"
    deletion_url: str = ""
    privacy_email: str = ""
    difficulty: str = ""
    note: str = ""
    letter: str = ""
    sent: bool = False
    error: str = ""


class EraseResult(Model):
    request_id: str
    actions: List[EraseAction] = []
    error: Optional[str] = None


class FollowUpTask(Model):
    request_id: str
    user_email: str
    user_name: str
    service: str
    contact: str
    sent_on: str
    due_on: str


class FollowUpAck(Model):
    request_id: str
    tracked: int
EOF

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m scripts.init_env

echo "Batch 1 done. Next: fill ASI1_API_KEY and HIBP_API_KEY in .env, then run batch 2."
