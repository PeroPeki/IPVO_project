"""
Real-time sloj — Socket.IO emitiranje kroz Redis message queue.

publish() piše u Redis queue koji svi Socket.IO serveri slušaju, pa emitirati
može bilo koji proces (API worker ili Celery task) i backend se može
horizontalno skalirati na više workera/replika.

Kanali:
- table_updates  → soba `event_{id}` (dostupnost stolova)
- order_updates  → sobe `waiter_{id}` i `bar_{event_id}` (narudžbe pića)
"""

import os

from flask_socketio import SocketIO

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
SOCKETIO_MESSAGE_QUEUE = f"redis://{REDIS_HOST}:6379/0"

# Write-only instanca: samo emitira u queue, ne poslužuje klijente
_emitter = SocketIO(message_queue=SOCKETIO_MESSAGE_QUEUE)


def publish(channel, data):
    """Objavi real-time događaj; kanal određuje Socket.IO event i sobe."""
    if channel == "table_updates":
        _emitter.emit("table_updated", data, room=f"event_{data['event_id']}")
    elif channel == "order_updates":
        if data.get("waiter_id"):
            _emitter.emit("order_updated", data, room=f"waiter_{data['waiter_id']}")
        _emitter.emit("order_updated", data, room=f"bar_{data['event_id']}")
