import { useEffect, useState } from 'react';
import { api, effectiveClubId } from '../../api';
import ItemForm from './ItemForm';

export default function MenuEditor() {
  const [menu, setMenu] = useState<any>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const clubId = effectiveClubId();
    if (!clubId) { setError('Odaberi klub'); return; }
    api(`/api/menu/club/${clubId}`)
      .then(setMenu)
      .catch(async () => {
        try {
          const created = await api('/api/menu', {
            body: { club_id: clubId, name: 'Cjenik pića', categories: [] },
          });
          setMenu(created);
        } catch (e: any) {
          setError(e.message);
        }
      });
  }, []);

  async function save() {
    setSaving(true);
    setError('');
    try {
      const updated = await api(`/api/menu/${menu._id}`, {
        method: 'PUT',
        body: { name: menu.name, categories: menu.categories },
      });
      setMenu(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  function addCategory() {
    setMenu({
      ...menu,
      categories: [...menu.categories, { id: `cat-${Date.now().toString(36)}`, name: 'Nova kategorija', items: [] }],
    });
  }

  function updateCategory(id: string, updates: any) {
    setMenu({
      ...menu,
      categories: menu.categories.map((c: any) => (c.id === id ? { ...c, ...updates } : c)),
    });
  }

  async function toggleAvailability(item: any) {
    try {
      await api(`/api/menu/${menu._id}/item/${item.id}/availability`, {
        method: 'PATCH',
        body: { is_available: !item.is_available },
      });
      setMenu({
        ...menu,
        categories: menu.categories.map((c: any) => ({
          ...c,
          items: c.items.map((i: any) =>
            i.id === item.id ? { ...i, is_available: !item.is_available } : i),
        })),
      });
    } catch (e: any) {
      setError(e.message);
    }
  }

  if (error && !menu) return <div className="error-msg">{error}</div>;
  if (!menu) return <p className="muted">Učitavanje…</p>;

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Meni pića</h1>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="secondary" onClick={addCategory}>+ Kategorija</button>
          <button onClick={save} disabled={saving}>{saving ? 'Spremam…' : 'Spremi meni'}</button>
        </div>
      </div>
      {error && <div className="error-msg">{error}</div>}

      {menu.categories.map((cat: any) => (
        <div className="card" key={cat.id}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <input value={cat.name} style={{ maxWidth: 300, fontWeight: 700 }}
                   onChange={(e) => updateCategory(cat.id, { name: e.target.value })} />
            <button className="danger"
                    onClick={() => setMenu({ ...menu, categories: menu.categories.filter((c: any) => c.id !== cat.id) })}>
              Obriši kategoriju
            </button>
          </div>

          <table style={{ marginTop: 12 }}>
            <thead>
              <tr><th>Naziv</th><th>Cijena</th><th>Volumen</th><th>Dostupno</th><th /></tr>
            </thead>
            <tbody>
              {cat.items.map((item: any) => (
                <tr key={item.id} style={{ opacity: item.is_available ? 1 : 0.45 }}>
                  <td>{item.name}</td>
                  <td>{item.price} €</td>
                  <td>{item.volume ?? '—'}</td>
                  <td>
                    <button className={item.is_available ? 'secondary' : ''}
                            onClick={() => toggleAvailability(item)}>
                      {item.is_available ? 'Isključi' : 'Uključi'}
                    </button>
                  </td>
                  <td>
                    <a href="#" style={{ color: 'var(--error)' }}
                       onClick={(e) => {
                         e.preventDefault();
                         updateCategory(cat.id, { items: cat.items.filter((i: any) => i.id !== item.id) });
                       }}>
                      Ukloni
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <ItemForm onAdd={(item) => updateCategory(cat.id, { items: [...cat.items, item] })} />
        </div>
      ))}
      {menu.categories.length === 0 && (
        <p className="muted">Nema kategorija — dodaj prvu s gumbom „+ Kategorija".</p>
      )}
    </>
  );
}
