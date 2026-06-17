import React from 'react';
import NavBar from './NavBar';

export default function Layout({ children }) {
  return (
    <div style={{ minHeight: '100vh', background: '#0f0f23', color: '#e0e0f0' }}>
      <NavBar />
      <main style={{ padding: '32px 40px', maxWidth: 1200, margin: '0 auto' }}>
        {children}
      </main>
    </div>
  );
}
