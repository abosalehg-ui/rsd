/**
 * رصد (Rasad) v1.0 - التطبيق الرئيسي
 */
import LiveTVDrawer from './components/Layout/LiveTVDrawer';
import React, { useState, useCallback, useMemo } from 'react';
import Header from './components/Layout/Header';
import RasadMap from './components/Map/RasadMap';
import NewsFeed from './components/NewsFeed/NewsFeed';
import Timeline from './components/Timeline/Timeline';
import StatsPanel from './components/Stats/StatsPanel';
import { usePolling, useFilters } from './hooks/usePolling';
import { MapPin, Newspaper, Clock, BarChart3, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { getEvents, getMapEvents, getStats, getLiveFlights, refreshSources } from './utils/api';

const TABS = [
  { id: 'news', label: 'الأحداث', icon: Newspaper },
  { id: 'timeline', label: 'الخط الزمني', icon: Clock },
  { id: 'stats', label: 'إحصائيات', icon: BarChart3 },
];

export default function App() {
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [activeTab, setActiveTab] = useState('news');
  const [panelOpen, setPanelOpen] = useState(true);
  const { filters, updateFilter, resetFilters } = useFilters();

  // جلب البيانات مع تحديث تلقائي
  const { data: eventsData, refetch: refetchEvents } = usePolling(
    useCallback(() => getEvents({ ...filters, limit: 200 }), [filters]),
    30000, [filters]
  );

  const { data: mapEvents } = usePolling(
    useCallback(() => getMapEvents(filters.hours), [filters.hours]),
    30000
  );

  const { data: stats, refetch: refetchStats } = usePolling(
    useCallback(() => getStats(filters.hours), [filters.hours]),
    60000
  );

  const { data: flights } = usePolling(
    useCallback(() => getLiveFlights(), []),
    30000
  );

  const events = useMemo(() => eventsData?.events || [], [eventsData]);
  const mapEvts = useMemo(() => mapEvents || [], [mapEvents]);

  const [refreshing, setRefreshing] = useState(false);

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
      <Header stats={stats} isConnected={true} onRefresh={handleRefresh} refreshing={refreshing} />

      {/* شريط الأخبار العاجلة */}
      {events.length > 0 && (
        <div className="bg-red-500/10 border-b border-red-500/20 px-4 py-1 overflow-hidden">
          <div className="flex items-center gap-3">
            <span className="text-xs bg-red-500 text-white px-3 py-1 rounded font-bold animate-pulse whitespace-nowrap">عاجل</span>
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
        {/* الخريطة */}
        <div className="flex-1 relative">
          <RasadMap
            events={mapEvts}
            flights={flights}
            selectedEvent={selectedEvent}
            onSelectEvent={setSelectedEvent}
          />

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
                    {tab.label}
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
                <StatsPanel stats={stats} />
              )}
            </div>
          </div>
        )}
      </div>

      <LiveTVDrawer />
    </div>
  );
}
