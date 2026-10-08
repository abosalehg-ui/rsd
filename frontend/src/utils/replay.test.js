import { describe, it, expect } from 'vitest';
import { HOUR_MS, eventsUntil, frameEnd, hourlyCounts, replayStart } from './replay';

const NOW = new Date('2026-10-08T15:40:00Z');
const at = (iso) => ({ id: iso, event_date: iso });

describe('replay helpers', () => {
  it('starts the window on a whole hour so frames align to the clock', () => {
    const start = replayStart(NOW, 48);
    expect(start.getUTCMinutes()).toBe(0);
    // آخر إطار ينتهي عند نهاية الساعة الجارية
    expect(frameEnd(start, 47).getTime()).toBe(Date.parse('2026-10-08T16:00:00Z'));
    expect(frameEnd(start, 0).getTime() - start.getTime()).toBe(HOUR_MS);
  });

  it('accumulates events hour by hour', () => {
    const start = replayStart(NOW, 48);
    const first = new Date(start.getTime() + 10 * 60 * 1000).toISOString();
    const third = new Date(start.getTime() + 2.5 * HOUR_MS).toISOString();
    const events = [at(first), at(third), at('not a date'), { id: 'x' }, at('2020-01-01T00:00:00Z')];
    expect(eventsUntil(events, start, 0).map(e => e.id)).toEqual([first]);
    expect(eventsUntil(events, start, 1).map(e => e.id)).toEqual([first]);
    expect(eventsUntil(events, start, 2).map(e => e.id)).toEqual([first, third]);
    expect(eventsUntil(events, start, 47)).toHaveLength(2);
    expect(eventsUntil(null, start, 3)).toEqual([]);
  });

  it('counts new events per hour', () => {
    const start = replayStart(NOW, 3);
    const counts = hourlyCounts([
      at(new Date(start.getTime() + 5 * 60 * 1000).toISOString()),
      at(new Date(start.getTime() + 20 * 60 * 1000).toISOString()),
      at(new Date(start.getTime() + 2.1 * HOUR_MS).toISOString()),
      at(new Date(start.getTime() + 9 * HOUR_MS).toISOString()),
    ], start, 3);
    expect(counts).toEqual([2, 0, 1]);
  });
});
