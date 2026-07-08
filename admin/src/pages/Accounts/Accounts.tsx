import { useEffect, useState } from 'react';
import { api } from '../../api';

export default function Accounts() {
  const [superadmins, setSuperadmins] = useState<any[]>([]);
  const [saForm, setSaForm] = useState({ username: '', password: '' });
  const [saError, setSaError] = useState('');

  const [users, setUsers] = useState<any[]>([]);
  const [userForm, setUserForm] = useState({ name: '', email: '', phone: '', password: '' });
  const [userError, setUserError] = useState('');
  const [search, setSearch] = useState('');

  function loadSuperadmins() {
    api<{ admins: any[] }>('/api/admin/superadmins').then((d) => setSuperadmins(d.admins)).catch(() => {});
  }

  function loadUsers() {
    api<{ users: any[] }>(`/api/admin/users?search=${encodeURIComponent(search)}`)
      .then((d) => setUsers(d.users)).catch(() => {});
  }

  useEffect(loadSuperadmins, []);
  useEffect(loadUsers, [search]);

  async function addSuperadmin(e: React.FormEvent) {
    e.preventDefault();
    setSaError('');
    try {
      await api('/api/admin/superadmins', { body: saForm });
      setSaForm({ username: '', password: '' });
      loadSuperadmins();
    } catch (err: any) {
      setSaError(err.message);
    }
  }

  async function addUser(e: React.FormEvent) {
    e.preventDefault();
    setUserError('');
    try {
      await api('/api/admin/users', { body: userForm });
      setUserForm({ name: '', email: '', phone: '', password: '' });
      loadUsers();
    } catch (err: any) {
      setUserError(err.message);
    }
  }

  return (
    <>
      <h1>Računi</h1>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Superadmini</h2>
        <table>
          <thead><tr><th>Korisničko ime</th><th>Status</th></tr></thead>
          <tbody>
            {superadmins.map((a) => (
              <tr key={a._id}>
                <td>{a.username}</td>
                <td><span className="badge success">Aktivan</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {superadmins.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema superadmina.</p>}

        <h3>Dodaj superadmina</h3>
        <form onSubmit={addSuperadmin} className="form-row" style={{ alignItems: 'flex-end' }}>
          <div>
            <label>Korisničko ime</label>
            <input value={saForm.username}
                   onChange={(e) => setSaForm({ ...saForm, username: e.target.value })} required />
          </div>
          <div>
            <label>Lozinka</label>
            <input type="password" value={saForm.password} minLength={6}
                   onChange={(e) => setSaForm({ ...saForm, password: e.target.value })} required />
          </div>
          <button>Dodaj</button>
        </form>
        {saError && <div className="error-msg">{saError}</div>}
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Gosti</h2>
        <input
          placeholder="Pretraga po imenu/emailu…"
          value={search} onChange={(e) => setSearch(e.target.value)}
          style={{ marginBottom: 12 }}
        />
        <table>
          <thead><tr><th>Ime</th><th>Email</th><th>Telefon</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u._id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{u.phone || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {users.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema gostiju.</p>}

        <h3>Dodaj gosta</h3>
        <form onSubmit={addUser} className="form-row" style={{ alignItems: 'flex-end' }}>
          <div>
            <label>Ime i prezime</label>
            <input value={userForm.name}
                   onChange={(e) => setUserForm({ ...userForm, name: e.target.value })} required />
          </div>
          <div>
            <label>Email</label>
            <input type="email" value={userForm.email}
                   onChange={(e) => setUserForm({ ...userForm, email: e.target.value })} required />
          </div>
          <div>
            <label>Telefon</label>
            <input value={userForm.phone}
                   onChange={(e) => setUserForm({ ...userForm, phone: e.target.value })} />
          </div>
          <div>
            <label>Lozinka</label>
            <input type="password" value={userForm.password} minLength={6}
                   onChange={(e) => setUserForm({ ...userForm, password: e.target.value })} required />
          </div>
          <button>Dodaj</button>
        </form>
        {userError && <div className="error-msg">{userError}</div>}
      </div>
    </>
  );
}
