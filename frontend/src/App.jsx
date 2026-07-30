/**
 * رصد (Rsd) - التطبيق الرئيسي
 */
import React, { useState, useCallback, useMemo, useEffect, Suspense, lazy } from 'react';
import { useTranslation } from 'react-i18next';
import Header from './components/Layout/Header';
import LiveTVDrawer from './components/Layout/LiveTVDrawer';
import AlertSettings from './components/Layout/AlertSettings';
import RasadMap from './components/Map/RasadMap';
import LayerToggles from './components/Map/LayerToggles';
import NewsFeed from './components/NewsFeed/NewsFeed';
import Timeline from './components/Timeline/Timeline';
import StatsPanel from './components/Stats/StatsPanel';
import IranPanel from './components/Iran/IranPanel';
import ErrorBoundary from './components/common/ErrorBoundary';
import { usePolling, useFilters } from './hooks/usePolling';
import { useAudioAlert } from './hooks/useAudioAlert';
import { Newspaper, Clock, BarChart3, PanelLeftClose, PanelLeftOpen, Crosshair, Map as MapIcon, X } from 'lucide-react';
import {
  getEvents, getMapEvents, getStats, getLiveFlights, refreshSources,
  getIranStrikes, getNuclearFacilities,
  getCountryIndex, getMilitaryBases, getPipelines,
} from './utils/api';

// تحميل كسول للكرة الأرضية — Three.js كبير الحجم
const RasadGlobe = lazy(() => import('./components/Map/RasadGlobe'));

const TABS = [
  { id: 'news', labelKey: 'tabs.news', icon: Newspaper },
  { id: 'timeline', labelKey: 'tabs.timeline', icon: Clock },
  { id: 'stats', labelKey: 'tabs.stats', icon: BarChart3 },
  { id: 'iran', labelKey: 'tabs.iran', icon: Crosshair },
];

// حالة الطبقات مرفوعة إلى App كي تتشارك الخريطة 2D والكرة 3D الإعدادات نفسها
// (كان لكل منهما افتراضات مختلفة، والكرة بلا أزرار تحكّم أصلاً).
const DEFAULT_LAYERS = {
  events: true,
  flights: true,
  iran: true,
  nuclear: true,
  bases: false,
  pipelines: false,
};

