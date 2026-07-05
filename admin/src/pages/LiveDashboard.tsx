import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';

/** Live prikaz eventa — osvježava se svakih 10 sekundi. */
export default function LiveDashboard() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = () =>
      api(`/api/admin/events/${id}/live`).then(setData).catch((e) => setError(e.message));
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [id]);

  if (error) return <div className="error-msg">{error}</div>;
  if (!data) return <p className="muted">Učitavanje…</p>;

  const items = [
    { label: 'Prodane karte', value: data.tickets_sold },
    { label: 'Ušli s kartom', value: data.tickets_checked_in },
    { label: 'Aktivne rezervacije', value: data.reservations_active },
    { label: 'Ušli s rezervacijom', value: data.reservations_checked_in },
    { label: 'Gostiju unutra', value: data.guests_inside },
    { label: 'Aktivne narudžbe', value: data.active_drink_orders },
    { label: 'Prihod od pića', value: `${data.drink_revenue} €` },
  ];

  return (
    <>
      <h1>Live — {data.event?.name}</h1>
      <p className="muted">
        {new Date(data.event?.date).toLocaleString('hr-HR')} · automatsko osvježavanje (10 s)
      </p>
      <div className="grid cols-4" style={{ marginTop: 16 }}>
        {items.map((i) => (
          <div className="card stat" key={i.label}>
            <div className="label">{i.label}</div>
            <div className="value">{i.value}</div>
          </div>
        ))}
      </div>
    </>
  );
}
