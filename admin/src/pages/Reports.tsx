import { useEffect, useState } from 'react';
import { api } from '../api';

export default function Reports() {
  const [reports, setReports] = useState<any[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api<{ reports: any[] }>('/api/admin/reports')
      .then((d) => setReports(d.reports))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <h1>Dnevni izvještaji</h1>
      {error && <div className="error-msg">{error}</div>}
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Datum</th><th>Karte</th><th>Rezervacije</th><th>Narudžbe</th>
              <th>Prihod karte</th><th>Prihod piće</th><th>Depoziti</th><th>Ukupno</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r._id}>
                <td>{new Date(r.date).toLocaleDateString('hr-HR')}</td>
                <td>{r.metrics?.total_tickets_sold}</td>
                <td>{r.metrics?.total_reservations}</td>
                <td>{r.metrics?.total_drink_orders}</td>
                <td>{r.metrics?.revenue_tickets} €</td>
                <td>{r.metrics?.revenue_drinks} €</td>
                <td>{r.metrics?.revenue_deposits} €</td>
                <td style={{ fontWeight: 700, color: 'var(--accent1)' }}>
                  {r.metrics?.total_revenue} €
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {reports.length === 0 && (
          <p className="muted" style={{ marginTop: 10 }}>
            Nema izvještaja — generiraju se dnevno kroz Celery Beat.
          </p>
        )}
      </div>
    </>
  );
}
