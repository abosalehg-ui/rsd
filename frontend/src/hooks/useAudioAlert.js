/**
 * رصد - خطاف التنبيهات الصوتية للأخبار الهامة
 *
 * يكتشف الأحداث الجديدة (التي لم تكن في polling السابق)،
 * يفلتر حسب العتبة والتصنيفات، ويشغّل صوت إنذار قصير عبر Web Audio API
 * بدون الحاجة لملفات صوتية خارجية.
 *
 * يخزّن التفضيلات في localStorage تحت المفتاح "rsd-alert-prefs".
 */
import { useEffect, useRef, useState, useCallback } from 'react';

const STORAGE_KEY = 'rsd-alert-prefs';
const SEVERITY_RANK = { low: 1, medium: 2, high: 3, critical: 4 };

const DEFAULT_PREFS = {
  enabled: true,
  threshold: 'high',          // low | medium | high | critical
  categories: [],             // [] = الكل، أو ['military', 'nuclear'] إلخ
  desktopNotifications: false,
  throttleSeconds: 20,        // لا أكثر من تنبيه واحد كل N ثانية
};

export function loadAlertPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFS;
    return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_PREFS;
  }
}

export function saveAlertPrefs(prefs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // الكوكيز معطّلة — تجاهل
  }
}

// ===== توليد صوت الإنذار عبر Web Audio API =====
let audioCtx = null;

function ensureCtx() {
  if (!audioCtx) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audioCtx = new Ctx();
  }
  if (audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

function playAlarmTone() {
  const ctx = ensureCtx();
  if (!ctx) return;

  const now = ctx.currentTime;
  const master = ctx.createGain();
  master.gain.setValueAtTime(0.0001, now);
  master.gain.exponentialRampToValueAtTime(0.25, now + 0.02);
  master.gain.exponentialRampToValueAtTime(0.0001, now + 1.4);
  master.connect(ctx.destination);

  // نغمتان متناوبتان (إنذار كلاسيكي)
  [[880, 0.0], [660, 0.35], [880, 0.7], [660, 1.05]].forEach(([freq, offset]) => {
    const osc = ctx.createOscillator();
    osc.type = 'square';
    osc.frequency.setValueAtTime(freq, now + offset);
    const env = ctx.createGain();
    env.gain.setValueAtTime(0.0001, now + offset);
    env.gain.exponentialRampToValueAtTime(0.9, now + offset + 0.02);
    env.gain.exponentialRampToValueAtTime(0.0001, now + offset + 0.3);
    osc.connect(env);
    env.connect(master);
    osc.start(now + offset);
    osc.stop(now + offset + 0.32);
  });
}

function shouldAlert(event, prefs) {
  if (!prefs.enabled) return false;
  const sev = (event.severity || 'low').toLowerCase();
  const rank = SEVERITY_RANK[sev] ?? 0;
  const threshold = SEVERITY_RANK[prefs.threshold] ?? 3;
  if (rank < threshold) return false;
  if (prefs.categories.length > 0 && !prefs.categories.includes(event.category)) return false;
  return true;
}

/**
 * @param {Array} events - قائمة الأحداث الحالية من polling
 * @returns {{ prefs, setPrefs, lastAlertEvent, recentAlerts, mute, unmute, testSound }}
 */
export function useAudioAlert(events) {
  const [prefs, setPrefsState] = useState(loadAlertPrefs);
  const [lastAlertEvent, setLastAlertEvent] = useState(null);
  const [recentAlerts, setRecentAlerts] = useState([]);   // آخر 5 تنبيهات
  const seenIds = useRef(new Set());                       // لتفادي التكرار
  const lastPlayedAt = useRef(0);
  const initialized = useRef(false);

  // أول استدعاء — فقط امتلئ seenIds بالأحداث الحالية بدون تنبيه
  useEffect(() => {
    if (initialized.current || !Array.isArray(events) || events.length === 0) return;
    events.forEach(e => e?.id != null && seenIds.current.add(e.id));
    initialized.current = true;
  }, [events]);

  useEffect(() => {
    if (!initialized.current || !Array.isArray(events)) return;
    const fresh = events.filter(e => e?.id != null && !seenIds.current.has(e.id));
    if (fresh.length === 0) return;

    fresh.forEach(e => seenIds.current.add(e.id));

    const triggers = fresh.filter(e => shouldAlert(e, prefs));
    if (triggers.length === 0) return;

    // throttle
    const nowMs = Date.now();
    const minGapMs = (prefs.throttleSeconds || 0) * 1000;
    if (nowMs - lastPlayedAt.current < minGapMs) return;
    lastPlayedAt.current = nowMs;

    // الأكثر خطورة من بين الجديد
    triggers.sort((a, b) => (SEVERITY_RANK[b.severity] || 0) - (SEVERITY_RANK[a.severity] || 0));
    const top = triggers[0];

    playAlarmTone();
    setLastAlertEvent(top);
    setRecentAlerts(prev => [{ ...top, _alertedAt: new Date().toISOString() }, ...prev].slice(0, 5));

    if (prefs.desktopNotifications && 'Notification' in window && Notification.permission === 'granted') {
      try {
        new Notification('🚨 رصد — خبر هام', {
          body: top.title || '',
          icon: '/favicon.ico',
          tag: `rsd-${top.id}`,
        });
      } catch {}
    }
  }, [events, prefs]);

  const setPrefs = useCallback((updater) => {
    setPrefsState(prev => {
      const next = typeof updater === 'function' ? updater(prev) : { ...prev, ...updater };
      saveAlertPrefs(next);
      return next;
    });
  }, []);

  const mute = useCallback(() => setPrefs({ enabled: false }), [setPrefs]);
  const unmute = useCallback(() => setPrefs({ enabled: true }), [setPrefs]);
  const testSound = useCallback(() => playAlarmTone(), []);
  const clearRecent = useCallback(() => setRecentAlerts([]), []);

  const requestDesktopPermission = useCallback(async () => {
    if (!('Notification' in window)) return false;
    if (Notification.permission === 'granted') return true;
    const result = await Notification.requestPermission();
    return result === 'granted';
  }, []);

  return {
    prefs,
    setPrefs,
    lastAlertEvent,
    recentAlerts,
    clearRecent,
    mute,
    unmute,
    testSound,
    requestDesktopPermission,
  };
}
