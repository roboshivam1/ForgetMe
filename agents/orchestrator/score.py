"""Privacy score: 100 is clean, lower means more exposure.

Each account costs points based on its risk score from the Risk Ranker,
weighted by verdict. The projected score assumes every delete-verdict account
is removed and every secure-verdict account has been secured; it is a
projection once companies confirm, never a claim that data is already gone.
"""

WEIGHTS = {"delete": 0.25, "secure": 0.15, "keep": 0.05}
FLOOR = 5


def _points(item):
    try:
        return max(0, min(100, int(item.get("score") or 0)))
    except (TypeError, ValueError):
        return 0


def privacy_score(items, removed=(), secured=False):
    removed = set(removed)
    penalty = 0.0
    for index, item in enumerate(items):
        if index in removed:
            continue
        verdict = item.get("verdict", "keep")
        if secured and verdict == "secure":
            verdict = "keep"
        penalty += _points(item) * WEIGHTS.get(verdict, WEIGHTS["keep"])
    return int(max(FLOOR, min(100, round(100 - penalty))))


def projected_score(items):
    removed = [i for i, item in enumerate(items) if item.get("verdict") == "delete"]
    return privacy_score(items, removed=removed, secured=True)


def grade(score):
    if score >= 80:
        return "Good", "success"
    if score >= 50:
        return "At risk", "info"
    return "Exposed", "warning"


def score_line(score, projected):
    label, _ = grade(score)
    line = f"🛡️ Privacy score: **{score}/100** ({label.lower()})."
    if projected > score:
        line += f" Delete the 🔴 accounts and secure the 🟡 ones to reach about **{projected}/100**."
    return line


def done_line(current, projected):
    if projected > current:
        return f"🛡️ Once companies confirm, your privacy score should rise from **{current}** to about **{projected}/100**."
    return ""
