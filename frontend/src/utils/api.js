/**
 * رصد - أدوات API
 *
 * في وضع التطوير: vite proxy يحوّل /api → http://localhost:8000
 * في وضع الإنتاج (GitHub Pages مثلاً): يستخدم VITE_API_BASE من البيئة،
 * وإلا يبقى '/api' (يتطلّب أن يكون الباك على نفس النطاق).
 *
 * مفتاح API اختياري: عند ضبط VITE_API_KEY تُرسَل الترويسة X-API-Key مع كل
 * طلب — مطلوبة للنقاط المحمية (POST /api/refresh) حين يفعّلها الخادم.
 *
 * حارس CSRF: النقاط المكلفة تشترط الترويسة X-Rasad-Client. وجودها وحده هو
 * المقصود — ترويسة غير بسيطة تُلزم المتصفح بطلب preflight يرفضه الخادم لأي
 * أصل خارج CORS_ORIGINS، فلا تستطيع صفحة خارجية إطلاق الجامعين على الجهاز.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api';
const API_KEY = import.meta.env.VITE_API_KEY || '';
const CLIENT_HEADER = 'X-Rasad-Client';

/** خطأ يحمل حالة HTTP و Retry-After كي تعرض الواجهة رسالة مفيدة بدل "فشل". */
export class ApiError extends Error {
  constructor(message, { status, retryAfter, detail } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.retryAfter = retryAfter;
    this.detail = detail;
  }
}

const resolveBase = () =>
  (API_BASE.startsWith('http') ? API_BASE : `${window.location.origin}${API_BASE}`);

const authHeaders = () => (API_KEY ? { 'X-API-Key': API_KEY } : undefined);

/** ترويسات النقاط المكلفة: حارس CSRF + المفتاح إن وُجد. */
const mutationHeaders = () => ({ [CLIENT_HEADER]: '1', ...authHeaders() });

async function toApiError(response) {
  const retryAfterRaw = response.headers?.get?.('Retry-After');
  const retryAfter = retryAfterRaw ? Number(retryAfterRaw) : undefined;

  let detail;
  try {
    const body = await response.json();
    detail = body?.detail;
  } catch { /* الجسم ليس JSON — نكتفي بالحالة */ }

  return new ApiError(detail || `API Error: ${response.status}`, {
    status: response.status,
    retryAfter: Number.isFinite(retryAfter) ? retryAfter : undefined,
    detail,
  });
}

export async function fetchAPI(endpoint, params = {}) {
  const url = new URL(`${resolveBase()}${endpoint}`);
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '') {
      url.searchParams.set(key, val);
    }
  });

  const response = await fetch(url, { headers: authHeaders() });
  if (!response.ok) throw await toApiError(response);
  return response.json();
}

export async function postAPI(endpoint) {
  const response = await fetch(`${resolveBase()}${endpoint}`, {
    method: 'POST',
    headers: mutationHeaders(),
  });
  if (!response.ok) throw await toApiError(response);
  return response.json();
}

// Events
export const getEvents = (params) => fetchAPI('/events/', params);
export const getMapEvents = (hours = 24) => fetchAPI('/events/map', { hours });
export const getStats = (hours = 24) => fetchAPI('/events/stats', { hours });

// Flights
export const getLiveFlights = () => fetchAPI('/flights/live');

// Refresh (محمي بمفتاح على الخادم عند تفعيله)
export const refreshSources = () => postAPI('/refresh');

// Iran OSINT
export const getIranStrikes = (params = {}) => fetchAPI('/iran/strikes', params);
export const getIranLeaders = (hours = 72) => fetchAPI('/iran/leaders', { hours });
export const getIranStats = (hours = 72) => fetchAPI('/iran/stats', { hours });

// Nuclear facilities ☢️
export const getNuclearFacilities = (params = {}) => fetchAPI('/nuclear/facilities', params);

// Country Intelligence Index 📊 (v1.3)
export const getCountryIndex = (params = {}) => fetchAPI('/events/country-index', params);

// Infrastructure (military bases + pipelines) 🗺️ (v1.3)
export const getMilitaryBases = (params = {}) => fetchAPI('/infrastructure/bases', params);
export const getPipelines = (params = {}) => fetchAPI('/infrastructure/pipelines', params);
