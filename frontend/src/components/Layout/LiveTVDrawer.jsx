/**
 * رصد - نافذة البث المباشر العائمة
 *
 * قابلة للسحب بالماوس **واللمس** (كانت mousemove فقط فتتعذّر على الجوال)،
 * وتتحوّل على الشاشات الصغيرة إلى لوحة سفلية بعرض كامل بدل صندوق 360px
 * مثبّت على إحداثيات تُحسب من عرض النافذة لحظة التركيب.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Tv, X } from 'lucide-react';

const CHANNELS = [
  { id: 'aljazeera', icon: '\u{1F7E2}', embedUrl: 'https://www.youtube-nocookie.com/embed/bNyUyrR0PHo' },
  { id: 'alarabiya', icon: '\u{1F7E0}', embedUrl: 'https://www.youtube-nocookie.com/embed/n7eQejkXbnM' },
  { id: 'bbc_arabic', icon: '\u{1F534}', embedUrl: 'https://www.youtube-nocookie.com/embed/O1pGmVtj2Y8' },
];

const PANEL_W = 360;
const PANEL_H = 280;
const MOBILE_QUERY = '(max-width: 767px)';

export default function LiveTVDrawer() {
  const { t, i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [activeChannel, setActiveChannel] = useState(CHANNELS[0]);
  const [isMobile, setIsMobile] = useState(false);
  // null = لم يُحسب بعد؛ يُحسب عند أول فتح فلا نقرأ innerWidth أثناء التركيب
  const [position, setPosition] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY);
    const apply = () => setIsMobile(mq.matches);
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, []);

  const clamp = useCallback((x, y) => ({
    x: Math.max(0, Math.min(window.innerWidth - PANEL_W, x)),
    y: Math.max(0, Math.min(window.innerHeight - PANEL_H, y)),
  }), []);

  // تُفتح النافذة على جهة الخريطة (يمين في RTL، يسار في LTR) كي لا تغطي
  // حاوية الأحداث — كانت مثبّتة على اليمين فتحجب اللوحة في الوضع الإنجليزي.
  const open = useCallback(() => {
    const mapSideX = i18n.dir() === 'rtl' ? window.innerWidth - PANEL_W - 20 : 20;
    setPosition(clamp(mapSideX, window.innerHeight - PANEL_H - 40));
    setIsOpen(true);
  }, [clamp, i18n]);

  // نقطة الحدث من الماوس أو اللمس
  const pointOf = (e) => (e.touches?.[0]
    ? { x: e.touches[0].clientX, y: e.touches[0].clientY }
    : { x: e.clientX, y: e.clientY });

  const startDrag = useCallback((e) => {
    if (isMobile || !e.target.closest('.drag-handle')) return;
    const p = pointOf(e);
    dragOffset.current = { x: p.x - (position?.x || 0), y: p.y - (position?.y || 0) };
    setIsDragging(true);
    if (e.cancelable) e.preventDefault();
  }, [isMobile, position]);

  useEffect(() => {
    if (!isDragging) return undefined;
    const move = (e) => {
      const p = pointOf(e);
      setPosition(clamp(p.x - dragOffset.current.x, p.y - dragOffset.current.y));
      if (e.cancelable) e.preventDefault();
    };
    const end = () => setIsDragging(false);
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', end);
    window.addEventListener('touchmove', move, { passive: false });
    window.addEventListener('touchend', end);
    window.addEventListener('touchcancel', end);
    return () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', end);
      window.removeEventListener('touchmove', move);
      window.removeEventListener('touchend', end);
      window.removeEventListener('touchcancel', end);
    };
  }, [isDragging, clamp]);

  // يبقى ضمن الشاشة عند تغيّر حجم النافذة
  useEffect(() => {
    if (isMobile) return undefined;
    const onResize = () => setPosition(prev => (prev ? clamp(prev.x, prev.y) : prev));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [isMobile, clamp]);

  // إغلاق بمفتاح Escape
  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setIsOpen(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen]);

  const floatingStyle = isMobile || !position
    ? undefined
    : {
      width: `${PANEL_W}px`,
      // `left` فيزيائي (لا insetInlineStart المنطقي): العنصر يُسحب بإحداثيات
      // مؤشر فيزيائية أصلها اليسار، فالخلط مع خاصية منطقية كان يعكس السحب في RTL.
      left: `${position.x}px`,
      top: `${position.y}px`,
      cursor: isDragging ? 'grabbing' : 'default',
    };

  return (
    <>
      {/* ===== زر فتح النافذة =====
          start-0 = حافة الخريطة في الاتجاهين (يمين بالعربية، يسار بالإنجليزية)
          — كان end-0 فيلتصق بحافة حاوية الأحداث ويغطي عناصرها في اللغتين. */}
      {!isOpen && (
        <button
          onClick={open}
          className="fixed bottom-24 md:bottom-64 start-0 z-[9999] flex items-center gap-1 bg-red-600 hover:bg-red-500 text-white ps-1.5 pe-2.5 py-2 rounded-e-lg shadow-lg transition-all group focus-ring"
          title={t('tv.open')}
          aria-label={t('tv.open')}
        >
          <Tv className="w-4 h-4" aria-hidden="true" />
          <span className="text-2xs font-bold">LIVE</span>
        </button>
      )}

      {/* ===== النافذة (عائمة على سطح المكتب، لوحة سفلية على الجوال) ===== */}
      {isOpen && (
        <div
          className={isMobile ? 'fixed z-[9999] inset-x-0 bottom-0 pb-[env(safe-area-inset-bottom)]' : 'fixed z-[9999]'}
          style={floatingStyle}
          onMouseDown={startDrag}
          onTouchStart={startDrag}
          role="dialog"
          aria-label={t('tv.title')}
        >
          <div className="bg-rasad-bg border border-rasad-border rounded-t-xl md:rounded-xl shadow-2xl overflow-hidden">
            {/* الشريط العلوي — منطقة السحب على سطح المكتب */}
            <div className={`drag-handle flex items-center justify-between px-3 py-1.5 bg-rasad-panel border-b border-rasad-border select-none ${isMobile ? '' : 'cursor-grab active:cursor-grabbing'}`}>
              <div className="flex items-center gap-2">
                <Tv className="w-3.5 h-3.5 text-red-300" aria-hidden="true" />
                <span className="text-xs font-bold text-white">
                  {activeChannel.icon} {t(`tv.channels.${activeChannel.id}`)}
                </span>
                <span className="text-2xs bg-red-600 text-white px-1.5 py-0.5 rounded font-bold animate-pulse">LIVE</span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                aria-label={t('tv.close')}
                className="p-1 rounded hover:bg-rasad-border text-slate-300 hover:text-white transition-colors focus-ring"
              >
                <X className="w-3.5 h-3.5" aria-hidden="true" />
              </button>
            </div>

            {/* مشغل الفيديو — يُركَّب فقط عند الفتح كي لا يبقى البث يستهلك
                الشبكة/المعالج في الخلفية عند الإغلاق (PERF-2).
                mute=1 لأن المتصفحات تحجب التشغيل التلقائي بصوت. */}
            <div className="bg-black h-[200px]">
              <iframe
                key={activeChannel.id}
                src={`${activeChannel.embedUrl}?autoplay=1&mute=1`}
                title={t(`tv.channels.${activeChannel.id}`)}
                className="w-full h-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>

            {/* أزرار القنوات */}
            <div className="flex gap-1 px-2 py-1.5 bg-rasad-panel border-t border-rasad-border">
              {CHANNELS.map((channel) => (
                <button
                  key={channel.id}
                  onClick={() => setActiveChannel(channel)}
                  aria-pressed={activeChannel.id === channel.id}
                  className={`flex-1 flex items-center justify-center gap-1 text-xs py-1.5 rounded transition-all focus-ring ${
                    activeChannel.id === channel.id
                      ? 'bg-red-500/20 text-red-200 font-bold'
                      : 'bg-rasad-border text-slate-300 hover:text-white'
                  }`}
                >
                  <span aria-hidden="true">{channel.icon}</span>
                  {t(`tv.channels.${channel.id}`)}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
