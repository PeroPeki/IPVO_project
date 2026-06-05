# NightClub Manager

> Distribuirana platforma za rezervaciju stolova u noćnim klubovima s dinamičkim određivanjem cijena temeljenim na strojnom učenju — izrađena u četiri faze za kolegij *Infrastruktura za velike podatke (IPVO)*.

[![Stack](https://img.shields.io/badge/stack-Docker%20Compose-2496ED)](https://docs.docker.com/compose/)
[![Backend](https://img.shields.io/badge/backend-Flask%203%20%7C%20Python%203-3776AB)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/database-MongoDB%207-47A248)](https://www.mongodb.com/)
[![Broker](https://img.shields.io/badge/broker-RabbitMQ%203.12-FF6600)](https://www.rabbitmq.com/)
[![Cache](https://img.shields.io/badge/cache-Redis-DC382D)](https://redis.io/)
[![ML](https://img.shields.io/badge/ML-XGBoost%20%2F%20scikit--learn-EE4C2C)](https://xgboost.readthedocs.io/)
[![Monitoring](https://img.shields.io/badge/monitoring-Prometheus%20%2B%20Grafana-E6522C)](https://grafana.com/)

---

## Sadržaj

1. [Što sustav radi](#što-sustav-radi)
2. [Arhitektura sustava](#arhitektura-sustava)
3. [Faze razvoja](#faze-razvoja)
4. [Tehnološki stack](#tehnološki-stack)
5. [Struktura repozitorija](#struktura-repozitorija)
6. [Brzi start](#brzi-start)
7. [Varijable okoline](#varijable-okoline)
8. [Servisni katalog](#servisni-katalog)
9. [MongoDB kolekcije](#mongodb-kolekcije)
10. [HTTP API referenca](#http-api-referenca)
11. [Celery rasporednik](#celery-rasporednik)
12. [Dinamičke cijene — ML pipeline](#dinamičke-cijene--ml-pipeline)
13. [Nadzor sustava](#nadzor-sustava)
14. [Testiranje](#testiranje)
15. [Poznata ograničenja](#poznata-ograničenja)

---

## Što sustav radi

Platforma korisnicima omogućuje pregled stvarnih glazbenih događaja s Ticketmastera, kupnju ulaznica i rezervaciju stolova u realnom vremenu. Iza korisničkog sučelja nalaze se:

| Mogućnost | Opis |
|-----------|------|
| **Stvarni glazbeni eventi** | Svi klubovi i eventi dohvaćaju se s Ticketmaster Discovery API-ja za 20 gradova diljem svijeta. Nema hardkodiranih podataka. |
| **Pregled i rezervacija** | Korisnik se prijavljuje korisničkim imenom, pregledava venue-e i nadolazeće evente, kupuje ulaznicu i rezervira slobodni stol. |
| **Ažuriranje u realnom vremenu** | Svaka rezervacija ili otkazivanje propagira se svim spojenim preglednicima unutar milisekundi putem RabbitMQ → Socket.IO. |
| **Horizontalna skalabilnost** | Dvije NGINX replike servira frontend iza Traefik load balancera; Flask backend je load-balanced sa sticky kolačićima za WebSocket afinitet. |
| **Brze čitanja** | Često zahtijevane liste stolova i event feed cachiraju se u Redisu s determinističkom invalidacijom pri svakom zapisu. |
| **Periodička analitika** | Celery worker s ugrađenim beat raspoređivačem agregira metrike rezervacija i ulaznica u kolekciju `reports`. |
| **Automatski dohvat podataka** | Raspoređeni pipeline povlači nadolazeće glazbene evente za 20 globalnih gradova i obogaćuje svakog izvođača Last.fm popularnosti signalima. Automatski se okida pri prvom pokretanju ako je baza prazna. |
| **Dinamičke cijene s ML-om** | Regresijski model (Random Forest vs XGBoost, pobjeđuje niži RMSE) predviđa optimalnu cijenu stola iz popularnosti izvođača, kapaciteta, hitnosti, žanra i popunjenosti. |
| **Asinkrono ažuriranje cijena** | Backend objavljuje feature payload u trajni RabbitMQ red; namjenski prediction mikroservis ga konzumira, pokreće inferenciju, zapisuje promjenu i ažurira pogođeni event. |
| **End-to-end nadzor** | Vlastite metrike backenda i metrike edge proxija (Traefik) skuplja Prometheus i vizualizira u Grafani. |
| **Tjedni automatski retraining** | Svake nedjelje u 3:00 Celery Beat automatski regenerira training podatke i trenira novi model. |

---

## Arhitektura sustava

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
   │  (NGINX)   │              │  (Flask +  │ └──────────────┘
   │ static UI  │              │ Socket.IO) │
   └────────────┘              └─┬───┬───┬──┘
                                 │   │   │
        ┌────────────────────────┘   │   └───────────────────┐
        ▼                            ▼                       ▼
 ┌─────────────┐             ┌─────────────┐          ┌─────────────┐
 │   MongoDB   │             │    Redis    │          │  RabbitMQ   │
 │   :27017    │             │   :6379     │          │  :5672      │
 └─────▲───────┘             └─────────────┘          └──┬──────▲───┘
       │                                                  │      │
 ┌─────┴──────────┐                               ┌───────▼──────┴────┐
 │ analytics_     │                               │ prediction_       │
 │ worker         │                               │ service           │
 │ (Celery +      │                               │ (Flask + ML +     │
 │  Beat)         │                               │  RabbitMQ         │
 └────────────────┘                               │  consumer)        │
                                                  └───────────────────┘
```

**Traefik routing pravila** (sve na `Host(localhost)`):

| Putanja | Cilj | Prioritet |
|---------|------|-----------|
| `/api/*`, `/socket.io/*`, `/metrics` | `backend:5000` | 100 |
| `/predict-price`, `/model-info` | `prediction_service:6000` | 200 |
| Sve ostalo | `web1` / `web2` round-robin | nizak |

---

## Faze razvoja

| Faza | Tema | Uvedene komponente |
|------|------|--------------------|
| **1** | Core CRUD i horizontalno skaliranje | Flask backend, MongoDB, Traefik load balancer, dvije NGINX frontend replike |
| **2** | Ažuriranje u realnom vremenu i periodička analitika | RabbitMQ fanout exchange, Socket.IO, Celery worker s ugrađenim beatom, task za dnevni izvještaj |
| **3** | Optimizacija čitanja i nadzor | Redis read-through cache s invalidacijom, Prometheus instrumentacija, Grafana dashboardi |
| **4** | Globalni živi podaci, ML cijene, bug ispravci | Ticketmaster + Last.fm pipeline (20 gradova), auto-bootstrap, dinamički klubovi iz venue-a, deterministički generator training podataka, Random Forest vs XGBoost trener, namjenski `prediction_service` mikroservis, bogat frontend (slike, filtriranje, auto-refresh, dinamičke cijene), tjedni automatski retraining |

---

## Tehnološki stack

| Sloj | Tehnologija | Verzija |
|------|-------------|---------|
| Reverse proxy / load balancer | Traefik (Docker provider, Prometheus exporter) | 2.11 |
| Frontend | Statički HTML/CSS/JS, dvije NGINX replike | nginx:alpine |
| Backend API | Python, Flask, Flask-SocketIO, gevent | Flask 3, Python 3 |
| Asinkrona obrada | Celery worker + beat u jednom kontejneru | Celery 5 |
| Baza podataka | MongoDB | 7.0 |
| Message broker | RabbitMQ (management plugin) | 3.12 |
| Cache | Redis | alpine |
| Nadzor | Prometheus + Grafana (auto-provisioning) | 2.51 / 10.4 |
| Strojno učenje | scikit-learn (Random Forest), XGBoost, joblib, pandas | latest |
| Živi podaci | Ticketmaster Discovery API, Last.fm API (pylast) | — |
| Runtime | Docker Compose | — |

---

## Struktura repozitorija

```
IPVO_projekt/
├── docker-compose.yml               # Orkestracija svih servisa
├── .env                             # Lokalni API ključevi (git-ignored)
├── .env.example                     # Predložak varijabli okoline
├── README.md
│
├── frontend/
│   ├── Dockerfile
│   ├── index.html                   # Ekran za prijavu
│   ├── clubs.html                   # Preglednik venue-a s filterima
│   ├── events.html                  # Feed evenata sa slikama i cijenama
│   ├── buy-ticket.html              # Kupnja ulaznice s detaljima eventa
│   ├── tables.html                  # Real-time grid rezervacije stolova
│   └── style.css
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                       # Flask + Socket.IO core + sve REST rute
│   ├── tasks.py                     # Celery taskovi (pipeline, dnevni izvještaj, retraining)
│   ├── celery_config.py             # Broker URL + beat raspored
│   ├── pipeline_task.py             # TM/Last.fm helperi + formula za cijene
│   ├── generate_training_data.py    # Generator training skupa (Last.fm izvođači)
│   ├── train_model.py               # RF vs XGBoost trainer
│   ├── run_tests.py                 # Sveobuhvatni integracijski testovi
│   └── models/                      # Mount točka za dijeljeni models volumen
│
├── prediction_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── service.py                   # ML inferencija + RabbitMQ consumer
│
├── seed-tools/
│   ├── Dockerfile
│   ├── package.json
│   └── seed.js                      # Opcionalni alat za ručno kreiranje MongoDB indeksa
│
├── mongo-init/
│   └── seed.js                      # Zastarjelo — samo dokumentacijski komentar
│
├── prometheus/
│   └── prometheus.yml               # Konfiguracija scrapeanja (15s interval)
│
├── grafana/
│   └── provisioning/                # Auto-provisioning dashboarda pri pokretanju
│       ├── datasources/
│       └── dashboards/
│
└── monitoring/
    └── prometheus.yml               # Alternativna scrape konfiguracija
```

---

## Brzi start

### Preduvjeti

- Docker i Docker Compose instalirani i pokrenuti
- Ticketmaster API ključ — besplatna registracija na [developer.ticketmaster.com](https://developer.ticketmaster.com/)
- Last.fm API ključ — besplatna registracija na [last.fm/api](https://www.last.fm/api)

### 1. Priprema API ključeva

```bash
cp .env.example .env
# Otvori .env i upiši svoje ključeve:
# TICKETMASTER_API_KEY=tvoj_kljuc
# LASTFM_API_KEY=tvoj_kljuc
```

### 2. Pokretanje sustava

```bash
docker compose up -d --build
```

Pričekaj ~30 sekundi da se svi kontejneri podignu. Provjeri status:

```bash
docker compose ps
```

Svi servisi trebaju biti `running` ili `healthy`.

### 3. Automatski dohvat podataka

Ako je baza prazna, backend automatski okida pipeline pri prvom startu.
Prati napredak:

```bash
docker compose logs analytics_worker -f --tail=60
# Vidjet ćeš: "Obrada grada: London, GB" ... "Pipeline gotov"
# Frontend se automatski osvježava čim podaci stignu (~2–5 min)
```

Ili ručno pokreni pipeline odmah:

```bash
curl -X POST http://localhost/api/sync-events
```

### 4. Pristup aplikaciji

| URL | Opis |
|-----|------|
| http://localhost/ | Frontend aplikacija |
| http://localhost:3000/ | Grafana (`admin` / `admin`) |
| http://localhost:15672/ | RabbitMQ Management (`guest` / `guest`) |
| http://localhost:8080/ | Traefik dashboard |
| http://localhost:9090/ | Prometheus |

### 5. ML model za dinamičke cijene (opcionalno)

ML model se automatski trenira svake nedjelje u 4:00 (Celery Beat). Za ručno pokretanje:

```bash
# Korak 1: Generiraj training podatke (~30 min, poziva Last.fm API)
docker compose exec analytics_worker python generate_training_data.py
# Dohvaća top 30 izvođača za 10 žanrova → ~33.000 training zapisa u MongoDB

# Korak 2: Treniraj model (Random Forest vs XGBoost, spremi bolji)
docker compose exec analytics_worker python train_model.py
# Ispisuje RMSE oba modela i sprema pobjednika u /app/models/

# Korak 3: Provjeri status modela
curl http://localhost/api/model-status
```

### Zaustavljanje

```bash
# Zaustavi, ali zadrži podatke
docker compose down

# Zaustavi i obriši sve podatke (baza, modeli)
docker compose down -v
```

---

## Varijable okoline

Kopiraj `.env.example` u `.env` i popuni vrijednosti:

| Varijabla | Opis | Obavezno |
|-----------|------|----------|
| `TICKETMASTER_API_KEY` | Ticketmaster Discovery API ključ | Da |
| `LASTFM_API_KEY` | Last.fm API ključ | Da |

Bez ovih ključeva pipeline preskače dohvat podataka i baza ostaje prazna.

---

## Servisni katalog

Svi servisi rade na dijeljenom Docker `app-net` mreži.

### `traefik`
Edge reverse proxy i load balancer. Port 80 za promet, 8080 za dashboard, 8082 za Prometheus metrike. Routing pravila deklarirana su putem Docker labela.

### `web1` / `web2`
Dvije NGINX instance koje servira statički frontend u round-robin načinu. Bez stanja — čitaju datoteke s read-only bind mounta.

### `backend`
Flask + Socket.IO core. Odgovornosti:
- REST API pod `/api/*`
- Socket.IO real-time kanal pod `/socket.io/*`
- RabbitMQ **producer** za `table_events` fanout exchange (rezervacije/otkazivanja)
- RabbitMQ **consumer thread** koji re-broadcastira na Socket.IO klijente u sobi eventa
- RabbitMQ **producer** za `price_update_queue` (asinkroni zahtjevi za cijene)
- Redis read-through cache za stolove (`tables_list_<id>`, 1h TTL) i event feed (60s TTL)
- Prometheus `/metrics` endpoint
- **Startup bootstrap thread**: automatski okida `run_data_pipeline` ako je kolekcija `events` prazna

### `analytics_worker`
Drugi Python kontejner iz iste backend slike, pokreće `celery -A tasks worker --beat`. Izvršava:
- `generate_daily_report` — agregira metrike u `reports` svakih 60 sekundi
- `run_data_pipeline` — jednom dnevno dohvaća 20 globalnih gradova, obogaćuje s Last.fm, upsertira klubove/evente/stolove u MongoDB, invalidira Redis cache
- `run_generate_training_data` — svake nedjelje u 3:00 regenerira ML training skup
- `run_train_model` — svake nedjelje u 4:00 trenira i sprema novi ML model

### `prediction_service`
Namjenski Flask mikroservis koji posjeduje ML model:
- Učitava `pricing_model.pkl` i `feature_cols.pkl` s dijeljenog `models` volumena
- Radi u degradiranom modu (HTTP 503) ako model još nije treniran
- Background daemon thread svakih 5 minuta provjerava postoji li novija verzija modela i reučitava je bez restarta kontejnera
- Background daemon thread konzumira `price_update_queue`; NACK bez requeuea ako model nije dostupan
- Cacheira predikcije u Redis (`price_prediction_<id>`, TTL 300s)
- Ažurira `current_price` i zapisuje u `price_log` kada predviđena cijena odstupa >5 EUR

### `mongo`
MongoDB 7. Podatci pohranjeni u trajnom Docker volumenu `mongo_`.

### `seed-tools`
Opcionalni Node.js alat za ručno kreiranje MongoDB indeksa. **Nije dio normalnog pokretanja** — indeksi se automatski kreiraju u `backend/app.py` pri svakom startu. Korisno samo ako se baza ručno čisti.

```bash
# Ručno kreiranje indeksa ako je potrebno
docker compose run --rm seed
```

### `rabbitmq`
RabbitMQ 3.12 s management pluginom. Hostera:
- `table_events` fanout exchange — real-time eventi rezervacija
- `price_update_queue` trajni queue — asinkroni zahtjevi za ML cijene

Docker healthcheck (`rabbitmq-diagnostics -q ping`) osigurava da ovisni servisi čekaju dok RabbitMQ ne bude potpuno spreman.

### `redis`
In-memory cache za liste stolova, event feedove i odgovore prediction servisa.

### `prometheus`
Skuplja metrike svakih 15s od backenda i Traefika.

### `grafana`
Vizualizira Prometheus metrike. Auto-provisioning dashboarda iz `grafana/provisioning/` direktorija pri pokretanju — nema potrebe za ručnom konfiguracijom.  
Port 3000, pristupni podaci: `admin` / `admin`.

---

## MongoDB kolekcije

| Kolekcija | Popunjava | Svrha |
|-----------|-----------|-------|
| `clubs` | `run_data_pipeline` | Jedan dokument po Ticketmaster venue-u; ključan po `id = "tm-<venue_id>"`. Polja: name, city, country, address, capacity, lat/lon. |
| `events` | `run_data_pipeline` | Jedan dokument po TM eventu, vezan na venue putem `club_id`. Polja: `ticketmaster_id`, `artist_name`, `image_url`, `event_date`, `artist_listeners`, `artist_playcount`, `genre_encoded`, `base_price`, `current_price`. |
| `tables` | `run_data_pipeline` | 20 slobodnih stolova po eventu, kreiraju se pri prvom pipeline runu. Vezani na event putem `event_id`. |
| `reservations` | `backend` | Append-only audit log svake rezervacije stola. |
| `users` | `backend` | Registar korisničkih imena. |
| `tickets` | `backend` | Vlasništvo ulaznica po korisniku i eventu. |
| `reports` | `analytics_worker` | Dnevni agregatni snimci (broj rezervacija i ulaznica). |
| `ml_training_data` | `generate_training_data.py` | Training zapisi: stvarni Last.fm izvođači × 10 kapacitetnih razina × 11 vremenskih scenarija (~33.000 zapisa). |
| `price_log` | `prediction_service` | Append-only log svake ML-pokrenute promjene cijene (stara → nova). |
| `model_metadata` | `train_model.py` | Ime pobjedničkog modela, RMSE oba modela, lista featureova, veličina training skupa, timestamp. |

---

## HTTP API referenca

### Backend (rutirano kroz Traefik na portu 80)

| Metoda | Putanja | Opis |
|--------|---------|------|
| GET | `/api/clubs` | Lista venue-a. Opcionalni filteri: `?city=`, `?country=`. Vraća `event_count` po venue-u putem `$lookup` agregacije. |
| POST | `/api/clubs` | Ručno ubacivanje kluba. |
| GET | `/api/clubs/<club_id>/events` | Eventi za venue, sortirani po datumu uzlazno. |
| GET | `/api/events` | Globalni event feed. Filteri: `?city=`, `?country=`, `?genre=`, `?q=` (full-text), `?limit=` (default 100, max 500). Redis cache 60s. |
| GET | `/api/events/<event_id>` | Puni dokument eventa po `id` ili `ticketmaster_id`. |
| GET | `/api/cities` | Agregirani popis gradova + broj evenata (za filter dropdown). |
| POST | `/api/sync-events` | Ručno okida `run_data_pipeline` putem Celerya. Vraća `task_id`. |
| GET | `/api/events/<event_id>/tables` | Stolovi za event (Redis cache, 1h TTL). |
| POST | `/api/events/<event_id>/tables/<table_id>/reserve` | Rezervacija stola (RabbitMQ broadcast + invalidacija cachea). |
| POST | `/api/events/<event_id>/tables/<table_id>/cancel` | Otkazivanje rezervacije (samo vlasnik, provjera vlasništva). |
| POST | `/api/users` | Kreiranje / provjera korisnika. |
| POST | `/api/users/<username>/buy-ticket/<event_id>` | Kupnja ulaznice. |
| GET | `/api/users/<username>/has-ticket/<event_id>` | Provjera vlasništva ulaznice. |
| GET | `/api/reports` | Zadnjih 10 dnevnih izvještaja. |
| GET | `/api/events/<event_id>/pricing` | `{base_price, current_price, high_demand, ...}`. Redis cache 60s. |
| POST | `/api/events/<event_id>/request-price-update` | Ručno šalje pricing featureove u prediction queue. |
| GET | `/api/price-log` | Zadnjih 50 ML-pokrenenih promjena cijena. |
| GET | `/api/model-status` | Proxy prema `prediction_service /model-info`. |
| GET | `/metrics` | Prometheus scrape endpoint. |

### Prediction Service (rutirano kroz Traefik na portu 80)

| Metoda | Putanja | Opis |
|--------|---------|------|
| POST | `/predict-price` | Ulaz: `{artist_listeners, artist_playcount, genre_encoded, venue_capacity, days_until_event, tickets_sold_ratio, day_of_week, event_id, current_price}`. Vraća predviđenu cijenu; ažurira `price_log` i event ako je razlika >5 EUR. |
| GET | `/model-info` | Zadnji `model_metadata` dokument. |
| GET | `/health` | `{"status": "ok", "model_loaded": true/false}`. |
| GET | `/metrics` | Prometheus metrike prediction servisa. |

### Real-time kanal (Socket.IO)

| Event | Smjer | Opis |
|-------|-------|------|
| `table_updated` | Server → klijent | Emitira se u sobi `event_<id>` pri svakoj rezervaciji ili otkazivanju. |
| `price_updated` | Server → klijent | Emitira se u sobi `event_<id>` kada ML model promijeni cijenu. Payload: `{event_id, current_price, high_demand}`. |
| `join_event` | Klijent → server | Klijent se pridružuje sobi eventa da prima ažuriranja. |

---

## Celery rasporednik

Konfiguracija u `backend/celery_config.py`:

| Naziv taska | Raspored | Opis |
|-------------|----------|------|
| `generate_daily_report` | Svakih 60 sekundi | Agregira broj rezervacija i ulaznica u `reports` kolekciju. |
| `run_data_pipeline` | Jednom dnevno (86400s) | Puni dohvat Ticketmaster + Last.fm za svih 20 gradova. |
| `run_generate_training_data` | Svake nedjelje u 3:00 UTC | Regenerira ML training skup (~33.000 zapisa). |
| `run_train_model` | Svake nedjelje u 4:00 UTC | Trenira Random Forest i XGBoost, sprema pobjednički model. |

---

## Dinamičke cijene — ML pipeline

### Tok podataka

```
Last.fm API (tag.gettopartists)
        │
        │  top 30 izvođača × 10 žanrova = ~300 izvođača
        ▼
generate_training_data.py
        │
        │  za svakog izvođača: 10 kapaciteta × 11 vremenskih scenarija
        │  = 110 zapisa po izvođaču = ~33.000 ukupno
        ▼
MongoDB: ml_training_data
        │
        ▼
train_model.py
        │
        │  80% train / 20% test split
        │  Random Forest (100 stabala) vs XGBoost (200 stabala)
        │  pobjeđuje niži RMSE
        ▼
/app/models/pricing_model.pkl   (dijeljeni Docker volumen)
        │
        ▼
prediction_service/service.py
        │
        │  konzumira price_update_queue
        │  poziva model.predict()
        │  ako razlika >5 EUR → ažuriraj MongoDB + Redis + WebSocket
        ▼
Korisnik vidi ažuriranu cijenu u pregledniku (bez refresha)
```

### Feature vektor (7 značajki)

| Feature | Izvor | Transformacija |
|---------|-------|----------------|
| `log_listeners` | Last.fm listeners | `log10(x + 1)` |
| `log_playcount` | Last.fm playcount | `log10(x + 1)` |
| `genre_encoded` | Last.fm tagovi → GENRE_MAP | 0–15 |
| `venue_capacity` | Ticketmaster venue | cijeli broj |
| `days_until_event` | datum eventa – danas | cijeli broj |
| `tickets_sold_ratio` | rezervirani / ukupni stolovi | 0.0–1.0 |
| `day_of_week` | datum eventa | 0 (pon) – 6 (ned) |

### GENRE_MAP — enkodiranje žanra

```python
GENRE_MAP = {
    "electronic": 1, "techno": 2, "house": 3, "trance": 4,
    "drum and bass": 5, "dubstep": 6, "edm": 7, "dance": 8,
    "pop": 9, "rock": 10, "hip-hop": 11, "jazz": 12,
    "classical": 13, "metal": 14, "indie": 15, "other": 0,
}
```

Elektronički žanrovi (kodovi 1–8) nose premiju od 20% u determinističkoj formuli.

### Deterministička bazna formula (`pipeline_task.py`)

```python
popularity_score = min(log10(artist_listeners) / 7.0, 1.0)
capacity_factor  = max(0.5, 1.0 - (venue_capacity / 10000) * 0.3)
urgency_factor   = 1.3 if days <= 7 else 1.1 if days <= 30 else 1.0
genre_factor     = 1.2 if genre_encoded in [1..8] else 1.0

base  = 20 + (popularity_score * 130 * capacity_factor * genre_factor)
price = round(base * urgency_factor, 2)
```

---

## Nadzor sustava

### Prometheus metrike — backend

| Metrika | Tip | Opis |
|---------|-----|------|
| `http_requests_total{method, endpoint, status}` | Counter | Ukupan broj HTTP zahtjeva |
| `http_request_duration_seconds{endpoint}` | Histogram | Latencija po endpointu |

### Prometheus metrike — prediction_service

| Metrika | Tip | Opis |
|---------|-----|------|
| `predictions_total` | Counter | Ukupan broj ML predikcija |
| `price_changes_total` | Counter | Broj promjena cijena (razlika >5 EUR) |
| `prediction_duration_seconds` | Histogram | Trajanje jedne predikcije |
| `model_loaded` | Gauge | 1 = model učitan, 0 = model nije dostupan |
| `cache_hits_total` | Counter | Broj Redis cache pogodaka |

### Grafana dashboard

Dashboard se automatski provisiona pri pokretanju iz `grafana/provisioning/`.  
Pristup: http://localhost:3000 (`admin` / `admin`)

Paneli dashboarda:
- Predikcije po sekundi
- Promjene cijena
- Status ML modela (učitan / nije)
- Prosječno trajanje predikcije
- Cache hit rate (Redis)
- HTTP zahtjevi prema backendu
- Latencija backenda

---

## Testiranje

Sveobuhvatni integracijski testovi pokrivaju sve komponente sustava:

```bash
docker compose exec backend python run_tests.py
```

Testovi obuhvaćaju:

| Kategorija | Što se testira |
|------------|----------------|
| Unit testovi | `calculate_base_price`, `encode_genre`, `compute_days_until_event`, `compute_default_tickets_sold_ratio` |
| MongoDB integracija | Postojanje kolekcija, indeksi, CRUD operacije |
| Redis integracija | Cache za stolove, invalidacija |
| RabbitMQ integracija | Objavljivanje i primanje poruka |
| REST API | `/api/clubs`, `/api/events`, `/api/tables`, rezervacija, otkazivanje, ulaznice |
| Prediction Service | `/predict-price`, `/health`, `/model-info` |
| Prometheus | Scrape endpoint na backendu i prediction servisu |

---

## Poznata ograničenja

| Ograničenje | Detalj |
|-------------|--------|
| Bez autentikacije | Korisničko ime pohranjuje se bez provjere u `localStorage`; nema lozinke ni JWT tokena. |
| Bez validacije ulaza | POST endpointi ne validiraju tipove ni opsege vrijednosti. |
| Bez rate limitinga | API je otvoren za zlouporabu. |
| ML model bez verzioniranja | Svaki retrain prepisuje prethodne `.pkl` datoteke — nema rollbacka na stariji model. |
| `generate_training_data.py` briše kolekciju | `db.ml_training_data.drop()` briše bez potvrde — pokretanje brišu sve prethodne training podatke. |
| Trajanje generiranja | Generiranje training podataka traje ~30 minuta zbog rate limiting Last.fm API-ja (pauza 0.3s po izvođaču). |
