FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flask mora slušati na 0.0.0.0
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# GeventWebSocketWorker omogućuje prave WebSocket konekcije (Socket.IO);
# -w 1 po kontejneru — skaliranje ide replikama (Socket.IO Redis queue)
CMD ["gunicorn", "--worker-class", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]
