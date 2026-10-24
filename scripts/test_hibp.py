import sys

from agents.breach_scout.hibp import HibpError, fetch_breaches

emails = sys.argv[1:] or ["multiple-breaches@hibp-integration-tests.com"]

for email in emails:
    print(f"\n{email}")
    try:
        breaches = fetch_breaches(email)
    except HibpError as err:
        print("  ERROR:", err)
        continue
    if not breaches:
        print("  no breaches found")
    for b in breaches:
        print(f"  {b.breach_date or '?':10}  {b.name:24} {b.domain:22} {', '.join(b.data_classes[:4])}")
    with_passwords = [b.name for b in breaches if "Passwords" in b.data_classes]
    print(f"  total {len(breaches)}, with passwords: {len(with_passwords)}")
