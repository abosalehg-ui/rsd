import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import i18n from '../../i18n';
import * as api from '../../utils/api';
import EventDrawer from '../Events/EventDrawer';
import ChainSection from './ChainSection';
import ChainsModal from './ChainsModal';

const evidence = (extra = {}) => ({
  shared: [
    { kind: 'country', key: 'IL', ar: 'إسرائيل', en: 'Israel' },
    { kind: 'country', key: 'IR', ar: 'إيران', en: 'Iran' },
  ],
  hours: 10,
  components: { template: 0.85, entity: 0.85, time: 1, match: 0.723, source_trust: 0.9 },
  cause_terms: ['strikes'],
  effect_terms: ['retaliatory strike*'],
  ...extra,
});

const link = (id, cause, effect, confidence, rule = 'strike_retaliation') => ({
  id, cause_id: cause, effect_id: effect, confidence, method: 'rule', rule_id: rule,
  relation_ar: 'ضربة ← رد انتقامي', relation_en: 'Strike → retaliation', evidence: evidence(),
});

const node = (id, title) => ({ id, title, url: `https://ex.test/${id}`, source_name: 'Wire' });

const chainBody = {
  event_id: 2,
  story_id: 2,
  causes: [{ ...link(1, 1, 2, 0.65), event: node(1, 'Israel strikes targets in Iran') }],
  effects: [{
    ...link(2, 2, 3, 0.46, 'gulf_attack_energy_shipping'),
    relation_en: 'Attack or threat in the Gulf or Yemen → energy or shipping disruption',
    event: node(3, 'Oil prices jump as Iran retaliation spreads'),
  }],
};

const story = {
  id: 2, title: 'Iran launches retaliatory strikes on Israel', category: 'military', severity: 'high',
  event_date: new Date().toISOString(), source_name: 'Wire', extra: {},
};

describe('<ChainSection> in the event drawer', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
  });

  it('lists causes and effects with confidence, rule and evidence', async () => {
    const spy = vi.spyOn(api, 'getEventChain').mockResolvedValue(chainBody);
    render(<EventDrawer event={story} onClose={() => {}} />);
    const section = within(await screen.findByRole('region', { name: 'Linked events' }));
    expect(spy).toHaveBeenCalledWith(2);
    expect(await section.findByText('Possible causes')).toBeInTheDocument();
    expect(section.getByText('Possible effects')).toBeInTheDocument();
    expect(section.getByText('Israel strikes targets in Iran')).toBeInTheDocument();
    expect(section.getByLabelText('Link confidence: 65% — Medium confidence')).toHaveTextContent('65%');
    expect(section.getByLabelText('Link confidence: 46% — Low confidence')).toBeInTheDocument();
    // الشفافية: القاعدة ومعرّفها، والكيانات المشتركة والفارق، والمعادلة بأرقامها
    expect(section.getByText('Strike → retaliation')).toBeInTheDocument();
    expect(section.getByText('strike_retaliation').parentElement).toHaveAttribute('title', 'Strike → retaliation');
    expect(section.getAllByText('Israel')[0]).toBeInTheDocument();
    expect(section.getAllByText(/10 h later/)[0]).toBeInTheDocument();
    expect(section.getAllByText('0.65 = 0.85 × 0.85 × 1 × 0.9')[0]).toBeInTheDocument();
  });

  it('opens a linked event', async () => {
    vi.spyOn(api, 'getEventChain').mockResolvedValue(chainBody);
    const onOpenEvent = vi.fn();
    render(<ChainSection eventId={2} onOpenEvent={onOpenEvent} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open event: Oil prices jump as Iran retaliation spreads' }));
    expect(onOpenEvent).toHaveBeenCalledWith(3);
  });

  it('says so when there are no links', async () => {
    vi.spyOn(api, 'getEventChain').mockResolvedValue({ event_id: 2, story_id: 2, causes: [], effects: [] });
    render(<ChainSection eventId={2} />);
    expect(await screen.findByText("No cause-and-effect links detected for this event's story.")).toBeInTheDocument();
  });

  it('ignores a response for another event', async () => {
    vi.spyOn(api, 'getEventChain').mockResolvedValue({ ...chainBody, event_id: 99 });
    render(<ChainSection eventId={2} />);
    await waitFor(() => expect(api.getEventChain).toHaveBeenCalled());
    expect(screen.getByText('Loading links…')).toBeInTheDocument();
    expect(screen.queryByText('Israel strikes targets in Iran')).not.toBeInTheDocument();
  });

  it('reports a failure', async () => {
    vi.spyOn(api, 'getEventChain').mockRejectedValue(new Error('down'));
    render(<ChainSection eventId={2} />);
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load linked events");
  });

  it('renders nothing for non-numeric ids (facility markers)', () => {
    const spy = vi.spyOn(api, 'getEventChain');
    const { container } = render(<ChainSection eventId="fac:ir-natanz" />);
    expect(container).toBeEmptyDOMElement();
    expect(spy).not.toHaveBeenCalled();
  });

  it('uses Arabic labels and entity names in Arabic', async () => {
    await i18n.changeLanguage('ar');
    vi.spyOn(api, 'getEventChain').mockResolvedValue(chainBody);
    render(<ChainSection eventId={2} />);
    const section = within(await screen.findByRole('region', { name: 'سلسلة الترابط' }));
    expect(await section.findByText('أسباب محتملة')).toBeInTheDocument();
    expect(section.getAllByText('إيران')[0]).toBeInTheDocument();
    expect(section.getAllByText('ضربة ← رد انتقامي', { selector: 'p' })[0]).toBeInTheDocument();
  });
});

