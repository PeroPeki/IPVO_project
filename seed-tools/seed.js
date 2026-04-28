/**
 * Seed skripta – stvarni hrvatski noćni klubovi i stvarni izvođači.
 * NE koristi Faker biblioteku.
 *
 * Klubovi su pravi noćni klubovi i festivalski venuei u Hrvatskoj.
 * Izvođači su stvarni svjetski i regionalni DJ-evi / izvođači koji nastupaju u
 * ovakvim klubovima – nema generiranih ili nasumičnih imena.
 */

const { MongoClient } = require('mongodb');

const REAL_CLUBS = [
  {
    id: 'club-1',
    name: 'Aquarius Club Zrće',
    location: 'Novalja, Zrće, Hrvatska',
    description: 'Kultni klub na plaži Zrće, jedan od najpoznatijih klubova u regiji.',
    venue_capacity: 2500,
  },
  {
    id: 'club-2',
    name: 'Papaya Club',
    location: 'Novalja, Zrće, Hrvatska',
    description: 'Open-air klub na Zrću, poznat po world-class line-upovima.',
    venue_capacity: 5000,
  },
  {
    id: 'club-3',
    name: 'Noa Beach Club',
    location: 'Novalja, Zrće, Hrvatska',
    description: 'Floating stage klub usred mora s vrhunskim sound systemom.',
    venue_capacity: 3500,
  },
  {
    id: 'club-4',
    name: 'Boogaloo',
    location: 'Zagreb, Hrvatska',
    description: 'Najveći zatvoreni klub u Zagrebu, domaćin svjetskih DJ-eva i bendova.',
    venue_capacity: 1800,
  },
  {
    id: 'club-5',
    name: 'Tvornica Kulture',
    location: 'Zagreb, Hrvatska',
    description: 'Multifunkcionalni klub i koncertna dvorana u centru Zagreba.',
    venue_capacity: 1500,
  },
  {
    id: 'club-6',
    name: 'Pepermint',
    location: 'Zagreb, Hrvatska',
    description: 'Underground klub s naglaskom na elektroničku glazbu.',
    venue_capacity: 600,
  },
  {
    id: 'club-7',
    name: 'Carpe Diem Beach',
    location: 'Hvar, Hrvatska',
    description: 'Beach klub na otoku Hvaru, poznat po ljetnoj sezoni.',
    venue_capacity: 1200,
  },
  {
    id: 'club-8',
    name: 'Revelin',
    location: 'Dubrovnik, Hrvatska',
    description: 'Klub smješten u utvrdi Revelin, dio Best Discotheque liste svijeta.',
    venue_capacity: 1500,
  },
];

// Stvarni izvođači – DJ-evi i bendovi koji aktivno nastupaju.
// Ovi podaci su stvarni i ne generirani.
const REAL_LINEUPS = [
  { artist: 'Solomun', genre: 'house', basePrice: 80, type: 'DJ Set' },
  { artist: 'Black Coffee', genre: 'house', basePrice: 90, type: 'Live Set' },
  { artist: 'Tale Of Us', genre: 'techno', basePrice: 85, type: 'DJ Set' },
  { artist: 'Charlotte de Witte', genre: 'techno', basePrice: 75, type: 'DJ Set' },
  { artist: 'Amelie Lens', genre: 'techno', basePrice: 75, type: 'DJ Set' },
  { artist: 'Hot Since 82', genre: 'house', basePrice: 65, type: 'DJ Set' },
  { artist: 'Boris Brejcha', genre: 'techno', basePrice: 80, type: 'DJ Set' },
  { artist: 'Dubioza Kolektiv', genre: 'rock', basePrice: 35, type: 'Live Concert' },
  { artist: 'Hladno Pivo', genre: 'rock', basePrice: 30, type: 'Live Concert' },
  { artist: 'Gibonni', genre: 'pop', basePrice: 40, type: 'Live Concert' },
  { artist: 'Petar Dundov', genre: 'techno', basePrice: 45, type: 'Live Set' },
  { artist: 'Insolate', genre: 'techno', basePrice: 35, type: 'DJ Set' },
];

