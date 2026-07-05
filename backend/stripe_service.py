"""
Stripe integracija — PaymentIntenti za karte, VIP depozite i narudžbe pića.

Sve funkcije vraćaju cijeli PaymentIntent objekt; pozivatelj koristi
`intent.client_secret` (za mobilni Payment Sheet) i `intent.id` (za praćenje).
"""

import os

import stripe

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')


def create_ticket_payment_intent(amount_eur, user, event_id, ticket_type_id):
    intent = stripe.PaymentIntent.create(
        amount=int(round(amount_eur * 100)),
        currency="eur",
        customer=user.get("stripe_customer_id"),
        metadata={
            "type": "ticket_purchase",
            "event_id": str(event_id),
            "ticket_type_id": str(ticket_type_id),
            "user_id": str(user["_id"])
        },
        automatic_payment_methods={"enabled": True},
    )
    return intent


def create_deposit_payment_intent(amount_eur, user, reservation_id):
    intent = stripe.PaymentIntent.create(
        amount=int(round(amount_eur * 100)),
        currency="eur",
        customer=user.get("stripe_customer_id"),
        metadata={
            "type": "vip_deposit",
            "reservation_id": str(reservation_id),
            "user_id": str(user["_id"])
        },
        automatic_payment_methods={"enabled": True},
    )
    return intent


def create_drink_payment_intent(amount_eur, user, order_id):
    intent = stripe.PaymentIntent.create(
        amount=int(round(amount_eur * 100)),
        currency="eur",
        customer=user.get("stripe_customer_id"),
        metadata={
            "type": "drink_order",
            "order_id": str(order_id),
            "user_id": str(user["_id"])
        },
        automatic_payment_methods={"enabled": True},
    )
    return intent


def get_or_create_stripe_customer(user):
    if user.get("stripe_customer_id"):
        return user["stripe_customer_id"]
    customer = stripe.Customer.create(
        email=user.get("email"),
        name=user.get("name"),
        metadata={"user_id": str(user["_id"])}
    )
    return customer.id


def refund_payment_intent(payment_intent_id):
    return stripe.Refund.create(payment_intent=payment_intent_id)
