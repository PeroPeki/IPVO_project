
const mockEvents = [
  { id: 1, name: "DJ Party", date: "2025-12-15" },
  { id: 2, name: "Live Band", date: "2025-12-20" }
];

document.addEventListener('DOMContentLoaded', () => {
  const eventsDiv = document.getElementById('events');
  eventsDiv.innerHTML = mockEvents.map(e => 
    `<div class="event">${e.name} - ${e.date}</div>`
  ).join('');
});

function reserveTable() {
  alert('Rezervacija uspješna! (mock)');
}
