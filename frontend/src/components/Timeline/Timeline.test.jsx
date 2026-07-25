import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '../../i18n';
import Timeline from './Timeline';

const now = Date.now();
const events = [
  { id: 1, title: 'Recent strike', category: 'military', severity: 'critical', country_code: 'IL', source: 'rss', event_date: new Date(now - 3600e3).toISOString() },
  { id: 2, title: 'Older talks', category: 'diplomatic', severity: 'medium', country_code: 'IR', source: 'gdelt', event_date: new Date(now - 30 * 3600e3).toISOString() },
];

describe('<Timeline>', () => {
  it('renders every event it is given (the window is owned by App)', () => {
    // انحدار: كان الخط الزمني يفلتر محلياً بنافذة قد تتجاوز البيانات المجلوبة،
    // فيعرض أزرار 48س بلا أي أثر. الآن يعرض ما يصله ويطلب توسيع النافذة للأعلى.
    render(<Timeline events={events} hours={48} />);
    expect(screen.getByText('Recent strike')).toBeInTheDocument();
    expect(screen.getByText('Older talks')).toBeInTheDocument();
  });

  it('asks the parent to widen the window when a period button is pressed', () => {
    const onHoursChange = vi.fn();
    render(<Timeline events={events} hours={24} onHoursChange={onHoursChange} />);
    fireEvent.click(screen.getByText('48h'));
    expect(onHoursChange).toHaveBeenCalledWith(48);
  });

  it('marks the active window with aria-pressed', () => {
    render(<Timeline events={events} hours={24} />);
    expect(screen.getByText('24h')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('48h')).toHaveAttribute('aria-pressed', 'false');
  });

  it('filters by category and can toggle the filter off', () => {
    render(<Timeline events={events} hours={48} />);
    const militaryBtn = screen.getByLabelText(/Military|عسكري/);

    fireEvent.click(militaryBtn);
    expect(screen.getByText('Recent strike')).toBeInTheDocument();
    expect(screen.queryByText('Older talks')).not.toBeInTheDocument();

    fireEvent.click(militaryBtn);
    expect(screen.getByText('Older talks')).toBeInTheDocument();
  });

  it('shows the empty state with no events', () => {
    render(<Timeline events={[]} hours={24} />);
    expect(screen.getByText(/No events|لا توجد أحداث/)).toBeInTheDocument();
  });

  it('is operable from the keyboard', () => {
    const onSelectEvent = vi.fn();
    render(<Timeline events={events} hours={48} onSelectEvent={onSelectEvent} />);
    const row = screen.getAllByRole('button').find(el => el.textContent.includes('Recent strike'));
    fireEvent.keyDown(row, { key: 'Enter' });
    expect(onSelectEvent).toHaveBeenCalledWith(events[0]);
  });

  it('ignores events with an unparseable date instead of crashing', () => {
    render(<Timeline events={[{ id: 9, title: 'Broken', event_date: 'nope', category: 'general', severity: 'low' }]} hours={24} />);
    expect(screen.getByText(/No events|لا توجد أحداث/)).toBeInTheDocument();
  });
});
