"""
Celery zadatci — NightClub Manager v2 (bez ML-a).

- generate_daily_report: dnevni agregat po klubu (karte, rezervacije, pića, prihod)
- send_reservation_reminders: podsjetnici dan prije eventa
"""

from datetime import datetime, timedelta

import pymongo
from celery import Celery

app = Celery('tasks')
app.config_from_object('celery_config')

MONGO_URI = "mongodb://mongo:27017"


@app.task
def generate_daily_report():
    """Dnevni izvještaj po klubu — karte, rezervacije, narudžbe i prihodi."""
    client = pymongo.MongoClient(MONGO_URI)
    db = client["mydb"]
    yesterday = datetime.utcnow() - timedelta(days=1)

    for club in db.clubs.find({"is_active": True}):
        cid = club["_id"]
        tickets = list(db.tickets.find({
            "club_id": cid,
            "purchased_at": {"$gte": yesterday},
            "status": {"$ne": "cancelled"}
        }))
        orders = list(db.drink_orders.find({
            "club_id": cid,
            "created_at": {"$gte": yesterday},
            "payment_status": "paid"
        }))
        deposits = list(db.table_reservations.find({
            "club_id": cid,
            "created_at": {"$gte": yesterday},
            "deposit_paid": True
        }))

        revenue_tickets = round(sum(t.get("price_paid", 0) for t in tickets), 2)
        revenue_drinks = round(sum(o.get("total", 0) for o in orders), 2)
        revenue_deposits = round(sum(r.get("deposit_amount", 0) for r in deposits), 2)

        db.reports.insert_one({
            "club_id": cid,
            "date": datetime.utcnow(),
            "type": "DAILY_STATS",
            "metrics": {
                "total_tickets_sold": len(tickets),
                "total_reservations": db.table_reservations.count_documents({
                    "club_id": cid,
                    "created_at": {"$gte": yesterday}
                }),
                "total_drink_orders": len(orders),
                "revenue_tickets": revenue_tickets,
                "revenue_drinks": revenue_drinks,
                "revenue_deposits": revenue_deposits,
                "total_revenue": round(
                    revenue_tickets + revenue_drinks + revenue_deposits, 2
                ),
            }
        })
        print(f"[report] Dnevni izvještaj spremljen za klub {club.get('name')}")
    client.close()


@app.task
def send_reservation_reminders():
    """Pošalji podsjetnike za rezervacije čiji event počinje za ~24h."""
    from email_service import send_reservation_reminder

    client = pymongo.MongoClient(MONGO_URI)
    db = client["mydb"]
    now = datetime.utcnow()
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    reservations = db.table_reservations.find({
        "status": "confirmed",
        "reminder_sent": False
    })
    sent = 0
    for r in reservations:
        event = db.events.find_one({"_id": r["event_id"]})
        if event and window_start <= event["date"] <= window_end:
            user = db.users.find_one({"_id": r["user_id"]})
            if user:
                send_reservation_reminder(r, event, user)
            db.table_reservations.update_one(
                {"_id": r["_id"]},
                {"$set": {"reminder_sent": True}}
            )
            sent += 1
    if sent:
        print(f"[reminders] Poslano {sent} podsjetnika.")
    client.close()
