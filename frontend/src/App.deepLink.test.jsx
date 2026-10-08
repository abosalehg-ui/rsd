/**
 * رابط المشاركة `?event=ID` يفتح لوحة التفاصيل عند التحميل، والعنوان يتبع
 * الحدث المفتوح ثم يُنظَّف عند الإغلاق.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import i18n from './i18n';
import App from './App';
import * as api from './utils/api';

const story = {
  id: 7,
  title: 'Tanker attacked in the Red Sea',
  description: 'Shipping firms reroute vessels.',
  category: 'military',
  severity: 'high',
  source_name: 'SPA',
  url: 'https://example.com/a',
  event_date: new Date().toISOString(),
  ksa_impact: 40.5,
  impact_sectors: ['shipping_ports'],
  impact: {
    score: 40.5, severity: 'high', proximity_band: 'adjacent', mention: 'chokepoint', mentioned: ['red sea'],
    components: { severity: 0.75, proximity: 1, mention: 0.85, source_trust: 0.9 },
  },
  story_related: [],
  extra: {},
};

describe('App deep link', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
  });
  afterEach(() => window.history.replaceState(null, '', '/'));

  it('opens the linked event on load and clears the link on close', { timeout: 20000 }, async () => {
    window.history.replaceState(null, '', '/?event=7&category=military');
    const getEvent = vi.spyOn(api, 'getEvent').mockResolvedValue(story);
    render(<App />);

    // التطبيق كاملًا (Leaflet + عشرات الاستطلاعات) ثقيل حين تعمل الاختبارات بالتوازي
    expect(await screen.findByRole('dialog', { name: story.title }, { timeout: 8000 })).toBeInTheDocument();
    expect(getEvent).toHaveBeenCalledWith(7);
    expect(new URLSearchParams(window.location.search).get('event')).toBe('7');

    fireEvent.click(screen.getByRole('button', { name: 'Close details' }));
    await waitFor(() => expect(new URLSearchParams(window.location.search).get('event')).toBeNull(), { timeout: 8000 });
    // بقية الفلاتر باقية
    expect(new URLSearchParams(window.location.search).get('category')).toBe('military');
  });

  it('reports a link to an event that no longer exists', { timeout: 20000 }, async () => {
    window.history.replaceState(null, '', '/?event=99');
    vi.spyOn(api, 'getEvent').mockRejectedValue(new api.ApiError('gone', { status: 404 }));
    render(<App />);
    expect(await screen.findByText(/Couldn't open the linked event/, {}, { timeout: 8000 })).toBeInTheDocument();
  });

  it('does not fetch anything without a link', () => {
    const getEvent = vi.spyOn(api, 'getEvent');
    render(<App />);
    expect(getEvent).not.toHaveBeenCalled();
  });
});
