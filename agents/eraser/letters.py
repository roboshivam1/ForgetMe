from datetime import date, timedelta
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "data" / "letters" / "deletion_request.txt"
RESPONSE_DAYS = 30


def deadline_from(start=None):
    return (start or date.today()) + timedelta(days=RESPONSE_DAYS)


def render_letter(service, user_name, user_email):
    today = date.today()
    text = TEMPLATE.read_text().format(
        service=service,
        user_name=user_name or "",
        user_email=user_email,
        date=today.strftime("%d %B %Y"),
        deadline=deadline_from(today).strftime("%d %B %Y"),
    )
    first, _, body = text.partition("\n")
    if first.lower().startswith("subject:"):
        return first[len("subject:"):].strip(), body.strip()
    return f"Request to delete my personal data ({service})", text.strip()
