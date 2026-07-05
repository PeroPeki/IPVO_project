"""
Email servis — potvrde kupnje i podsjetnici.

Koristi SendGrid ako je SENDGRID_API_KEY postavljen; u suprotnom samo
logira (dovoljno za lokalni razvoj bez vanjskih servisa).
"""

import os

import requests

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("EMAIL_FROM", "noreply@nightclub-manager.hr")


def _send(to_email, subject, body):
    if not to_email:
        return
    if not SENDGRID_API_KEY:
        print(f"[email] (dev-mode) Za: {to_email} | {subject}\n{body}")
        return
    try:
        requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}"},
            json={
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": FROM_EMAIL},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
            timeout=10,
        )
    except Exception as exc:
        print(f"[email] Greška pri slanju: {exc}")


def send_ticket_confirmation(ticket):
    from db import events_col, users_col
    user = users_col.find_one({"_id": ticket["user_id"]})
    event = events_col.find_one({"_id": ticket["event_id"]})
    if not user or not event:
        return
    _send(
        user.get("email"),
        f"Potvrda kupnje karte — {event['name']}",
        (
            f"Bok {user.get('name', '')},\n\n"
            f"tvoja karta za {event['name']} ({event['date']}) je potvrđena.\n"
            f"Tip karte: {ticket.get('ticket_type_name')}\n"
            f"QR kod: {ticket.get('qr_code')}\n\n"
            "Pokaži QR kod hostesi na ulazu. Vidimo se!"
        ),
    )


def send_reservation_reminder(reservation, event, user):
    _send(
        user.get("email"),
        f"Podsjetnik — sutra je {event['name']}",
        (
            f"Bok {user.get('name', '')},\n\n"
            f"podsjećamo te na rezervaciju stola {reservation.get('table_label')} "
            f"za event {event['name']} ({event['date']}).\n\n"
            "Vidimo se!"
        ),
    )
