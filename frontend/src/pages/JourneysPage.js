import React, { useEffect, useState } from 'react';
import { listPaths, bulkImport, deletePath } from '../api/journeys';
import { listChannels } from '../api/channels';

export default function JourneysPage() {
  const [paths, setPaths] = useState([]);
  const [channels, setChannels] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ user_id: '', converted: false, conversion_value: '', touchpoints: [] });
  const [newTp, setNewTp] = useState({ channel: '', timestamp: '', position: 1 });
  const [error, setError] = useState('');

  const load = () =>
    Promise.all([listPaths(), listChannels()]).then(([p, c]) => {
      setPaths(p.data.results || p.data);
      setChannels(c.data.results || c.data);
    }).catch(() => {});

  useEffect(() => { load(); }, []);

  const addTouchpoint = () => {
    if (!newTp.channel || !newTp.timestamp) return;
    setForm({ ...form, touchpoints: [...form.touchpoints, { ...newTp, channel: parseInt(newTp.channel), position: form.touchpoints.length + 1 }] });
    setNewTp({ channel: '', timestamp: '', position: form.touchpoints.length + 2 });
  };

  const removeTp = (idx) => setForm({ ...form, touchpoints: form.touchpoints.filter((_, i) => i !== idx) });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await bulkImport({ ...form, conversion_value: parseFloat(form.conversion_value) || 0 });
      setForm({ user_id: '', converted: false, conversion_value: '', touchpoints: [] });
      setShowForm(false);
      load();
    } catch {
      setError('Failed to create path.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete path?')) return;
    await deletePath(id);
    load();
  };

  const channelName = (id) => channels.find((c) => c.id === id)?.name || id;

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Conversion Paths</h1>
        <button style={styles.addBtn} onClick={() => setShowForm(!showForm)}>+ Add Path</button>
      </div>

      {showForm && (
        <div style={styles.formCard}>
          <h3 style={styles.formTitle}>New Conversion Path</h3>
          <form onSubmit={handleSubmit} style={styles.form}>
            <input style={styles.input} placeholder="User ID" value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} required />
            <label style={styles.checkLabel}>
              <input type="checkbox" checked={form.converted} onChange={(e) => setForm({ ...form, converted: e.target.checked })} />
              <span>Converted</span>
            </label>
            {form.converted && (
              <input style={styles.input} type="number" step="0.01" placeholder="Conversion Value ($)" value={form.conversion_value} onChange={(e) => setForm({ ...form, conversion_value: e.target.value })} />
            )}
            <div style={styles.tpSection}>
              <strong style={{ color: '#a0a8c0', fontSize: 13 }}>Touchpoints</strong>
              {form.touchpoints.map((tp, i) => (
                <div key={i} style={styles.tpRow}>
                  <span style={{ color: '#a0c4ff' }}>#{tp.position} {channelName(tp.channel)}</span>
                  <button type="button" style={styles.removeTpBtn} onClick={() => removeTp(i)}>×</button>
                </div>
              ))}
              <div style={styles.tpAdd}>
                <select style={styles.inputSm} value={newTp.channel} onChange={(e) => setNewTp({ ...newTp, channel: e.target.value })}>
                  <option value="">Select channel</option>
                  {channels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <input style={styles.inputSm} type="datetime-local" value={newTp.timestamp} onChange={(e) => setNewTp({ ...newTp, timestamp: e.target.value })} />
                <button type="button" style={styles.addTpBtn} onClick={addTouchpoint}>Add</button>
              </div>
            </div>
            {error && <div style={styles.error}>{error}</div>}
            <div style={styles.formActions}>
              <button style={styles.saveBtn} type="submit">Save Path</button>
              <button style={styles.cancelBtn} type="button" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div style={styles.table}>
        <div style={styles.tableHeader}>
          <span>User ID</span>
          <span>Touchpoints</span>
          <span>Converted</span>
          <span>Value ($)</span>
          <span>Actions</span>
        </div>
        {paths.map((path) => (
          <React.Fragment key={path.id}>
            <div style={styles.tableRow} onClick={() => setExpanded(expanded === path.id ? null : path.id)}>
              <span style={styles.userId}>{path.user_id}</span>
              <span style={styles.count}>{path.touchpoints?.length || 0}</span>
              <span style={{ color: path.converted ? '#4ade80' : '#f87171' }}>{path.converted ? 'Yes' : 'No'}</span>
              <span>{parseFloat(path.conversion_value).toFixed(2)}</span>
              <button style={styles.deleteBtn} onClick={(e) => { e.stopPropagation(); handleDelete(path.id); }}>Delete</button>
            </div>
            {expanded === path.id && (
              <div style={styles.expanded}>
                {path.touchpoints?.length > 0 ? (
                  path.touchpoints.map((tp) => (
                    <div key={tp.id} style={styles.tpDetail}>
                      <span style={styles.tpPos}>#{tp.position}</span>
                      <span style={styles.tpChannel}>{tp.channel_detail?.name || tp.channel}</span>
                      <span style={styles.tpPlatform}>{tp.channel_detail?.platform}</span>
                      <span style={styles.tpTime}>{new Date(tp.timestamp).toLocaleString()}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ color: '#a0a8c0', fontSize: 13 }}>No touchpoints.</div>
                )}
              </div>
            )}
          </React.Fragment>
        ))}
        {paths.length === 0 && <div style={styles.empty}>No conversion paths yet.</div>}
      </div>
    </div>
  );
}

