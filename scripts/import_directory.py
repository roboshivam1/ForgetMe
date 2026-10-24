import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "directory.csv"
TARGET = ROOT / "data" / "directory.json"
FIELDS = ["service", "domain", "hibp_name", "method", "deletion_url", "privacy_email",
          "difficulty", "note", "source_url", "checked_on"]
METHODS = {"link", "email", "form", "app_only", "impossible"}
DIFFICULTY = {"easy", "medium", "hard", "impossible", ""}

entries, problems = [], []
with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
    for line_no, row in enumerate(csv.DictReader(handle), start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        entry = {field: row.get(field, "") for field in FIELDS}
        if not entry["service"]:
            continue
        entry["method"] = entry["method"].lower()
        entry["difficulty"] = entry["difficulty"].lower()
        if entry["method"] not in METHODS:
            problems.append(f"row {line_no} {entry['service']}: method '{entry['method']}' is not one of {sorted(METHODS)}")
        if entry["difficulty"] not in DIFFICULTY:
            problems.append(f"row {line_no} {entry['service']}: difficulty '{entry['difficulty']}' is unexpected")
        if not entry["domain"]:
            problems.append(f"row {line_no} {entry['service']}: missing domain (matching will be weaker)")
        if not entry["deletion_url"] and not entry["privacy_email"]:
            problems.append(f"row {line_no} {entry['service']}: no link and no email, so the agent can't act")
        entries.append(entry)

TARGET.write_text(json.dumps(entries, indent=2))
print(f"Imported {len(entries)} services into data/directory.json")
for problem in problems:
    print("  check:", problem)
