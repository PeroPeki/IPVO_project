import { useState } from 'react';

export default function ItemForm({ onAdd }: { onAdd: (item: any) => void }) {
  const [form, setForm] = useState({ name: '', price: '', volume: '', description: '' });

  function submit() {
    if (!form.name || !form.price) return;
    onAdd({
      id: `item-${Date.now().toString(36)}`,
      name: form.name,
      description: form.description || null,
      price: Number(form.price),
      image_url: null,
      is_available: true,
      allergens: [],
      volume: form.volume || null,
    });
    setForm({ name: '', price: '', volume: '', description: '' });
  }

  return (
    <div className="form-row" style={{ marginTop: 12, alignItems: 'flex-end' }}>
      <div>
        <label>Nova stavka</label>
        <input placeholder="npr. Gin tonik" value={form.name}
               onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div>
        <label>Cijena (€)</label>
        <input type="number" step="0.1" value={form.price}
               onChange={(e) => setForm({ ...form, price: e.target.value })} />
      </div>
      <div>
        <label>Volumen</label>
        <input placeholder="0.2l" value={form.volume}
               onChange={(e) => setForm({ ...form, volume: e.target.value })} />
      </div>
      <button type="button" className="secondary" onClick={submit}>+ Dodaj</button>
    </div>
  );
}
