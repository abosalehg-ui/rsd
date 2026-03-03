/**
 * رصد - أدوات API
 */

const API_BASE = '/api';

export async function fetchAPI(endpoint, params = {}) {
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
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
  const url = `${API_BASE}${endpoint}`;
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