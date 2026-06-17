import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ChannelsPage from './pages/ChannelsPage';
import JourneysPage from './pages/JourneysPage';
import AttributionPage from './pages/AttributionPage';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout>
                  <DashboardPage />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/channels"
            element={
              <PrivateRoute>
                <Layout>
                  <ChannelsPage />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/journeys"
            element={
              <PrivateRoute>
                <Layout>
                  <JourneysPage />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/attribution"
            element={
              <PrivateRoute>
                <Layout>
                  <AttributionPage />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
