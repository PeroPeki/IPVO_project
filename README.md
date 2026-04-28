# NightClub Manager

> A distributed, real-time, ML-driven nightclub reservation platform — built across four phases for the *Big Data Infrastructure (IPVO)* college course.

![Stack](https://img.shields.io/badge/stack-Docker%20Compose-2496ED)
![Backend](https://img.shields.io/badge/backend-Flask%203%20%7C%20Python%203-3776AB)
![Database](https://img.shields.io/badge/database-MongoDB%207-47A248)
![Broker](https://img.shields.io/badge/broker-RabbitMQ%203.12-FF6600)
![Cache](https://img.shields.io/badge/cache-Redis-DC382D)
![ML](https://img.shields.io/badge/ML-XGBoost%20%2F%20scikit--learn-EE4C2C)
![Monitoring](https://img.shields.io/badge/monitoring-Prometheus%20%2B%20Grafana-E6522C)

The platform lets visitors browse nightclub events, purchase tickets and reserve tables in real time. Behind the user-facing UI sits a load-balanced Flask backend, an asynchronous message bus, a Redis read-cache, an automated data pipeline that ingests live event information from Ticketmaster and Last.fm, and a dedicated machine-learning microservice that produces dynamic table-pricing predictions.

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
| **Browse and book** | Users log in with a username, browse a curated catalogue of clubs and events, purchase a ticket and reserve any of the available tables for that event. |
| **Real-time updates** | Every reservation or cancellation propagates to all connected browsers within milliseconds via RabbitMQ → Socket.IO, eliminating the need for manual refresh. |
| **Horizontal scalability** | Two NGINX replicas serve the frontend behind a Traefik load balancer; the Flask backend is also exposed through the same load-balancer service with sticky cookies for WebSocket affinity. |
| **High-throughput reads** | Frequently requested table lists are cached in Redis with deterministic invalidation on every write, so reads never block on MongoDB. |
| **Periodic analytics** | A Celery worker with an embedded beat scheduler aggregates reservation and ticket metrics into a `reports` collection on a recurring schedule. |
| **Live data ingestion** | A scheduled pipeline pulls upcoming music events from the Ticketmaster Discovery API for ten European capitals and enriches each artist with Last.fm popularity signals. |
| **Dynamic pricing with ML** | A regression model (Random Forest vs XGBoost, lower-RMSE wins) predicts an optimal table price for each event from real-world artist popularity, venue capacity, urgency, genre and demand features. |
| **Asynchronous price updates** | The backend publishes feature payloads to a durable RabbitMQ queue; a dedicated prediction microservice consumes them, runs inference, logs the change and updates the affected event. |
| **End-to-end observability** | Custom backend metrics (request count, latency histogram) and edge-proxy metrics (Traefik) are scraped by Prometheus and visualised in Grafana. |

---

## Phase 4 Highlights — Live Data and Machine Learning

The fourth phase introduces a self-contained data engineering and ML stack on top of the Phase 1–3 platform. It satisfies all five course requirements (live data, processing, storage, ML, integration) without using mock or pre-packaged datasets.

- **`pipeline_task.py`** — pulls real upcoming music events from Ticketmaster Discovery API for ten European capitals and enriches every artist with Last.fm `listeners`, `playcount` and top tags. A deterministic pricing formula computes a base price from popularity, venue capacity, days-until-event and genre.
- **`generate_training_data.py`** — fetches top artists across ten music genres from Last.fm and produces a fully deterministic training set by combining each artist with ten venue-capacity tiers and eleven days-until-event scenarios. No `Faker`, no `random()` — the same inputs always yield the same outputs.
- **`train_model.py`** — performs an 80/20 train/test split, trains a `RandomForestRegressor` and an `XGBRegressor`, compares root-mean-squared error and persists the winning model together with its feature list and a metadata document.
- **`prediction_service/`** — a standalone Flask microservice that owns the model. It exposes `POST /predict-price` and `GET /model-info`, caches predictions in Redis with a five-minute TTL and runs a daemon thread that consumes `price_update_queue` from RabbitMQ for asynchronous repricing.
- **Backend integration** — the Flask backend exposes `/api/events/<id>/pricing`, `/api/events/<id>/request-price-update`, `/api/price-log` and `/api/model-status`. Whenever the predicted price diverges from the current price by more than five euros the change is logged in `price_log` and reflected on the event document.
- **Frontend integration** — `tables.html` reads the pricing endpoint and surfaces a *high-demand* banner when the current price exceeds the base price by more than twenty per cent.

---

## Phase Roadmap

| Phase | Theme | Components Introduced |
|-------|-------|----------------------|
| **1** | Core CRUD and horizontal scaling | Flask backend, MongoDB, Traefik load balancer, two NGINX frontend replicas, deterministic seed scripts |
| **2** | Real-time updates and periodic analytics | RabbitMQ fanout exchange, Socket.IO, Celery worker with embedded beat, daily-report task |
| **3** | Read-path optimisation and monitoring | Redis read-through cache with invalidation, Prometheus instrumentation, Grafana dashboards |
| **4** | Live data, data pipeline and ML pricing | Ticketmaster + Last.fm pipeline, deterministic training-data generator, Random Forest vs XGBoost trainer, dedicated `prediction_service` microservice with RabbitMQ consumer |

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

Traefik routes traffic on `Host(localhost)` as follows: `/api`, `/socket.io` and `/metrics` are forwarded to the backend; `/predict-price` and `/model-info` reach the prediction microservice; everything else is served by the two NGINX frontends. Sticky cookies on the backend service keep WebSocket sessions pinned to a single instance.

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
├── .env                         # Local secrets (git-ignored)
│
├── frontend/
│   ├── Dockerfile
│   ├── index.html
│   ├── clubs.html
│   ├── events.html
│   ├── buy-ticket.html
│   ├── tables.html
│   └── style.css
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   ├── tasks.py
│   ├── celery_config.py
│   ├── pipeline_task.py
│   ├── generate_training_data.py
│   ├── train_model.py
│   └── models/                  # Mount point for the shared models volume
│
├── prediction_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── service.py
│
├── mongo-init/
│   └── seed.js
│
├── seed-tools/
│   ├── Dockerfile
│   ├── package.json
│   └── seed.js
│
├── prometheus/
│   └── prometheus.yml
│
└── monitoring/
    └── prometheus.yml           # Alternative scrape configuration
```

---

## File Reference

### Orchestration

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Declarative orchestration of all eleven services on the shared `app-net` network, including build contexts, environment variables, Traefik labels, healthchecks and the named volumes (`mongo_`, `models`). |
| `.env` | Holds `TICKETMASTER_API_KEY` and `LASTFM_API_KEY`. Loaded by Compose into the `backend`, `analytics_worker` and `prediction_service` containers. Excluded from version control via `.gitignore`. |
| `.gitignore` | Excludes secrets, Python virtualenvs, IDE artefacts and Celery beat schedule files. |

### Frontend (`frontend/`)

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds an NGINX image and mounts the static HTML/CSS as a read-only volume. |
| `index.html` | Login screen — captures the username, calls `POST /api/users` and stores it in `localStorage`. |
| `clubs.html` | Renders the list of clubs returned by `GET /api/clubs`. |
| `events.html` | Renders all events for the selected club via `GET /api/clubs/<id>/events`. |
| `buy-ticket.html` | Ticket-purchase flow that posts to `POST /api/users/<username>/buy-ticket/<event_id>`. |
| `tables.html` | The real-time table grid. Opens a Socket.IO connection, subscribes to the `table_updated` event and re-renders on every update. Reads dynamic pricing from `GET /api/events/<id>/pricing` and shows a *high-demand* banner whenever `current_price` exceeds `base_price × 1.2`. |
| `style.css` | Shared visual styling for all pages. |

### Backend (`backend/`)

| File | Purpose |
|------|---------|
| `Dockerfile` | Python 3 base image plus the dependencies declared in `requirements.txt`. |
| `requirements.txt` | Flask 3, Flask-SocketIO, gevent, pymongo, pika, redis, prometheus-client, celery, plus the Phase 4 additions: `pylast`, `xgboost`, `scikit-learn`, `pandas`, `numpy`, `joblib`, `requests`. |
| `app.py` | The Flask + Socket.IO core. Defines all REST routes, the Prometheus middleware (`Counter`, `Histogram` and `/metrics`), the RabbitMQ producer (`publish_to_rabbitmq`), the consumer thread (`listen_to_rabbitmq` → Socket.IO emit), the Redis read-through cache for table lists, and the Phase 4 dynamic-pricing endpoints (`/api/events/<id>/pricing`, `/api/events/<id>/request-price-update`, `/api/price-log`, `/api/model-status`). |
| `tasks.py` | Celery task definitions: `generate_daily_report` (aggregates reservations and tickets into the `reports` collection) and `run_data_pipeline` (Phase 4 — Ticketmaster fetch, Last.fm enrichment, deterministic upsert). |
| `celery_config.py` | Celery broker URL (RabbitMQ), result backend and the periodic `beat_schedule` — daily report every sixty seconds and the data pipeline once per day. |
| `pipeline_task.py` | Pure functions used by `run_data_pipeline`: `fetch_ticketmaster_events`, `get_lastfm_artist_data`, `encode_genre`, `compute_days_until_event` and the deterministic `calculate_base_price` formula. The same pricing function is duplicated in the training-data generator to guarantee identical inputs/outputs across the pipeline. |
| `generate_training_data.py` | Builds the training set from real Last.fm artists. For each genre it fetches the top artists, retrieves their listeners/playcount/tags and emits one row per (artist × venue capacity × days-until-event) combination into `ml_training_data`. Fully deterministic — no random values, no synthetic data. |
| `train_model.py` | Loads `ml_training_data`, engineers `log_listeners`/`log_playcount` features, performs an 80/20 train/test split, trains a Random Forest and an XGBoost regressor, compares RMSE, persists the winning model and its feature list to the shared `/app/models/` volume and inserts a metadata document into `model_metadata`. |
| `models/` | Mount point for the shared `models` Docker volume — contains the serialised `pricing_model.pkl` and `feature_cols.pkl`. |

### Prediction Service (`prediction_service/`)

| File | Purpose |
|------|---------|
| `Dockerfile` | Slim Python 3 image that installs the ML runtime and runs `service.py`. |
| `requirements.txt` | Flask, xgboost, scikit-learn, joblib, pymongo, redis, pika, numpy, pandas. |
| `service.py` | Loads the trained model on boot, exposes `POST /predict-price`, `GET /model-info` and `GET /health`, caches predictions in Redis (`price_prediction_<event_id>`, TTL 300 s) and runs a background thread that consumes `price_update_queue` from RabbitMQ. When a prediction differs from the current price by more than five euros it appends a row to `price_log` and updates `current_price` on the corresponding event. |

### Database Seeds

| File | Purpose |
|------|---------|
| `mongo-init/seed.js` | Auto-runs on the first MongoDB boot (`/docker-entrypoint-initdb.d`). Inserts five real Croatian clubs, twenty-five events and four hundred tables. Fully deterministic — no `Faker`, no `Math.random()`. |
| `seed-tools/Dockerfile` | Node.js 20 alpine image used by the `seed` Compose service. |
| `seed-tools/package.json` | Declares the `mongodb` dependency for the manual reseed script. |
| `seed-tools/seed.js` | Manual reseeder. Inserts a richer dataset — eight Croatian clubs, twelve real artists (Solomun, Black Coffee, Tale Of Us, Charlotte de Witte, Boris Brejcha, Dubioza Kolektiv, etc.), six events per club and twenty-five tables per event. |

### Monitoring

| File | Purpose |
|------|---------|
| `prometheus/prometheus.yml` | Active scrape configuration (15-second interval) for the `prometheus`, `backend` and `traefik` jobs. |
| `monitoring/prometheus.yml` | Alternative configuration kept for reference. |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | This document. |

---

## Service Catalogue

Every service runs on the shared `app-net` Docker network.

### `traefik`
Edge reverse proxy and load balancer. Listens on port 80 for application traffic and 8080 for the Traefik dashboard. Exposes its own metrics on port 8082. Routing rules and priorities are declared via Docker labels on each service.

### `web1` / `web2`
Two NGINX containers serving the static frontend. They share the same Traefik router and load-balancer service definition, so traffic is distributed in round-robin fashion.

### `backend`
The Flask + Socket.IO core. Its responsibilities are:
- exposing the REST API under `/api/*`;
- maintaining a persistent Socket.IO connection over `/socket.io/*` for real-time table updates;
- acting as a **RabbitMQ producer** for the `table_events` fanout exchange (every reservation or cancellation publishes a message);
- running a **RabbitMQ consumer thread** that re-broadcasts those events to connected Socket.IO clients;
- acting as a **RabbitMQ producer** for the `price_update_queue` (Phase 4 — sends pricing-feature payloads to the prediction service);
- reading through and invalidating Redis for the table list (`tables_list_<event_id>` key, one-hour TTL);
- exposing Prometheus metrics on `/metrics` via custom `Counter` and `Histogram` instruments.

### `analytics_worker`
A second Python container running `celery -A tasks worker --beat` from the same backend image. It executes both scheduled jobs:
- `generate_daily_report` — aggregates reservations and ticket counts into the `reports` collection;
- `run_data_pipeline` — fetches Ticketmaster events for ten European capitals, enriches each with Last.fm artist data, computes the deterministic base price and upserts into MongoDB while invalidating the relevant Redis keys.

### `prediction_service` *(Phase 4 microservice)*
A dedicated Flask service that owns the ML model:
- loads `pricing_model.pkl` and `feature_cols.pkl` from the shared `models` volume on boot;
- exposes `POST /predict-price`, `GET /model-info` and `GET /health` (the first two are routed through Traefik);
- caches predictions in Redis (`price_prediction_<event_id>`, TTL 300 s);
- spawns a daemon thread that consumes `price_update_queue`, runs the model on each message, writes a row to `price_log` and updates `current_price` whenever the predicted price moves by more than five euros.

### `mongo`
MongoDB 7 instance. The script `mongo-init/seed.js` auto-runs on the very first container start and seeds the `clubs`, `events`, `tables` and `reservations` collections with curated, deterministic real-world data.

### `seed`
A Node.js one-shot container that connects to MongoDB and writes a richer, fully deterministic dataset. Useful for re-seeding without recreating the Mongo volume.

### `rabbitmq`
RabbitMQ 3.12 with the management plugin (UI on port 15672). Hosts:
- the `table_events` fanout exchange (real-time reservation events);
- the `price_update_queue` durable queue (asynchronous pricing requests from backend → prediction service).

### `redis`
Used as a cache in two places — for `GET /api/events/<id>/tables` responses (with explicit invalidation on every reservation or cancellation) and for prediction-service responses (keyed by `event_id`).

### `prometheus`
Scrapes metrics every fifteen seconds from itself, the backend (`/metrics`) and Traefik (`:8082`).

### `grafana`
Visualises Prometheus metrics. Reachable on port 3000 with `admin` / `admin` as the default credentials.

---

## MongoDB Collections

| Collection | Owner | Purpose |
|------------|-------|---------|
| `clubs` | seed | Static catalogue of nightclubs |
| `events` | seed + pipeline | Curated and Ticketmaster-imported events; Phase 4 enriches each document with `artist_listeners`, `artist_playcount`, `artist_tags`, `genre_encoded`, `base_price`, `current_price`, `min_price` and `max_price` |
| `tables` | seed | Reservable tables per event |
| `reservations` | backend | Audit log of every booked table |
| `users` / `tickets` | backend | Username login and per-event ticket ownership |
| `reports` | celery | Daily aggregate snapshots produced by `generate_daily_report` |
| `ml_training_data` | generator | Training rows produced from real Last.fm artists × capacity × days-until scenarios |
| `price_log` | prediction_service | Append-only log of every ML-driven price change |
| `model_metadata` | trainer | Latest model name, RMSE values, train-set size, feature list |

---

## HTTP API Reference

### Backend (routed through Traefik)

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/clubs` | List all clubs |
| POST   | `/api/clubs` | Insert a club |
| GET    | `/api/clubs/<club_id>/events` | Events for a given club |
| GET    | `/api/events/<event_id>/tables` | Tables for an event (Redis-cached) |
| POST   | `/api/events/<event_id>/tables/<table_id>/reserve` | Reserve a table (publishes to RabbitMQ, invalidates cache) |
| POST   | `/api/events/<event_id>/tables/<table_id>/cancel` | Cancel a reservation |
| POST   | `/api/users` | Create a user |
| POST   | `/api/users/<username>/buy-ticket/<event_id>` | Purchase a ticket |
| GET    | `/api/users/<username>/has-ticket/<event_id>` | Ticket-ownership check |
| GET    | `/api/reports` | Most recent ten daily reports |
| GET    | `/api/events/<event_id>/pricing` | Current, base, minimum and maximum price for an event |
| POST   | `/api/events/<event_id>/request-price-update` | Manually trigger a price-update message via RabbitMQ |
| GET    | `/api/price-log` | Last fifty pricing changes |
| GET    | `/api/model-status` | Proxy to the prediction service’s `/model-info` |
| GET    | `/metrics` | Prometheus metrics scrape endpoint |

### Prediction Service (also routed through Traefik)

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/predict-price` | Returns a model-predicted price for the given feature payload |
| GET    | `/model-info` | Latest model metadata from MongoDB |
| GET    | `/health` | Liveness probe |

### Real-Time Channel

The Socket.IO event `table_updated` is broadcast to every connected client whenever a reservation or cancellation flows through the `table_events` exchange.

---

## Quick Start

> **Prerequisites:** Docker and Docker Compose. For Phase 4 live data, place `TICKETMASTER_API_KEY` and `LASTFM_API_KEY` in a `.env` file at the repository root. Without them the pipeline silently skips remote calls.

```bash
# 1. Build and start the entire stack
docker compose build
docker compose up -d

# 2. (Optional) Reseed MongoDB with the richer Node.js dataset
docker compose run --rm seed

# 3. (Phase 4) Run the data pipeline once on demand
docker compose exec analytics_worker celery -A tasks call tasks.run_data_pipeline

# 4. (Phase 4) Generate the training dataset from Last.fm
docker compose exec backend python generate_training_data.py

# 5. (Phase 4) Train the model — the lower-RMSE estimator wins
docker compose exec backend python train_model.py

# 6. Reload the model into the prediction service
docker compose restart prediction_service
```

Endpoints:

| URL | What you get |
|-----|--------------|
| http://localhost/ | Frontend (login → clubs → events → tables) |
| http://localhost/api/model-status | Latest model metadata |
| http://localhost/metrics | Prometheus metrics from the backend |
| http://localhost:8080/ | Traefik dashboard |
| http://localhost:15672/ | RabbitMQ Management UI (`guest` / `guest`) |
| http://localhost:9090/ | Prometheus |
| http://localhost:3000/ | Grafana (`admin` / `admin`) |

---

## Observability

The Flask backend records two custom metrics through `prometheus_client`:

- `http_requests_total{method, endpoint, status}` — request counter.
- `http_request_duration_seconds{endpoint}` — latency histogram.

Traefik exports its own request metrics on the dedicated `metrics` entry point (port 8082). Both are scraped by Prometheus every fifteen seconds and visualised in Grafana, providing end-to-end visibility from the edge proxy down to individual API endpoints.
