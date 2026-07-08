import { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { api, auth } from '../api';

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [clubs, setClubs] = useState<any[]>([]);

  // Superadmin bira klub nad kojim radi
  useEffect(() => {
    if (auth.role !== 'superadmin') return;
    api<{ clubs: any[] }>('/api/clubs')
      .then((d) => {
        setClubs(d.clubs);
        if (!auth.clubId && d.clubs.length) auth.setClub(d.clubs[0]._id);
      })
      .catch(() => {});
  }, []);

  const isAdmin = auth.role === 'admin' || auth.role === 'superadmin';

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">NIGHTCLUB<br />MANAGER</div>
        {auth.role === 'superadmin' && clubs.length > 0 && (
          <div style={{ padding: '0 20px 14px' }}>
            <label>Aktivni klub</label>
            <select
              defaultValue={auth.clubId ?? ''}
              onChange={(e) => { auth.setClub(e.target.value); window.location.reload(); }}
            >
              {clubs.map((c) => <option key={c._id} value={c._id}>{c.name}</option>)}
            </select>
          </div>
        )}
        <nav>
          {isAdmin && (
            <>
              <NavLink to="/" end>Dashboard</NavLink>
              {auth.role === 'superadmin' && <NavLink to="/clubs">Klubovi</NavLink>}
              <NavLink to="/events">Eventi</NavLink>
              <NavLink to="/floor-map">Mapa stolova</NavLink>
              <NavLink to="/staff">Osoblje</NavLink>
              <NavLink to="/menu">Meni</NavLink>
              <NavLink to="/reports">Izvještaji</NavLink>
              {auth.role === 'superadmin' && <NavLink to="/accounts">Računi</NavLink>}
            </>
          )}
          {auth.role === 'hostess' && <NavLink to="/checkin">Check-in</NavLink>}
          {auth.role === 'waiter' && <NavLink to="/orders">Narudžbe</NavLink>}
        </nav>
        <button
          className="secondary logout"
          onClick={() => { auth.logout(); navigate('/login'); }}
        >
          Odjava
        </button>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
