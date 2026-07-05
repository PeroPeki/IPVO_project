import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api('/api/admin/dashboard').then(setStats).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error-msg">{error}</div>;
  if (!stats) return <p className="muted">Učitavanje…</p>;

  const items = [
    { label: 'Nadolazeći eventi', value: stats.upcoming_events },
    { label: 'Prodane karte (30 d)', value: stats.tickets_sold },
    { label: 'Rezervacije (30 d)', value: stats.reservations },
    { label: 'Narudžbe pića (30 d)', value: stats.drink_orders },
    { label: 'Prihod — karte', value: `${stats.revenue_tickets} €` },
    { label: 'Prihod — piće', value: `${stats.revenue_drinks} €` },
    { label: 'Prihod — depoziti', value: `${stats.revenue_deposits} €` },
    { label: 'Ukupan prihod', value: `${stats.total_revenue} €` },
  ];

  return (
    <>
      <h1>Dashboard</h1>
      <p className="muted">Statistike zadnjih {stats.period_days} dana</p>
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
