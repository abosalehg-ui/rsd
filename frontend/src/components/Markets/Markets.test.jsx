import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import i18n from '../../i18n';
import MarketTicker from './MarketTicker';
import MarketsPanel from './MarketsPanel';
import SyncChart, { linePath } from './SyncChart';
import Header from '../Layout/Header';
import * as api from '../../utils/api';

const quote = (code, value, pct, extra = {}) => ({
  code,
  unit: code === 'VIXCLS' ? 'index' : code === 'DHHNGSP' ? 'USD/MMBtu' : 'USD/bbl',
  value,
  observed_at: value == null ? null : '2026-10-05',
  prev_value: value == null ? null : value - 1,
  prev_observed_at: value == null ? null : '2026-10-02',
  change: value == null ? null : 1,
  change_pct: pct,
  fetched_at: value == null ? null : '2026-10-07T06:00:00+00:00',
  ...extra,
});

const latest = {
  enabled: true,
  has_data: true,
  as_of: '2026-10-05',
  fetched_at: '2026-10-07T06:00:00+00:00',
  frequency: 'daily',
  source: { name: 'FRED' },
  series: [
    quote('DCOILBRENTEU', 84, 5),
    quote('DCOILWTICO', 80.5, -1.2),
    quote('DHHNGSP', 2.95, 0),
    quote('VIXCLS', 18.5, null),
  ],
};

const empty = {
  ...latest, enabled: false, has_data: false, as_of: null, fetched_at: null,
  series: latest.series.map(s => quote(s.code, null, null)),
};

const day = (i, extra = {}) => ({
  date: `2026-09-${String(10 + i).padStart(2, '0')}`, nuclear: 20 + i, ksa: 40 - i, brent: i % 7 === 5 ? null : 80 + i, partial: false, ...extra,
});
const sync = {
  days: 30,
  coverage_start: '2026-09-10',
  brent_as_of: '2026-10-05',
  points: Array.from({ length: 12 }, (_, i) => day(i)),
  correlation: { nuclear_brent: { r: 0.83, n: 11 }, ksa_brent: { r: null, n: 4 }, min_days: 10 },
};

