import client from './client';

export const listChannels = () => client.get('/channels/');
export const getChannel = (id) => client.get(`/channels/${id}/`);
export const createChannel = (data) => client.post('/channels/', data);
export const updateChannel = (id, data) => client.put(`/channels/${id}/`, data);
export const deleteChannel = (id) => client.delete(`/channels/${id}/`);
