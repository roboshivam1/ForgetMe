import re
import time
from urllib.parse import quote

import requests

from shared.config import env
from shared.models import Breach

API = "https://haveibeenpwned.com/api/v3/breachedaccount/"
TEST_KEY = "0" * 32
CACHE_TTL = 600
_cache = {}


class HibpError(Exception):
    pass


def valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()))


def mask(email):
    local, _, domain = (email or "").partition("@")
    return f"{local[:2]}***@{domain}"


def _retry_after(response):
    try:
        return min(int(response.headers.get("Retry-After", "2")), 8)
    except ValueError:
        return 2


def _request(email, key):
    for _ in range(3):
        try:
            response = requests.get(
                API + quote(email, safe=""),
                headers={"hibp-api-key": key, "user-agent": "forgetme-hackathon"},
                params={"truncateResponse": "false"},
                timeout=15,
            )
        except requests.RequestException as err:
            raise HibpError("Couldn't reach the breach database. Check the connection and try again.") from err
        if response.status_code == 429:
            time.sleep(_retry_after(response))
            continue
        return response
    raise HibpError("The breach database is rate-limiting us. Try again in a minute.")


def _to_breach(item):
    return Breach(
        name=item.get("Title") or item.get("Name") or "Unknown",
        domain=item.get("Domain") or "",
        breach_date=item.get("BreachDate") or "",
        data_classes=list(item.get("DataClasses") or []),
        pwn_count=int(item.get("PwnCount") or 0),
        is_sensitive=bool(item.get("IsSensitive", False)),
    )


def fetch_breaches(email):
    email = email.strip().lower()
    cached = _cache.get(email)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]

    key = env("HIBP_API_KEY") or TEST_KEY
    response = _request(email, key)

    if response.status_code == 404:
        breaches = []
    elif response.status_code in (401, 403):
        raise HibpError("Breach lookup was not authorised. Check the HIBP API key in .env.")
    elif response.status_code == 400:
        raise HibpError("That email address was rejected by the breach database.")
    elif response.status_code != 200:
        raise HibpError(f"The breach database returned an unexpected error ({response.status_code}).")
    else:
        items = response.json()
        keep = [i for i in items if not i.get("IsSpamList") and not i.get("IsStealerLog")]
        breaches = sorted((_to_breach(i) for i in keep), key=lambda b: b.breach_date or "9999")

    _cache[email] = (time.time(), breaches)
    return breaches
