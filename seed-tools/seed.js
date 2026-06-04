/**
 * NAPOMENA: Ova skripta je sada opcijska pomoćna alatka, nije dio normalnog
 * pokretanja stoga. Kreiranje indeksa se automatski vrši u backend/app.py
 * pri svakom startu aplikacije (ensure_indexes()).
 *
 * Ako ipak želiš ručno rekreirati indekse (npr. nakon manual čišćenja baze):
 *   docker compose run --rm seed
 *
 * VIŠE SE NE BRIŠE nikakav podatak – destruktivni deleteMany pozivi su uklonjeni.
 */

const { MongoClient } = require('mongodb');

async function createIndexes() {
  const uri = 'mongodb://mongo:27017';
  const client = new MongoClient(uri);

  try {
    console.log('seed-tools: spajanje na MongoDB...');
    await client.connect();
    const db = client.db('mydb');

    console.log('seed-tools: kreiram indekse...');
    await db.collection('clubs').createIndex({ id: 1 }, { unique: true });
    await db.collection('events').createIndex({ ticketmaster_id: 1 }, { unique: true, sparse: true });
    await db.collection('events').createIndex({ id: 1 });
    await db.collection('events').createIndex({ club_id: 1 });
    await db.collection('events').createIndex({ city: 1, country: 1 });
    await db.collection('events').createIndex({ event_date: 1 });
    await db.collection('tables').createIndex({ event_id: 1 });
    await db.collection('tables').createIndex({ id: 1 });
    await db.collection('reservations').createIndex({ event_id: 1, table_id: 1 });

    console.log('seed-tools: indeksi gotovi.');
  } catch (error) {
    console.error('seed-tools greška:', error.message);
    process.exit(1);
  } finally {
    await client.close();
  }
}

createIndexes();
