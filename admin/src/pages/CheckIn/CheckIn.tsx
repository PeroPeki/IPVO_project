import { useEffect, useState } from 'react';
import { api, effectiveClubId } from '../../api';

export default function CheckIn() {
  const [events, setEvents] = useState<any[]>([]);
  const [eventId, setEventId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [guests, setGuests] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    api<{ events: any[] }>(`/api/events?club_id=${effectiveClubId()}`)
      .then((d) => setEvents(d.events))
      .catch((e) => setError(e.message));
  }, []);

  function loadGuests() {
    if (!eventId) return;
    api<{ guests: any[] }>(`/api/hostess/event/${eventId}/guests?search=${encodeURIComponent(search)}`)
      .then((d) => setGuests(d.guests))
      .catch((e) => setError(e.message));
  }

  function loadStats() {
    if (!eventId) return;
    api(`/api/hostess/event/${eventId}/stats`).then(setStats).catch(() => {});
  }

  useEffect(() => {
    if (!eventId) return;
    loadGuests();
    loadStats();
    const interval = setInterval(loadStats, 15000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, search]);

  async function checkin(guest: any) {
    setError('');
    setMessage('');
    const path = guest.type === 'ticket'
      ? `/api/hostess/checkin/ticket/${guest.id}`
      : `/api/hostess/checkin/reservation/${guest.id}`;
    try {
      const res = await api<{ guest_name?: string }>(path, { method: 'POST' });
      setMessage(`✓ Ulaz potvrđen — ${res.guest_name ?? guest.name}`);
      loadGuests();
      loadStats();
    } catch (err: any) {
      setError(err.message);
    }
  }

  if (!eventId) {
    return (
      <>
        <h1>Odaberi event</h1>
        <div className="card">
          <table>
            <thead><tr><th>Naziv</th><th>Datum</th><th /></tr></thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev._id}>
                  <td>{ev.name}</td>
                  <td>{new Date(ev.date).toLocaleString('hr-HR')}</td>
                  <td><a href="#" onClick={(e) => { e.preventDefault(); setEventId(ev._id); }}>Odaberi</a></td>
                </tr>
              ))}
            </tbody>
          </table>
          {events.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema eventa.</p>}
        </div>
        {error && <div className="error-msg">{error}</div>}
      </>
    );
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Check-in</h1>
        <a href="#" onClick={(e) => { e.preventDefault(); setEventId(null); }}>← Promijeni event</a>
      </div>

      {stats && (
        <div className="grid cols-4" style={{ marginBottom: 16 }}>
          <div className="card stat"><div className="label">Unutra</div><div className="value">{stats.total_inside}</div></div>
          <div className="card stat"><div className="label">Karata prodano</div><div className="value">{stats.tickets_sold}</div></div>
          <div className="card stat"><div className="label">Rezervacija potvrđeno</div><div className="value">{stats.reservations_confirmed}</div></div>
          <div className="card stat"><div className="label">Rezervacija ušlo</div><div className="value">{stats.reservations_checked_in}</div></div>
        </div>
      )}

      <div className="card">
        <input
          placeholder="Pretraga po imenu/prezimenu…"
          value={search} onChange={(e) => setSearch(e.target.value)}
          style={{ marginBottom: 12 }}
        />
        {message && <div className="badge success" style={{ marginBottom: 12 }}>{message}</div>}
        {error && <div className="error-msg">{error}</div>}
        <table>
          <thead><tr><th>Ime</th><th>Detalji</th><th>Status</th><th /></tr></thead>
          <tbody>
            {guests.map((g) => {
              const inside = g.status === 'checked_in';
              return (
                <tr key={`${g.type}-${g.id}`}>
                  <td>{g.name}</td>
                  <td className="muted">{g.detail}</td>
                  <td>
                    <span className={`badge ${inside ? 'success' : 'muted'}`}>
                      {inside ? 'Unutra' : 'Vani'}
                    </span>
                  </td>
                  <td>
                    {!inside && <button onClick={() => checkin(g)}>Check-in</button>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {guests.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema gostiju za prikaz.</p>}
      </div>
    </>
  );
}
