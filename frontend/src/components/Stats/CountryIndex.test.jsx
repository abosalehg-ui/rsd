import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '../../i18n';  // يهيّئ i18next
import CountryIndex from './CountryIndex';

const sample = {
  total_countries: 2,
  period_hours: 72,
  max_raw_score: 30,
  ranking: [
    {
      country_code: 'IL',
      country_name: 'Israel',
      score: 100.0,
      total: 5,
      by_severity: { critical: 2, high: 2, medium: 1, low: 0 },
      by_category: { military: 4, nuclear: 1 },
      by_confidence: { HIGH: 3, MEDIUM: 1, LOW: 1, NONE: 0 },
    },
    {
      country_code: 'IR',
      country_name: 'Iran',
      score: 55.5,
      total: 3,
      by_severity: { critical: 0, high: 1, medium: 2, low: 0 },
      by_category: { diplomatic: 2, military: 1 },
      by_confidence: { HIGH: 1, MEDIUM: 1, LOW: 1, NONE: 0 },
    },
  ],
};

describe('<CountryIndex>', () => {
  it('renders empty state when no data', () => {
    render(<CountryIndex data={null} />);
    // عنوان المؤشر يظهر — سواء بالعربية أو الإنجليزية حسب اللغة المُكتشفة
    expect(screen.getByText(/Country Intelligence Index|مؤشر استخبارات الدول/)).toBeInTheDocument();
    expect(screen.getByText(/No data|لا توجد بيانات/)).toBeInTheDocument();
  });

  it('renders ranking with scores', () => {
    render(<CountryIndex data={sample} />);
    expect(screen.getByText('Israel')).toBeInTheDocument();
    expect(screen.getByText('Iran')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('55.5')).toBeInTheDocument();
  });

  it('respects the order (highest first)', () => {
    const { container } = render(<CountryIndex data={sample} />);
    const ranks = container.querySelectorAll('span.w-4');
    expect(ranks[0].textContent).toBe('#1');
    expect(ranks[1].textContent).toBe('#2');
  });

  it('shows severity badges when present', () => {
    render(<CountryIndex data={sample} />);
    // 2 critical → نص "2❗"
    expect(screen.getByText(/2❗/)).toBeInTheDocument();
  });
});
