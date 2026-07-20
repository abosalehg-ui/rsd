/**
 * رصد (Rasad) v1.0 - التطبيق الرئيسي
 */
import LiveTVDrawer from './components/Layout/LiveTVDrawer';
import AlertSettings from './components/Layout/AlertSettings';
import React, { useState, useCallback, useMemo, Suspense, lazy } from 'react';
import { useTranslation } from 'react-i18next';
import Header from './components/Layout/Header';
import RasadMap from './components/Map/RasadMap';
// تحميل كسول للكرة الأرضية — Three.js كبير الحجم
const RasadGlobe = lazy(() => import('./components/Map/RasadGlobe'));
import NewsFeed from './components/NewsFeed/NewsFeed';
import Timeline from './components/Timeline/Timeline';
import StatsPanel from './components/Stats/StatsPanel';
import IranPanel from './components/Iran/IranPanel';
import { usePolling, useFilters } from './hooks/usePolling';
import { useAudioAlert } from './hooks/useAudioAlert';
import { MapPin, Newspaper, Clock, BarChart3, PanelLeftClose, PanelLeftOpen, Crosshair } from 'lucide-react';
import {
  getEvents, getMapEvents, getStats, getLiveFlights, refreshSources,
  getIranStrikes, getNuclearFacilities,
  getCountryIndex, getMilitaryBases, getPipelines,
} from './utils/api';

