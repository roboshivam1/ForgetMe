import re
import time
from urllib.parse import quote

import requests

from shared.config import env
from shared.models import Breach

HIBP = "https://haveibeenpwned.com/api/v3"
UA = {"user-agent": "forgetme-hackathon"}
CACHE_TTL = 600
MAX_DETAIL_LOOKUPS = 10
_cache = {}
_catalog = {"loaded": 0.0, "by_key": {}}


class HibpError(Exception):
    pass


def valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()))


def mask(email):
    local, _, domain = (email or "").partition("@")
    return f"{local[:2]}***@{domain}"


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _hibp_key():
    key = (env("HIBP_API_KEY") or "").strip()
    if re.fullmatch(r"[0-9a-fA-F]{32}", key) and set(key) != {"0"}:
        return key
    return ""


def _to_breach(item):
    return Breach(
        name=item.get("Title") or item.get("Name") or "Unknown",
        domain=item.get("Domain") or "",
        breach_date=item.get("BreachDate") or "",
        data_classes=list(item.get("DataClasses") or []),
        pwn_count=int(item.get("PwnCount") or 0),
        is_sensitive=bool(item.get("IsSensitive", False)),
    )


def _load_catalog():
    if _catalog["by_key"] and time.time() - _catalog["loaded"] < 6 * 3600:
        return _catalog["by_key"]
    try:
        response = requests.get(f"{HIBP}/breaches", headers=UA, timeout=20)
        response.raise_for_status()
        by_key = {}
        for item in response.json():
            for key in (item.get("Name"), item.get("Title")):
                if key:
                    by_key.setdefault(_norm(key), item)
        _catalog.update(loaded=time.time(), by_key=by_key)
    except (requests.RequestException, ValueError):
        pass
    return _catalog["by_key"]


def _hibp_lookup(email, key):
    for _ in range(3):
        try:
            response = requests.get(
                f"{HIBP}/breachedaccount/{quote(email, safe='')}",
                headers={**UA, "hibp-api-key": key},
                params={"truncateResponse": "false"},
                timeout=15,
            )
        except requests.RequestException as err:
            raise HibpError("Couldn't reach the breach database. Check the connection and try again.") from err
        if response.status_code == 429:
            time.sleep(min(int(response.headers.get("Retry-After", "2") or 2), 8))
            continue
        if response.status_code == 404:
            return []
        if response.status_code in (401, 403):
            raise HibpError("Breach lookup was not authorised. Check the HIBP API key in .env.")
        if response.status_code != 200:
            raise HibpError(f"The breach database returned an unexpected error ({response.status_code}).")
        items = [i for i in response.json() if not i.get("IsSpamList") and not i.get("IsStealerLog")]
        return [_to_breach(i) for i in items]
    raise HibpError("The breach database is rate-limiting us. Try again in a minute.")


def _flatten_names(raw):
    names = []
    for item in raw or []:
        if isinstance(item, (list, tuple)):
            names.extend(_flatten_names(item))
        elif isinstance(item, str):
            names.extend(p.strip() for p in re.split(r"[;,]", item) if p.strip())
        else:
            names.append(str(getattr(item, "breach_id", item)))
    return list(dict.fromkeys(names))


def _pick(row, *attrs):
    for attr in attrs:
        value = getattr(row, attr, None)
        if value is None and isinstance(row, dict):
            value = row.get(attr)
        if value:
            return value
    return None


def _xon_details(xon, name):
    try:
        rows = xon.get_breaches(breach_id=name)
    except Exception:
        return None
    if not rows:
        return None
    row = rows[0]
    data = _pick(row, "xposed_data", "exposed_data", "exposedData", "data_classes") or []
    if isinstance(data, str):
        data = [d.strip() for d in re.split(r"[;,]", data) if d.strip()]
    try:
        count = int(_pick(row, "xposed_records", "exposed_records", "exposedRecords") or 0)
    except (TypeError, ValueError):
        count = 0
    return Breach(
        name=name,
        domain=str(_pick(row, "domain") or ""),
        breach_date=str(_pick(row, "breached_date", "breach_date", "breachedDate") or "")[:10],
        data_classes=list(data),
        pwn_count=count,
    )


def _xon_lookup(email):
    try:
        from xposedornot import NotFoundError, RateLimitError, XposedOrNot
    except ImportError as err:
        raise HibpError("Breach lookup library is missing. Run: .venv/bin/pip install xposedornot") from err

    catalog = _load_catalog()
    try:
        with XposedOrNot() as xon:
            try:
                names = _flatten_names(getattr(xon.check_email(email), "breaches", []))
            except NotFoundError:
                return []
            breaches, lookups = [], 0
            for name in names:
                item = catalog.get(_norm(name))
                if item:
                    if not item.get("IsSpamList") and not item.get("IsStealerLog"):
                        breaches.append(_to_breach(item))
                    continue
                detail = None
                if lookups < MAX_DETAIL_LOOKUPS:
                    lookups += 1
                    detail = _xon_details(xon, name)
                breaches.append(detail or Breach(name=name))
            return breaches
    except RateLimitError as err:
        raise HibpError("The breach database is rate-limiting us. Try again in a minute.") from err
    except HibpError:
        raise
    except Exception as err:
        raise HibpError("Couldn't reach the breach database. Try again shortly.") from err


def fetch_breaches(email):
    email = email.strip().lower()
    cached = _cache.get(email)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]

    key = _hibp_key()
    breaches = _hibp_lookup(email, key) if key else _xon_lookup(email)
    breaches = sorted(breaches, key=lambda b: b.breach_date or "9999")

    _cache[email] = (time.time(), breaches)
    return breaches


def source_name():
    return "Have I Been Pwned" if _hibp_key() else "XposedOrNot, with breach details from Have I Been Pwned"