const chains = {
  period_hours: 72,
  min_confidence: 0.4,
  links: 3,
  chains: [
    {
      length: 2,
      confidence: 0.46,
      nodes: [node(1, 'Israel strikes targets in Iran'), node(2, 'Iran launches retaliatory strikes on Israel'), node(3, 'Oil prices jump')],
      links: [link(1, 1, 2, 0.65), link(2, 2, 3, 0.46, 'gulf_attack_energy_shipping')],
    },
  ],
};

describe('<ChainsModal>', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.restoreAllMocks();
  });

  it('lists chains with per-link confidence and the chain confidence', async () => {
    vi.spyOn(api, 'getChains').mockResolvedValue(chains);
    render(<ChainsModal open onClose={() => {}} />);
    expect(await screen.findByText('Israel strikes targets in Iran')).toBeInTheDocument();
    expect(screen.getByRole('dialog', { name: 'Impact chains' })).toBeInTheDocument();
    expect(screen.getByText('Links: 2')).toBeInTheDocument();
    expect(screen.getByText('Chain confidence (weakest link)')).toBeInTheDocument();
    expect(screen.getAllByText('46%')).toHaveLength(2);         // الحلقة الأضعف = ثقة السلسلة
    expect(screen.getByText('65%')).toBeInTheDocument();
    expect(screen.getByText('gulf_attack_energy_shipping')).toBeInTheDocument();
  });

  it('hides low-confidence links by asking the server for stronger ones', async () => {
    const spy = vi.spyOn(api, 'getChains').mockResolvedValue(chains);
    render(<ChainsModal open onClose={() => {}} />);
    await screen.findByText('Israel strikes targets in Iran');
    expect(spy).toHaveBeenLastCalledWith(72, undefined);
    spy.mockResolvedValue({ ...chains, chains: [] });
    fireEvent.click(screen.getByRole('checkbox', { name: 'Hide low-confidence links (below 55%)' }));
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith(72, 0.55));
    expect(await screen.findByText('No chains above the confidence threshold in this period.')).toBeInTheDocument();
  });

  it('changes the period', async () => {
    const spy = vi.spyOn(api, 'getChains').mockResolvedValue(chains);
    render(<ChainsModal open onClose={() => {}} />);
    await screen.findByText('Israel strikes targets in Iran');
    fireEvent.change(screen.getByLabelText('Period'), { target: { value: '24' } });
    await waitFor(() => expect(spy).toHaveBeenLastCalledWith(24, undefined));
  });

  it('opens an event and closes on Escape', async () => {
    vi.spyOn(api, 'getChains').mockResolvedValue(chains);
    const onOpenEvent = vi.fn();
    const onClose = vi.fn();
    render(<ChainsModal open onClose={onClose} onOpenEvent={onOpenEvent} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open event: Oil prices jump' }));
    expect(onOpenEvent).toHaveBeenCalledWith(3);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('shows a failure and renders nothing when closed', async () => {
    vi.spyOn(api, 'getChains').mockRejectedValue(new Error('down'));
    const { rerender } = render(<ChainsModal open onClose={() => {}} />);
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load linked events");
    rerender(<ChainsModal open={false} onClose={() => {}} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
