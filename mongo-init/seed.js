db = db.getSiblingDB("mydb");
db.clubs.insertMany([
  { id: "c1", name: "Club A", location: "Rijeka", description: "Opis..." }
]);