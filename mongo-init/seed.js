// Ova skripta je zastarjela i više se ne montira u MongoDB kontejner.
//
// Kreiranje MongoDB indeksa sada se vrši automatski pri startu backend servisa
// (backend/app.py → ensure_indexes()).
//
// Kreiranje stvarnih podataka vrši se putem Ticketmaster + Last.fm pipelinea
// koji se automatski okida pri prvom pokretanju ako je baza prazna.
// Ručno pokretanje: POST /api/sync-events
