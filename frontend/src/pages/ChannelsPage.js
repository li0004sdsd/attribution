import React, { useEffect, useState } from 'react';
import { listChannels, createChannel, updateChannel, deleteChannel } from '../api/channels';

const PLATFORMS = ['google', 'facebook', 'twitter', 'linkedin', 'tiktok', 'email', 'organic', 'other'];

const emptyForm = { name: '', platform: 'other', cost_per_click: '', active: true };

export default function ChannelsPage() {
  const [channels, setChannels] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editId, setEditId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');

  const load = () =>
    listChannels().then(({ data }) => setChannels(data.results || data)).catch(() => {});

  useEffect(() => { load(); }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === 'checkbox' ? checked : value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (editId) {
        await updateChannel(editId, form);
      } else {
        await createChannel(form);
      }
      setForm(emptyForm);
      setEditId(null);
      setShowForm(false);
      load();
    } catch (err) {
      setError('Failed to save channel.');
    }
  };

  const startEdit = (ch) => {
    setForm({ name: ch.name, platform: ch.platform, cost_per_click: ch.cost_per_click, active: ch.active });
    setEditId(ch.id);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this channel?')) return;
    await deleteChannel(id);
    load();
  };

  const cancel = () => { setForm(emptyForm); setEditId(null); setShowForm(false); setError(''); };

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Ad Channels</h1>
        <button style={styles.addBtn} onClick={() => setShowForm(true)}>+ Add Channel</button>
      </div>

      {showForm && (
        <div style={styles.formCard}>
          <h3 style={styles.formTitle}>{editId ? 'Edit Channel' : 'New Channel'}</h3>
          <form onSubmit={handleSubmit} style={styles.form}>
            <input style={styles.input} name="name" placeholder="Channel name" value={form.name} onChange={handleChange} required />
            <select style={styles.input} name="platform" value={form.platform} onChange={handleChange}>
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <input style={styles.input} name="cost_per_click" type="number" step="0.0001" placeholder="CPC" value={form.cost_per_click} onChange={handleChange} />
            <label style={styles.checkLabel}>
              <input type="checkbox" name="active" checked={form.active} onChange={handleChange} />
              <span>Active</span>
            </label>
            {error && <div style={styles.error}>{error}</div>}
            <div style={styles.formActions}>
              <button style={styles.saveBtn} type="submit">Save</button>
              <button style={styles.cancelBtn} type="button" onClick={cancel}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div style={styles.table}>
        <div style={styles.tableHeader}>
          <span>Name</span>
          <span>Platform</span>
          <span>CPC ($)</span>
          <span>Status</span>
          <span>Actions</span>
        </div>
        {channels.map((ch) => (
          <div key={ch.id} style={styles.tableRow}>
            <span style={styles.name}>{ch.name}</span>
            <span style={styles.badge}>{ch.platform}</span>
            <span>{parseFloat(ch.cost_per_click).toFixed(4)}</span>
            <span style={{ color: ch.active ? '#4ade80' : '#f87171' }}>{ch.active ? 'Active' : 'Inactive'}</span>
            <div style={styles.actions}>
              <button style={styles.editBtn} onClick={() => startEdit(ch)}>Edit</button>
              <button style={styles.deleteBtn} onClick={() => handleDelete(ch.id)}>Delete</button>
            </div>
          </div>
        ))}
        {channels.length === 0 && <div style={styles.empty}>No channels yet.</div>}
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
  form: { display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 400 },
  input: { background: '#0f0f23', border: '1px solid #2a2a4a', borderRadius: 8, padding: '10px 14px', color: '#e0e0f0', fontSize: 14 },
  checkLabel: { display: 'flex', alignItems: 'center', gap: 8, color: '#a0a8c0', cursor: 'pointer' },
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
    alignItems: 'center', color: '#e0e0f0', fontSize: 14,
  },
  name: { fontWeight: 500 },
  badge: { background: '#0f3460', color: '#a0c4ff', padding: '2px 8px', borderRadius: 4, fontSize: 11, display: 'inline-block' },
  actions: { display: 'flex', gap: 8 },
  editBtn: { background: 'transparent', border: '1px solid #e94560', color: '#e94560', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 12 },
  deleteBtn: { background: 'transparent', border: '1px solid #f87171', color: '#f87171', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 12 },
  empty: { padding: 40, textAlign: 'center', color: '#a0a8c0' },
};
