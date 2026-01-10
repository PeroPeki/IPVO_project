FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flask mora slušati na 0.0.0.0
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# -w 1 znači jedan worker (proces) jer koristimo gevent koji je asinkroni
CMD ["gunicorn", "--worker-class", "gevent", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]
