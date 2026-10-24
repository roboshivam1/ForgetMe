from agents.orchestrator import payments

if not payments.enabled():
    print("Stripe keys missing: set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY in .env")
    raise SystemExit(1)
if not str(payments.env("STRIPE_SECRET_KEY")).startswith("sk_test_"):
    print("Refusing: STRIPE_SECRET_KEY must be a test key (sk_test_...)")
    raise SystemExit(1)

checkout = payments.create_checkout("agent1qcheck")
print("Checkout session created:", checkout["checkout_session_id"])
print("Paid yet?", payments.is_paid(checkout["checkout_session_id"]))
print("Stripe test mode works.")
