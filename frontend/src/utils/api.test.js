import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchAPI, getCountryIndex, getMilitaryBases } from './api';

describe('fetchAPI', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() => Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    }));
  });

  it('builds URL with query params', async () => {
    await fetchAPI('/events/country-index', { hours: 72, top: 10 });
    const call = globalThis.fetch.mock.calls[0][0];
    expect(call.toString()).toContain('/api/events/country-index');
    expect(call.searchParams.get('hours')).toBe('72');
    expect(call.searchParams.get('top')).toBe('10');
  });

  it('drops null/undefined/empty params', async () => {
    await fetchAPI('/x', { a: 1, b: null, c: undefined, d: '' });
    const url = globalThis.fetch.mock.calls[0][0];
    expect(url.searchParams.get('a')).toBe('1');
    expect(url.searchParams.has('b')).toBe(false);
    expect(url.searchParams.has('c')).toBe(false);
    expect(url.searchParams.has('d')).toBe(false);
  });

  it('throws on non-2xx', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({ ok: false, status: 500 }));
    await expect(fetchAPI('/x')).rejects.toThrow(/500/);
  });
});

describe('helper endpoints', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() => Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    }));
  });

  it('getCountryIndex hits /events/country-index', async () => {
    await getCountryIndex({ hours: 24 });
    const url = globalThis.fetch.mock.calls[0][0].toString();
    expect(url).toContain('/events/country-index');
  });

  it('getMilitaryBases hits /infrastructure/bases', async () => {
    await getMilitaryBases();
    const url = globalThis.fetch.mock.calls[0][0].toString();
    expect(url).toContain('/infrastructure/bases');
  });
});
