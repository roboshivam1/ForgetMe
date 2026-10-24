import json
import re
from pathlib import Path

DIRECTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "directory.json"
_cache = {"mtime": None, "entries": []}


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _norm_domain(domain):
    domain = (domain or "").lower().strip()
    domain = re.sub(r"^https?://", "", domain).split("/")[0]
    return domain[4:] if domain.startswith("www.") else domain


def load_directory():
    if not DIRECTORY_PATH.exists():
        return []
    mtime = DIRECTORY_PATH.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache["entries"] = json.loads(DIRECTORY_PATH.read_text() or "[]")
        _cache["mtime"] = mtime
    return _cache["entries"]


def lookup(service, domain=""):
    entries = load_directory()
    wanted_domain = _norm_domain(domain)
    if wanted_domain:
        for entry in entries:
            if _norm_domain(entry.get("domain")) == wanted_domain:
                return entry
    wanted = _norm(service)
    if wanted:
        for entry in entries:
            if wanted in (_norm(entry.get("hibp_name")), _norm(entry.get("service"))):
                return entry
    return None