const styles = {
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  heading: { color: '#e0e0f0', margin: 0 },
  addBtn: { background: '#e94560', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', cursor: 'pointer', fontWeight: 600 },
  formCard: { background: '#16213e', borderRadius: 10, padding: 24, marginBottom: 24 },
  formTitle: { color: '#e0e0f0', marginTop: 0 },
  form: { display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 500 },
  input: { background: '#0f0f23', border: '1px solid #2a2a4a', borderRadius: 8, padding: '10px 14px', color: '#e0e0f0', fontSize: 14 },
  inputSm: { background: '#0f0f23', border: '1px solid #2a2a4a', borderRadius: 6, padding: '8px 12px', color: '#e0e0f0', fontSize: 13, flex: 1 },
  checkLabel: { display: 'flex', alignItems: 'center', gap: 8, color: '#a0a8c0', cursor: 'pointer' },
  tpSection: { display: 'flex', flexDirection: 'column', gap: 8, background: '#0f0f23', borderRadius: 8, padding: 12 },
  tpRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' },
  removeTpBtn: { background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: 18 },
  tpAdd: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  addTpBtn: { background: '#0f3460', color: '#a0c4ff', border: 'none', borderRadius: 6, padding: '8px 16px', cursor: 'pointer', fontSize: 13 },
  error: { color: '#e94560', fontSize: 13 },
  formActions: { display: 'flex', gap: 12 },
  saveBtn: { background: '#e94560', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 24px', cursor: 'pointer', fontWeight: 600 },
  cancelBtn: { background: 'transparent', border: '1px solid #2a2a4a', color: '#a0a8c0', borderRadius: 8, padding: '10px 24px', cursor: 'pointer' },
  table: { background: '#16213e', borderRadius: 10, overflow: 'hidden' },
  tableHeader: {
    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
    padding: '12px 20px', background: '#0f0f23', color: '#a0a8c0',
    fontSize: 12, fontWeight: 600, textTransform: 'uppercase',
  },
  tableRow: {
    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
    padding: '14px 20px', borderBottom: '1px solid #1a1a3a',
    alignItems: 'center', color: '#e0e0f0', fontSize: 14, cursor: 'pointer',
  },
  userId: { fontWeight: 500, color: '#a0c4ff' },
  count: { color: '#e0e0f0' },
  deleteBtn: { background: 'transparent', border: '1px solid #f87171', color: '#f87171', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 12 },
  expanded: { background: '#0d0d1f', padding: '12px 24px', borderBottom: '1px solid #1a1a3a' },
  tpDetail: { display: 'grid', gridTemplateColumns: '40px 2fr 1fr 2fr', gap: 12, padding: '6px 0', alignItems: 'center' },
  tpPos: { color: '#e94560', fontWeight: 700 },
  tpChannel: { color: '#e0e0f0', fontSize: 13 },
  tpPlatform: { background: '#0f3460', color: '#a0c4ff', padding: '2px 8px', borderRadius: 4, fontSize: 11 },
  tpTime: { color: '#a0a8c0', fontSize: 12 },
  empty: { padding: 40, textAlign: 'center', color: '#a0a8c0' },
};
