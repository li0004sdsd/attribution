import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { login as apiLogin } from '../api/auth';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { data } = await apiLogin(form.username, form.password);
      login(data.access, data.refresh, { username: form.username });
      navigate('/');
    } catch {
      setError('Invalid username or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Attribution Platform</h1>
        <h2 style={styles.subtitle}>Sign In</h2>
        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            style={styles.input}
            name="username"
            placeholder="Username"
            value={form.username}
            onChange={handleChange}
            required
          />
          <input
            style={styles.input}
            name="password"
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
            required
          />
          {error && <div style={styles.error}>{error}</div>}
          <button style={styles.btn} type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <p style={styles.footer}>
          No account? <Link to="/register" style={styles.link}>Register</Link>
        </p>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    background: '#0f0f23',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  card: {
    background: '#16213e',
    borderRadius: 12,
    padding: '48px 40px',
    width: 380,
    boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  },
  title: { color: '#e94560', textAlign: 'center', margin: '0 0 8px', fontSize: 22 },
  subtitle: { color: '#a0a8c0', textAlign: 'center', margin: '0 0 32px', fontWeight: 400, fontSize: 16 },
  form: { display: 'flex', flexDirection: 'column', gap: 16 },
  input: {
    background: '#0f0f23',
    border: '1px solid #2a2a4a',
    borderRadius: 8,
    padding: '12px 16px',
    color: '#e0e0f0',
    fontSize: 14,
    outline: 'none',
  },
  error: { color: '#e94560', fontSize: 13, textAlign: 'center' },
  btn: {
    background: '#e94560',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    padding: '12px',
    fontWeight: 600,
    fontSize: 15,
    cursor: 'pointer',
    marginTop: 8,
  },
  footer: { color: '#a0a8c0', textAlign: 'center', marginTop: 24, fontSize: 13 },
  link: { color: '#e94560' },
};
