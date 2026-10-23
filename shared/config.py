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
