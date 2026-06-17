import client from './client';

export const runAttribution = (modelType) =>
  client.post('/attribution/run/', { model_type: modelType });

export const listResults = (modelType) =>
  client.get('/attribution/results/', { params: modelType ? { model_type: modelType } : {} });
