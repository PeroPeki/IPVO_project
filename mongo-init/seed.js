db = db.getSiblingDB("mydb");


// Obriši stare podatke
db.clubs.deleteMany({});
db.events.deleteMany({});
db.tables.deleteMany({});
db.reservations.deleteMany({});



// novi klubovi - početni podaci
const clubs = [
  { 
    id: "club-1", 
    name: "Club Riviera", 
    location: "Rijeka, Hrvatska", 
    description: "Najbolji klub uz more - glazba do zore!" 
  },
  { 
    id: "club-2", 
    name: "Club Dalmatino", 
    location: "Split, Hrvatska", 
    description: "Prave dalmatinske noći na Obali" 
  },
  { 
    id: "club-3", 
    name: "Club Central", 
    location: "Zagreb, Hrvatska", 
    description: "Epicentar zabave u gradu" 
  },
  { 
    id: "club-4", 
    name: "Club Danube", 
    location: "Osijek, Hrvatska", 
    description: "Slavonska glazbena tradicija s modernim zvukom" 
  },
  { 
    id: "club-5", 
    name: "Club Paradise", 
    location: "Dubrovnik, Hrvatska", 
    description: "Luksuzni klub s pogledom na Jadran" 
  }
];

db.clubs.insertMany(clubs);


// početni eventi, 5 po klubu
const events = [];
const eventNames = [
  "Friday Night Fever",
  "Saturday Beats",
  "Summer Party",
  "Tech Sounds",
  "Sunset Vibes"
];

clubs.forEach(club => {
  for (let i = 0; i < 5; i++) {
    events.push({
      id: `${club.id}-event-${i+1}`,
      club_id: club.id,
      name: `🎉 ${eventNames[i]}`,
      date: new Date(Date.now() + (i+1) * 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      description: `Spektakularni event u ${club.name}`
    });
  }
});

db.events.insertMany(events);

// početni stolovi - 20 po eventu
const tables = [];

events.forEach(event => {
  for (let i = 1; i <= 20; i++) {
    const isReserved = Math.random() > 0.55; // 45% je rezervirano
    tables.push({
      id: `${event.id}-table-${i}`,
      event_id: event.id,
      number: i,
      status: isReserved ? "reserved" : "free"
    });
  }
});

db.tables.insertMany(tables);


// rezervacije za rezervirane stolove
const reservations = [];

tables.forEach(table => {
  if (table.status === "reserved") {
    reservations.push({
      id: `reservation-${table.id}`,
      event_id: table.event_id,
      table_id: table.id,
      status: "booked",
      created_at: new Date().toISOString()
    });
  }
});

db.reservations.insertMany(reservations);

// izvješće
print(`   - Klubova: ${clubs.length}`);
print(`   - Evenata: ${events.length}`);
print(`   - Stolova: ${tables.length}`);
print(`   - Rezervacija: ${reservations.length}`);
