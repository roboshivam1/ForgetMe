from datetime import date

from shared.models import Account

PASSWORD = {"passwords", "password hints", "auth tokens", "security questions and answers"}
FINANCIAL = {
    "credit cards", "credit card cvv", "partial credit card data", "bank account numbers",
    "payment histories", "financial transactions", "government issued ids",
    "passport numbers", "social security numbers",
}
PERSONAL = {
    "physical addresses", "phone numbers", "dates of birth", "private messages", "chat logs",
    "photos", "browser search histories", "purchases", "medical conditions",
    "health insurance information", "sexual orientations", "sexual preferences",
}

DELETE_AT = 60
SECURE_AT = 35


def years_since(breach_date):
    try:
        parts = (breach_date or "").split("-")
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 6
        return (date.today() - date(year, month, 1)).days / 365.25
    except (ValueError, IndexError):
        return None


def score_account(account, category_risk=0):
    score = category_risk
    breach = account.breach
    if breach is None:
        return min(score, 100), None, False

    classes = {c.lower() for c in breach.data_classes}
    score += 30
    if classes & PASSWORD:
        score += 25
    if classes & FINANCIAL:
        score += 20
    if classes & PERSONAL:
        score += 10
    if breach.is_sensitive:
        score += 10

    years = years_since(breach.breach_date)
    if years is not None:
        if years >= 5:
            score += 15
        elif years >= 2:
            score += 5

    high_impact = bool(classes & FINANCIAL) or breach.is_sensitive
    return min(score, 100), years, high_impact


def verdict_for(score, years, high_impact):
    if score >= DELETE_AT:
        verdict = "delete"
    elif score >= SECURE_AT:
        verdict = "secure"
    else:
        verdict = "keep"
    if verdict == "delete" and years is not None and years < 2 and not high_impact:
        verdict = "secure"
    return verdict


def fallback_reason(account):
    breach = account.breach
    if breach is None:
        return "No known breach, but you have an account here."
    year = (breach.breach_date or "")[:4] or "an unknown year"
    leaked = ", ".join(breach.data_classes[:4]) or "account details"
    return f"Breached in {year}: {leaked} exposed."
