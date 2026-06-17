import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, ResponsiveContainer,
} from 'recharts';
import { runAttribution, listResults } from '../api/attribution';

const MODELS = [
  { key: 'first_touch', label: 'First Touch' },
  { key: 'last_touch', label: 'Last Touch' },
  { key: 'linear', label: 'Linear' },
];

const COLORS = ['#e94560', '#0f3460', '#533483', '#16213e', '#4ade80', '#f87171', '#a0c4ff', '#fbbf24'];

export default function AttributionPage() {
  const [activeModel, setActiveModel] = useState('linear');
  const [results, setResults] = useState([]);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadResults = (model) => {
    setLoading(true);
    listResults(model)
      .then(({ data }) => setResults(data.results || data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadResults(activeModel); }, [activeModel]);

  const handleRun = async () => {
    setRunning(true);
    try {
      const { data } = await runAttribution(activeModel);
      setResults(data.results || data);
    } catch {
    } finally {
      setRunning(false);
    }
  };

  const chartData = results.map((r) => ({
    name: r.channel_detail?.name || `Ch ${r.channel}`,
    credit: parseFloat(parseFloat(r.credit).toFixed(2)),
  }));

  const total = results.reduce((s, r) => s + parseFloat(r.credit), 0);

  return (
    <div>
      <div style={styles.header}>
        <h1 style={styles.heading}>Attribution Analysis</h1>
      </div>

      <div style={styles.controls}>
        <div style={styles.modelTabs}>
          {MODELS.map(({ key, label }) => (
            <button
              key={key}
              style={{ ...styles.tab, ...(activeModel === key ? styles.activeTab : {}) }}
              onClick={() => setActiveModel(key)}
            >
              {label}
            </button>
          ))}
        </div>
        <button style={styles.runBtn} onClick={handleRun} disabled={running}>
          {running ? 'Calculating...' : 'Run Attribution'}
        </button>
      </div>

      {loading ? (
        <div style={styles.loading}>Loading results...</div>
      ) : results.length === 0 ? (
        <div style={styles.empty}>No results. Click "Run Attribution" to calculate.</div>
      ) : (
        <>
          <div style={styles.charts}>
            <div style={styles.chartCard}>
              <h3 style={styles.chartTitle}>Credit by Channel (Bar)</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
                  <XAxis dataKey="name" stroke="#a0a8c0" tick={{ fill: '#a0a8c0', fontSize: 11 }} angle={-30} textAnchor="end" />
                  <YAxis stroke="#a0a8c0" tick={{ fill: '#a0a8c0', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#16213e', border: '1px solid #2a2a4a', color: '#e0e0f0' }} />
                  <Bar dataKey="credit" fill="#e94560" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={styles.chartCard}>
              <h3 style={styles.chartTitle}>Credit Distribution (Pie)</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    dataKey="credit"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={{ stroke: '#a0a8c0' }}
                  >
                    {chartData.map((_, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#16213e', border: '1px solid #2a2a4a', color: '#e0e0f0' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div style={styles.tableSection}>
            <h3 style={styles.chartTitle}>Detailed Results</h3>
            <div style={styles.table}>
              <div style={styles.tableHeader}>
                <span>Channel</span>
                <span>Platform</span>
                <span>Credit ($)</span>
                <span>Share (%)</span>
              </div>
              {results.map((r) => (
                <div key={r.id} style={styles.tableRow}>
                  <span style={styles.chName}>{r.channel_detail?.name || r.channel}</span>
                  <span style={styles.badge}>{r.channel_detail?.platform || '-'}</span>
                  <span style={styles.credit}>${parseFloat(r.credit).toFixed(2)}</span>
                  <span style={styles.share}>
                    {total > 0 ? ((parseFloat(r.credit) / total) * 100).toFixed(1) : 0}%
                  </span>
                </div>
              ))}
              <div style={styles.totalRow}>
                <span>Total</span>
                <span></span>
                <span style={styles.credit}>${total.toFixed(2)}</span>
                <span>100%</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const styles = {
  header: { marginBottom: 24 },
  heading: { color: '#e0e0f0', margin: 0 },
  controls: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  modelTabs: { display: 'flex', gap: 4, background: '#16213e', padding: 4, borderRadius: 8 },
  tab: {
    background: 'transparent', border: 'none', color: '#a0a8c0',
    padding: '8px 20px', borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 500,
  },
  activeTab: { background: '#e94560', color: '#fff' },
  runBtn: {
    background: '#533483', color: '#fff', border: 'none',
    borderRadius: 8, padding: '10px 24px', cursor: 'pointer', fontWeight: 600, fontSize: 14,
  },
  loading: { padding: 60, textAlign: 'center', color: '#a0a8c0' },
  empty: { padding: 60, textAlign: 'center', color: '#a0a8c0', background: '#16213e', borderRadius: 10 },
  charts: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 },
  chartCard: { background: '#16213e', borderRadius: 10, padding: 24 },
  chartTitle: { color: '#e0e0f0', marginTop: 0, marginBottom: 16, fontSize: 16 },
  tableSection: { background: '#16213e', borderRadius: 10, padding: 24 },
  table: { display: 'flex', flexDirection: 'column' },
  tableHeader: {
    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr',
    padding: '8px 12px', background: '#0f0f23', color: '#a0a8c0',
    fontSize: 12, fontWeight: 600, textTransform: 'uppercase', borderRadius: '6px 6px 0 0',
  },
  tableRow: {
    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr',
    padding: '12px', borderBottom: '1px solid #1a1a3a',
    alignItems: 'center', color: '#e0e0f0', fontSize: 14,
  },
  totalRow: {
    display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr',
    padding: '12px', background: '#0f0f23', color: '#e0e0f0',
    fontWeight: 700, fontSize: 14, borderRadius: '0 0 6px 6px',
  },
  chName: { fontWeight: 500 },
  badge: { background: '#0f3460', color: '#a0c4ff', padding: '2px 8px', borderRadius: 4, fontSize: 11, display: 'inline-block' },
  credit: { color: '#4ade80', fontWeight: 600 },
  share: { color: '#fbbf24' },
};
