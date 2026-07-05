export type TableDef = {
  id: string;
  label: string;
  type: 'standard' | 'standing' | 'separe' | 'vip_separe' | string;
  x: number; y: number; width: number; height: number;
  capacity: number;
  min_spend: number;
  deposit: number;
  section_id: string | null;
  description?: string;
};

const TABLE_TYPES = [
  { value: 'standard', label: 'Standardni stol' },
  { value: 'standing', label: 'Stajaći (bar) stol' },
  { value: 'separe', label: 'Separé' },
  { value: 'vip_separe', label: 'VIP separé (depozit)' },
];

export default function TableEditor({
  table, sections, onChange, onRemove, onClose,
}: {
  table: TableDef;
  sections: any[];
  onChange: (updates: Partial<TableDef>) => void;
  onRemove: () => void;
  onClose: () => void;
}) {
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>Stol {table.label}</h2>
        <button className="secondary" onClick={onClose}>Zatvori</button>
      </div>

      <label>Naziv</label>
      <input value={table.label} onChange={(e) => onChange({ label: e.target.value })} />

      <label>Tip</label>
      <select value={table.type} onChange={(e) => onChange({ type: e.target.value })}>
        {TABLE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
      </select>

      <div className="form-row">
        <div>
          <label>Kapacitet</label>
          <input type="number" value={table.capacity}
                 onChange={(e) => onChange({ capacity: Number(e.target.value) })} />
        </div>
        <div>
          <label>Min. potrošnja (€)</label>
          <input type="number" value={table.min_spend}
                 onChange={(e) => onChange({ min_spend: Number(e.target.value) })} />
        </div>
      </div>

      {table.type === 'vip_separe' && (
        <>
          <label>Depozit (€) — pretvara se u kupon za piće</label>
          <input type="number" value={table.deposit}
                 onChange={(e) => onChange({ deposit: Number(e.target.value) })} />
        </>
      )}

      <label>Sekcija</label>
      <select value={table.section_id ?? ''}
              onChange={(e) => onChange({ section_id: e.target.value || null })}>
        <option value="">Bez sekcije</option>
        {sections.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>

      <div className="form-row">
        <div>
          <label>Širina (%)</label>
          <input type="number" step="0.5" value={table.width}
                 onChange={(e) => onChange({ width: Number(e.target.value) })} />
        </div>
        <div>
          <label>Visina (%)</label>
          <input type="number" step="0.5" value={table.height}
                 onChange={(e) => onChange({ height: Number(e.target.value) })} />
        </div>
      </div>

      <label>Opis</label>
      <textarea rows={2} value={table.description ?? ''}
                onChange={(e) => onChange({ description: e.target.value })} />

      <button className="danger" style={{ marginTop: 14, width: '100%' }} onClick={onRemove}>
        Obriši stol
      </button>
    </div>
  );
}
