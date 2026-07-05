"""
Real-time sloj — Redis Pub/Sub (zamjena za RabbitMQ).

Kanali:
- table_updates  → soba `event_{id}` (dostupnost stolova)
- order_updates  → sobe `waiter_{id}` i `bar_{event_id}` (narudžbe pića)
"""

import json
import os
import threading

import redis

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")

_redis = redis.Redis(host=REDIS_HOST, port=6379, db=0)


def publish(channel, data):
    _redis.publish(channel, json.dumps(data, default=str))


def start_listener(socketio):
    """Pokreće pozadinsku dretvu koja Redis poruke prosljeđuje u Socket.IO sobe."""

    def _listen():
        pubsub = _redis.pubsub()
        pubsub.subscribe('table_updates', 'order_updates')
        for msg in pubsub.listen():
            if msg['type'] != 'message':
                continue
            try:
                data = json.loads(msg['data'])
                ch = msg['channel'].decode()
                if ch == 'table_updates':
                    socketio.emit('table_updated', data,
                                  room=f"event_{data['event_id']}")
                elif ch == 'order_updates':
                    # Obavijesti konobara i barski zaslon
                    if data.get('waiter_id'):
                        socketio.emit('order_updated', data,
                                      room=f"waiter_{data['waiter_id']}")
                    socketio.emit('order_updated', data,
                                  room=f"bar_{data['event_id']}")
            except Exception as exc:
                print(f"[realtime] Greška u listeneru: {exc}")

    threading.Thread(target=_listen, daemon=True).start()
