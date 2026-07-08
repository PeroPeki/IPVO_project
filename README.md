# NightClub Manager v2

> Platforma za noćne klubove u Hrvatskoj — kupnja ulaznica, rezervacija stolova s
> depozitom, naručivanje pića za stol i alati za osoblje. MVP fokus: **Zrće (Novalja)**.

[![Stack](https://img.shields.io/badge/stack-Docker%20Compose-2496ED)](https://docs.docker.com/compose/)
[![Backend](https://img.shields.io/badge/backend-Flask%203%20%7C%20Python%203-3776AB)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/database-MongoDB%207-47A248)](https://www.mongodb.com/)
[![Realtime](https://img.shields.io/badge/realtime-Redis%20Pub%2FSub%20%2B%20Socket.IO-DC382D)](https://redis.io/)
[![Payments](https://img.shields.io/badge/payments-Stripe-635BFF)](https://stripe.com/)
[![Mobile](https://img.shields.io/badge/mobile-React%20Native%20%2B%20Expo-61DAFB)](https://expo.dev/)
[![Admin](https://img.shields.io/badge/admin-React%20%2B%20Vite-646CFF)](https://vitejs.dev/)

---

## Što sustav radi

| Uloga | Mogućnosti |
|-------|-----------|
| **Gost (mobilna app)** | Registracija/prijava (email, Google, Facebook), pregled klubova i evenata, kupnja ulaznica (Stripe — kartice, Apple Pay, Google Pay), QR karta, rezervacija stola na interaktivnoj SVG mapi s real-time dostupnošću, VIP depozit koji se pretvara u kupon za piće, naručivanje pića za stol |
| **Hostesa (web)** | Prijava emailom + PIN-om, pretraga gostiju po prezimenu, check-in karata i rezervacija, live statistike ulaska |
| **Konobar (web)** | Prijava emailom + PIN-om, narudžbe svoje sekcije, prihvat i dostava, potvrda naplate gotovine |
| **Admin kluba (web)** | CRUD evenata s tipovima karata, floor map editor (upload tlocrta + postavljanje stolova klikom + sekcije), meni pića, osoblje i dodjela sekcija, live dashboard eventa, izvještaji |
| **Superadmin (web)** | Kreiranje klubova i njihovih admina, sve što i admin — za bilo koji klub |

---

## Arhitektura

```
   ┌──────────────────┐    ┌───────────────────┐
   │  Mobilna app     │    │  Admin panel      │
   │  (React Native + │    │  (React + Vite)   │
   │   Expo Router)   │    │  admin.localhost  │
   └───────┬──────────┘    └────────┬──────────┘
           │ HTTP / WebSocket       │
           ▼                        ▼
   ┌──────────────────────────────────────────┐      ┌──────────────┐
   │              Traefik :80                 │◄─────│  Prometheus  │
   │  /api /socket.io /metrics → backend      │      │    :9090     │
   │  admin.localhost → admin (NGINX)         │      └──────┬───────┘
   └───────────────────┬──────────────────────┘             ▼
                       ▼                             ┌──────────────┐
   ┌──────────────────────────────────────────┐      │   Grafana    │
   │   backend (Flask + Socket.IO + JWT)      │      │    :3001     │
   │   Stripe PaymentIntents + webhook        │      └──────────────┘
   └──────┬──────────────────┬────────────────┘
          │                  │
          ▼                  ▼
   ┌─────────────┐    ┌─────────────────────────┐
   │   MongoDB   │    │   Redis                 │
   │   :27017    │    │   db0: Pub/Sub + cache  │
   └─────▲───────┘    │   db1/db2: Celery       │
         │            └───────────▲─────────────┘
   ┌─────┴────────────────────────┴─────┐
   │  analytics_worker (Celery + Beat)  │
   │  dnevni izvještaji + podsjetnici   │
   └────────────────────────────────────┘
```

**Real-time tok:** backend i Celery worker emitiraju kroz Socket.IO
**Redis message queue** (`realtime.publish`) → Socket.IO server isporučuje
u sobe: `event_{id}` (mapa stolova), `waiter_{id}` (konobar),
`bar_{event_id}` (barski zaslon). Zahvaljujući message queueu backend se
može horizontalno skalirati (više replika dijeli isti queue).
Socket konekcija zahtijeva važeći JWT (`auth: {token}`), a sobe
`waiter_*`/`bar_*` dostupne su samo osoblju.

---

## Tehnološki stack

| Sloj | Tehnologija |
|------|-------------|
| Backend API | Flask 3 (Python 3.12), flask-jwt-extended (+ revokacija), flask-limiter, Flask-SocketIO (gevent + WebSocket worker) |
| Baza | MongoDB 7 |
| Real-time + cache + broker | Redis (Socket.IO message queue, rate-limit/blocklist, Celery broker/backend) |
| Plaćanja | Stripe (PaymentIntents, Payment Sheet, webhookovi, refundi) |
| Periodički zadatci | Celery + Celery Beat |
| Mobilna aplikacija | React Native + Expo (Expo Router, NativeWind, Zustand, @stripe/stripe-react-native, react-native-svg, socket.io-client) |
| Admin panel | React 18 + Vite + TypeScript, react-router |
| Edge / LB | Traefik 2.11 |
| Nadzor | Prometheus + Grafana (auto-provisioning) |
| Slike | Cloudinary (opcionalno; fallback lokalni disk) |
| Email | SendGrid (opcionalno; fallback log) |

### Paleta boja (tamna tema, bez light modea)

```
bgDark  #0A0010 · bgCard  #1A0030 · accent1 #CC00FF · accent2 #8B00CC
accent3 #4A0080 · text    #F0E6FF · muted   #9B7BC0
success #34C759 · warning #F4B860 · error   #FF3B30
```

---

## Struktura repozitorija

```
IPVO_projekt/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app.py                  # Flask + Socket.IO (auth) + JWT + webhook + metrike
│   ├── extensions.py           # Rate limiter + Redis (blocklist tokena)
│   ├── db.py                   # Mongo konekcija + indeksi (v2 shema)
│   ├── auth_utils.py           # JWT role, hash lozinki, serijalizacija
│   ├── realtime.py             # Socket.IO emit kroz Redis message queue
│   ├── stripe_service.py       # PaymentIntenti (karte, depoziti, piće)
│   ├── payments.py             # Potvrde plaćanja (webhook logika)
│   ├── reservation_service.py  # Rezervacije, depozit, kupon, check-in
│   ├── order_service.py        # Narudžbe pića + dodjela konobara
│   ├── email_service.py        # SendGrid / dev log
│   ├── upload_service.py       # Cloudinary / lokalni disk
│   ├── tasks.py                # Celery: izvještaji + podsjetnici
│   ├── celery_config.py        # Redis broker + beat raspored
│   ├── migrate_v2.py           # Migracija: briše v1 kolekcije
│   ├── seed_superadmin.py      # Inicijalni superadmin
│   ├── run_tests.py            # Integracijski testovi
│   └── routes/                 # Blueprintovi: auth, clubs, events, tickets,
│                               # hostess, floor_maps, reservations, menu,
│                               # orders, admin
├── mobile/                     # Expo React Native aplikacija
│   ├── app/                    # Expo Router ekrani
│   │   ├── (auth)/             # login, register, oauth
│   │   ├── (tabs)/             # home, explore, tickets, profile
│   │   ├── club/[slug].tsx     # detalji kluba
│   │   ├── event/[id].tsx      # detalji eventa + kupnja karte
│   │   ├── reservation/        # SVG mapa + potvrda/depozit
│   │   └── order/              # meni → košarica → naplata
│   ├── components/             # FloorMap, TableMarker, PaymentSheet…
│   ├── hooks/  services/  store/  constants/
├── admin/                      # React admin panel (Vite)
│   └── src/pages/              # Dashboard, Clubs, Events, FloorMapEditor,
│                               # Staff, Menu, Reservations, LiveDashboard, Reports
├── prometheus/prometheus.yml
└── grafana/provisioning/       # Datasource + dashboard auto-provisioning
```

---

## Brzi start

### 1. Priprema okoline

```bash
cp .env.example .env
# Upiši Stripe test ključeve (https://dashboard.stripe.com/test/apikeys)
# i generiraj JWT tajnu: openssl rand -hex 32
```

### 2. Pokretanje

```bash
docker compose up -d --build
```

### 3. Inicijalni podaci

```bash
# Ako nadograđuješ s v1 — očisti stare kolekcije:
docker compose exec backend python migrate_v2.py

# Kreiraj superadmina (default: superadmin / superadmin123):
docker compose exec backend python seed_superadmin.py
```

### 4. Pristup

| URL | Servis |
|-----|--------|
| http://localhost/api/health | Backend health check |
| http://admin.localhost/ | Admin panel (superadmin / superadmin123) |
| http://localhost:8080/ | Traefik dashboard |
| http://localhost:9090/ | Prometheus |
| http://localhost:3001/ | Grafana (`admin` / `admin`) |

### 5. Mobilna aplikacija (Expo)

```bash
cd mobile
npm install
# U .env ili shellu postavi IP računala (Expo Go ne vidi "localhost"):
EXPO_PUBLIC_API_URL=http://192.168.x.x \
EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_... \
npx expo start
```

### 6. Stripe webhook (lokalni razvoj)

```bash
stripe listen --forward-to localhost/api/webhooks/stripe
# whsec_... upiši u .env kao STRIPE_WEBHOOK_SECRET pa restartaj backend
```

Bez webhooka mobilna app poziva `/api/tickets/confirm` kao fallback potvrdu.

---

## Varijable okoline

| Varijabla | Opis | Obavezno |
|-----------|------|----------|
| `STRIPE_SECRET_KEY` | Stripe tajni ključ (`sk_test_...`) | Da (za plaćanja) |
| `STRIPE_PUBLISHABLE_KEY` | Stripe javni ključ | Da (za plaćanja) |
| `STRIPE_WEBHOOK_SECRET` | Potpis webhooka (`whsec_...`) | Za webhookove |
| `JWT_SECRET` | Tajna za potpisivanje JWT tokena | Da |
| `CLOUDINARY_URL` | Cloudinary za slike | Ne (fallback: disk) |
| `SENDGRID_API_KEY` | SendGrid za emailove | Ne (fallback: log) |

---

## MongoDB kolekcije (v2 shema)

| Kolekcija | Svrha | Ključni indeksi |
|-----------|-------|-----------------|
| `superadmins` | Superadmin računi | `username` (unique) |
| `clubs` | Klubovi (lokacija, kapacitet, galerija, socijalne mreže) | `slug` (unique), `location.city`, `is_active` |
| `club_admins` | Admini klubova | `email` (unique) |
| `hostesses` / `waiters` | Osoblje (PIN prijava; konobari imaju `assigned_sections`) | `email` (unique), `club_id` |
| `users` | Korisnici (email/OAuth, Stripe customer) | `email` (unique), `auth_provider_id` |
| `events` | Eventi s ugniježđenim `ticket_types` i `lineup` | `club_id`, `date`, `is_published` |
| `tickets` | Karte s QR kodom (UUID v4) i Stripe PI | `user_id`, `event_id`, `qr_code` (unique) |
| `floor_maps` | Tlocrt kluba: stolovi (% koordinate) + sekcije | `club_id` |
| `table_reservations` | Rezervacije: statusi `pending/confirmed/cancelled/checked_in/no_show`, depozit, kupon | partial unique `(event_id, table_id)` za aktivne |
| `menus` | Meni pića: kategorije → stavke | `club_id` |
| `drink_orders` | Narudžbe: `placed/accepted/preparing/delivered/cancelled` | `event_id`, `waiter_id`, `order_status` |
| `reports` | Dnevni agregati po klubu (karte/rezervacije/piće/prihodi) | `club_id + date` |

Atomnost rezervacija: partial unique indeks na `(event_id, table_id)` s
filterom `active_hold: true` sprječava dvostruku rezervaciju istog stola
čak i pri istovremenim zahtjevima.

---

## HTTP API referenca (sažetak)

### Autentikacija `/api/auth/`
`POST register` · `POST login` · `POST google` · `POST facebook` ·
`POST refresh` (rotira refresh token) · `POST logout` (revocira token) ·
`POST admin/login` · `POST staff/login` (email + PIN, hashiran u bazi)

Sve auth rute imaju rate limiting po IP-u (flask-limiter + Redis);
staff login je najstroži (5/min) zbog 4-znamenkastog PIN-a.

### Klubovi `/api/clubs/`
`GET ?city=` · `GET :slug` · `POST` (superadmin) · `PUT :id` (admin) ·
`POST :id/upload-image`

### Eventi `/api/events/`
`GET` (filteri: club_id, city, date_from, date_to) · `GET upcoming` ·
`GET :id` · `POST` / `PUT :id` / `DELETE :id` (admin — DELETE je otkazivanje)

### Karte `/api/tickets/`
`POST purchase` (atomarno rezervira kvotu + Stripe PI + pending karta) ·
`POST confirm` (fallback) · `GET my` · `POST :id/cancel` (refund + vraća kvotu) ·
`GET /api/events/:id/tickets` i `.../ticket-stats` (admin)

### Hostesa `/api/hostess/`
`GET event/:id/guests?search=` · `POST checkin/ticket/:id` (`?by=qr` za QR) ·
`POST checkin/reservation/:id` · `GET event/:id/stats`

### Mape stolova `/api/floor-maps/`
`GET club/:id` · `GET event/:id` (s dostupnošću) · `POST` · `PUT :id` ·
`POST :id/upload-bg` · `PUT :id/tables` (drag&drop editor)

### Rezervacije `/api/reservations/`
`GET event/:id` (dostupnost) · `POST` · `POST :id/deposit` (Stripe) ·
`POST :id/cancel` (refund ako je na vrijeme) · `GET my` ·
`GET event/:id/all` (admin) · `PUT :id/checkin` (hostesa)

### Meni `/api/menu/`
`GET club/:id` · `POST` · `PUT :id` · `PATCH :id/item/:item_id/availability`

### Narudžbe `/api/orders/`
`POST` (samo s aktivnom rezervacijom!) · `GET waiter` · `PUT :id/accept` ·
`PUT :id/deliver` · `PUT :id/collect-cash` (potvrda naplate gotovine) ·
`PUT :id/cancel` (uz automatski refund ako je plaćeno karticom) ·
`POST :id/payment` (Stripe/gotovina) · `GET bar/:event_id` · `GET my`

### Admin `/api/admin/`
`GET dashboard` · `GET events/:id/live` · `GET reports` ·
`POST staff` · `PUT staff/:id/sections` · `GET staff`

### Ostalo
`POST /api/webhooks/stripe` · `GET /api/health` · `GET /metrics`

### Socket.IO
| Event | Smjer | Soba |
|-------|-------|------|
| `join_event` / `leave_event` | klijent → server | `event_{id}` |
| `join_waiter` / `join_bar` | klijent → server | `waiter_{id}` / `bar_{event_id}` |
| `table_updated` | server → klijent | `event_{id}` |
| `order_updated` | server → klijent | `waiter_{id}` + `bar_{event_id}` |

---

## Poslovna logika — depozit i kupon

1. Rezervacija **VIP separéa** kreira se sa statusom `pending` i rokom
   otkazivanja 24 h prije eventa. Ako depozit ne bude plaćen u roku od
   **15 minuta**, Celery task oslobađa stol (a zakašnjela uplata se
   automatski potvrđuje ako je stol još slobodan, inače refundira).
2. Gost plaća depozit (Stripe Payment Sheet) → webhook potvrđuje →
   status `confirmed`, a **cijeli iznos depozita postaje kupon**
   (`deposit_coupon_remaining`).
3. Pri narudžbi pića kupon se automatski primjenjuje (`apply_coupon`);
   ako pokrije cijelu narudžbu, ništa se ne naplaćuje.
   *Kupon je vezan uz gosta osobno i ne može se dijeliti.*
4. Otkazivanje **prije roka** → automatski Stripe refund depozita;
   nakon roka depozit propada.
5. Standardni stolovi nemaju depozit — odmah su `confirmed`.

Naručivanje pića dopušteno je **samo gostima s aktivnom rezervacijom**
(`confirmed` ili `checked_in`); ostali dobivaju poruku:
*„Naručivanje pića dostupno je samo gostima s rezerviranim stolom."*

---

## Celery rasporednik

| Task | Raspored | Opis |
|------|----------|------|
| `generate_daily_report` | jednom dnevno | Agregat po klubu: karte, rezervacije, narudžbe, prihodi (uklj. depozite) |
| `send_reservation_reminders` | svakih sat | Podsjetnik gostima ~24 h prije eventa (jednom po rezervaciji) |
| `expire_stale_payments` | svakih 5 min | Oslobađa stolove s neplaćenim VIP depozitom i vraća kvotu neplaćenih karata (TTL 15 min) |

Broker i result backend su Redis (`redis://redis:6379/1` i `/2`).

---

## Nadzor

- Backend izlaže `http_requests_total` i `http_request_duration_seconds`
  na `/metrics` (label `endpoint` je Flask ruta, ne sirovi path).
- Prometheus scrapea backend i Traefik svakih 15 s.
- Grafana (port **3001**) auto-provisiona dashboard „NightClub Manager v2":
  zahtjevi po ruti/statusu, p95 latencija, Traefik promet, brojači kupnji
  i rezervacija.

---

## Testiranje

```bash
docker compose exec backend python run_tests.py
```

Pokriveno: health, registracija/prijava/refresh/logout (revokacija), role
(403), superadmin kreiranje kluba/eventa/osoblja, staff PIN prijava, floor
mapa s dostupnošću, rezervacija + zaštita od duplikata, meni + narudžba s
gotovinom, konobarski accept/deliver/collect-cash, hostess check-in +
statistike, admin dashboard/live, Stripe granica (bez ključa kontrolirana
greška + provjera vraćanja kvote) i validacija neispravnog ObjectId-a.

Napomena: auth rute imaju rate limiting, pa učestalo ponavljanje testova
unutar iste minute može vratiti 429 na staff loginu.

---

## Poznata ograničenja (MVP)

| Ograničenje | Detalj |
|-------------|--------|
| Push notifikacije | Expo Notifications još nisu žičane; podsjetnici idu emailom (SendGrid) |
| Facebook OAuth | Backend ruta postoji; mobilni flow zahtijeva Facebook App ID |
| QR skener | Hostesa ima pretragu + ručni check-in; kamera skener (expo-camera) je pripremljen u ovisnostima |
| Barski zaslon | Dostupan kroz API (`GET /api/orders/bar/:event_id`) i konobarski ekran; zaseban veliki zaslon nije izrađen |
| Password reset / verifikacija emaila | Nisu implementirani (za produkciju obavezno) |
| TLS / HTTPS | Traefik sluša samo na :80 — za produkciju dodati Let's Encrypt resolver |
| Sign in with Apple | Potreban za App Store objavu uz Google/Facebook login |
