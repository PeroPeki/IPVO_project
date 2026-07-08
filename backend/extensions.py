"""Dijeljene ekstenzije — rate limiter i Redis klijent za revokaciju JWT-ova.

Odvojeno od app.py da ih blueprintovi mogu importati bez kružnih importa.
Redis db=3 drži rate-limit brojače i blocklist revociranih tokena
(db0 je Socket.IO queue, db1/db2 su Celery).
"""

import os

import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")

redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=3, decode_responses=True)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{REDIS_HOST}:6379/3",
    default_limits=[],
)
