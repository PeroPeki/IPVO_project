import os

# Redis kao broker i result backend (RabbitMQ je uklonjen iz sustava)
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")

broker_url = f'redis://{REDIS_HOST}:6379/1'
result_backend = f'redis://{REDIS_HOST}:6379/2'

beat_schedule = {
    'daily-report': {
        'task': 'tasks.generate_daily_report',
        'schedule': 86400.0,
    },
    'reservation-reminders': {
        'task': 'tasks.send_reservation_reminders',
        'schedule': 3600.0,   # svakih sat vremena provjerava
    },
    'expire-stale-payments': {
        'task': 'tasks.expire_stale_payments',
        'schedule': 300.0,    # svakih 5 min oslobađa neplaćene rezervacije/karte
    },
}

timezone = 'UTC'
