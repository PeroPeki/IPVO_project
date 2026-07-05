import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';

const STATUS_BADGE: Record<string, string> = {
  pending: 'warning',
  confirmed: 'success',
  checked_in: 'success',
  cancelled: 'error',
  no_show: 'muted',
};

export default function Reservations() {
  const { id } = useParams();
  const [reservations, setReservations] = useState<any[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api<{ reservations: any[] }>(`/api/reservations/event/${id}/all`)
      .then((d) => setReservations(d.reservations))
      .catch((e) => setError(e.message));
  }, [id]);

  return (
    <>
      <h1>Rezervacije eventa</h1>
      {error && <div className="error-msg">{error}</div>}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Gost</th><th>Stol</th><th>Tip</th><th>Gosti</th>
              <th>Depozit</th><th>Kupon preostalo</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {reservations.map((r) => (
              <tr key={r._id}>
                <td>{r.user?.name ?? '—'}<div className="muted">{r.user?.email}</div></td>
                <td>{r.table_label}</td>
                <td>{r.table_type === 'vip_separe' ? 'VIP separé' : r.table_type}</td>
                <td>{r.guests_count}</td>
                <td>{r.deposit_amount ? `${r.deposit_amount} € ${r.deposit_paid ? '✓' : '(neplaćen)'}` : '—'}</td>
                <td>{r.deposit_coupon_remaining ? `${r.deposit_coupon_remaining} €` : '—'}</td>
                <td><span className={`badge ${STATUS_BADGE[r.status] ?? 'muted'}`}>{r.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {reservations.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema rezervacija.</p>}
      </div>
    </>
  );
}
