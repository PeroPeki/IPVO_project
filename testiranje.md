# Testiranje — NightClub Manager v2

Ručna provjera svih funkcionalnosti aplikacije, organizirana po ulogama.
Redoslijed je bitan: kasnije sekcije ovise o podacima iz ranijih (klub → event → karte/rezervacije).

---

## 0. Priprema

- [ ] `.env` postoji s ispunjenim `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` i `JWT_SECRET`
- [ ] `docker compose up -d --build` — svih 8 kontejnera je `Up` (`docker compose ps`)
- [ ] Seed superadmina: `docker compose exec backend python seed_superadmin.py`
- [ ] Health check: http://localhost/api/health vraća 200
- [ ] Admin panel se učitava: http://admin.localhost/
- [ ] (Za plaćanja) Stripe webhook: `stripe listen --forward-to localhost/api/webhooks/stripe`, `whsec_...` u `.env`, restart backenda — bez toga app koristi `/api/tickets/confirm` fallback
- [ ] Mobilna app: `cd mobile && npm install`, pa `EXPO_PUBLIC_API_URL=http://<IP-računala> npx expo start` (Expo Go ne vidi `localhost`)

**Stripe test kartice:** `4242 4242 4242 4242` (uspjeh), `4000 0000 0000 0002` (odbijena), bilo koji budući datum + CVC.

---

## 1. Superadmin (web — admin.localhost)

- [ ] Prijava sa `superadmin / superadmin123`
- [ ] Prijava s krivom lozinkom → greška, bez prijave
- [ ] Kreiranje novog kluba (ime, slug, grad, kapacitet)
- [ ] Upload slike kluba (bez `CLOUDINARY_URL` sprema se lokalno — provjeri da se slika prikazuje)
- [ ] Uređivanje postojećeg kluba
- [ ] Kreiranje admina za klub (email + lozinka)
- [ ] Superadmin vidi i može uređivati **sve** klubove

## 2. Admin kluba (web)

### Prijava i eventi
- [ ] Prijava kao admin kluba (kreiran u koraku 1)
- [ ] Admin vidi **samo svoj klub** (ne tuđe podatke)
- [ ] Kreiranje eventa: naziv, datum, lineup, tipovi karata (npr. Regular 20 €, VIP 50 €, ograničena količina)
- [ ] Uređivanje eventa
- [ ] Objava eventa (`is_published`) — tek tada je vidljiv u mobilnoj app
- [ ] Brisanje eventa → event je otkazan, ne obrisan

### Floor map editor
- [ ] Upload tlocrta (pozadinska slika)
- [ ] Dodavanje stolova klikom na mapu (pozicija u %)
- [ ] Pomicanje stola drag & dropom, spremanje
- [ ] Definiranje sekcija i dodjela stolova sekcijama
- [ ] Postavljanje min. depozita / kapaciteta po stolu

### Meni pića
- [ ] Kreiranje kategorija (npr. Žestoka pića, Kokteli)
- [ ] Dodavanje stavki s cijenama
- [ ] Toggle dostupnosti stavke (nedostupna stavka se ne smije moći naručiti u mobilnoj app)

### Osoblje
- [ ] Kreiranje hostese (email + PIN)
- [ ] Kreiranje konobara (email + PIN)
- [ ] Dodjela sekcija konobaru
- [ ] Promjena dodjele sekcija — narudžbe idu novom konobaru

## 3. Gost (mobilna app)

### Autentikacija
- [ ] Registracija emailom i lozinkom
- [ ] Registracija s već postojećim emailom → greška
- [ ] Prijava / odjava / ponovna prijava
- [ ] Google prijava (ako je konfigurirana)
- [ ] Facebook prijava (ako je konfigurirana)
- [ ] Token refresh: ostavi app otvorenu dulje — sesija ne smije "ispasti"

### Pregled
- [ ] Home prikazuje nadolazeće evente
- [ ] Explore: lista klubova, filter po gradu
- [ ] Detalji kluba (galerija, lokacija, eventi)
- [ ] Detalji eventa: lineup, tipovi karata s cijenama
- [ ] Neobjavljeni event **nije** vidljiv

