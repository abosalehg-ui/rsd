import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchAPI, postAPI, getCountryIndex, getMilitaryBases, ApiError } from './api';

const okResponse = () => ({
  ok: true,
  status: 200,
  headers: new Headers(),
  json: async () => ({ ok: true }),
});

describe('fetchAPI', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() => Promise.resolve(okResponse()));
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

  it('throws an ApiError carrying the status on non-2xx', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({
      ok: false,
      status: 500,
      headers: new Headers(),
      json: async () => { throw new Error('not json'); },
    }));
    await expect(fetchAPI('/x')).rejects.toBeInstanceOf(ApiError);
    await expect(fetchAPI('/x')).rejects.toMatchObject({ status: 500 });
  });

  it('surfaces the server detail message when present', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({
      ok: false,
      status: 401,
      headers: new Headers(),
      json: async () => ({ detail: 'مفتاح API غير صالح' }),
    }));
    await expect(fetchAPI('/x')).rejects.toThrow('مفتاح API غير صالح');
  });
});

describe('postAPI rate limiting', () => {
  it('parses Retry-After from a 429 so the UI can show a countdown', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({
      ok: false,
      status: 429,
      headers: new Headers({ 'Retry-After': '87' }),
      json: async () => ({ detail: 'throttled' }),
    }));

    await expect(postAPI('/refresh')).rejects.toMatchObject({
      status: 429,
      retryAfter: 87,
    });
  });

  it('leaves retryAfter undefined when the header is absent', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({
      ok: false,
      status: 429,
      headers: new Headers(),
      json: async () => ({}),
    }));
    await expect(postAPI('/refresh')).rejects.toMatchObject({ retryAfter: undefined });
  });

  it('sends POST for refresh', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve(okResponse()));
    await postAPI('/refresh');
    expect(globalThis.fetch.mock.calls[0][1].method).toBe('POST');
  });
});

describe('helper endpoints', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() => Promise.resolve(okResponse()));
  });

  it('getCountryIndex hits /events/country-index', async () => {
    await getCountryIndex({ hours: 24 });
    expect(globalThis.fetch.mock.calls[0][0].toString()).toContain('/events/country-index');
  });

  it('getMilitaryBases hits /infrastructure/bases', async () => {
    await getMilitaryBases();
    expect(globalThis.fetch.mock.calls[0][0].toString()).toContain('/infrastructure/bases');
  });

  it('omits the API key header when none is configured', async () => {
    await getMilitaryBases();
    expect(globalThis.fetch.mock.calls[0][1].headers).toBeUndefined();
  });
});