export default function App() {
  const { t } = useTranslation();
  const TABS = [
    { id: 'news', labelKey: 'tabs.news', icon: Newspaper },
    { id: 'timeline', labelKey: 'tabs.timeline', icon: Clock },
    { id: 'stats', labelKey: 'tabs.stats', icon: BarChart3 },
    { id: 'iran', labelKey: 'tabs.iran', icon: Crosshair },
  ];
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [activeTab, setActiveTab] = useState('news');
  const [panelOpen, setPanelOpen] = useState(true);
  const [viewMode, setViewMode] = useState(() => {
    try { return localStorage.getItem('rsd-view-mode') || '2d'; } catch { return '2d'; }
  });
  const { filters, updateFilter } = useFilters();

  // جلب البيانات مع تحديث تلقائي
  const { data: eventsData, refetch: refetchEvents } = usePolling(
    useCallback(() => getEvents({ ...filters, limit: 200 }), [filters]),
    30000, [filters]
  );

  const { data: mapEvents } = usePolling(
    useCallback(() => getMapEvents(filters.hours), [filters.hours]),
    30000, [filters.hours]
  );

  const { data: stats, refetch: refetchStats } = usePolling(
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
  const { data: countryIndex } = usePolling(
    useCallback(() => getCountryIndex({ hours: 72, top: 15 }), []),
    120000
  );

  const events = useMemo(() => eventsData?.events || [], [eventsData]);
  const iranStrikes = useMemo(() => iranData?.strikes || [], [iranData]);
  const mapEvts = useMemo(() => mapEvents || [], [mapEvents]);
  const nuclearFacilities = useMemo(() => nuclearData?.facilities || [], [nuclearData]);
  const militaryBases = useMemo(() => basesData?.bases || [], [basesData]);
  const pipelines = useMemo(() => pipelinesData?.pipelines || [], [pipelinesData]);

  // 🔔 محرّك التنبيهات الصوتية — يراقب الأحداث الجديدة
  const {
    prefs: alertPrefs,
    setPrefs: setAlertPrefs,
    lastAlertEvent,
    recentAlerts,
    clearRecent,
    testSound,
    requestDesktopPermission,
  } = useAudioAlert(events);

  const [alertsOpen, setAlertsOpen] = useState(false);

  const [refreshing, setRefreshing] = useState(false);

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
    } catch (e) {
      console.error('خطأ في التحديث:', e);
    } finally {
      setRefreshing(false);
    }
  }, [refetchEvents, refetchStats]);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0a0e17] text-white font-arabic overflow-hidden">
      {/* الشريط العلوي */}
      <Header
        stats={stats}
        isConnected={true}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        alertsEnabled={alertPrefs.enabled}
        lastAlertEvent={lastAlertEvent}
        recentAlertCount={recentAlerts.length}
        onOpenAlerts={() => setAlertsOpen(true)}
        viewMode={viewMode}
        onToggleView={toggleViewMode}
      />

      {/* شريط الأخبار العاجلة */}
      {events.length > 0 && (
        <div className="bg-red-500/10 border-b border-red-500/20 px-4 py-1 overflow-hidden">
          <div className="flex items-center gap-3">
            <span className="text-xs bg-red-500 text-white px-3 py-1 rounded font-bold animate-pulse whitespace-nowrap">{t('app.breaking')}</span>
            <div className="overflow-hidden flex-1">
              <div className="flex gap-8 animate-[ticker-scroll_60s_linear_infinite] whitespace-nowrap">
                {events.filter(e => e.severity === 'critical' || e.severity === 'high').slice(0, 10).map((ev, i) => (
                  <span key={i} className="text-sm text-red-200 cursor-pointer hover:text-white" onClick={() => setSelectedEvent(ev)}>
                    <span className="text-red-400">●</span> {ev.title}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* المحتوى الرئيسي */}
      <div className="flex-1 flex overflow-hidden">
        {/* الخريطة / الكرة الأرضية */}
        {/* min-w-0 + overflow-hidden: يمنع canvas الكرة الأرضية (globe.gl) من فرض
            عرضه الثابت كحد أدنى للعنصر المرن وسحق اللوحة الجانبية حتى الاختفاء في وضع 3D */}
        <div className="flex-1 relative min-w-0 overflow-hidden">
          {viewMode === '3d' ? (
            <Suspense fallback={<div className="flex items-center justify-center h-full text-cyan-400 text-sm">🌍 جاري تحميل الكرة الأرضية...</div>}>
              <RasadGlobe
                events={mapEvts}
                iranStrikes={iranStrikes}
                nuclearFacilities={nuclearFacilities}
                bases={militaryBases}
                pipelines={pipelines}
                selectedEvent={selectedEvent}
                onSelectEvent={setSelectedEvent}
              />
            </Suspense>
          ) : (
            <RasadMap
              events={mapEvts}
              flights={flights}
              iranStrikes={iranStrikes}
              nuclearFacilities={nuclearFacilities}
              militaryBases={militaryBases}
              pipelines={pipelines}
              selectedEvent={selectedEvent}
              onSelectEvent={setSelectedEvent}
            />
          )}

          {/* زر طي/فتح اللوحة — داخل الخريطة على حافتها */}
          <button
            onClick={() => setPanelOpen(!panelOpen)}
            className="absolute top-1/2 left-0 z-[1000] -translate-y-1/2 w-6 h-16 bg-[#111827] border border-[#1e293b] border-l-0 rounded-r-lg flex items-center justify-center text-cyan-400 hover:bg-[#1e293b]"
            title={panelOpen ? 'طي اللوحة' : 'فتح اللوحة'}
          >
            {panelOpen ? <PanelLeftOpen className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          </button>
        </div>

        {/* اللوحة الجانبية — تظهر/تختفي بالكامل */}
        {panelOpen && (
          <div className="w-[500px] flex flex-col border-r border-[#1e293b] bg-[#111827]">
            {/* تبويبات */}
            <div className="flex border-b border-[#1e293b]">
              {TABS.map(tab => {
                const Icon = tab.icon;
                const label = t(tab.labelKey);
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm transition-colors ${
                      activeTab === tab.id
                        ? 'text-cyan-400 border-b-2 border-cyan-400 bg-cyan-400/5'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.id === 'iran' ? <span>🇮🇷 {label}</span> : label}
                  </button>
                );
              })}
            </div>

            {/* محتوى التبويب */}
            <div className="flex-1 overflow-hidden">
              {activeTab === 'news' && (
                <NewsFeed
                  events={events}
                  onSelectEvent={setSelectedEvent}
                  filters={filters}
                  onFilterChange={updateFilter}
                />
              )}
              {activeTab === 'timeline' && (
                <Timeline events={events} onSelectEvent={setSelectedEvent} />
              )}
              {activeTab === 'stats' && (
                <StatsPanel stats={stats} countryIndex={countryIndex} />
              )}
              {activeTab === 'iran' && (
                <IranPanel onSelectStrike={setSelectedEvent} />
              )}
            </div>
          </div>
        )}
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
        onSelectAlert={setSelectedEvent}
      />
    </div>
  );
}