### Kupnja ulaznice
- [ ] Kupnja Regular karte testnom karticom `4242...` → uspjeh
- [ ] Karta se pojavi u tabu "Tickets" s QR kodom
- [ ] Kupnja odbijenom karticom `4000...0002` → jasna greška, karta se NE kreira
- [ ] Apple Pay / Google Pay opcija u Payment Sheetu (na fizičkom uređaju)
- [ ] Rasprodano: kupi sve karte jednog tipa → daljnja kupnja onemogućena
- [ ] Otkazivanje karte → refund u Stripe test dashboardu, karta označena otkazanom

### Rezervacija stola
- [ ] Otvaranje SVG mape za event — stolovi na pozicijama iz editora
- [ ] Slobodni i zauzeti stolovi vizualno različiti
- [ ] Rezervacija slobodnog stola → potvrda
- [ ] VIP stol traži depozit → Stripe naplata → depozit postaje **kupon za piće**
- [ ] Real-time: rezerviraj stol na jednom uređaju → na drugom uređaju stol **odmah** postane zauzet (bez refresha)
- [ ] Dvostruka rezervacija: dva uređaja istovremeno rezerviraju isti stol → samo jedan uspije
- [ ] Otkazivanje rezervacije → stol se oslobodi na mapi
- [ ] "Moje rezervacije" prikazuje ispravne statuse

### Naručivanje pića
- [ ] Meni dostupan nakon check-ina za stol
- [ ] Dodavanje u košaricu, promjena količina, uklanjanje
- [ ] Slanje narudžbe → status "placed"
- [ ] Plaćanje karticom (Stripe) i opcija gotovine
- [ ] Kupon od depozita umanjuje iznos narudžbe
- [ ] Status narudžbe se real-time ažurira (placed → accepted → delivered)

## 4. Hostesa (mobilna app — staff prijava)

- [ ] Prijava emailom + PIN-om; krivi PIN → greška
- [ ] Lista gostiju eventa, pretraga po prezimenu
- [ ] Check-in karte (ručno i skeniranjem QR koda)
- [ ] Ponovni check-in iste karte → upozorenje/greška (ne smije proći dvaput)
- [ ] Check-in rezervacije → gost tek tada može naručivati piće
- [ ] Live statistike ulaska se ažuriraju nakon svakog check-ina

## 5. Konobar (mobilna app — staff prijava)

- [ ] Prijava emailom + PIN-om
- [ ] Nova narudžba iz **njegove sekcije** stigne real-time (bez refresha)
- [ ] Narudžba iz tuđe sekcije mu se NE prikazuje
- [ ] Prihvat narudžbe → gost vidi promjenu statusa
- [ ] Označavanje dostavljeno
- [ ] Naplata gotovinom / karticom
- [ ] Otkazivanje narudžbe

## 6. Admin — live nadzor i izvještaji (web)

- [ ] Live dashboard eventa: broj ušlih, zauzetost stolova, aktivne narudžbe — ažurira se u realnom vremenu
- [ ] Reservations stranica prikazuje sve rezervacije eventa sa statusima
- [ ] Reports: dnevni agregati (karte / rezervacije / piće / prihodi)
- [ ] Celery dnevni izvještaj: `docker compose logs analytics_worker` — beat task se izvršava bez grešaka
- [ ] Email podsjetnici: bez `SENDGRID_API_KEY` sadržaj emaila se logira (provjeri u logovima backenda/workera)

## 7. Infrastruktura i nadzor

- [ ] Traefik dashboard: http://localhost:8080 — routeri `api` i `admin` zeleni
- [ ] Prometheus: http://localhost:9090/targets — svi targeti `UP`
- [ ] Grafana: http://localhost:3001 (`admin`/`admin`) — dashboard s panelima prikazuje podatke nakon malo prometa
- [ ] `/api/metrics` vraća Prometheus metrike
- [ ] Restart test: `docker compose restart` → sve se digne, podaci sačuvani (Mongo volume)
- [ ] Integracijski testovi: `docker compose exec backend python run_tests.py`

## 8. Sigurnost i rubni slučajevi

- [ ] Pristup admin API-ju bez tokena → 401
- [ ] Gostov token na admin endpointu (npr. `POST /api/events`) → 403
- [ ] Admin kluba A ne može mijenjati podatke kluba B
- [ ] Hostesa/konobar ne mogu na admin endpointe
- [ ] Istekli/neispravni JWT → 401, mobilna app radi refresh ili traži ponovnu prijavu
- [ ] Kupnja karte za otkazani event → greška
- [ ] Narudžba nedostupne stavke menija → greška