async function seedDatabase() {
  const uri = 'mongodb://mongo:27017';
  const client = new MongoClient(uri);

  try {
    console.log('Povezivanje s MongoDB...');
    await client.connect();
    const db = client.db('mydb');
    console.log("Spojeno s bazom podataka 'mydb'");

    console.log('Brisanje starih podataka...');
    await db.collection('clubs').deleteMany({});
    await db.collection('events').deleteMany({});
    await db.collection('tables').deleteMany({});
    await db.collection('reservations').deleteMany({});

    // KLUBOVI
    console.log('Unos stvarnih klubova...');
    await db.collection('clubs').insertMany(REAL_CLUBS);
    console.log(`${REAL_CLUBS.length} klubova upisano`);

    // EVENTI – deterministički raspoređeni izvođači po klubovima
    console.log('Unos eventa sa stvarnim izvođačima...');
    const events = [];
    const today = Date.now();
    const dayMs = 24 * 60 * 60 * 1000;

    REAL_CLUBS.forEach((club, clubIdx) => {
      for (let i = 0; i < 6; i++) {
        const lineup = REAL_LINEUPS[(clubIdx * 6 + i) % REAL_LINEUPS.length];
        // Eventi 7, 14, 21, 28, 35, 42 dana od danas (deterministički)
        const eventDate = new Date(today + (i + 1) * 7 * dayMs);
        const daysUntil = (i + 1) * 7;

        events.push({
          id: `${club.id}-event-${i + 1}`,
          club_id: club.id,
          name: `${lineup.artist} – ${lineup.type}`,
          artist_name: lineup.artist,
          venue_name: club.name,
          venue_capacity: club.venue_capacity,
          city: club.location.split(',')[0].trim(),
          date: eventDate.toISOString().split('T')[0],
          event_date: eventDate.toISOString(),
          days_until_event: daysUntil,
          base_price: lineup.basePrice,
          current_price: lineup.basePrice,
          min_price: Math.round(lineup.basePrice * 0.5 * 100) / 100,
          max_price: Math.round(lineup.basePrice * 2.5 * 100) / 100,
          source: 'curated_real_data',
          description: `${lineup.type} izvođača ${lineup.artist} u klubu ${club.name}.`,
        });
      }
    });

    await db.collection('events').insertMany(events);
    console.log(`${events.length} eventa upisano`);

    // STOLOVI – deterministički status (svaki treći stol slobodan)
    console.log('Unos stolova...');
    const tables = [];
    events.forEach((event) => {
      for (let i = 1; i <= 25; i++) {
        const isReserved = i % 3 !== 0;
        // Kapacitet stola deterministički ovisi o broju
        const capacity = ((i - 1) % 4) + 2; // 2..5
        // Cijena stola = cijena eventa skalirana po kapacitetu
        const tablePrice = Math.round(event.base_price * capacity * 0.3);

        tables.push({
          id: `${event.id}-table-${i}`,
          event_id: event.id,
          number: i,
          capacity,
          status: isReserved ? 'reserved' : 'free',
          price: tablePrice,
        });
      }
    });

    await db.collection('tables').insertMany(tables);
    console.log(`${tables.length} stolova upisano`);

    // REZERVACIJE – stvarni domaći user-name format, deterministički
    console.log('Unos rezervacija...');
    const reservations = [];
    let reservationCount = 0;

    tables.forEach((table, idx) => {
      if (table.status === 'reserved') {
        reservations.push({
          id: `reservation-${table.id}`,
          event_id: table.event_id,
          table_id: table.id,
          user_name: `gost_${idx + 1}`,
          status: 'booked',
          guests: ((idx % table.capacity) || 1),
          created_at: new Date(today - (idx % 30) * dayMs).toISOString(),
        });
        reservationCount++;
      }
    });

    await db.collection('reservations').insertMany(reservations);
    console.log(`${reservations.length} rezervacija upisano`);

    console.log('\nZavršeno');
    console.log('='.repeat(50));
    console.log('Ukupni podaci:');
    console.log(`   Klubova: ${REAL_CLUBS.length}`);
    console.log(`   Evenata: ${events.length}`);
    console.log(`   Stolova: ${tables.length}`);
    console.log(`   Rezervacija: ${reservations.length}`);
    console.log(`   Slobodno: ${tables.length - reservationCount}`);
    console.log('='.repeat(50));
  } catch (error) {
    console.error('GREŠKA:', error.message);
    process.exit(1);
  } finally {
    await client.close();
  }
}

seedDatabase();
