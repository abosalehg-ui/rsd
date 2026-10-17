import { describe, it, expect, beforeAll } from 'vitest';
import i18n from '../i18n';
import { refreshToast } from './refresh';

const t = (...args) => i18n.t(...args);
const ok = { status: 'ok', new_events: 3 };
const err = { status: 'error', message: 'x' };

describe('refreshToast', () => {
  beforeAll(async () => { await i18n.changeLanguage('en'); });

  it('reports success when every source collected', () => {
    expect(refreshToast({ sources: { gdelt: ok, rss: ok } }, t)).toEqual({ kind: 'ok', text: 'Sources refreshed' });
  });

  it('reports partial failure with counts', () => {
    expect(refreshToast({ sources: { gdelt: ok, rss: err, ucdp: err } }, t))
      .toEqual({ kind: 'error', text: 'Sources refreshed; 2 of 3 could not be collected' });
  });

  it('never says "refreshed" when every source failed', () => {
    const toast = refreshToast({ status: 'ok', sources: { gdelt: err, rss: err } }, t);
    expect(toast.kind).toBe('error');
    expect(toast.text).toBe('No source could be collected — the data shown has not changed');
  });

  it('treats a response without sources as success (older server)', () => {
    expect(refreshToast({ status: 'ok' }, t).kind).toBe('ok');
  });
});
