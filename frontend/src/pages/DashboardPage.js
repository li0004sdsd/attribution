import React, { useEffect, useState } from 'react';
import { listChannels } from '../api/channels';
import { listPaths } from '../api/journeys';
import { listResults } from '../api/attribution';

export default function DashboardPage() {
  const [stats, setStats] = useState({ channels: 0, paths: 0, converted: 0, totalValue: 0 });
  const [topChannels, setTopChannels] = useState([]);

  useEffect(() => {
    Promise.all([listChannels(), listPaths(), listResults('linear')]).then(
      ([chRes, pathRes, attrRes]) => {
        const paths = pathRes.data.results || pathRes.data;
        const converted = paths.filter((p) => p.converted);
        const totalValue = converted.reduce((s, p) => s + parseFloat(p.conversion_value), 0);
        setStats({
          channels: (chRes.data.results || chRes.data).length,
          paths: paths.length,
          converted: converted.length,
          totalValue: totalValue.toFixed(2),
        });
        const results = attrRes.data.results || attrRes.data;
        const sorted = [...results].sort((a, b) => parseFloat(b.credit) - parseFloat(a.credit)).slice(0, 5);
        setTopChannels(sorted);
      }
    ).catch(() => {});
  }, []);

  const statCards = [
    { label: 'Ad Channels', value: stats.channels, color: '#e94560' },
    { label: 'Conversion Paths', value: stats.paths, color: '#0f3460' },
    { label: 'Conversions', value: stats.converted, color: '#533483' },
    { label: 'Total Value', value: `$${stats.totalValue}`, color: '#16213e' },
  ];

  return (
    <div>
      <h1 style={styles.heading}>Dashboard</h1>
      <div style={styles.cards}>
        {statCards.map(({ label, value, color }) => (
          <div key={label} style={{ ...styles.card, borderTop: `4px solid ${color === '#16213e' ? '#e94560' : color}` }}>
            <div style={styles.cardValue}>{value}</div>
            <div style={styles.cardLabel}>{label}</div>
          </div>
        ))}
      </div>
      {topChannels.length > 0 && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Top Channels (Linear Attribution)</h2>
          <div style={styles.table}>
            <div style={styles.tableHeader}>
              <span>Channel</span>
              <span>Platform</span>
              <span>Credit ($)</span>
            </div>
            {topChannels.map((r) => (
              <div key={r.id} style={styles.tableRow}>
                <span>{r.channel_detail?.name || r.channel}</span>
                <span style={styles.badge}>{r.channel_detail?.platform || '-'}</span>
                <span style={styles.credit}>${parseFloat(r.credit).toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  heading: { color: '#e0e0f0', marginBottom: 24 },
  cards: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20, marginBottom: 40 },
  card: { background: '#16213e', borderRadius: 10, padding: '24px 20px' },
  cardValue: { fontSize: 32, fontWeight: 700, color: '#e0e0f0', marginBottom: 8 },
  cardLabel: { color: '#a0a8c0', fontSize: 14 },
  section: { background: '#16213e', borderRadius: 10, padding: 24 },
  sectionTitle: { color: '#e0e0f0', marginBottom: 20, fontSize: 18 },
  table: { display: 'flex', flexDirection: 'column', gap: 0 },
  tableHeader: {
    display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
    color: '#a0a8c0', fontSize: 12, fontWeight: 600,
    padding: '8px 12px', borderBottom: '1px solid #2a2a4a', textTransform: 'uppercase',
  },
  tableRow: {
    display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
    padding: '12px', borderBottom: '1px solid #1a1a3a',
    alignItems: 'center', color: '#e0e0f0', fontSize: 14,
  },
  badge: {
    background: '#0f3460', color: '#a0c4ff', padding: '2px 8px',
    borderRadius: 4, fontSize: 11, display: 'inline-block',
  },
  credit: { color: '#4ade80', fontWeight: 600 },
};
