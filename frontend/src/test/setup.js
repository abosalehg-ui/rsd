import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// localStorage stub لـ jsdom (يدعمه أصلاً لكن نتأكّد)
if (!globalThis.localStorage) {
  let store = {};
  globalThis.localStorage = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
    clear: () => { store = {}; },
    key: (i) => Object.keys(store)[i] ?? null,
    get length() { return Object.keys(store).length; },
  };
}

// matchMedia stub (Leaflet/recharts قد تستخدمه)
if (!globalThis.matchMedia) {
  globalThis.matchMedia = () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  });
}

// fetch stub بسيط — كل اختبار يعيد تعريفه إن لزم
globalThis.fetch = vi.fn(() => Promise.resolve({
  ok: true,
  status: 200,
  json: async () => ({}),
  text: async () => '',
}));

// ResizeObserver stub (Globe.jsx يستخدمه)
class ROStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = globalThis.ResizeObserver || ROStub;
