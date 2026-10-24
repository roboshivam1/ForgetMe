"""Stripe checkout for the ForgetMe Concierge upgrade (test mode keys only).

The Agent Payment Protocol carries the request; Stripe is the payment rail.
RequestPayment.metadata["stripe"] holds the embedded checkout details so a
compatible UI (the Agentverse inspector chat) can render the card form.
"""
import time

from shared.config import env

RETURN_URL = "https://agentverse.ai/payment-success?session_id={CHECKOUT_SESSION_ID}"


def price_cents():
    try:
        return int(env("CONCIERGE_PRICE_CENTS", "100") or 100)
    except ValueError:
        return 100


def currency():
    return (env("CONCIERGE_CURRENCY", "usd") or "usd").lower()


def price_text():
    return f"{price_cents() / 100:.2f} {currency().upper()}"


def enabled():
    return bool(env("STRIPE_SECRET_KEY") and env("STRIPE_PUBLISHABLE_KEY"))


def _stripe():
    import stripe

    stripe.api_key = env("STRIPE_SECRET_KEY", required=True)
    return stripe


def create_checkout(user_address):
    session = _stripe().checkout.Session.create(
        ui_mode="embedded_page",
        redirect_on_completion="if_required",
        mode="payment",
        return_url=RETURN_URL,
        expires_at=int(time.time()) + 31 * 60,
        line_items=[{
            "price_data": {
                "currency": currency(),
                "product_data": {
                    "name": "ForgetMe Concierge",
                    "description": "ForgetMe keeps chasing every company until they confirm your data is deleted.",
                },
                "unit_amount": price_cents(),
            },
            "quantity": 1,
        }],
        metadata={"user_address": user_address, "service": "forgetme_concierge"},
    )
    return {
        "ui_mode": "embedded",
        "publishable_key": env("STRIPE_PUBLISHABLE_KEY"),
        "client_secret": session.client_secret,
        "checkout_session_id": session.id,
        "currency": currency(),
        "amount_cents": str(price_cents()),
    }


def is_paid(checkout_session_id):
    session = _stripe().checkout.Session.retrieve(checkout_session_id)
    return getattr(session, "payment_status", None) == "paid"
