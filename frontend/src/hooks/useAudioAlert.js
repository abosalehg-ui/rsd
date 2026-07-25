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
import i18n from '../i18n';

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

// نغمة "جرس" واحدة: أساس جيبي + توافقية ثُمانية خافتة للبريق، بغلاف جرسي ناعم.
// تُعطي إحساس تنبيه راقٍ (لا موجة مربّعة قاسية تُشبه ألعاب الريترو).
function playBell(ctx, dest, freq, offset, dur, peak) {
  const t = ctx.currentTime + offset;

  const env = ctx.createGain();
  env.gain.setValueAtTime(0.0001, t);
  env.gain.exponentialRampToValueAtTime(peak, t + 0.015);
  env.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  env.connect(dest);

  const o1 = ctx.createOscillator();
  o1.type = 'sine';
  o1.frequency.setValueAtTime(freq, t);
  o1.connect(env);
  o1.start(t);
  o1.stop(t + dur + 0.05);

  // توافقية علوية خافتة (بريق الجرس)
  const o2 = ctx.createOscillator();
  o2.type = 'triangle';
  o2.frequency.setValueAtTime(freq * 2, t);
  const g2 = ctx.createGain();
  g2.gain.setValueAtTime(0.0001, t);
  g2.gain.exponentialRampToValueAtTime(peak * 0.22, t + 0.015);
  g2.gain.exponentialRampToValueAtTime(0.0001, t + dur * 0.55);
  o2.connect(g2);
  g2.connect(dest);
  o2.start(t);
  o2.stop(t + dur);
}

function playAlarmTone() {
  const ctx = ensureCtx();
  if (!ctx) return;

  const now = ctx.currentTime;

  // غلاف رئيسي ناعم → مرشّح تمرير منخفض (دفء، يزيل الحدّة) → الخرج
  const master = ctx.createGain();
  master.gain.setValueAtTime(0.0001, now);
  master.gain.exponentialRampToValueAtTime(0.6, now + 0.01);
  master.gain.exponentialRampToValueAtTime(0.0001, now + 2.0);

  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass';
  lp.frequency.setValueAtTime(5000, now);
  lp.Q.value = 0.6;

  master.connect(lp);
  lp.connect(ctx.destination);

  // موتيف تنبيه تصاعدي راقٍ (ثلاثي نوتة من سُلّم دو الكبير: G5 → C6 → E6)
  playBell(ctx, master, 783.99, 0.0, 0.55, 0.45);   // G5
  playBell(ctx, master, 1046.5, 0.17, 0.55, 0.45);  // C6
  playBell(ctx, master, 1318.51, 0.34, 1.25, 0.55); // E6 — نوتة الحلّ، أطول رنيناً
}

/** هل يستحق هذا الحدث تنبيهاً وفق التفضيلات؟ (مُصدَّر للاختبار) */
export function shouldAlert(event, prefs) {
  if (!prefs.enabled) return false;
  const sev = (event.severity || 'low').toLowerCase();
  const rank = SEVERITY_RANK[sev] ?? 0;
  const threshold = SEVERITY_RANK[prefs.threshold] ?? 3;
  if (rank < threshold) return false;
  if (prefs.categories.length > 0 && !prefs.categories.includes(event.category)) return false;
  return true;
}

// سقف حجم مجموعة المعرّفات المرئية — الجلسات الطويلة كانت تُراكم كل معرّف
// شوهد منذ الإقلاع بلا حدّ. عند التجاوز نُبقي الأحدث فقط.
const MAX_SEEN_IDS = 2000;

function rememberSeen(seen, ids) {
  ids.forEach(id => seen.add(id));
  if (seen.size > MAX_SEEN_IDS) {
    // Set يحفظ ترتيب الإدراج — نُسقط الأقدم
    const excess = seen.size - MAX_SEEN_IDS;
    let dropped = 0;
    for (const id of seen) {
      if (dropped >= excess) break;
      seen.delete(id);
      dropped += 1;
    }
  }
}

/**
 * @param {Array} events - قائمة الأحداث الحالية من polling
 * @param {Object} filters - الفلاتر الفعّالة؛ تغيّرها يعيد ضبط خط الأساس
 * @returns {{ prefs, setPrefs, lastAlertEvent, recentAlerts, mute, unmute, testSound }}
 */
export function useAudioAlert(events, filters) {
  const [prefs, setPrefsState] = useState(loadAlertPrefs);
  const [lastAlertEvent, setLastAlertEvent] = useState(null);
  const [recentAlerts, setRecentAlerts] = useState([]);   // آخر 5 تنبيهات
  const seenIds = useRef(new Set());                       // لتفادي التكرار
  const lastPlayedAt = useRef(0);
  const initialized = useRef(false);

  // تغيير الفلاتر يجلب مجموعة أحداث مختلفة كلياً — أحداث قديمة لم تكن ضمن
  // النتيجة السابقة تبدو "جديدة" فتُطلق إنذاراً كاذباً. نعيد ضبط خط الأساس.
  // يُعلَن أولاً كي يعمل قبل تأثير خط الأساس أدناه (التأثيرات تُنفَّذ بالترتيب).
  const filterKey = JSON.stringify(filters ?? {});
  useEffect(() => {
    initialized.current = false;
  }, [filterKey]);

  // أول استدعاء (أو بعد تغيير فلتر) — امتلئ seenIds بالحالي بدون تنبيه
  useEffect(() => {
    if (initialized.current || !Array.isArray(events) || events.length === 0) return;
    rememberSeen(seenIds.current, events.filter(e => e?.id != null).map(e => e.id));
    initialized.current = true;
  }, [events]);

  useEffect(() => {
    if (!initialized.current || !Array.isArray(events)) return;
    const fresh = events.filter(e => e?.id != null && !seenIds.current.has(e.id));
    if (fresh.length === 0) return;

    rememberSeen(seenIds.current, fresh.map(e => e.id));

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
        new Notification(i18n.t('alerts.notificationTitle'), {
          body: top.title || '',
          icon: '/favicon.ico',
          tag: `rsd-${top.id}`,
        });
      } catch { /* منع الإشعار — تجاهل */ }
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
