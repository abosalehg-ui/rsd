import { describe, it, expect, vi } from 'vitest';
import L from 'leaflet';
import { buildEventsLayer } from './events';
import { buildIranLayer } from './iran';
import { buildNuclearLayer } from './nuclear';
import { buildZonesLayer } from './zones';
import { buildBasesLayer } from './bases';
import { buildFlightsLayer } from './flights';
import { buildPipelinesLayer } from './pipelines';
import { THEME } from '../../../utils/constants';
import { Z_OFFSET } from './shared';

const ctx = { popupCtx: { t: (k) => k, dir: 'ltr', lang: 'en' } };

describe('map layer builders', () => {
  it('draws single events and clusters, selecting the clicked event', () => {
    const group = L.layerGroup();
    const onSelectEvent = vi.fn();
    const a = { id: 1, latitude: 24, longitude: 46, category: 'military', severity: 'high' };
    const b = { id: 2, latitude: 30, longitude: 50, category: 'nuclear', severity: 'critical', risk_score: 80 };
    const c = { id: 3, latitude: 30, longitude: 50, category: 'nuclear', severity: 'low', risk_score: 20 };
    const clusters = [
      { lat: 24, lng: 46, spreadPx: 0, events: [a] },
      { lat: 30, lng: 50, spreadPx: 0, events: [b, c] },
    ];
    buildEventsLayer(group, { events: [a, b, c], clusters, nudges: new Map(), zoomLevel: 5 },
      { ...ctx, onSelectEvent, getMap: () => null });
    const markers = group.getLayers();
    expect(markers).toHaveLength(2);
    expect(markers[1].options.icon.options.html).toContain('>2</div>');
    expect(markers[0].options.zIndexOffset).toBe(Z_OFFSET.event);
    markers[0].fire('click');
    expect(onSelectEvent).toHaveBeenCalledWith(a);
  });

  it('offsets nudged markers and skips items without coordinates', () => {
    const group = L.layerGroup();
    buildIranLayer(group, {
      iranStrikes: [{ id: 7, latitude: 32, longitude: 51, confidence: 'HIGH' }, { id: 8 }],
      nudges: new Map([['ir:7', { dx: 10, dy: 0 }]]),
    }, { ...ctx, onSelectEvent: vi.fn() });
    const [m] = group.getLayers();
    expect(group.getLayers()).toHaveLength(1);
    expect(m.options.icon.options.iconAnchor).toEqual([3, 13]);   // (18+8)/2 − 10
  });

  it('draws facilities and planning zones for operating plants only', () => {
    const fac = { id: 'bu', type: 'power', status: 'operational', latitude: 28.8, longitude: 50.9, name_en: 'Bushehr',
      planning_zones: [{ key: 'PAZ', km: 5 }, { key: 'UPZ', km: 30 }] };
    const planned = { ...fac, id: 'x', status: 'planned' };
    const nuclear = L.layerGroup();
    buildNuclearLayer(nuclear, { nuclearFacilities: [fac, planned], nudges: new Map() }, ctx);
    expect(nuclear.getLayers()).toHaveLength(2);
    const zones = L.layerGroup();
    buildZonesLayer(zones, [fac, planned]);
    expect(zones.getLayers()).toHaveLength(3);                       // دائرتان + تسمية
  });

  it('draws military bases with a type icon, escaping the name', () => {
    const group = L.layerGroup();
    buildBasesLayer(group, {
      militaryBases: [
        { id: 'b1', latitude: 25, longitude: 51, type: 'air', name_en: 'Al <b>Udeid</b>' },
        { id: 'b2' },
      ],
      nudges: new Map([['ba:b1', { dx: 4, dy: 0 }]]),
    }, ctx);
    const [m] = group.getLayers();
    expect(group.getLayers()).toHaveLength(1);
    expect(m.options.zIndexOffset).toBe(Z_OFFSET.base);
    expect(m.options.icon.options.iconAnchor).toEqual([5, 9]);
    expect(m.options.icon.options.html).toContain('Al &lt;b&gt;Udeid&lt;/b&gt;');
    expect(m.options.icon.options.html).toContain(THEME.violet);
  });

  it('draws flights below other layers and highlights emergencies', () => {
    const group = L.layerGroup();
    buildFlightsLayer(group, {
      flights: [
        { icao24: 'a', latitude: 24, longitude: 46, heading: 90, is_military: false },
        { icao24: 'b', latitude: 25, longitude: 47, heading: 0, is_emergency: true, squawk: '7700' },
        { icao24: 'c' },
      ],
    }, ctx);
    const markers = group.getLayers();
    expect(markers).toHaveLength(2);
    expect(markers.every(m => m.options.zIndexOffset === Z_OFFSET.flight)).toBe(true);
    expect(markers[0].options.icon.options.html).toContain('rotate(45deg)');
    expect(markers[1].options.icon.options.html).toContain(`drop-shadow(0 0 6px ${THEME.emergency})`);
  });

  it('draws oil and gas pipelines in their theme colours, dashing partial lines', () => {
    const group = L.layerGroup();
    buildPipelinesLayer(group, [
      { name_en: 'Oil', type: 'oil', coordinates: [[24, 46], [26, 50]] },
      { name_en: 'Gas', type: 'gas', status: 'partial', coordinates: [[24, 46], [25, 47]] },
      { name_en: 'Too short', type: 'oil', coordinates: [[24, 46]] },
    ], ctx);
    const [oil, gas] = group.getLayers();
    expect(group.getLayers()).toHaveLength(2);
    expect(oil.options.color).toBe(THEME.pipelineOil);
    expect(gas.options.color).toBe(THEME.pipelineGas);
    expect(gas.options.dashArray).toBe('5, 8');
  });
});
