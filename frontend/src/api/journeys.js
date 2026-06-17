import client from './client';

export const listPaths = () => client.get('/journeys/paths/');
export const getPath = (id) => client.get(`/journeys/paths/${id}/`);
export const createPath = (data) => client.post('/journeys/paths/', data);
export const bulkImport = (data) => client.post('/journeys/bulk-import/', data);
export const deletePath = (id) => client.delete(`/journeys/paths/${id}/`);
