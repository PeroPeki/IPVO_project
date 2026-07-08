import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api';

export default function ClubForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const existing = (useLocation().state as any) || null;

  const [form, setForm] = useState({
    name: existing?.name ?? '',
    city: existing?.location?.city ?? 'Novalja',
    address: existing?.location?.address ?? '',
    description: existing?.description ?? '',
    capacity: existing?.capacity ?? 1000,
    working_hours: existing?.working_hours ?? '23:00 – 06:00',
    dress_code: existing?.dress_code ?? '',
    age_limit: existing?.age_limit ?? 18,
    is_active: existing?.is_active ?? true,
  });
  const [error, setError] = useState('');

  const [admins, setAdmins] = useState<any[]>([]);
  const [adminForm, setAdminForm] = useState({ name: '', email: '', password: '' });
  const [adminError, setAdminError] = useState('');

  function loadAdmins() {
    if (!id) return;
    api<{ admins: any[] }>(`/api/admin/club-admins?club_id=${id}`)
      .then((d) => setAdmins(d.admins))
      .catch(() => setAdmins([]));
  }

  useEffect(loadAdmins, [id]);

  async function addAdmin(e: React.FormEvent) {
    e.preventDefault();
    setAdminError('');
    try {
      await api(`/api/admin/club-admins?club_id=${id}`, { body: adminForm });
      setAdminForm({ name: '', email: '', password: '' });
      loadAdmins();
    } catch (err: any) {
      setAdminError(err.message);
    }
  }

  function set(key: string, value: any) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const payload = {
      name: form.name,
      location: { city: form.city, address: form.address },
      description: form.description,
      capacity: Number(form.capacity),
      working_hours: form.working_hours,
      dress_code: form.dress_code,
      age_limit: Number(form.age_limit),
      is_active: form.is_active,
    };
    try {
      if (id) await api(`/api/clubs/${id}`, { method: 'PUT', body: payload });
      else await api('/api/clubs', { body: payload });
      navigate('/clubs');
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function uploadImage(e: React.ChangeEvent<HTMLInputElement>) {
    if (!id || !e.target.files?.[0]) return;
    const fd = new FormData();
    fd.append('image', e.target.files[0]);
    try {
      await api(`/api/clubs/${id}/upload-image?field=cover`, { formData: fd });
      alert('Slika uploadana.');
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <>
      <h1>{id ? 'Uredi klub' : 'Novi klub'}</h1>
      <form className="card" onSubmit={submit} style={{ maxWidth: 640 }}>
        <label>Naziv</label>
        <input value={form.name} onChange={(e) => set('name', e.target.value)} required />
        <div className="form-row">
          <div>
            <label>Grad</label>
            <input value={form.city} onChange={(e) => set('city', e.target.value)} required />
          </div>
          <div>
            <label>Adresa</label>
            <input value={form.address} onChange={(e) => set('address', e.target.value)} />
          </div>
        </div>
        <label>Opis</label>
        <textarea rows={3} value={form.description} onChange={(e) => set('description', e.target.value)} />
        <div className="form-row">
          <div>
            <label>Kapacitet</label>
            <input type="number" value={form.capacity} onChange={(e) => set('capacity', e.target.value)} />
          </div>
          <div>
            <label>Dobna granica</label>
            <input type="number" value={form.age_limit} onChange={(e) => set('age_limit', e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div>
            <label>Radno vrijeme</label>
            <input value={form.working_hours} onChange={(e) => set('working_hours', e.target.value)} />
          </div>
          <div>
            <label>Dress code</label>
            <input value={form.dress_code} onChange={(e) => set('dress_code', e.target.value)} />
          </div>
        </div>
        {id && (
          <>
            <label>Cover slika</label>
            <input type="file" accept="image/*" onChange={uploadImage} />
          </>
        )}
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
          <input
            type="checkbox" style={{ width: 'auto' }}
            checked={form.is_active} onChange={(e) => set('is_active', e.target.checked)}
          />
          Aktivan
        </label>
        {error && <div className="error-msg">{error}</div>}
        <button style={{ marginTop: 16 }}>{id ? 'Spremi' : 'Kreiraj'}</button>
      </form>

      {id && (
        <div className="card" style={{ maxWidth: 640 }}>
          <h2 style={{ marginTop: 0 }}>Admini kluba</h2>
          <table>
            <thead>
              <tr><th>Ime</th><th>Email</th><th>Status</th></tr>
            </thead>
            <tbody>
              {admins.map((a) => (
                <tr key={a._id}>
                  <td>{a.name}</td>
                  <td>{a.email}</td>
                  <td>
                    <span className={`badge ${a.is_active ? 'success' : 'muted'}`}>
                      {a.is_active ? 'Aktivan' : 'Neaktivan'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {admins.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema admina.</p>}

          <h3>Dodaj admina</h3>
          <form onSubmit={addAdmin} className="form-row" style={{ alignItems: 'flex-end' }}>
            <div>
              <label>Ime i prezime</label>
              <input value={adminForm.name}
                     onChange={(e) => setAdminForm({ ...adminForm, name: e.target.value })} required />
            </div>
            <div>
              <label>Email</label>
              <input type="email" value={adminForm.email}
                     onChange={(e) => setAdminForm({ ...adminForm, email: e.target.value })} required />
            </div>
            <div>
              <label>Lozinka</label>
              <input type="password" value={adminForm.password} minLength={6}
                     onChange={(e) => setAdminForm({ ...adminForm, password: e.target.value })} required />
            </div>
            <button>Dodaj</button>
          </form>
          {adminError && <div className="error-msg">{adminError}</div>}
        </div>
      )}
    </>
  );
}
