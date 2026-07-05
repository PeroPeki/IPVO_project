import { useState } from 'react';
import { api } from '../../api';

export default function SectionAssignment({
  waiter, sections, onDone,
}: {
  waiter: any;
  sections: any[];
  onDone: () => void;
}) {
  const [selected, setSelected] = useState<string[]>(waiter.assigned_sections ?? []);
  const [error, setError] = useState('');

  function toggle(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  async function save() {
    try {
      await api(`/api/admin/staff/${waiter._id}/sections`, {
        method: 'PUT',
        body: { sections: selected },
      });
      onDone();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div className="card" style={{ borderColor: 'var(--accent1)' }}>
      <h2 style={{ marginTop: 0 }}>Sekcije — {waiter.name}</h2>
      {sections.length === 0 && (
        <p className="muted">Nema definiranih sekcija. Kreiraj ih u editoru mape stolova.</p>
      )}
      {sections.map((s) => (
        <label key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" style={{ width: 'auto' }}
                 checked={selected.includes(s.id)} onChange={() => toggle(s.id)} />
          <span style={{ width: 12, height: 12, borderRadius: 3, background: s.color, display: 'inline-block' }} />
          {s.name}
        </label>
      ))}
      {error && <div className="error-msg">{error}</div>}
      <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
        <button onClick={save}>Spremi</button>
        <button className="secondary" onClick={onDone}>Odustani</button>
      </div>
    </div>
  );
}
