/**
 * رصد - استطلاعات لوحة التحكم المشتركة.
 *
 * كل ما يشاركه أكثر من مكوّن (الخريطة والكرة، والهيدر واللوحات) يُجلب هنا مرة
 * واحدة بفاصل يناسب سرعة تغيّره. ما يخص لوحة واحدة (قصص الرصد النووي، العدسة،
 * السلاسل، التزامن) يبقى في لوحته.
 */
import { useCallback, useMemo } from 'react';
import { usePolling } from './usePolling';
import {
  getEvents, getMapEvents, getStats, getLiveFlights,
  getIranStrikes, getNuclearFacilities, getNuclearRisk,
  getCountryIndex, getMilitaryBases, getPipelines, getLatestEvents,
  getSchedule, getMarketsLatest,
} from '../utils/api';

export function useDashboardData({ filters, nuclearHours }) {
  const events = usePolling(
    useCallback(() => getEvents({ ...filters, limit: 200 }), [filters]),
    30000, [filters],
  );

  // الحدّ نفسه الذي تطلبه القائمة (200 قصة) كي تعرض الخريطة والقائمة المجموعة نفسها
  const { data: mapEvents } = usePolling(
    useCallback(() => getMapEvents(filters.hours, 200), [filters.hours]),
    30000, [filters.hours],
  );

  // تيار التنبيهات مستقل عن فلاتر العرض: فلتر «اقتصادي» أو بحث عن «غزة» لا
  // يُسكت الضربات العسكرية خارج الفلتر بلا إشارة.
  const { data: latestEvents } = usePolling(useCallback(() => getLatestEvents(50), []), 30000);

  const stats = usePolling(
    useCallback(() => getStats(filters.hours), [filters.hours]),
    60000, [filters.hours],
  );

  const { data: flights } = usePolling(useCallback(() => getLiveFlights(), []), 30000);

  // كل 30 دقيقة مثل iranstrikemap
  const { data: iranData } = usePolling(
    useCallback(() => getIranStrikes({ hours: 72, limit: 100 }), []),
    1800000,
  );

  // المنشآت النووية والقواعد وخطوط الأنابيب — بيانات ثابتة، تكفي مرة كل ساعة
  const { data: nuclearData } = usePolling(useCallback(() => getNuclearFacilities(), []), 3600000);
  const { data: basesData } = usePolling(useCallback(() => getMilitaryBases(), []), 3600000);
  const { data: pipelinesData } = usePolling(useCallback(() => getPipelines(), []), 3600000);

  // مؤشر المخاطر النووية والإشعاعية — يشاركه الهيدر ولوحة الرصد النووي
  const risk = usePolling(
    useCallback(() => getNuclearRisk(nuclearHours), [nuclearHours]),
    60000, [nuclearHours],
  );

  // وقت آخر تحليل وموعد المزامنة القادمة — للهيدر
  const schedule = usePolling(useCallback(() => getSchedule(), []), 60000);

  // الطاقة والأسواق (FRED يومي) — يشاركه شريط الهيدر ولوحة الأسواق. القيم
  // من قاعدة الخادم، فنصف ساعة يكفي ليلتقط جلبه اليومي.
  const markets = usePolling(useCallback(() => getMarketsLatest(), []), 1800000);

  // مؤشر استخبارات الدول
  const country = usePolling(
    useCallback(() => getCountryIndex({ hours: 72, top: 15 }), []),
    120000,
  );

  const eventsList = useMemo(() => events.data?.events || [], [events.data]);
  const iranStrikes = useMemo(() => iranData?.strikes || [], [iranData]);
  const liveMapEvents = useMemo(() => mapEvents || [], [mapEvents]);
  const nuclearFacilities = useMemo(() => nuclearData?.facilities || [], [nuclearData]);
  const militaryBases = useMemo(() => basesData?.bases || [], [basesData]);
  const pipelines = useMemo(() => pipelinesData?.pipelines || [], [pipelinesData]);
  const latest = useMemo(() => latestEvents || [], [latestEvents]);

  return {
    events: eventsList,
    eventsError: events.error,
    eventsLoading: events.loading,
    refetchEvents: events.refetch,
    liveMapEvents,
    latestEvents: latest,
    stats: stats.data,
    statsError: stats.error,
    refetchStats: stats.refetch,
    statsFetchedAt: stats.lastFetchedAt,
    flights,
    iranStrikes,
    nuclearFacilities,
    militaryBases,
    pipelines,
    nuclearRisk: risk.data,
    nuclearRiskError: risk.error,
    nuclearRiskStale: risk.stale,
    refetchRisk: risk.refetch,
    schedule: schedule.data,
    scheduleFetchedAt: schedule.lastFetchedAt,
    marketsLatest: markets.data,
    marketsError: markets.error,
    countryIndex: country.data,
    countryLoading: country.loading,
  };
}
