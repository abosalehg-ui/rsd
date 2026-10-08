/**
 * رصد - شريط إعادة التشغيل الزمني تحت الخريطة والكرة.
 *
 * في الوضع الحي يبقى الشريط زرّ تشغيل ومنزلقًا عند «الآن». أول تفاعل (تشغيل
 * أو تحريك المنزلق) يدخل وضع الإعادة: تُجلب أحداث النافذة (48 أو 72 ساعة) من
 * `/api/events/map` نفسها، ثم يُصفّى بـ `event_date` في المتصفح فتتراكم
 * الأحداث ساعة بساعة. `onFrame(events)` يمرّر أحداث الإطار للخريطة/الكرة،
 * و`onFrame(null)` يعيدهما للبيانات الحيّة.
 *
 * الزمن يجري من اليسار لليمين في اللغتين (عُرف المحاور الزمنية)، فالمنزلق
 * `dir="ltr"` صراحةً. لا شيء هنا يخص الكرة: لا تحميل إضافي لـ three.js.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Play, Pause, History, X, RotateCcw } from 'lucide-react';
import { getMapEvents } from '../../utils/api';
import { REPLAY_WINDOWS, eventsUntil, frameEnd, hourlyCounts, replayStart } from '../../utils/replay';

export const PLAY_INTERVAL_MS = 700;
const REPLAY_LIMIT = 1000;   // سقف /api/events/map

export default function ReplayBar({ onFrame, now: fixedNow = null }) {
  const { t, i18n } = useTranslation();
  const [active, setActive] = useState(false);
  const [hours, setHours] = useState(REPLAY_WINDOWS[0]);
  const [anchor, setAnchor] = useState(null);      // «الآن» مثبّت طوال الإعادة كي لا تنزاح الإطارات
  const [events, setEvents] = useState(null);
  const [status, setStatus] = useState('idle');    // idle | loading | ready | error
  const [step, setStep] = useState(REPLAY_WINDOWS[0] - 1);
  const [playing, setPlaying] = useState(false);
  const seq = useRef(0);

  const start = useMemo(() => (anchor ? replayStart(anchor, hours) : null), [anchor, hours]);
  const lastStep = hours - 1;

  const load = useCallback(async (h) => {
    const mine = ++seq.current;
    setStatus('loading');
    try {
      const data = await getMapEvents(h, REPLAY_LIMIT);
      if (mine !== seq.current) return;
      setEvents(Array.isArray(data) ? data : []);
      setStatus('ready');
    } catch {
      if (mine !== seq.current) return;
      setEvents([]);
      setStatus('error');
      setPlaying(false);
    }
  }, []);

  const activate = useCallback(() => {
    if (active) return;
    setActive(true);
    setAnchor(fixedNow ? new Date(fixedNow) : new Date());
    load(hours);
  }, [active, fixedNow, hours, load]);

  const close = useCallback(() => {
    seq.current += 1;
    setActive(false);
    setPlaying(false);
    setEvents(null);
    setStatus('idle');
    setStep(hours - 1);
    onFrame?.(null);
  }, [hours, onFrame]);

  // الإطار الحالي ← الخريطة/الكرة
  const frame = useMemo(
    () => (active && start && events ? eventsUntil(events, start, step) : null),
    [active, start, events, step],
  );
  useEffect(() => {
    if (frame) onFrame?.(frame);
  }, [frame, onFrame]);

  // التشغيل: ساعة كل PLAY_INTERVAL_MS حتى نهاية النافذة. الموضع الحالي من
  // مرجع كي لا يُعاد إنشاء المؤقّت مع كل إطار.
  const stepRef = useRef(step);
  useEffect(() => { stepRef.current = step; }, [step]);
  useEffect(() => {
    if (!playing || status !== 'ready') return undefined;
    const id = setInterval(() => {
      if (stepRef.current >= lastStep) {
        setPlaying(false);
        return;
      }
      stepRef.current += 1;
      setStep(stepRef.current);
    }, PLAY_INTERVAL_MS);
    return () => clearInterval(id);
  }, [playing, status, lastStep]);

  const togglePlay = () => {
    if (playing) { setPlaying(false); return; }
    activate();
    // من البداية إن كان المؤشر عند النهاية (أول تشغيل أو بعد انتهاء الإعادة)
    setStep(s => (s >= lastStep ? 0 : s));
    setPlaying(true);
  };

  const onSlide = (e) => {
    activate();
    setPlaying(false);
    setStep(Number(e.target.value));
  };

  const changeWindow = (e) => {
    const h = Number(e.target.value);
    setHours(h);
    setStep(h - 1);
    setPlaying(false);
    if (active) load(h);
  };

  const counts = useMemo(
    () => (start && events ? hourlyCounts(events, start, hours) : []),
    [start, events, hours],
  );
  const peak = Math.max(1, ...counts);

  const locale = i18n.language === 'ar' ? 'ar-SA-u-ca-gregory-nu-latn' : 'en-GB';
  const timeLabel = start
    ? frameEnd(start, step).toLocaleString(locale, { weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false })
    : '';

  return (
    <div
      className={`flex items-center gap-2 px-2 py-1.5 border-t border-rasad-border ${active ? 'bg-cyan-500/5' : 'bg-rasad-panel'}`}
      role="group"
      aria-label={t('replay.open')}
    >
      <button
        onClick={togglePlay}
        disabled={status === 'loading'}
        aria-label={playing ? t('replay.pause') : t('replay.play')}
        title={playing ? t('replay.pause') : t('replay.play')}
        className="min-w-11 min-h-11 flex items-center justify-center rounded-md bg-rasad-raised border border-rasad-border text-cyan-300 hover:border-cyan-500 focus-ring disabled:opacity-50"
      >
        {playing ? <Pause className="w-4 h-4" aria-hidden="true" /> : <Play className="w-4 h-4" aria-hidden="true" />}
      </button>

      {active && (
        <button
          onClick={() => { setPlaying(false); setStep(0); }}
          aria-label={t('replay.restart')}
          title={t('replay.restart')}
          className="hidden sm:flex min-w-9 min-h-11 items-center justify-center rounded-md text-slate-300 hover:text-white focus-ring"
        >
          <RotateCcw className="w-4 h-4" aria-hidden="true" />
        </button>
      )}

      <div dir="ltr" className="relative flex-1 min-w-0">
        {counts.length > 0 && (
          <div className="absolute inset-x-0 bottom-full flex items-end gap-px h-3 pointer-events-none" aria-hidden="true">
            {counts.map((c, i) => (
              <span
                key={i}
                className={`flex-1 rounded-t-sm ${i <= step ? 'bg-cyan-400/60' : 'bg-slate-500/30'}`}
                style={{ height: `${c ? Math.max(15, (c / peak) * 100) : 0}%` }}
              />
            ))}
          </div>
        )}
        <label htmlFor="rsd-replay-slider" className="sr-only">{t('replay.slider')}</label>
        <input
          id="rsd-replay-slider"
          type="range"
          min={0}
          max={lastStep}
          step={1}
          value={step}
          onChange={onSlide}
          aria-valuetext={timeLabel || t('replay.open')}
          className="w-full accent-cyan-400 focus-ring"
        />
      </div>

      <div className="hidden sm:flex flex-col items-end leading-tight min-w-[7.5rem] text-2xs" aria-live="polite">
        {!active && (
          <span className="flex items-center gap-1 text-slate-300">
            <History className="w-3.5 h-3.5" aria-hidden="true" /> {t('replay.open')}
          </span>
        )}
        {active && status === 'loading' && <span className="text-slate-300">{t('replay.loading')}</span>}
        {active && status === 'error' && <span className="text-red-200" role="alert">{t('replay.failed')}</span>}
        {active && status === 'ready' && (
          <>
            <span className="text-cyan-200 tabular-nums">{t('replay.until', { time: timeLabel })}</span>
            <span className="text-slate-400">{t('replay.count', { count: frame?.length ?? 0 })}</span>
          </>
        )}
      </div>

      <label htmlFor="rsd-replay-window" className="sr-only">{t('replay.window')}</label>
      <select
        id="rsd-replay-window"
        value={hours}
        onChange={changeWindow}
        className="bg-rasad-bg border border-rasad-border rounded px-1.5 py-1 text-xs text-slate-100 focus-ring"
      >
        {REPLAY_WINDOWS.map(h => <option key={h} value={h}>{t(`replay.windows.${h}`)}</option>)}
      </select>

      {active && (
        <button
          onClick={close}
          aria-label={t('replay.close')}
          title={t('replay.close')}
          className="min-w-11 min-h-11 flex items-center justify-center rounded-md text-slate-300 hover:text-white hover:bg-rasad-border focus-ring"
        >
          <X className="w-4 h-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
