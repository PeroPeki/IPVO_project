const { faker } = require('@faker-js/faker');
const { MongoClient } = require('mongodb');

async function seedDatabase() {
  const uri = "mongodb://mongo:27017";
  const client = new MongoClient(uri);
  
  try {
    console.log("\n Povezivanje s MongoDB...");
    await client.connect();
    const db = client.db("mydb");
    console.log("Spojeno s bazom podataka 'mydb'");
    
    // Obriši stare podatke
    console.log("\n Brisanje starih podataka...");
    await db.collection("clubs").deleteMany({});
    await db.collection("events").deleteMany({});
    await db.collection("tables").deleteMany({});
    await db.collection("reservations").deleteMany({});
    
    // klubovi
    console.log("\n Generiranje klubova...");
    const clubs = Array.from({ length: 8 }, (_, i) => ({
      id: `club-${i + 1}`,
      name: faker.company.name() + " Club",
      location: faker.location.city() + ", Hrvatska",
      description: faker.lorem.sentence()
    }));
    
    await db.collection("clubs").insertMany(clubs);
    console.log(`${clubs.length} klubova generirano`);
    
    // eventi
    console.log("\n Generiranje eventa...");
    const events = [];
    const eventTypes = [
      "DJ Night", "Live Concert", "Party Night", 
      "Electronic Beats", "Retro Party", "Foam Party", 
      "VIP Dinner", "Summer Fest"
    ];
    
    clubs.forEach(club => {
      for (let i = 0; i < 6; i++) {
        const eventDate = faker.date.future({ years: 1 });
        events.push({
          id: `${club.id}-event-${i + 1}`,
          club_id: club.id,
          name: `🎉 ${eventTypes[i % eventTypes.length]} - ${faker.lorem.words(2)}`,
          date: eventDate.toISOString().split('T')[0],
          description: faker.lorem.sentences(2)
        });
      }
    });
    
    await db.collection("events").insertMany(events);
    console.log(`${events.length} evenata generirano`);
    
    // stolovi
    console.log("\n Generiranje stolova...");
    const tables = [];
    
    events.forEach(event => {
      for (let i = 1; i <= 25; i++) {
        const isReserved = Math.random() > 0.5; // 50% je rezervirano
        tables.push({
          id: `${event.id}-table-${i}`,
          event_id: event.id,
          number: i,
          capacity: faker.number.int({ min: 2, max: 8 }),
          status: isReserved ? "reserved" : "free",
          price: faker.number.int({ min: 50, max: 500 })
        });
      }
    });
    
    await db.collection("tables").insertMany(tables);
    console.log(`${tables.length} stolova generirano`);
    
    // rezervacije
    console.log("\n Generiranje rezervacija...");
    const reservations = [];
    let reservationCount = 0;
    
    tables.forEach(table => {
      if (table.status === "reserved") {
        reservations.push({
          id: `reservation-${table.id}`,
          event_id: table.event_id,
          table_id: table.id,
          user_name: faker.person.fullName(),
          user_email: faker.internet.email(),
          status: "booked",
          guests: faker.number.int({ min: 1, max: table.capacity }),
          created_at: new Date(
            Date.now() - faker.number.int({ min: 0, max: 30 * 24 * 60 * 60 * 1000 })
          ).toISOString()
        });
        reservationCount++;
      }
    });
    
    await db.collection("reservations").insertMany(reservations);
    console.log(`${reservations.length} rezervacija generirano`);
    
    // izvješće

    console.log("\nZavršeno!");
    console.log("=".repeat(50));
    console.log("Ukupni podaci:");
    console.log(`   Klubova: ${clubs.length}`);
    console.log(`   Evenata: ${events.length}`);
    console.log(`   Stolova: ${tables.length}`);
    console.log(`   Rezervacija: ${reservations.length}`);
    console.log(`   Slobodno: ${tables.length - reservationCount}`);
    console.log("=".repeat(50));
    
  } catch (error) {
    console.error("GREŠKA:", error.message);
    process.exit(1);
  } finally {
    await client.close();
  }
}

seedDatabase();
