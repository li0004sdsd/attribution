import client from './client';

export const login = (username, password) =>
  client.post('/auth/login/', { username, password });

export const register = (username, email, password) =>
  client.post('/auth/register/', { username, email, password });

export const getMe = () => client.get('/auth/me/');
