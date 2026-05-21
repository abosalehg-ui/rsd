/**
 * رصد - أدوات API
 *
 * في وضع التطوير: vite proxy يحوّل /api → http://localhost:8000
 * في وضع الإنتاج (GitHub Pages مثلاً): يستخدم VITE_API_BASE من البيئة،
 * وإلا يبقى '/api' (يتطلّب أن يكون الباك على نفس النطاق).
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export async function fetchAPI(endpoint, params = {}) {
  const base = API_BASE.startsWith('http') ? API_BASE : `${window.location.origin}${API_BASE}`;
  const url = new URL(`${base}${endpoint}`);
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      url.searchParams.set(key, val);
    }
  });

  const response = await fetch(url);
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return response.json();
}

export async function postAPI(endpoint) {
  const base = API_BASE.startsWith('http') ? API_BASE : `${window.location.origin}${API_BASE}`;
  const url = `${base}${endpoint}`;
  const response = await fetch(url, { method: 'POST' });
  if (!response.ok) throw new Error(`API Error: ${response.status}`);
  return response.json();
}

// Events
export const getEvents = (params) => fetchAPI('/events/', params);
export const getLatestEvents = (limit = 20) => fetchAPI('/events/latest', { limit });
export const getMapEvents = (hours = 24) => fetchAPI('/events/map', { hours });
export const getStats = (hours = 24) => fetchAPI('/events/stats', { hours });
export const getTimeline = (hours = 48) => fetchAPI('/events/timeline', { hours });

// Flights
export const getLiveFlights = () => fetchAPI('/flights/live');
export const getMilitaryHistory = (hours = 24) => fetchAPI('/flights/military/history', { hours });
export const getMilitaryStats = (hours = 24) => fetchAPI('/flights/military/stats', { hours });

// Health
export const getHealth = () => fetchAPI('/health');
export const getSources = () => fetchAPI('/sources');
export const refreshSources = () => postAPI('/refresh');

// Iran OSINT
export const getIranStrikes = (params = {}) => fetchAPI('/iran/strikes', params);
export const getIranLeaders = (hours = 72) => fetchAPI('/iran/leaders', { hours });
export const getIranStats = (hours = 72) => fetchAPI('/iran/stats', { hours });

// Nuclear facilities ☢️
export const getNuclearFacilities = (params = {}) => fetchAPI('/nuclear/facilities', params);
export const getNuclearStats = () => fetchAPI('/nuclear/stats');
