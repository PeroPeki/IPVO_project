import { useEffect, useState } from 'react';
import { api, effectiveClubId } from '../../api';
import SectionAssignment from './SectionAssignment';

export default function StaffList() {
  const [staff, setStaff] = useState<any[]>([]);
  const [sections, setSections] = useState<any[]>([]);
  const [form, setForm] = useState({ role: 'hostess', name: '', email: '', pin: '' });
  const [error, setError] = useState('');
  const [assigning, setAssigning] = useState<any>(null);

  function load() {
    api<{ staff: any[] }>('/api/admin/staff').then((d) => setStaff(d.staff)).catch((e) => setError(e.message));
    const clubId = effectiveClubId();
    if (clubId) {
      api(`/api/floor-maps/club/${clubId}`)
        .then((m: any) => setSections(m.sections ?? []))
        .catch(() => setSections([]));
    }
  }

  useEffect(load, []);

  async function addStaff(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await api('/api/admin/staff', { body: form });
      setForm({ role: 'hostess', name: '', email: '', pin: '' });
      load();
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <>
      <h1>Osoblje</h1>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Dodaj osoblje</h2>
        <form onSubmit={addStaff} className="form-row" style={{ alignItems: 'flex-end' }}>
          <div>
            <label>Rola</label>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="hostess">Hostesa</option>
              <option value="waiter">Konobar</option>
            </select>
          </div>
          <div>
            <label>Ime i prezime</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div>
            <label>Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div>
            <label>PIN (4 znamenke)</label>
            <input value={form.pin} maxLength={4} pattern="\d{4}"
                   onChange={(e) => setForm({ ...form, pin: e.target.value })} required />
          </div>
          <button>Dodaj</button>
        </form>
        {error && <div className="error-msg">{error}</div>}
      </div>

      <div className="card">
        <table>
          <thead>
            <tr><th>Ime</th><th>Email</th><th>Rola</th><th>Sekcije</th><th /></tr>
          </thead>
          <tbody>
            {staff.map((s) => (
              <tr key={s._id}>
                <td>{s.name}</td>
                <td>{s.email}</td>
                <td>
                  <span className={`badge ${s.role === 'waiter' ? 'warning' : 'success'}`}>
                    {s.role === 'waiter' ? 'Konobar' : 'Hostesa'}
                  </span>
                </td>
                <td>{s.role === 'waiter' ? (s.assigned_sections ?? []).join(', ') || '—' : '—'}</td>
                <td>
                  {s.role === 'waiter' && (
                    <a href="#" onClick={(e) => { e.preventDefault(); setAssigning(s); }}>
                      Dodijeli sekcije
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {staff.length === 0 && <p className="muted" style={{ marginTop: 10 }}>Nema osoblja.</p>}
      </div>

      {assigning && (
        <SectionAssignment
          waiter={assigning}
          sections={sections}
          onDone={() => { setAssigning(null); load(); }}
        />
      )}
    </>
  );
}