describe('<MarketTicker>', () => {
  beforeEach(async () => { await i18n.changeLanguage('en'); });

  it('renders nothing before the first response', () => {
    const { container } = render(<MarketTicker markets={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows each value with a colored, signed change and the data date', () => {
    render(<MarketTicker markets={latest} />);
    const brent = within(screen.getByTestId('ticker-DCOILBRENTEU'));
    expect(brent.getByText('Brent')).toBeInTheDocument();
    expect(brent.getByText('84.00')).toBeInTheDocument();
    const up = brent.getByText('+5.00%');
    expect(up).toHaveClass('text-emerald-300');
    expect(brent.getByText('up')).toHaveClass('sr-only');      // الاتجاه ليس لونًا وحده

    const wti = within(screen.getByTestId('ticker-DCOILWTICO'));
    expect(wti.getByText('−1.20%')).toHaveClass('text-red-300');
    expect(within(screen.getByTestId('ticker-DHHNGSP')).getByText('0.00%')).toHaveClass('text-slate-400');
    // VIX بلا قيمة سابقة: لا شارة تغيّر
    expect(within(screen.getByTestId('ticker-VIXCLS')).queryByText(/%/)).not.toBeInTheDocument();

    // تاريخ البيانات ظاهر، ولا ادّعاء «لحظي»
    const asOf = screen.getByText('as of 5 Oct');
    expect(asOf).toHaveAttribute('title', expect.stringMatching(/not live/));
  });

  it('shows the enable hint when there is no key and no stored data', () => {
    render(<MarketTicker markets={empty} />);
    expect(screen.getByText('add FRED_API_KEY to enable')).toBeInTheDocument();
    expect(screen.queryByTestId('ticker-DCOILBRENTEU')).not.toBeInTheDocument();
  });

  it('keeps the last known values when the key was removed, with the hint', () => {
    render(<MarketTicker markets={{ ...latest, enabled: false }} />);
    expect(screen.getByText('84.00')).toBeInTheDocument();
    expect(screen.getByText(/add FRED_API_KEY to enable/)).toBeInTheDocument();
  });

  it('says it is waiting for the first fetch when the key is set', () => {
    render(<MarketTicker markets={{ ...empty, enabled: true }} />);
    expect(screen.getByText(/waiting for the first daily fetch/)).toBeInTheDocument();
  });

  it('opens the markets panel on click', () => {
    const onOpen = vi.fn();
    render(<MarketTicker markets={latest} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole('button', { name: /Energy & markets/ }));
    expect(onOpen).toHaveBeenCalled();
  });

  it('renders in Arabic', async () => {
    await i18n.changeLanguage('ar');
    render(<MarketTicker markets={latest} />);
    expect(screen.getByText('برنت')).toBeInTheDocument();
    expect(screen.getByText('84.00').closest('[dir="ltr"]')).not.toBeNull();
  });

  it('is part of the header', () => {
    render(<Header isConnected markets={empty} />);
    expect(screen.getByRole('banner')).toHaveTextContent('add FRED_API_KEY to enable');
  });
});

describe('<MarketsPanel>', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
    vi.spyOn(api, 'getMarketSeries').mockResolvedValue({
      days: 90,
      series: {
        DCOILBRENTEU: [{ date: '2026-10-01', value: 79 }, { date: '2026-10-02', value: 83 }, { date: '2026-10-05', value: 84 }],
        DCOILWTICO: [], DHHNGSP: [], VIXCLS: [],
      },
    });
  });

  it('explains how to enable FRED when there is no key', async () => {
    vi.spyOn(api, 'getMarketsCorrelation').mockResolvedValue({ ...sync, points: [] });
    render(<MarketsPanel latest={empty} />);
    const hint = screen.getByRole('note', { name: 'Add FRED_API_KEY to enable' });
    expect(hint).toHaveTextContent('FRED_API_KEY=');
    expect(hint).toHaveTextContent(/fred\.stlouisfed\.org/);
    expect(screen.queryByRole('list', { name: 'Latest values' })).not.toBeInTheDocument();
    // التزامن يبقى بعبارته حتى بلا مفتاح
    expect(screen.getByText('A synchronization reading — not a forecast and not financial advice.')).toBeInTheDocument();
    await waitFor(() => expect(api.getMarketsCorrelation).toHaveBeenCalledWith(30));
  });

  it('shows the cards with their trading dates and a clear not-live note', async () => {
    vi.spyOn(api, 'getMarketsCorrelation').mockResolvedValue(sync);
    render(<MarketsPanel latest={latest} />);
    expect(screen.getByText('Data date: 5 Oct 2026')).toBeInTheDocument();
    expect(screen.getByText(/this is not live data/)).toBeInTheDocument();
    const cards = within(screen.getByRole('list', { name: 'Latest values' }));
    const brent = within(cards.getByRole('listitem', { name: 'Brent crude' }));
    expect(brent.getByText('84.00')).toBeInTheDocument();
    expect(brent.getByText('USD / barrel')).toBeInTheDocument();
    expect(brent.getByText(/Trading day 5 Oct 2026/)).toBeInTheDocument();
    expect(await brent.findByRole('img', { name: 'Brent crude over 90 days: low 79.00, high 84.00' })).toBeInTheDocument();
  });

  it('draws the sync chart with its label, correlation and coverage', async () => {
    vi.spyOn(api, 'getMarketsCorrelation').mockResolvedValue(sync);
    render(<MarketsPanel latest={latest} />);
    expect(await screen.findByRole('img', { name: /over 12 days on one time axis/ })).toBeInTheDocument();
    expect(screen.getByText('r = 0.83 over 11 shared days')).toBeInTheDocument();
    expect(screen.getByText('not enough shared days (4 of 10)')).toBeInTheDocument();
    expect(screen.getByText(/Index data starts 10 Sept? 2026/)).toBeInTheDocument();
  });

  it('refetches the sync chart when the period changes', async () => {
    const spy = vi.spyOn(api, 'getMarketsCorrelation').mockResolvedValue(sync);
    render(<MarketsPanel latest={latest} />);
    fireEvent.change(screen.getByLabelText('Period'), { target: { value: '90' } });
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith(90));
  });

  it('shows the sync error and the latest-values error', async () => {
    vi.spyOn(api, 'getMarketsCorrelation').mockRejectedValue(new Error('down'));
    render(<MarketsPanel latest={latest} />);
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load the synchronization chart.");
  });

  it('reports a failed first load', () => {
    vi.spyOn(api, 'getMarketsCorrelation').mockResolvedValue(sync);
    render(<MarketsPanel latest={null} latestError="down" />);
    expect(screen.getByRole('alert')).toHaveTextContent("Couldn't load market data.");
  });

  it('carries the Arabic disclaimer verbatim', async () => {
    await i18n.changeLanguage('ar');
    vi.spyOn(api, 'getMarketsCorrelation').mockResolvedValue(sync);
    render(<MarketsPanel latest={latest} />);
    expect(screen.getByText('قراءة تزامن وليست تنبؤًا ولا نصيحة مالية')).toBeInTheDocument();
  });
});

