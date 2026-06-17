import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const navLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/channels', label: 'Ad Channels' },
  { to: '/journeys', label: 'Conversion Paths' },
  { to: '/attribution', label: 'Attribution' },
];

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav style={styles.nav}>
      <div style={styles.brand}>Attribution Platform</div>
      <div style={styles.links}>
        {navLinks.map(({ to, label }) => (
          <Link
            key={to}
            to={to}
            style={{
              ...styles.link,
              ...(location.pathname === to ? styles.activeLink : {}),
            }}
          >
            {label}
          </Link>
        ))}
      </div>
      <div style={styles.user}>
        <span style={styles.username}>{user?.username}</span>
        <button style={styles.logoutBtn} onClick={handleLogout}>Logout</button>
      </div>
    </nav>
  );
}

const styles = {
  nav: {
    display: 'flex',
    alignItems: 'center',
    background: '#1a1a2e',
    padding: '0 24px',
    height: 56,
    gap: 24,
  },
  brand: { color: '#e94560', fontWeight: 700, fontSize: 18, marginRight: 16 },
  links: { display: 'flex', gap: 4, flex: 1 },
  link: {
    color: '#a0a8c0',
    textDecoration: 'none',
    padding: '6px 14px',
    borderRadius: 6,
    fontSize: 14,
    transition: 'all 0.2s',
  },
  activeLink: { color: '#fff', background: 'rgba(233,69,96,0.2)' },
  user: { display: 'flex', alignItems: 'center', gap: 12 },
  username: { color: '#a0a8c0', fontSize: 14 },
  logoutBtn: {
    background: 'transparent',
    border: '1px solid #e94560',
    color: '#e94560',
    padding: '4px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 13,
  },
};
