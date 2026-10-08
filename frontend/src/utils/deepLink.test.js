import { describe, it, expect, vi, afterEach } from 'vitest';
import { copyText, eventLink, readEventId, writeEventId } from './deepLink';

describe('event deep link', () => {
  afterEach(() => window.history.replaceState(null, '', '/'));

  it('reads a positive integer id only', () => {
    expect(readEventId('?event=42')).toBe(42);
    expect(readEventId('?category=military&event=7')).toBe(7);
    expect(readEventId('?event=abc')).toBeNull();
    expect(readEventId('?event=-3')).toBeNull();
    expect(readEventId('?event=0')).toBeNull();
    expect(readEventId('?event=1e3')).toBeNull();
    expect(readEventId('')).toBeNull();
  });

  it('builds a clean shareable link without the current view filters', () => {
    window.history.replaceState(null, '', '/?category=military&hours=72');
    expect(eventLink(42)).toBe(`${window.location.origin}/?event=42`);
  });

  it('writes and clears the id while keeping other params', () => {
    window.history.replaceState(null, '', '/?category=military');
    writeEventId(42);
    expect(window.location.search).toBe('?category=military&event=42');
    writeEventId(null);
    expect(window.location.search).toBe('?category=military');
    writeEventId('fac:ir-bushehr-1');           // ليس حدثًا: لا يُكتب
    expect(window.location.search).toBe('?category=military');
  });

  it('copies with the Clipboard API', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    expect(await copyText('x')).toBe(true);
    expect(writeText).toHaveBeenCalledWith('x');
  });

  it('falls back to execCommand when the Clipboard API is missing or blocked', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) }, configurable: true,
    });
    document.execCommand = vi.fn(() => true);
    expect(await copyText('y')).toBe(true);
    expect(document.execCommand).toHaveBeenCalledWith('copy');
    document.execCommand = vi.fn(() => false);
    expect(await copyText('z')).toBe(false);
  });
});