export default function App() {
  const { t } = useTranslation();
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [activeTab, setActiveTab] = useState('news');
  const [panelOpen, setPanelOpen] = useState(true);
  // على الجوال لا تتّسع الشاشة للخريطة واللوحة معاً — نعرض واحدة في كل مرة
  const [mobileView, setMobileView] = useState('map');
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [viewMode, setViewMode] = useState(() => {
    try { return localStorage.getItem('rsd-view-mode') || '2d'; } catch { return '2d'; }
  });
  const { filters, updateFilter, resetFilters } = useFilters();

  const setLayer = useCallback((key, value) => {
    setLayers(prev => ({ ...prev, [key]: value }));
  }, []);

  // جلب البيانات مع تحديث تلقائي
  const { data: eventsData, error: eventsError, loading: eventsLoading, refetch: refetchEvents } = usePolling(
    useCallback(() => getEvents({ ...filters, limit: 200 }), [filters]),
    30000, [filters]
  );

  const { data: mapEvents } = usePolling(
    useCallback(() => getMapEvents(filters.hours), [filters.hours]),
    30000, [filters.hours]
  );

  const { data: stats, error: statsError, refetch: refetchStats } = usePolling(
    useCallback(() => getStats(filters.hours), [filters.hours]),
    60000, [filters.hours]
  );

  const { data: flights } = usePolling(
    useCallback(() => getLiveFlights(), []),
    30000
  );

  const { data: iranData } = usePolling(
    useCallback(() => getIranStrikes({ hours: 72, limit: 100 }), []),
    1800000  // كل 30 دقيقة مثل iranstrikemap
  );

  // المنشآت النووية ☢️ — بيانات ثابتة، تكفي مرة واحدة كل ساعة
  const { data: nuclearData } = usePolling(
    useCallback(() => getNuclearFacilities(), []),
    3600000
  );

  // قواعد عسكرية + خطوط أنابيب — بيانات ثابتة (v1.3)
  const { data: basesData } = usePolling(
    useCallback(() => getMilitaryBases(), []),
    3600000
  );
  const { data: pipelinesData } = usePolling(
    useCallback(() => getPipelines(), []),
    3600000
  );

  // مؤشر استخبارات الدول (v1.3)
  const { data: countryIndex, loading: countryLoading } = usePolling(
    useCallback(() => getCountryIndex({ hours: 72, top: 15 }), []),
    120000
  );

  const events = useMemo(() => eventsData?.events || [], [eventsData]);
  const iranStrikes = useMemo(() => iranData?.strikes || [], [iranData]);
  const mapEvts = useMemo(() => mapEvents || [], [mapEvents]);
  const nuclearFacilities = useMemo(() => nuclearData?.facilities || [], [nuclearData]);
  const militaryBases = useMemo(() => basesData?.bases || [], [basesData]);
  const pipelines = useMemo(() => pipelinesData?.pipelines || [], [pipelinesData]);
  const criticalEvents = useMemo(
    () => events.filter(e => e.severity === 'critical' || e.severity === 'high').slice(0, 10),
    [events]
  );

  // 🔔 محرّك التنبيهات الصوتية — يراقب الأحداث الجديدة
  const {
    prefs: alertPrefs,
    setPrefs: setAlertPrefs,
    lastAlertEvent,
    recentAlerts,
    clearRecent,
    testSound,
    requestDesktopPermission,
  } = useAudioAlert(events, filters);

  const [alertsOpen, setAlertsOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);   // { kind: 'ok'|'error', text }

  // إخفاء الإشعار تلقائياً
  useEffect(() => {
    if (!toast) return undefined;
    const id = setTimeout(() => setToast(null), 6000);
    return () => clearTimeout(id);
  }, [toast]);

  const toggleViewMode = useCallback(() => {
    setViewMode(prev => {
      const next = prev === '2d' ? '3d' : '2d';
      try { localStorage.setItem('rsd-view-mode', next); } catch { /* التخزين معطّل */ }
      return next;
    });
  }, []);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refreshSources();
      refetchEvents();
      refetchStats();
      setToast({ kind: 'ok', text: t('app.refreshDone') });
    } catch (e) {
      // الخادم يعيد 429 مع Retry-After عند التحديث المتقارب — كان يُبتلَع صامتاً
      setToast(
        e?.status === 429 && e?.retryAfter
          ? { kind: 'error', text: t('app.refreshThrottled', { seconds: e.retryAfter }) }
          : { kind: 'error', text: t('app.refreshFailed', { message: e?.message || '' }) }
      );
    } finally {
      setRefreshing(false);
    }
  }, [refetchEvents, refetchStats, t]);

  // اختيار حدث من اللوحة على الجوال ينقل المستخدم إلى الخريطة تلقائياً
  const handleSelectEvent = useCallback((ev) => {
    setSelectedEvent(ev);
    if (window.matchMedia('(max-width: 767px)').matches) setMobileView('map');
  }, []);

  const mapNode = viewMode === '3d' ? (
    <ErrorBoundary onReset={() => setViewMode('2d')}>
      <Suspense fallback={<div className="flex items-center justify-center h-full text-cyan-300 text-sm">🌍 {t('app.loadingGlobe')}</div>}>
        <RasadGlobe
          events={mapEvts}
          flights={flights}
          iranStrikes={iranStrikes}
          nuclearFacilities={nuclearFacilities}
          bases={militaryBases}
          pipelines={pipelines}
          layers={layers}
          selectedEvent={selectedEvent}
          onSelectEvent={setSelectedEvent}
        />
      </Suspense>
      {/* تحكمات الطبقات فوق الكرة — الكرة نفسها بلا chrome داخلي */}
      <LayerToggles
        layers={layers}
        onLayerChange={setLayer}
        className="absolute bottom-3 start-3 z-[1000] max-w-[45vw]"
      />
    </ErrorBoundary>
  ) : (
    <ErrorBoundary>
      <RasadMap
        events={mapEvts}
        flights={flights}
        iranStrikes={iranStrikes}
        nuclearFacilities={nuclearFacilities}
        militaryBases={militaryBases}
        pipelines={pipelines}
        layers={layers}
        onLayerChange={setLayer}
        selectedEvent={selectedEvent}
        onSelectEvent={setSelectedEvent}
      />
    </ErrorBoundary>
  );

  const panelNode = (
    <>
      {/* تبويبات */}
      <div className="flex border-b border-rasad-border" role="tablist" aria-label={t('news.title')}>
        {TABS.map(tab => {
          const Icon = tab.icon;
          const label = t(tab.labelKey);
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={active}
              aria-controls={`tabpanel-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm transition-colors focus-ring ${
                active
                  ? 'text-cyan-300 border-b-2 border-cyan-400 bg-cyan-400/5'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Icon className="w-4 h-4" aria-hidden="true" />
              {tab.id === 'iran' ? <span>🇮🇷 {label}</span> : label}
            </button>
          );
        })}
      </div>

      {/* محتوى التبويب */}
      <div
        className="flex-1 overflow-hidden"
        role="tabpanel"
        id={`tabpanel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
      >
        {activeTab === 'news' && (
          <NewsFeed
            events={events}
            error={eventsError}
            loading={eventsLoading}
            onSelectEvent={handleSelectEvent}
            filters={filters}
            onFilterChange={updateFilter}
            onResetFilters={resetFilters}
          />
        )}
        {activeTab === 'timeline' && (
          <Timeline
            events={events}
            loading={eventsLoading}
            hours={filters.hours}
            onHoursChange={(h) => updateFilter('hours', h)}
            onSelectEvent={handleSelectEvent}
          />
        )}
        {activeTab === 'stats' && (
          <StatsPanel stats={stats} countryIndex={countryIndex} countryLoading={countryLoading} />
        )}
        {activeTab === 'iran' && (
          <IranPanel onSelectStrike={handleSelectEvent} />
        )}
      </div>
    </>
  );

  return (
    <div className="h-dvh w-full flex flex-col bg-rasad-bg text-white font-arabic overflow-hidden">
      <a href="#rsd-panel" className="skip-link">{t('app.skipToPanel')}</a>

      <Header
        stats={stats}
        isConnected={!statsError}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        alertsEnabled={alertPrefs.enabled}
        lastAlertEvent={lastAlertEvent}
        recentAlertCount={recentAlerts.length}
        onOpenAlerts={() => setAlertsOpen(true)}
        viewMode={viewMode}
        onToggleView={toggleViewMode}
      />

      {/* بانر تعذّر الاتصال — البيانات المعروضة قد تكون قديمة */}
      {statsError && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-1.5 text-center" role="alert">
          <span className="text-xs text-amber-200">
            ⚠️ {t('app.connectionLost')}
          </span>
        </div>
      )}

      {/* نتيجة التحديث اليدوي (نجاح / 429 / خطأ) */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className={`flex items-center justify-center gap-3 px-4 py-1.5 border-b text-xs ${
            toast.kind === 'ok'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
              : 'bg-red-500/10 border-red-500/30 text-red-200'
          }`}
        >
          <span>{toast.text}</span>
          <button onClick={() => setToast(null)} aria-label={t('app.dismiss')} className="focus-ring rounded p-0.5 hover:text-white">
            <X className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        </div>
      )}

      {/* شريط الأخبار العاجلة */}
      {criticalEvents.length > 0 && (
        <div className="bg-red-500/10 border-b border-red-500/20 px-4 py-1 overflow-hidden">
          <div className="flex items-center gap-3">
            <span className="text-xs bg-red-600 text-white px-3 py-1 rounded font-bold animate-pulse whitespace-nowrap">
              {t('app.breaking')}
            </span>
            <div className="overflow-hidden flex-1">
              <div className="flex gap-8 ticker whitespace-nowrap">
                {criticalEvents.map((ev) => (
                  <button
                    key={ev.id}
                    onClick={() => handleSelectEvent(ev)}
                    className="text-sm text-red-200 hover:text-white focus-ring rounded"
                  >
                    <span className="text-red-300" aria-hidden="true">●</span> {ev.title}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* مبدّل الجوال بين الخريطة واللوحة */}
      <div className="md:hidden flex border-b border-rasad-border">
        {[
          { id: 'map', label: t('app.showMap'), Icon: MapIcon },
          { id: 'panel', label: t('app.showPanel'), Icon: Newspaper },
        ].map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setMobileView(id)}
            aria-pressed={mobileView === id}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm focus-ring ${
              mobileView === id ? 'text-cyan-300 border-b-2 border-cyan-400 bg-cyan-400/5' : 'text-slate-300'
            }`}
          >
            <Icon className="w-4 h-4" aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>

      {/* المحتوى الرئيسي — عمودي على الجوال، أفقي من md فأعلى */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* الخريطة / الكرة الأرضية
            min-w-0 + overflow-hidden: يمنع canvas الكرة (globe.gl) من فرض عرضه
            الثابت كحد أدنى للعنصر المرن وسحق اللوحة الجانبية في وضع 3D */}
        <div
          className={`relative min-w-0 min-h-0 overflow-hidden flex-1 ${
            mobileView === 'map' ? 'flex' : 'hidden'
          } md:flex md:flex-1`}
        >
          <div className="absolute inset-0">{mapNode}</div>

          {/* زر طي/فتح اللوحة — سطح المكتب فقط (على الجوال يوجد المبدّل).
              خصائص منطقية (end/border-e/rounded-s) كي لا ينفصل التبويب على
              الجانب الخطأ في الوضع الإنجليزي؛ والأيقونة تدلّ على الإجراء لا الحالة. */}
          <button
            onClick={() => setPanelOpen(!panelOpen)}
            aria-label={panelOpen ? t('app.collapsePanel') : t('app.expandPanel')}
            title={panelOpen ? t('app.collapsePanel') : t('app.expandPanel')}
            className="hidden md:flex absolute top-1/2 end-0 z-[1000] -translate-y-1/2 w-6 h-16 bg-rasad-panel border border-rasad-border border-e-0 rounded-s-lg items-center justify-center text-cyan-300 hover:bg-rasad-border focus-ring"
          >
            {panelOpen ? <PanelLeftClose className="w-4 h-4" aria-hidden="true" /> : <PanelLeftOpen className="w-4 h-4" aria-hidden="true" />}
          </button>
        </div>

        {/* اللوحة الجانبية — main + tabIndex كي ينقل رابط التخطّي التركيز فعلاً
            (كان div غير قابل للتركيز فيفشل التخطّي في Safari/Firefox) */}
        <main
          id="rsd-panel"
          tabIndex={-1}
          className={`${mobileView === 'panel' ? 'flex' : 'hidden'} ${
            panelOpen ? 'md:flex' : 'md:hidden'
          } flex-1 md:flex-none w-full md:w-[360px] lg:w-[420px] xl:w-[500px] min-h-0 flex-col border-t md:border-t-0 md:border-s border-rasad-border bg-rasad-panel focus:outline-none`}
        >
          {panelNode}
        </main>
      </div>

      <LiveTVDrawer />

      <AlertSettings
        isOpen={alertsOpen}
        onClose={() => setAlertsOpen(false)}
        prefs={alertPrefs}
        setPrefs={setAlertPrefs}
        recentAlerts={recentAlerts}
        clearRecent={clearRecent}
        testSound={testSound}
        requestDesktopPermission={requestDesktopPermission}
        onSelectAlert={handleSelectEvent}
      />
    </div>
  );
}
