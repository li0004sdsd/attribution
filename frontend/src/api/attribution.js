import client from './client';

export const runAttribution = (modelType, weights = null) => {
  const payload = { model_type: modelType };
  if (modelType === 'custom_weight' && weights) {
    payload.first_touch_weight = weights.first_touch;
    payload.middle_touch_weight = weights.middle_touch;
    payload.last_touch_weight = weights.last_touch;
  }
  return client.post('/attribution/run/', payload);
};

export const listResults = (modelType) =>
  client.get('/attribution/results/', { params: modelType ? { model_type: modelType } : {} });
