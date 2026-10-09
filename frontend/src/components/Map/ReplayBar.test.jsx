import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import i18n from '../../i18n';
import ReplayBar, { PLAY_INTERVAL_MS } from './ReplayBar';
import * as api from '../../utils/api';
import { HOUR_MS, replayStart } from '../../utils/replay';

const NOW = new Date('2026-10-08T15:40:00Z');
const START = replayStart(NOW, 48);
const ev = (id, hoursIn) => ({
  id, latitude: 24, longitude: 46, event_date: new Date(START.getTime() + hoursIn * HOUR_MS).toISOString(),
});
const EVENTS = [ev(1, 0.2), ev(2, 1.5), ev(3, 30.2), ev(4, 47.5)];

describe('<ReplayBar>', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
  });
  afterEach(() => vi.useRealTimers());

  it('stays live until the user interacts', () => {
    const spy = vi.spyOn(api, 'getMapEvents').mockResolvedValue(EVENTS);
    const onFrame = vi.fn();
    render(<ReplayBar onFrame={onFrame} now={NOW} />);
    expect(spy).not.toHaveBeenCalled();
    expect(onFrame).not.toHaveBeenCalled();
    expect(screen.getByRole('slider', { name: 'Hour shown' })).toHaveValue('47');
  });

  it('filters the existing map endpoint by event_date as the slider moves', async () => {
    const spy = vi.spyOn(api, 'getMapEvents').mockResolvedValue(EVENTS);
    const onFrame = vi.fn();
    render(<ReplayBar onFrame={onFrame} now={NOW} />);

    fireEvent.change(screen.getByRole('slider'), { target: { value: '0' } });
    expect(spy).toHaveBeenCalledWith(48, 1000);
    await waitFor(() => expect(onFrame).toHaveBeenLastCalledWith([EVENTS[0]]));
    expect(screen.getByText('1 event')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('slider'), { target: { value: '30' } });
    await waitFor(() => expect(onFrame).toHaveBeenLastCalledWith(EVENTS.slice(0, 3)));
  });

  it('plays hour by hour from the start and returns to live on close', async () => {
    vi.spyOn(api, 'getMapEvents').mockResolvedValue(EVENTS);
    const onFrame = vi.fn();
    render(<ReplayBar onFrame={onFrame} now={NOW} />);

    vi.useFakeTimers();
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Play' })); });
    expect(screen.getByRole('slider')).toHaveValue('0');
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument();

    await act(async () => { vi.advanceTimersByTime(PLAY_INTERVAL_MS * 2); });
    expect(screen.getByRole('slider')).toHaveValue('2');
    expect(onFrame).toHaveBeenLastCalledWith(EVENTS.slice(0, 2));

    // يتوقّف عند نهاية النافذة
    await act(async () => { vi.advanceTimersByTime(PLAY_INTERVAL_MS * 60); });
    expect(screen.getByRole('slider')).toHaveValue('47');
    expect(screen.getByRole('button', { name: 'Play' })).toBeInTheDocument();
    expect(onFrame).toHaveBeenLastCalledWith(EVENTS);
    vi.useRealTimers();

    fireEvent.click(screen.getByRole('button', { name: 'Close replay' }));
    expect(onFrame).toHaveBeenLastCalledWith(null);
  });

  it('switches to the 72-hour window', async () => {
    const spy = vi.spyOn(api, 'getMapEvents').mockResolvedValue(EVENTS);
    render(<ReplayBar onFrame={vi.fn()} now={NOW} />);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '3' } });
    fireEvent.change(screen.getByLabelText('Replay window'), { target: { value: '72' } });
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith(72, 1000));
    expect(screen.getByRole('slider')).toHaveAttribute('max', '71');
  });

  it('keeps the live map on a failed load and says why on every screen size', async () => {
    vi.spyOn(api, 'getMapEvents').mockRejectedValue(new Error('down'));
    const onFrame = vi.fn();
    render(<ReplayBar onFrame={onFrame} now={NOW} />);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '3' } });
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent("Couldn't load replay events.");
    expect(alert).toHaveTextContent('Load failed');                // النسخة المختصرة للجوال
    // لا إطار فارغ يمسح الخريطة: null يعيدها للبيانات الحيّة
    expect(onFrame).toHaveBeenCalledWith(null);
    expect(onFrame).not.toHaveBeenCalledWith([]);
    // سطر الحالة غير مخفي على الجوال
    expect(alert.closest('.hidden')).toBeNull();
  });

  it('retries a failed load on the next interaction', async () => {
    const spy = vi.spyOn(api, 'getMapEvents').mockRejectedValueOnce(new Error('down')).mockResolvedValue(EVENTS);
    const onFrame = vi.fn();
    render(<ReplayBar onFrame={onFrame} now={NOW} />);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '3' } });
    await screen.findByRole('alert');
    fireEvent.change(screen.getByRole('slider'), { target: { value: '0' } });
    await waitFor(() => expect(onFrame).toHaveBeenLastCalledWith([EVENTS[0]]));
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it('announces play start, pause and end only — not every frame', async () => {
    vi.spyOn(api, 'getMapEvents').mockResolvedValue(EVENTS);
    render(<ReplayBar onFrame={vi.fn()} now={NOW} />);
    const live = screen.getByRole('status');
    expect(live).toHaveAttribute('aria-live', 'polite');

    vi.useFakeTimers();
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Play' })); });
    expect(live).toHaveTextContent('Replay started');
    await act(async () => { vi.advanceTimersByTime(PLAY_INTERVAL_MS * 3); });
    expect(live).toHaveTextContent('Replay started');            // الإطارات لا تُعلَن
    expect(live.textContent).not.toMatch(/event/);
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Pause' })); });
    expect(live).toHaveTextContent('Replay paused');
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Play' })); });
    await act(async () => { vi.advanceTimersByTime(PLAY_INTERVAL_MS * 60); });
    expect(live).toHaveTextContent('Replay finished');
    vi.useRealTimers();
  });
});
