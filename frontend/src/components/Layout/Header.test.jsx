import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import i18n from '../../i18n';
import Header, { formatCountdown, nextSyncAt } from './Header';

describe('formatCountdown', () => {
  it.each([
    [0, '0:00'], [9, '0:09'], [75, '1:15'], [3600, '1:00:00'], [3725, '1:02:05'], [-5, '0:00'],
  ])('%s s → %s', (secs, out) => {
    expect(formatCountdown(secs)).toBe(out);
  });
});

describe('nextSyncAt', () => {
  it('anchors the relative delay to the fetch time (not the server clock)', () => {
    const fetched = new Date('2026-10-08T12:00:00Z');
    expect(nextSyncAt({ next_sync_in_seconds: 90 }, fetched).toISOString()).toBe('2026-10-08T12:01:30.000Z');
    expect(nextSyncAt({ next_sync_in_seconds: null }, fetched)).toBeNull();
    expect(nextSyncAt(null, fetched)).toBeNull();
  });
});

describe('<Header> schedule', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-08T12:00:00Z'));
  });
  afterEach(() => vi.useRealTimers());

  it('shows the last analysis time and counts down to the next sync', () => {
    render(<Header
      isConnected
      schedule={{ last_analysis: '2026-10-08T11:55:00Z', next_sync_in_seconds: 125 }}
      scheduleFetchedAt={new Date('2026-10-08T12:00:00Z')}
    />);
    expect(screen.getByText(/Last analysis/)).toBeInTheDocument();
    expect(screen.getByText('Next sync in 2:05')).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(5000); });
    expect(screen.getByText('Next sync in 2:00')).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(200 * 1000); });
    expect(screen.getByText('Next sync due now')).toBeInTheDocument();
  });

  it('shows nothing when the scheduler is not reporting', () => {
    render(<Header isConnected schedule={{ last_analysis: null, next_sync_in_seconds: null }} />);
    expect(screen.queryByText(/Next sync/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Last analysis/)).not.toBeInTheDocument();
  });
});
