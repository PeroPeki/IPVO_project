const PALETTE = ['#CC00FF', '#8B00CC', '#4A0080', '#34C759', '#F4B860', '#FF3B30'];

export default function SectionEditor({
  sections, onChange,
}: {
  sections: any[];
  onChange: (sections: any[]) => void;
}) {
  function addSection() {
    const id = `sec-${Date.now().toString(36)}`;
    onChange([...sections, {
      id,
      name: `Sekcija ${sections.length + 1}`,
      table_ids: [],
      color: PALETTE[sections.length % PALETTE.length],
    }]);
  }

  function update(id: string, updates: any) {
    onChange(sections.map((s) => (s.id === id ? { ...s, ...updates } : s)));
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>Sekcije</h2>
      <p className="muted">Konobari se dodjeljuju sekcijama — narudžbe sa stolova sekcije stižu njima.</p>
      {sections.map((s) => (
        <div key={s.id} style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10 }}>
          <input type="color" value={s.color} style={{ width: 42, padding: 2, height: 36 }}
                 onChange={(e) => update(s.id, { color: e.target.value })} />
          <input value={s.name} onChange={(e) => update(s.id, { name: e.target.value })} />
          <button className="danger" onClick={() => onChange(sections.filter((x) => x.id !== s.id))}>×</button>
        </div>
      ))}
      <button className="secondary" style={{ marginTop: 14 }} onClick={addSection}>
        + Dodaj sekciju
      </button>
    </div>
  );
}
