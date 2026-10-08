import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '../../i18n';
import i18n from '../../i18n';
import NewsFeed, { categoryCount } from './NewsFeed';

const baseFilters = {
  category: '', severity: '', country_code: '', source: '', search: '', sector: '', hours: 24,
};

const sampleEvents = [
  {
    id: 1, title: 'Strike on a depot', description: 'details here',
    category: 'military', severity: 'critical', country_code: 'IL',
    source: 'rss', url: 'https://example.com/a', event_date: new Date().toISOString(),
  },
  {
    id: 2, title: 'Talks resume', description: '',
    category: 'diplomatic', severity: 'medium', country_code: 'IR',
    source: 'gdelt', url: 'javascript:alert(1)', event_date: new Date().toISOString(),
  },
];

describe('<NewsFeed>', () => {
  it('renders the events with their count', () => {
    render(<NewsFeed events={sampleEvents} filters={baseFilters} />);
    expect(screen.getByText('Strike on a depot')).toBeInTheDocument();
    expect(screen.getByText('Talks resume')).toBeInTheDocument();
    // العدّاد في رأس اللوحة (رؤوس المجموعات الزمنية تحمل أعدادها أيضًا)
    const heading = screen.getByText(/^(Events|الأحداث)$/).parentElement;
    expect(heading).toHaveTextContent('2');
  });

  it('groups stories under time headings', () => {
    render(<NewsFeed events={sampleEvents} filters={baseFilters} />);
    expect(screen.getByRole('region', { name: /Last hour|آخر ساعة/ })).toBeInTheDocument();
  });

  it('shows an error state instead of "no events" when loading failed', () => {
    render(<NewsFeed events={[]} error="network down" filters={baseFilters} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText(/No events|لا توجد أحداث/)).not.toBeInTheDocument();
  });

  it('shows the empty state when there is no error', () => {
    render(<NewsFeed events={[]} filters={baseFilters} />);
    expect(screen.getByText(/No events|لا توجد أحداث/)).toBeInTheDocument();
  });

  it('exposes a search box wired to the filters', () => {
    render(<NewsFeed events={sampleEvents} filters={baseFilters} />);
    expect(screen.getByRole('searchbox')).toBeInTheDocument();
  });

  it('debounces search input before calling onFilterChange', async () => {
    vi.useFakeTimers();
    const onFilterChange = vi.fn();
    render(<NewsFeed events={sampleEvents} filters={baseFilters} onFilterChange={onFilterChange} />);

    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'gaza' } });
    expect(onFilterChange).not.toHaveBeenCalled();     // لم يمرّ زمن السكون بعد

    await act(async () => { vi.advanceTimersByTime(500); });
    expect(onFilterChange).toHaveBeenCalledWith('search', 'gaza');
    vi.useRealTimers();
  });

  it('caps the search length to what the backend accepts', () => {
    render(<NewsFeed events={[]} filters={baseFilters} />);
    expect(screen.getByRole('searchbox')).toHaveAttribute('maxlength', '100');
  });

  it('opens the story instead of expanding inline (links live in the details drawer)', () => {
    const onSelectEvent = vi.fn();
    render(<NewsFeed events={sampleEvents} filters={baseFilters} onSelectEvent={onSelectEvent} />);
    fireEvent.click(screen.getByText('Strike on a depot'));
    expect(onSelectEvent).toHaveBeenCalledWith(sampleEvents[0]);
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('is operable from the keyboard', () => {
    const onSelectEvent = vi.fn();
    render(<NewsFeed events={sampleEvents} filters={baseFilters} onSelectEvent={onSelectEvent} />);
    const row = screen.getAllByRole('button').find(el => el.textContent.includes('Strike on a depot'));
    fireEvent.keyDown(row, { key: 'Enter' });
    expect(onSelectEvent).toHaveBeenCalledWith(sampleEvents[0]);
  });
});

describe('<NewsFeed> filter panel', () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.useRealTimers());

  it('reveals country / source / period selects once opened', () => {
    render(<NewsFeed events={sampleEvents} filters={baseFilters} />);
    fireEvent.click(screen.getByLabelText(/Toggle filters|إظهار\/إخفاء الفلاتر/));
    expect(screen.getAllByRole('combobox')).toHaveLength(3);
  });

  it('pushes the selected country to the filters', () => {
    const onFilterChange = vi.fn();
    render(<NewsFeed events={sampleEvents} filters={baseFilters} onFilterChange={onFilterChange} />);
    fireEvent.click(screen.getByLabelText(/Toggle filters|إظهار\/إخفاء الفلاتر/));
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'IR' } });
    expect(onFilterChange).toHaveBeenCalledWith('country_code', 'IR');
  });

  it('pushes the period as a number, not a string', () => {
    const onFilterChange = vi.fn();
    render(<NewsFeed events={sampleEvents} filters={baseFilters} onFilterChange={onFilterChange} />);
    fireEvent.click(screen.getByLabelText(/Toggle filters|إظهار\/إخفاء الفلاتر/));
    fireEvent.change(screen.getAllByRole('combobox')[2], { target: { value: '72' } });
    expect(onFilterChange).toHaveBeenCalledWith('hours', 72);
  });
});

describe('<NewsFeed> counts and sectors', () => {
  beforeEach(async () => { await i18n.changeLanguage('en'); });

  it('shows the event count next to each category', () => {
    render(<NewsFeed
      events={sampleEvents}
      filters={baseFilters}
      categoryCounts={{ military: 38, diplomatic: 12, nuclear: 3, radiological: 2 }}
    />);
    const group = screen.getByRole('group', { name: 'By category' });
    expect(group).toHaveTextContent('Military38');
    expect(group).toHaveTextContent('Diplomatic12');
    // «نووي» في الخادم يشمل الإشعاعي
    expect(group).toHaveTextContent('Nuclear5');
    expect(group).toHaveTextContent('All55');
  });

  it('hides counts until stats arrive instead of showing a misleading 0', () => {
    render(<NewsFeed events={sampleEvents} filters={baseFilters} />);
    expect(screen.getByRole('group', { name: 'By category' })).not.toHaveTextContent(/\d/);
  });

  it('filters by Kingdom-impact sector with counts', () => {
    const onFilterChange = vi.fn();
    render(<NewsFeed
      events={sampleEvents}
      filters={baseFilters}
      onFilterChange={onFilterChange}
      sectorCounts={{ energy: 4, security: 9 }}
    />);
    fireEvent.click(screen.getByLabelText('Toggle filters'));
    const sectors = screen.getByRole('group', { name: 'By sector (Kingdom impact)' });
    expect(sectors).toHaveTextContent('Energy4');
    expect(sectors).toHaveTextContent('Health0');
    fireEvent.click(screen.getByRole('button', { name: /^Energy/ }));
    expect(onFilterChange).toHaveBeenCalledWith('sector', 'energy');
  });

  it('counts the active sector as a filter', () => {
    render(<NewsFeed events={sampleEvents} filters={{ ...baseFilters, sector: 'energy' }} />);
    expect(screen.getByLabelText('Toggle filters').textContent).toBe('1');
  });

  it('categoryCount merges radiological into nuclear', () => {
    expect(categoryCount(null, 'military')).toBeNull();
    expect(categoryCount({ nuclear: 1, radiological: 2 }, 'nuclear')).toBe(3);
    expect(categoryCount({}, 'economic')).toBe(0);
  });
});
