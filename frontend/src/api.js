import axios from 'axios';

let currentMerchantId = null;

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
});

api.interceptors.request.use((config) => {
  if (currentMerchantId) {
    config.headers['X-Merchant-ID'] = currentMerchantId;
  }
  return config;
});

export function setMerchantId(id) {
  currentMerchantId = id;
}

export const getMerchants = () => api.get('/api/v1/merchants/');
export const getMerchant = () => api.get('/api/v1/merchants/me/');
export const getPayouts = () => api.get('/api/v1/payouts/');
export const getLedger = () => api.get('/api/v1/ledger/');

export const createPayout = (data, idempotencyKey) =>
  api.post('/api/v1/payouts/', data, {
    headers: { 'Idempotency-Key': idempotencyKey },
  });
