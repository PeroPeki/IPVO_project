"""
Celery zadatci — NightClub Manager v2.

- generate_daily_report: dnevni agregat po klubu (Mongo aggregation pipeline)
- send_reservation_reminders: podsjetnici dan prije eventa
- expire_stale_payments: oslobađa neplaćene pending rezervacije i karte

Konekcija na Mongo ide kroz db.py (MONGO_URI iz okoline), a real-time
obavijesti kroz realtime.publish (Redis message queue) — worker tako može
emitirati Socket.IO evente iako ne poslužuje klijente.
"""

from datetime import datetime, timedelta

from celery import Celery

from db import (
    clubs_col,
    drink_orders_col,
    events_col,
    reports_col,
    table_reservations_col,
    tickets_col,
    users_col,
)
# Svi importi moraju biti na razini modula: Celery nakon starta makne radni
# direktorij sa sys.path (security kad worker vrti root), pa import unutar
# taska podigne ModuleNotFoundError
from email_service import send_reservation_reminder
from realtime import publish
from reservation_service import PENDING_DEPOSIT_TTL_MINUTES

app = Celery('tasks')
app.config_from_object('celery_config')


def _sum_and_count(col, match, field):
    res = list(col.aggregate([
        {"$match": match},
        {"$group": {"_id": None, "total": {"$sum": f"${field}"}, "count": {"$sum": 1}}},
    ]))
    if not res:
        return 0.0, 0
    return round(res[0]["total"] or 0, 2), res[0]["count"]


@app.task
def generate_daily_report():
    """Dnevni izvještaj po klubu — karte, rezervacije, narudžbe i prihodi."""
    yesterday = datetime.utcnow() - timedelta(days=1)

    for club in clubs_col.find({"is_active": True}):
        cid = club["_id"]

        revenue_tickets, tickets_sold = _sum_and_count(tickets_col, {
            "club_id": cid,
            "purchased_at": {"$gte": yesterday},
            "status": {"$in": ["valid", "checked_in"]},
        }, "price_paid")

        revenue_drinks, drink_orders = _sum_and_count(drink_orders_col, {
            "club_id": cid,
            "created_at": {"$gte": yesterday},
            "payment_status": "paid",
        }, "total")

        revenue_deposits, _ = _sum_and_count(table_reservations_col, {
            "club_id": cid,
            "created_at": {"$gte": yesterday},
            "deposit_paid": True,
        }, "deposit_amount")

        reports_col.insert_one({
            "club_id": cid,
            "date": datetime.utcnow(),
            "type": "DAILY_STATS",
            "metrics": {
                "total_tickets_sold": tickets_sold,
                "total_reservations": table_reservations_col.count_documents({
                    "club_id": cid,
                    "created_at": {"$gte": yesterday},
                }),
                "total_drink_orders": drink_orders,
                "revenue_tickets": revenue_tickets,
                "revenue_drinks": revenue_drinks,
                "revenue_deposits": revenue_deposits,
                "total_revenue": round(
                    revenue_tickets + revenue_drinks + revenue_deposits, 2
                ),
            }
        })
        print(f"[report] Dnevni izvještaj spremljen za klub {club.get('name')}")


@app.task
def send_reservation_reminders():
    """Pošalji podsjetnike za rezervacije čiji event počinje za ~24h."""
    now = datetime.utcnow()
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    reservations = table_reservations_col.find({
        "status": "confirmed",
        "reminder_sent": False
    })
    sent = 0
    for r in reservations:
        event = events_col.find_one({"_id": r["event_id"]})
        if event and window_start <= event["date"] <= window_end:
            user = users_col.find_one({"_id": r["user_id"]})
            if user:
                send_reservation_reminder(r, event, user)
            table_reservations_col.update_one(
                {"_id": r["_id"]},
                {"$set": {"reminder_sent": True}}
            )
            sent += 1
    if sent:
        print(f"[reminders] Poslano {sent} podsjetnika.")


@app.task
def expire_stale_payments():
    """
    Oslobađa resurse koje drže neplaćeni Stripe flowovi:
    - pending VIP rezervacije bez depozita → stol se vraća u prodaju
    - pending karte → kvota (sold_quantity) se vraća

    Zakašnjeli webhook nakon isteka rješava se u payments.py /
    reservation_service.py (revive ili automatski refund).
    """
    cutoff = datetime.utcnow() - timedelta(minutes=PENDING_DEPOSIT_TTL_MINUTES)
    freed_tables = 0
    freed_tickets = 0

    for r in table_reservations_col.find({
        "status": "pending",
        "deposit_paid": False,
        "created_at": {"$lt": cutoff},
    }):
        result = table_reservations_col.update_one(
            {"_id": r["_id"], "status": "pending"},
            {"$set": {
                "status": "cancelled",
                "active_hold": False,
                "cancelled_at": datetime.utcnow(),
                "cancel_reason": "deposit_timeout",
            }},
        )
        if result.modified_count:
            freed_tables += 1
            publish('table_updates', {
                "event_id": str(r["event_id"]),
                "table_id": r["table_id"],
                "status": "free",
            })

    for t in tickets_col.find({
        "status": "pending",
        "purchased_at": {"$lt": cutoff},
    }):
        result = tickets_col.update_one(
            {"_id": t["_id"], "status": "pending"},
            {"$set": {"status": "expired"}},
        )
        if result.modified_count:
            freed_tickets += 1
            events_col.update_one(
                {"_id": t["event_id"]},
                {"$inc": {"ticket_types.$[tt].sold_quantity": -1}},
                array_filters=[{"tt.id": t["ticket_type_id"]}],
            )

    if freed_tables or freed_tickets:
        print(f"[expiry] Oslobođeno {freed_tables} stolova i {freed_tickets} karata.")
