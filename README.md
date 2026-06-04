# NightClub Manager

> A distributed, real-time, ML-driven nightclub reservation platform — built across four phases for the *Big Data Infrastructure (IPVO)* college course.

![Stack](https://img.shields.io/badge/stack-Docker%20Compose-2496ED)
![Backend](https://img.shields.io/badge/backend-Flask%203%20%7C%20Python%203-3776AB)
![Database](https://img.shields.io/badge/database-MongoDB%207-47A248)
![Broker](https://img.shields.io/badge/broker-RabbitMQ%203.12-FF6600)
![Cache](https://img.shields.io/badge/cache-Redis-DC382D)
![ML](https://img.shields.io/badge/ML-XGBoost%20%2F%20scikit--learn-EE4C2C)
![Monitoring](https://img.shields.io/badge/monitoring-Prometheus%20%2B%20Grafana-E6522C)

The platform lets visitors browse real, live music events from around the world, purchase tickets and reserve tables in real time. Behind the UI sits a load-balanced Flask backend, an asynchronous message bus, a Redis read-cache, an automated global data pipeline that ingests live event information from Ticketmaster and Last.fm, and a dedicated machine-learning microservice that produces dynamic table-pricing predictions.

---

## Table of Contents

1. [What the System Does](#what-the-system-does)
2. [Phase 4 Highlights — Live Data and Machine Learning](#phase-4-highlights--live-data-and-machine-learning)
3. [Phase Roadmap](#phase-roadmap)
4. [System Architecture](#system-architecture)
5. [Technology Stack](#technology-stack)
6. [Repository Layout](#repository-layout)
7. [File Reference](#file-reference)
8. [Service Catalogue](#service-catalogue)
9. [MongoDB Collections](#mongodb-collections)
10. [HTTP API Reference](#http-api-reference)
11. [Quick Start](#quick-start)
12. [Observability](#observability)

---

## What the System Does

| Capability | Detail |
|------------|--------|
| **Global live events** | Every club/venue and event in the system is fetched in real time from the Ticketmaster Discovery API across 20 cities worldwide (Europe, North America, Australia). No hardcoded data. |
| **Browse and book** | Users log in with a username, browse venues and real upcoming events, purchase a ticket and reserve any of the available tables for that event. |
| **Real-time updates** | Every reservation or cancellation propagates to all connected browsers within milliseconds via RabbitMQ → Socket.IO, eliminating the need for manual refresh. |
| **Horizontal scalability** | Two NGINX replicas serve the frontend behind a Traefik load balancer; the Flask backend is also load-balanced with sticky cookies for WebSocket affinity. |
| **High-throughput reads** | Frequently requested table lists and event feeds are cached in Redis with deterministic invalidation on every write. |
| **Periodic analytics** | A Celery worker with an embedded beat scheduler aggregates reservation and ticket metrics into a `reports` collection on a recurring schedule. |
| **Live data ingestion** | A scheduled pipeline pulls upcoming music events from the Ticketmaster Discovery API for 20 global cities and enriches each artist with Last.fm popularity signals. On first boot the pipeline triggers automatically if the database is empty. |
| **Dynamic pricing with ML** | A regression model (Random Forest vs XGBoost, lower-RMSE wins) predicts an optimal table price from real-world artist popularity, venue capacity, urgency, genre and demand features. |
| **Asynchronous price updates** | The backend publishes feature payloads to a durable RabbitMQ queue; a dedicated prediction microservice consumes them, runs inference, logs the change and updates the affected event. |
| **End-to-end observability** | Custom backend metrics (request count, latency histogram) and edge-proxy metrics (Traefik) are scraped by Prometheus and visualised in Grafana. |

---

## Phase 4 Highlights — Live Data and Machine Learning

Phase 4 introduces a self-contained data-engineering and ML stack on top of the Phase 1–3 platform. It satisfies all five course requirements (live data, processing, storage, ML, integration) without using mock or pre-packaged datasets.

### Global data pipeline

- **20 target cities** — Zagreb, London, Berlin, Amsterdam, Barcelona, Paris, Madrid, Milan, Vienna, Prague, New York, Los Angeles, Chicago, Miami, Las Vegas, Boston, Atlanta, Toronto, Sydney, Melbourne.
- Each **Ticketmaster venue** automatically becomes a **club** in the system, keyed by a stable `tm-<venue_id>` identifier. Events are linked to their venue via `club_id`, so the existing frontend navigation (Clubs → Events → Tables) continues to work unchanged.
- Each event is enriched with: event image, venue address, local date/time, Ticketmaster genre classification, original ticket price ranges, and a direct Ticketmaster URL.
- Each new event automatically receives **20 reservable tables** (all free at creation).
- **Auto-bootstrap**: on backend startup, if the `events` collection is empty, the pipeline is queued automatically via Celery — no manual step needed on first run.

### Data files

| File | Role |
|------|------|
| `pipeline_task.py` | Pure helper functions: `fetch_ticketmaster_events`, `get_lastfm_artist_data`, `encode_genre`, `calculate_base_price`, `slugify` and time utilities. |
| `tasks.py` | Celery task `run_data_pipeline` — orchestrates the full flow: TM fetch → Last.fm enrichment → club upsert → event upsert → table creation → Redis invalidation. |
| `generate_training_data.py` | Fetches top artists for 10 genres from Last.fm and generates a fully deterministic training set (artist × capacity tier × days-until-event). No `Faker`, no `random()`. |
| `train_model.py` | 80/20 train/test split, trains Random Forest and XGBoost, compares RMSE, persists the winner to the shared `models` volume and writes metadata to MongoDB. |

### ML feature vector

All four code paths (`pipeline_task.py`, `generate_training_data.py`, `train_model.py`, `prediction_service/service.py`) use identical features in identical order:

| Feature | Source | Transformation |
|---------|--------|----------------|
| `log_listeners` | Last.fm listeners | `log10(x + 1)` |
| `log_playcount` | Last.fm playcount | `log10(x + 1)` |
| `genre_encoded` | Last.fm tags → GENRE_MAP | 0–15 |
| `venue_capacity` | Ticketmaster venue | raw integer |
| `days_until_event` | event date – today | raw integer |
| `tickets_sold_ratio` | deterministic formula | 0.0–1.0 |
| `day_of_week` | event date | 0 (Mon) – 6 (Sun) |

### Bug fixes included in Phase 4

| Bug | Fix |
|-----|-----|
| `requests` module imported locally inside a function | Moved to top-level import |
| RabbitMQ consumer only started when model was loaded | Consumer always starts; sends `NACK, requeue=False` if model missing |
| N+1 MongoDB queries in `GET /api/clubs` | Replaced with a single `$lookup` aggregation |
| Double query `find_one({id}) or find_one({ticketmaster_id})` | Replaced with `$or` query |
| `depends_on: rabbitmq` without health-check condition | Changed to `condition: service_healthy` for all three consumers |
| Duplicate `import json` / `from flask import ...` mid-file | Removed duplicate imports |

---

## Phase Roadmap

| Phase | Theme | Components Introduced |
|-------|-------|----------------------|
| **1** | Core CRUD and horizontal scaling | Flask backend, MongoDB, Traefik load balancer, two NGINX frontend replicas, deterministic seed scripts |
| **2** | Real-time updates and periodic analytics | RabbitMQ fanout exchange, Socket.IO, Celery worker with embedded beat, daily-report task |
| **3** | Read-path optimisation and monitoring | Redis read-through cache with invalidation, Prometheus instrumentation, Grafana dashboards |
| **4** | Global live data, ML pricing, bug fixes | Ticketmaster + Last.fm pipeline (20 cities), auto-bootstrap, dynamic clubs from venues, deterministic training-data generator, Random Forest vs XGBoost trainer, dedicated `prediction_service` microservice, rich frontend (images, filtering, auto-refresh) |

---

## System Architecture

```
                  ┌─────────────────┐
                  │   Browser (UI)  │
                  └────────┬────────┘
                           │ HTTP / WebSocket
                           ▼
                  ┌─────────────────┐         ┌──────────────┐
                  │  Traefik :80    │◄────────│  Prometheus  │
                  │ (load balancer) │  /metrics│   :9090      │
                  └─┬───────┬───────┘         └──────┬───────┘
                    │       │                        │
          ┌─────────┘       └─────────┐              ▼
          ▼                           ▼       ┌──────────────┐
   ┌────────────┐              ┌────────────┐ │   Grafana    │
   │ web1/web2  │              │  backend   │ │    :3000     │
   │ (NGINX)    │              │  (Flask +  │ └──────────────┘
   │ static UI  │              │  Socket.IO)│
   └────────────┘              └─┬───┬───┬──┘
                                 │   │   │
        ┌────────────────────────┘   │   └────────────────────┐
        ▼                            ▼                        ▼
 ┌─────────────┐             ┌─────────────┐          ┌──────────────┐
 │  MongoDB    │             │   Redis     │          │   RabbitMQ   │
 │   :27017    │             │   :6379     │          │ :5672/:15672 │
 └─────▲───────┘             └─────▲───────┘          └──┬───────▲───┘
       │                           │                     │       │
       │                           │                     │       │
 ┌─────┴───────┐             ┌─────┴───────┐      ┌──────▼───────┴───┐
 │   seed      │             │  analytics  │      │ prediction_      │
 │  (one-shot) │             │   _worker   │      │ service          │
 └─────────────┘             │ (Celery +   │      │ (Flask + ML +    │
                             │  beat)      │      │  RabbitMQ        │
                             └─────────────┘      │  consumer)       │
                                                  └──────────────────┘
```

Traefik routes traffic on `Host(localhost)`:
- `/api`, `/socket.io`, `/metrics` → `backend`
- `/predict-price`, `/model-info` → `prediction_service`
- Everything else → `web1` / `web2` (round-robin)

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Reverse proxy / load balancer | Traefik 2.11 (Docker provider, native Prometheus exporter) |
| Frontend | Static HTML / CSS / JavaScript served by two NGINX replicas |
| Backend API | Python 3, Flask 3, Flask-SocketIO, gevent |
| Async processing | Celery 5 (worker + beat in a single container) |
| Database | MongoDB 7 |
| Message broker | RabbitMQ 3.12 (with management plugin) |
| Cache | Redis (alpine) |
| Monitoring | Prometheus 2.51, Grafana 10.4 |
| Machine learning | scikit-learn (Random Forest), XGBoost, joblib |
| Live data sources | Ticketmaster Discovery API, Last.fm API (`pylast`) |
| Container runtime | Docker Compose |

---

## Repository Layout

```
IPVO_projekt/
├── docker-compose.yml
├── README.md
├── context.md                       # Developer change log (what was built and why)
├── task.md                          # Bug tracker + future tasks + recommendations
├── .env                             # Local secrets (git-ignored)
├── .env.example                     # Template for required environment variables
│
├── frontend/
│   ├── Dockerfile
│   ├── index.html                   # Login screen
│   ├── clubs.html                   # Venue browser with city/country filter + auto-polling
│   ├── events.html                  # Event feed with images, artist, pricing badges
│   ├── buy-ticket.html              # Ticket purchase with full event detail
│   ├── tables.html                  # Real-time table reservation grid
│   └── style.css
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                       # Flask + Socket.IO core + all REST routes
│   ├── tasks.py                     # Celery tasks (pipeline, daily report)
│   ├── celery_config.py             # Broker URL + beat schedule
│   ├── pipeline_task.py             # TM/Last.fm helpers + pricing formula
│   ├── generate_training_data.py    # Last.fm-based training set generator
│   ├── train_model.py               # RF vs XGBoost trainer
│   └── models/                      # Mount point for the shared models volume
│
├── prediction_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── service.py                   # ML inference service + RabbitMQ consumer
│
├── seed-tools/
│   ├── Dockerfile
│   ├── package.json
│   └── seed.js                      # Clears stale data + creates MongoDB indexes
│
├── prometheus/
│   └── prometheus.yml
│
└── monitoring/
    └── prometheus.yml               # Alternative scrape configuration
```

---

## File Reference

### Orchestration

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Declarative orchestration of all twelve services on the shared `app-net` network. Includes build contexts, environment variables, Traefik labels, `service_healthy` conditions for RabbitMQ and the named volumes (`mongo_`, `models`). |
| `.env` | Holds `TICKETMASTER_API_KEY` and `LASTFM_API_KEY`. Required for the data pipeline. Excluded from version control. |
| `.env.example` | Template showing which environment variables are needed. |

### Frontend (`frontend/`)

| File | Purpose |
|------|---------|
| `index.html` | Login screen — captures the username, calls `POST /api/users` and stores it in `localStorage`. |
| `clubs.html` | Venue browser. Fetches dynamic venues from `GET /api/clubs` with optional `?city` / `?country` filters. Populates the country dropdown from `GET /api/cities`. Auto-polls every 10 seconds while the database is empty (pipeline still running), then renders venue cards automatically once data arrives. |
| `events.html` | Event feed for a selected venue. Displays Ticketmaster event image, artist, date/time, city, country, dynamic price with a 🔥 high-demand badge, genre tag and a link to the original Ticketmaster page. |
| `buy-ticket.html` | Ticket-purchase flow. Fetches full event detail from `GET /api/events/<id>` and renders: hero image, artist, venue/address, capacity, genre, days-until, Last.fm statistics, current vs base price block and a Ticketmaster link. |
| `tables.html` | Real-time table grid. Opens a Socket.IO connection and re-renders on `table_updated` events. Shows a mini event summary (image, artist, venue, date) above the grid. Reads dynamic pricing from `GET /api/events/<id>/pricing` and shows a high-demand warning when `current_price > base_price × 1.2`. |
| `style.css` | Shared styling including dark theme, card/grid layouts and all Phase 4 additions (event-card, hot-badge, genre-tag, filter-bar, event-summary, price-block, lastfm-block). |

### Backend (`backend/`)

| File | Purpose |
|------|---------|
| `app.py` | Flask + Socket.IO core. REST routes (see API Reference), Prometheus middleware, RabbitMQ producer/consumer, Redis caching, and a **startup bootstrap thread** that auto-queues `run_data_pipeline` if the events collection is empty. |
| `tasks.py` | Celery tasks: `generate_daily_report` (daily aggregates) and `run_data_pipeline` (TM fetch → Last.fm enrichment → club upsert → event upsert → table creation → cache invalidation). |
| `celery_config.py` | RabbitMQ broker URL, result backend, and the beat schedule (daily report every 60 s, data pipeline once per day). |
| `pipeline_task.py` | Pure helper functions for the pipeline: `fetch_ticketmaster_events` (extracts image, address, genre, price ranges), `get_lastfm_artist_data`, `encode_genre`, `calculate_base_price` (deterministic pricing formula), `slugify` and time utilities. |
| `generate_training_data.py` | Builds the ML training set. For each of 10 genres it fetches the top 30 artists from Last.fm, retrieves their full stats and emits one row per (artist × 10 capacity tiers × 11 days-until scenarios) into `ml_training_data`. Fully deterministic — up to ~33,000 records. |
| `train_model.py` | Loads `ml_training_data`, applies `log10` transforms, performs 80/20 split, trains RandomForest and XGBoost, persists the winner to the shared volume and writes a `model_metadata` document. |

### Prediction Service (`prediction_service/`)

| File | Purpose |
|------|---------|
| `service.py` | Loads the trained model on boot (degraded mode if missing). Exposes `POST /predict-price`, `GET /model-info` and `GET /health`. Caches predictions in Redis (TTL 300 s). Background daemon thread always runs consuming `price_update_queue` — if the model is absent it `NACK`s without requeue. Writes `price_log` and updates `current_price` whenever the predicted price moves by more than €5. |

### Seed (`seed-tools/`)

| File | Purpose |
|------|---------|
| `seed.js` | One-shot container. Clears all stale hardcoded data from `clubs`, `events`, `tables` and `reservations` collections, then creates optimised MongoDB indexes. Real data is populated by the Ticketmaster pipeline — this script does **not** insert any venues or events. |

### Monitoring

| File | Purpose |
|------|---------|
| `prometheus/prometheus.yml` | Active scrape config (15 s interval) for `backend` (`/metrics`) and Traefik (`:8082`). |

---

## Service Catalogue

Every service runs on the shared `app-net` Docker network.

### `traefik`
Edge reverse proxy and load balancer. Port 80 for traffic, 8080 for dashboard, 8082 for metrics. Routing rules are declared via Docker labels.

### `web1` / `web2`
Two NGINX containers serving the static frontend in round-robin. No state — purely serve HTML/CSS/JS files from a read-only volume mount.

### `backend`
Flask + Socket.IO core. Responsibilities:
- REST API under `/api/*` (see HTTP API Reference)
- Socket.IO real-time channel over `/socket.io/*`
- RabbitMQ **producer** for the `table_events` fanout exchange (reservations/cancellations)
- RabbitMQ **consumer thread** that re-broadcasts to Socket.IO clients
- RabbitMQ **producer** for `price_update_queue` (async pricing requests)
- Redis read-through cache for tables (`tables_list_<id>`, 1 h TTL) and event feeds
- Prometheus `/metrics` endpoint
- **Startup bootstrap thread**: queues `run_data_pipeline` via Celery if `events` is empty

### `analytics_worker`
Second Python container from the same backend image, running `celery -A tasks worker --beat`. Executes:
- `generate_daily_report` — aggregates metrics into `reports`
- `run_data_pipeline` — fetches 20 global cities from Ticketmaster, enriches with Last.fm, upserts clubs/events/tables into MongoDB, invalidates Redis

### `prediction_service`
Dedicated Flask microservice that owns the ML model:
- Loads `pricing_model.pkl` and `feature_cols.pkl` from the shared `models` volume
- `POST /predict-price`, `GET /model-info`, `GET /health`
- Caches predictions in Redis (`price_prediction_<id>`, TTL 300 s)
- Background daemon thread always consumes `price_update_queue`; NACKs without requeue if model is not yet trained

### `mongo`
MongoDB 7. On first start, `mongo-init/` scripts run. The `seed` service then clears any stale data and creates indexes.

### `seed`
Node.js one-shot container. Clears old hardcoded collections, creates MongoDB indexes, exits. Runs after `mongo` is started.

### `rabbitmq`
RabbitMQ 3.12 with management plugin. Hosts:
- `table_events` fanout exchange (real-time reservation events)
- `price_update_queue` durable queue (async pricing)

A Docker healthcheck (`rabbitmq-diagnostics -q ping`) ensures dependent services wait until RabbitMQ is fully ready.

### `redis`
In-memory cache for table lists, event feeds and prediction-service responses.

### `prometheus`
Scrapes metrics every 15 s from the backend and Traefik.

### `grafana`
Visualises Prometheus metrics. Port 3000, credentials `admin` / `admin`.

---

## MongoDB Collections

| Collection | Populated by | Purpose |
|------------|-------------|---------|
| `clubs` | `run_data_pipeline` | One document per Ticketmaster venue; keyed by `id = "tm-<venue_id>"`. Fields: name, city, country, address, capacity, lat/lon. |
| `events` | `run_data_pipeline` | One document per TM event. Linked to its venue via `club_id`. Fields include: `ticketmaster_id`, `artist_name`, `image_url`, `event_date`, `url`, `artist_listeners`, `artist_playcount`, `genre_encoded`, `base_price`, `current_price`, `venue_capacity`, `days_until_event`. |
| `tables` | `run_data_pipeline` | 20 free tables per event, created on first pipeline run. Linked by `event_id` (= `ticketmaster_id`). |
| `reservations` | `backend` | Append-only audit log of every table reservation. |
| `users` | `backend` | Username registry. |
| `tickets` | `backend` | Per-user, per-event ticket ownership. |
| `reports` | `analytics_worker` | Daily aggregate snapshots (reservation + ticket counts). |
| `ml_training_data` | `generate_training_data.py` | Training rows: real Last.fm artists × 10 capacity tiers × 11 days-until scenarios. |
| `price_log` | `prediction_service` | Append-only log of every ML-driven price change (old price → new price). |
| `model_metadata` | `train_model.py` | Latest model name, RF RMSE, XGBoost RMSE, feature list, training set size, timestamp. |

---

## HTTP API Reference

### Backend (routed through Traefik on port 80)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/clubs` | List venues. Optional filters: `?city=`, `?country=`. Returns `event_count` per venue via a single `$lookup` aggregation. |
| POST | `/api/clubs` | Insert a club document manually. |
| GET | `/api/clubs/<club_id>/events` | Events for a venue, sorted by date ascending. |
| GET | `/api/events` | Global event feed. Filters: `?city=`, `?country=`, `?genre=`, `?q=` (full-text), `?limit=` (default 100, max 500). Redis-cached for 60 s. |
| GET | `/api/events/<event_id>` | Full event document by `id` or `ticketmaster_id`. |
| GET | `/api/cities` | Aggregated list of cities + event counts (for filter dropdowns). |
| POST | `/api/sync-events` | Manually queue `run_data_pipeline` via Celery. Returns `task_id`. |
| GET | `/api/events/<event_id>/tables` | Tables for an event (Redis-cached, 1 h TTL). |
| POST | `/api/events/<event_id>/tables/<table_id>/reserve` | Reserve a table (RabbitMQ broadcast + cache invalidation). |
| POST | `/api/events/<event_id>/tables/<table_id>/cancel` | Cancel a reservation. |
| POST | `/api/users` | Create / ensure a user. |
| POST | `/api/users/<username>/buy-ticket/<event_id>` | Purchase a ticket. |
| GET | `/api/users/<username>/has-ticket/<event_id>` | Ticket ownership check. |
| GET | `/api/reports` | Most recent 10 daily reports. |
| GET | `/api/events/<event_id>/pricing` | `{base_price, current_price, high_demand, ...}`. Redis-cached for 60 s. |
| POST | `/api/events/<event_id>/request-price-update` | Manually send pricing features to the prediction queue. |
| GET | `/api/price-log` | Last 50 ML-driven price changes. |
| GET | `/api/model-status` | Proxy to `prediction_service /model-info`. |
| GET | `/metrics` | Prometheus scrape endpoint. |

### Prediction Service (routed through Traefik on port 80)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/predict-price` | Input: `{artist_listeners, artist_playcount, genre_encoded, venue_capacity, days_until_event, tickets_sold_ratio, day_of_week, event_id, current_price}`. Returns predicted price; updates `price_log` and event if delta > €5. |
| GET | `/model-info` | Latest `model_metadata` document. |
| GET | `/health` | `{"status": "ok", "model_loaded": true/false}`. |

### Real-Time Channel

Socket.IO event `table_updated` is broadcast to **all** connected clients whenever a reservation or cancellation flows through the `table_events` exchange. The frontend filters by `event_id` client-side.

---

## Quick Start

> **Prerequisites:** Docker and Docker Compose installed. API keys in a `.env` file at the repository root (copy from `.env.example`).

```bash
# 1. Add your API keys
cp .env.example .env
# Edit .env and fill in TICKETMASTER_API_KEY and LASTFM_API_KEY

# 2. Build and start the entire stack
docker compose build
docker compose up -d

# 3. Watch the pipeline run automatically
docker compose logs analytics_worker -f --tail=60
# You will see: "Obrada grada: London, GB", "Pipeline gotov: {...}"
# clubs.html auto-polls and populates once events arrive (~2–5 min)

# --- ML model (optional, for dynamic pricing) ---

# 4. Generate the training dataset (~30 min, hits Last.fm API)
docker compose exec backend python generate_training_data.py

# 5. Train the model (RF vs XGBoost, picks lower RMSE)
docker compose exec backend python train_model.py

# 6. Reload the prediction service so it picks up the new model
docker compose restart prediction_service

# --- Utilities ---

# Manually re-trigger the data pipeline (e.g. after API key change)
docker compose exec analytics_worker celery -A tasks call tasks.run_data_pipeline

# Re-run seed (clears old data, recreates indexes)
docker compose run --rm seed
```

### Endpoints

| URL | What you get |
|-----|--------------|
| http://localhost/ | Frontend (login → venues → events → tables) |
| http://localhost/api/events | Global event feed (JSON) |
| http://localhost/api/cities | City + event count aggregation (JSON) |
| http://localhost/api/model-status | Latest ML model metadata |
| http://localhost/metrics | Prometheus metrics from the backend |
| http://localhost:8080/ | Traefik dashboard |
| http://localhost:15672/ | RabbitMQ Management UI (`guest` / `guest`) |
| http://localhost:9090/ | Prometheus |
| http://localhost:3000/ | Grafana (`admin` / `admin`) |

---

## Observability

The Flask backend records two custom metrics via `prometheus_client`:

- `http_requests_total{method, endpoint, status}` — request counter.
- `http_request_duration_seconds{endpoint}` — latency histogram.

Traefik exports its own request metrics on the `metrics` entry point (port 8082). Both are scraped by Prometheus every 15 seconds and visualised in Grafana, providing end-to-end visibility from the edge proxy down to individual API endpoints.

---

## Known Limitations & Future Work

See `task.md` for the full list of open tasks and improvement recommendations. Key items:

- No authentication/authorisation — `username` is stored unverified in `localStorage`
- No input validation on POST endpoints
- No rate limiting — API is open to abuse
- WebSocket broadcasts go to all clients (not room-scoped by event)
- `generate_training_data.py` drops the collection without confirmation prompt
- ML model has no versioning — each retrain overwrites the previous `.pkl`
