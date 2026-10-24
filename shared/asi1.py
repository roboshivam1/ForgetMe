import asyncio
import json
import re
import time
from openai import OpenAI
from shared.config import env

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(base_url="https://api.asi1.ai/v1", api_key=env("ASI1_API_KEY", required=True))
    return _client


def ask(system, user, max_tokens=1500, retries=2):
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = _get_client().chat.completions.create(
                model=env("ASI1_MODEL", "asi1"),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=0.2,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as err:
            last_error = err
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"ASI1 call failed: {last_error}")


def ask_json(system, user, max_tokens=2500):
    text = ask(system + "\nRespond with valid JSON only. No prose, no markdown fences.", user, max_tokens)
    match = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if not match:
        raise ValueError(f"ASI1 returned no JSON: {text[:200]}")
    return json.loads(match.group(1))


async def aask(system, user, max_tokens=1500):
    return await asyncio.to_thread(ask, system, user, max_tokens)


async def aask_json(system, user, max_tokens=2500):
    return await asyncio.to_thread(ask_json, system, user, max_tokens)