describe('<SyncChart>', () => {
  beforeEach(async () => { await i18n.changeLanguage('en'); });

  it('breaks index lines at gaps but connects Brent across non-trading days', () => {
    const x = (i) => i;
    const y = (v) => v;
    expect(linePath([1, null, 3, 4], x, y)).toBe('M0.0,1.0M2.0,3.0L3.0,4.0');
    expect(linePath([1, null, 3], x, y, { connect: true })).toBe('M0.0,1.0L2.0,3.0');
    expect(linePath([null, null], x, y)).toBe('');
  });

  it('shows every series value for the hovered or focused day', () => {
    render(<SyncChart points={sync.points} />);
    const chart = screen.getByRole('img');
    chart.getBoundingClientRect = () => ({ left: 0, width: 360, top: 0, height: 208 });
    fireEvent.pointerMove(chart, { clientX: 26 });   // أول يوم
    const tip = screen.getByRole('status');
    expect(tip).toHaveTextContent(/10 Sept? 2026/);
    expect(tip).toHaveTextContent('20.0');
    expect(tip).toHaveTextContent('40.0');
    expect(tip).toHaveTextContent('$80.00');
    fireEvent.keyDown(chart, { key: 'ArrowRight' });
    expect(screen.getByRole('status')).toHaveTextContent('21.0');
    fireEvent.pointerLeave(chart);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('marks non-trading days and days without index coverage', () => {
    const points = [day(0, { nuclear: null, ksa: null }), day(5), day(6, { partial: true })];
    render(<SyncChart points={points} />);
    const chart = screen.getByRole('img');
    chart.getBoundingClientRect = () => ({ left: 0, width: 360, top: 0, height: 208 });
    fireEvent.pointerMove(chart, { clientX: 26 });
    expect(screen.getByRole('status')).toHaveTextContent('no data');
    fireEvent.pointerMove(chart, { clientX: 180 });
    expect(screen.getByRole('status')).toHaveTextContent('no trading');
    fireEvent.pointerMove(chart, { clientX: 330 });
    expect(screen.getByRole('status')).toHaveTextContent('today (partial)');
  });

  it('offers a data table', () => {
    render(<SyncChart points={sync.points} />);
    const table = screen.getByRole('table', { name: 'Daily values of the two indices and Brent' });
    expect(within(table).getAllByRole('row')).toHaveLength(sync.points.length + 1);
  });

  it('says when there is no Brent data', () => {
    render(<SyncChart points={[day(0, { brent: null }), day(1, { brent: null })]} />);
    expect(screen.getByText('No Brent values in this period')).toBeInTheDocument();
    expect(screen.queryByTestId('sync-line-brent')).not.toBeInTheDocument();
  });

  it('renders nothing without points', () => {
    const { container } = render(<SyncChart points={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
