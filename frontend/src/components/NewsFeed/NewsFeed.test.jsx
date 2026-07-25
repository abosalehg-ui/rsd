import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '../../i18n';
import NewsFeed from './NewsFeed';

const baseFilters = {
  category: '', severity: '', country_code: '', source: '', search: '', hours: 24,
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
    expect(screen.getByText('2')).toBeInTheDocument();
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

  it('renders a safe source link and drops a javascript: URL', () => {
    render(<NewsFeed events={sampleEvents} filters={baseFilters} />);

    fireEvent.click(screen.getByText('Strike on a depot'));
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', 'https://example.com/a');

    fireEvent.click(screen.getByText('Talks resume'));
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
