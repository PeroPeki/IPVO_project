import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api';

export default function ClubList() {
  const [clubs, setClubs] = useState<any[]>([]);

  useEffect(() => {
    api<{ clubs: any[] }>('/api/clubs').then((d) => setClubs(d.clubs)).catch(() => {});
  }, []);

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Klubovi</h1>
        <Link to="/clubs/new" className="btn">+ Novi klub</Link>
      </div>
      <div className="card">
        <table>
          <thead>
            <tr><th>Naziv</th><th>Grad</th><th>Kapacitet</th><th>Eventi</th><th>Status</th><th /></tr>
          </thead>
          <tbody>
            {clubs.map((c) => (
              <tr key={c._id}>
                <td>{c.name}</td>
                <td>{c.location?.city}</td>
                <td>{c.capacity ?? '—'}</td>
                <td>{c.upcoming_event_count}</td>
                <td>
                  <span className={`badge ${c.is_active ? 'success' : 'muted'}`}>
                    {c.is_active ? 'Aktivan' : 'Neaktivan'}
                  </span>
                </td>
                <td><Link to={`/clubs/${c._id}/edit`} state={c}>Uredi</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
        {clubs.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema klubova.</p>}
      </div>
    </>
  );
}
