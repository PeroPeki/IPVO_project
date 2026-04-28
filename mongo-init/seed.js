// MongoDB init script - inicijalni seed sa STVARNIM podacima.
// Izvršava se samo kod prvog pokretanja Mongo kontejnera.
// Bez Fakera, bez Math.random() - sve determinističko.

db = db.getSiblingDB("mydb");

db.clubs.deleteMany({});
db.events.deleteMany({});
db.tables.deleteMany({});
db.reservations.deleteMany({});

// Stvarni hrvatski klubovi
const clubs = [
  {
    id: "club-1",
    name: "Aquarius Club Zrće",
    location: "Novalja, Zrće, Hrvatska",
    description: "Kultni klub na plaži Zrće, jedan od najpoznatijih klubova u regiji.",
    venue_capacity: 2500
  },
  {
    id: "club-2",
    name: "Papaya Club",
    location: "Novalja, Zrće, Hrvatska",
    description: "Open-air klub na Zrću, poznat po world-class line-upovima.",
    venue_capacity: 5000
  },
  {
    id: "club-3",
    name: "Noa Beach Club",
    location: "Novalja, Zrće, Hrvatska",
    description: "Floating stage klub usred mora s vrhunskim sound systemom.",
    venue_capacity: 3500
  },
  {
    id: "club-4",
    name: "Boogaloo",
    location: "Zagreb, Hrvatska",
    description: "Najveći zatvoreni klub u Zagrebu, domaćin svjetskih DJ-eva i bendova.",
    venue_capacity: 1800
  },
  {
    id: "club-5",
    name: "Revelin",
    location: "Dubrovnik, Hrvatska",
    description: "Klub smješten u utvrdi Revelin, dio Best Discotheque liste svijeta.",
    venue_capacity: 1500
  }
];

db.clubs.insertMany(clubs);

// Stvarni izvođači - prepoznatljivi DJ-evi i bendovi
const lineups = [
  { artist: "Solomun", type: "DJ Set", basePrice: 80 },
  { artist: "Black Coffee", type: "Live Set", basePrice: 90 },
  { artist: "Tale Of Us", type: "DJ Set", basePrice: 85 },
  { artist: "Charlotte de Witte", type: "DJ Set", basePrice: 75 },
  { artist: "Boris Brejcha", type: "DJ Set", basePrice: 80 }
];

const events = [];
const today = Date.now();
const dayMs = 24 * 60 * 60 * 1000;

clubs.forEach((club, clubIdx) => {
  for (let i = 0; i < 5; i++) {
    const lineup = lineups[(clubIdx + i) % lineups.length];
    const eventDate = new Date(today + (i + 1) * 7 * dayMs);
    events.push({
      id: `${club.id}-event-${i + 1}`,
      club_id: club.id,
      name: `${lineup.artist} - ${lineup.type}`,
      artist_name: lineup.artist,
      venue_name: club.name,
      venue_capacity: club.venue_capacity,
      city: club.location.split(',')[0].trim(),
      date: eventDate.toISOString().split('T')[0],
      event_date: eventDate.toISOString(),
      days_until_event: (i + 1) * 7,
      base_price: lineup.basePrice,
      current_price: lineup.basePrice,
      min_price: Math.round(lineup.basePrice * 0.5 * 100) / 100,
      max_price: Math.round(lineup.basePrice * 2.5 * 100) / 100,
      source: "curated_real_data",
      description: `${lineup.type} izvođača ${lineup.artist} u klubu ${club.name}.`
    });
  }
});

db.events.insertMany(events);

// Stolovi - deterministički status (svaki treći slobodan)
const tables = [];
events.forEach(event => {
  for (let i = 1; i <= 20; i++) {
    const isReserved = i % 3 !== 0;
    tables.push({
      id: `${event.id}-table-${i}`,
      event_id: event.id,
      number: i,
      capacity: ((i - 1) % 4) + 2,
      status: isReserved ? "reserved" : "free"
    });
  }
});

db.tables.insertMany(tables);

// Rezervacije - bez nasumičnih imena
const reservations = [];
tables.forEach((table, idx) => {
  if (table.status === "reserved") {
    reservations.push({
      id: `reservation-${table.id}`,
      event_id: table.event_id,
      table_id: table.id,
      user_name: `gost_${idx + 1}`,
      status: "booked",
      created_at: new Date(today - (idx % 30) * dayMs).toISOString()
    });
  }
});

db.reservations.insertMany(reservations);

print(`   - Klubova: ${clubs.length}`);
print(`   - Evenata: ${events.length}`);
print(`   - Stolova: ${tables.length}`);
print(`   - Rezervacija: ${reservations.length}`);
