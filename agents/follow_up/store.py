import json
from pathlib import Path

STORE = Path(__file__).resolve().parents[2] / "data" / "followups.json"


def load():
    if not STORE.exists():
        return {}
    try:
        return json.loads(STORE.read_text() or "{}")
    except ValueError:
        return {}


def save(tasks):
    STORE.write_text(json.dumps(tasks, indent=2))
