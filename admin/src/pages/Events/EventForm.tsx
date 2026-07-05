import { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api';

type TicketType = {
  id?: string; name: string; price: number;
  total_quantity: number; sold_quantity?: number; is_active?: boolean;
};

export default function EventForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const existing = (useLocation().state as any) || null;

  const [form, setForm] = useState({
    name: existing?.name ?? '',
    date: existing?.date ? existing.date.slice(0, 16) : '',
    doors_open: existing?.doors_open ?? '23:00',
    end_time: existing?.end_time ?? '06:00',
    genre: existing?.genre ?? '',
    description: existing?.description ?? '',
    age_limit: existing?.age_limit ?? 18,
    dress_code: existing?.dress_code ?? '',
    is_published: existing?.is_published ?? false,
  });
  const [lineup, setLineup] = useState<any[]>(existing?.lineup ?? []);
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>(
    existing?.ticket_types ?? [{ name: 'Regular', price: 15, total_quantity: 200 }],
  );
  const [error, setError] = useState('');

  function set(key: string, value: any) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const payload = { ...form, age_limit: Number(form.age_limit), lineup, ticket_types: ticketTypes };
    try {
      if (id) await api(`/api/events/${id}`, { method: 'PUT', body: payload });
      else await api('/api/events', { body: payload });
      navigate('/events');
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <>
      <h1>{id ? 'Uredi event' : 'Novi event'}</h1>
      <form onSubmit={submit} style={{ maxWidth: 720 }}>
        <div className="card">
          <label>Naziv</label>
          <input value={form.name} onChange={(e) => set('name', e.target.value)} required />
          <div className="form-row">
            <div>
              <label>Datum i vrijeme</label>
              <input type="datetime-local" value={form.date}
                     onChange={(e) => set('date', e.target.value)} required />
            </div>
            <div>
              <label>Vrata se otvaraju</label>
              <input value={form.doors_open} onChange={(e) => set('doors_open', e.target.value)} />
            </div>
            <div>
              <label>Kraj</label>
              <input value={form.end_time} onChange={(e) => set('end_time', e.target.value)} />
            </div>
          </div>
          <div className="form-row">
            <div>
              <label>Žanr</label>
              <input value={form.genre} onChange={(e) => set('genre', e.target.value)} />
            </div>
            <div>
              <label>Dobna granica</label>
              <input type="number" value={form.age_limit} onChange={(e) => set('age_limit', e.target.value)} />
            </div>
            <div>
              <label>Dress code</label>
              <input value={form.dress_code} onChange={(e) => set('dress_code', e.target.value)} />
            </div>
          </div>
          <label>Opis</label>
          <textarea rows={3} value={form.description} onChange={(e) => set('description', e.target.value)} />
        </div>

        <div className="card">
          <h2>Lineup</h2>
          {lineup.map((a, i) => (
            <div className="form-row" key={i} style={{ marginBottom: 8 }}>
              <input placeholder="Izvođač" value={a.artist_name}
                     onChange={(e) => setLineup(lineup.map((x, j) => j === i ? { ...x, artist_name: e.target.value } : x))} />
              <input placeholder="Nastup (npr. 01:00)" value={a.stage_time ?? ''}
                     onChange={(e) => setLineup(lineup.map((x, j) => j === i ? { ...x, stage_time: e.target.value } : x))} />
              <button type="button" className="danger" onClick={() => setLineup(lineup.filter((_, j) => j !== i))}>×</button>
            </div>
          ))}
          <button type="button" className="secondary"
                  onClick={() => setLineup([...lineup, { artist_name: '', stage_time: '', image_url: null }])}>
            + Dodaj izvođača
          </button>
        </div>

        <div className="card">
          <h2>Tipovi karata</h2>
          {ticketTypes.map((t, i) => (
            <div className="form-row" key={i} style={{ marginBottom: 8, alignItems: 'flex-end' }}>
              <div>
                <label>Naziv</label>
                <input value={t.name}
                       onChange={(e) => setTicketTypes(ticketTypes.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
              </div>
              <div>
                <label>Cijena (€)</label>
                <input type="number" step="0.5" value={t.price}
                       onChange={(e) => setTicketTypes(ticketTypes.map((x, j) => j === i ? { ...x, price: Number(e.target.value) } : x))} />
              </div>
              <div>
                <label>Količina</label>
                <input type="number" value={t.total_quantity}
                       onChange={(e) => setTicketTypes(ticketTypes.map((x, j) => j === i ? { ...x, total_quantity: Number(e.target.value) } : x))} />
              </div>
              <button type="button" className="danger" onClick={() => setTicketTypes(ticketTypes.filter((_, j) => j !== i))}>×</button>
            </div>
          ))}
          <button type="button" className="secondary"
                  onClick={() => setTicketTypes([...ticketTypes, { name: '', price: 20, total_quantity: 100 }])}>
            + Dodaj tip karte
          </button>
        </div>

        <div className="card">
          <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" style={{ width: 'auto' }} checked={form.is_published}
                   onChange={(e) => set('is_published', e.target.checked)} />
            Objavljen (vidljiv u mobilnoj aplikaciji)
          </label>
          {error && <div className="error-msg">{error}</div>}
          <button style={{ marginTop: 12 }}>{id ? 'Spremi' : 'Kreiraj event'}</button>
        </div>
      </form>
    </>
  );
}
