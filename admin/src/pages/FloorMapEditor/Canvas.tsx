import { useEffect, useRef, useState } from 'react';
import { api, effectiveClubId } from '../../api';
import SectionEditor from './SectionEditor';
import TableEditor, { TableDef } from './TableEditor';

/**
 * Floor Map Editor:
 * 1. Admin uploada sliku tlocrta (PNG/JPG) — prikazuje se kao SVG pozadina
 * 2. Klik na prazno mjesto dodaje stol na tu poziciju (% koordinate)
 * 3. Povlačenje pomiče stol; klik na stol otvara editor svojstava
 * 4. Stolovi se grupiraju u sekcije (boja sekcije = vizualna razlika)
 */
export default function FloorMapEditor() {
  const [map, setMap] = useState<any>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  const dragging = useRef<{ id: string; moved: boolean } | null>(null);

  useEffect(() => {
    const clubId = effectiveClubId();
    if (!clubId) { setError('Odaberi klub'); return; }
    api(`/api/floor-maps/club/${clubId}`)
      .then(setMap)
      .catch(async () => {
        // Nema mape — kreiraj praznu
        try {
          const created = await api('/api/floor-maps', {
            body: { club_id: clubId, name: 'Glavni tlocrt', tables: [], sections: [] },
          });
          setMap(created);
        } catch (e: any) {
          setError(e.message);
        }
      });
  }, []);

  function pctCoords(e: React.PointerEvent): { x: number; y: number } {
    const rect = svgRef.current!.getBoundingClientRect();
    return {
      x: Math.round(((e.clientX - rect.left) / rect.width) * 1000) / 10,
      y: Math.round(((e.clientY - rect.top) / rect.height) * 1000) / 10,
    };
  }

  function addTable(e: React.PointerEvent) {
    if (dragging.current?.moved) { dragging.current = null; return; }
    const { x, y } = pctCoords(e);
    const id = `t-${Date.now().toString(36)}`;
    const table: TableDef = {
      id, label: `S${(map.tables?.length ?? 0) + 1}`, type: 'standard',
      x, y, width: 6, height: 6, capacity: 4, min_spend: 0, deposit: 0,
      section_id: map.sections?.[0]?.id ?? null, description: '',
    };
    setMap({ ...map, tables: [...(map.tables ?? []), table] });
    setSelected(id);
  }

  function onTablePointerDown(e: React.PointerEvent, id: string) {
    e.stopPropagation();
    dragging.current = { id, moved: false };
    setSelected(id);
  }

  function onPointerMove(e: React.PointerEvent) {
    if (!dragging.current) return;
    dragging.current.moved = true;
    const { x, y } = pctCoords(e);
    setMap((m: any) => ({
      ...m,
      tables: m.tables.map((t: TableDef) =>
        t.id === dragging.current!.id ? { ...t, x, y } : t),
    }));
  }

  function onPointerUp() {
    if (dragging.current && !dragging.current.moved) dragging.current = null;
    else setTimeout(() => { dragging.current = null; }, 0);
  }

  function updateTable(id: string, updates: Partial<TableDef>) {
    setMap((m: any) => ({
      ...m,
      tables: m.tables.map((t: TableDef) => (t.id === id ? { ...t, ...updates } : t)),
    }));
  }

  function removeTable(id: string) {
    setMap((m: any) => ({ ...m, tables: m.tables.filter((t: TableDef) => t.id !== id) }));
    setSelected(null);
  }

  async function save() {
    setSaving(true);
    setError('');
    try {
      await api(`/api/floor-maps/${map._id}/tables`, {
        method: 'PUT',
        body: { tables: map.tables, sections: map.sections },
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function uploadBackground(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.[0]) return;
    const fd = new FormData();
    fd.append('image', e.target.files[0]);
    try {
      const res = await api<{ url: string }>(`/api/floor-maps/${map._id}/upload-bg`, { formData: fd });
      setMap({ ...map, background_image_url: res.url });
    } catch (err: any) {
      setError(err.message);
    }
  }

  if (error && !map) return <div className="error-msg">{error}</div>;
  if (!map) return <p className="muted">Učitavanje…</p>;

  const sectionColor = (sectionId: string | null) =>
    map.sections?.find((s: any) => s.id === sectionId)?.color ?? '#4A0080';
  const selectedTable = map.tables?.find((t: TableDef) => t.id === selected) ?? null;

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Mapa stolova</h1>
        <div style={{ display: 'flex', gap: 10 }}>
          <label className="btn secondary" style={{ margin: 0, cursor: 'pointer' }}>
            Upload tlocrta
            <input type="file" accept="image/*" style={{ display: 'none' }} onChange={uploadBackground} />
          </label>
          <button onClick={save} disabled={saving}>{saving ? 'Spremam…' : 'Spremi mapu'}</button>
        </div>
      </div>
      {error && <div className="error-msg">{error}</div>}
      <p className="muted">Klik na tlocrt dodaje stol. Povuci stol za premještanje, klikni za uređivanje.</p>

      <div className="editor-layout" style={{ marginTop: 14 }}>
        <div className="editor-canvas card">
          <svg
            ref={svgRef}
            className="floor-svg"
            viewBox="0 0 100 70"
            onPointerDown={addTable}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
          >
            {map.background_image_url && (
              <image href={map.background_image_url} x="0" y="0" width="100" height="70"
                     preserveAspectRatio="xMidYMid slice" opacity="0.45" />
            )}
            {(map.tables ?? []).map((t: TableDef) => (
              <g key={t.id} onPointerDown={(e) => onTablePointerDown(e, t.id)}
                 style={{ cursor: 'grab' }}>
                <rect
                  x={t.x - t.width / 2} y={t.y - t.height / 2}
                  width={t.width} height={t.height} rx={1.2}
                  fill={sectionColor(t.section_id)}
                  fillOpacity={t.type === 'vip_separe' ? 0.9 : 0.65}
                  stroke={selected === t.id ? '#CC00FF' : '#F0E6FF'}
                  strokeWidth={selected === t.id ? 0.6 : 0.25}
                />
                <text x={t.x} y={t.y + 1} textAnchor="middle" fontSize="2.6"
                      fill="#F0E6FF" style={{ pointerEvents: 'none', userSelect: 'none' }}>
                  {t.label}
                </text>
              </g>
            ))}
          </svg>
        </div>

        <div className="editor-panel">
          {selectedTable ? (
            <TableEditor
              table={selectedTable}
              sections={map.sections ?? []}
              onChange={(u) => updateTable(selectedTable.id, u)}
              onRemove={() => removeTable(selectedTable.id)}
              onClose={() => setSelected(null)}
            />
          ) : (
            <SectionEditor
              sections={map.sections ?? []}
              onChange={(sections) => setMap({ ...map, sections })}
            />
          )}
        </div>
      </div>
    </>
  );
}
