import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, effectiveClubId } from '../../api';

export default function EventList() {
  const [events, setEvents] = useState<any[]>([]);
  const [error, setError] = useState('');

  function load() {
    const clubId = effectiveClubId();
    // Admin dohvaća i neobjavljene evente svog kluba kroz javnu rutu + filtar;
    // objavljeni dolaze iz /api/events, ostalo se vidi nakon publish akcije.
    api<{ events: any[] }>(`/api/events${clubId ? `?club_id=${clubId}` : ''}`)
      .then((d) => setEvents(d.events))
      .catch((e) => setError(e.message));
  }

  useEffect(load, []);

  async function cancelEvent(id: string) {
    if (!confirm('Sigurno otkazati event?')) return;
    try {
      await api(`/api/events/${id}`, { method: 'DELETE' });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Eventi</h1>
        <Link to="/events/new" className="btn">+ Novi event</Link>
      </div>
      {error && <div className="error-msg">{error}</div>}
      <div className="card">
        <table>
          <thead>
            <tr><th>Naziv</th><th>Datum</th><th>Žanr</th><th>Karte</th><th>Akcije</th></tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e._id}>
                <td>{e.name}</td>
                <td>{new Date(e.date).toLocaleString('hr-HR')}</td>
                <td>{e.genre ?? '—'}</td>
                <td>
                  {(e.ticket_types || []).reduce((s: number, t: any) => s + t.sold_quantity, 0)}
                  {' / '}
                  {(e.ticket_types || []).reduce((s: number, t: any) => s + t.total_quantity, 0)}
                </td>
                <td style={{ display: 'flex', gap: 10 }}>
                  <Link to={`/events/${e._id}/edit`} state={e}>Uredi</Link>
                  <Link to={`/events/${e._id}/live`}>Live</Link>
                  <Link to={`/events/${e._id}/reservations`}>Rezervacije</Link>
                  <a href="#" onClick={(ev) => { ev.preventDefault(); cancelEvent(e._id); }}
                     style={{ color: 'var(--error)' }}>Otkaži</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {events.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema eventa.</p>}
      </div>
    </>
  );
}
