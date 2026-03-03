/**
 * رصد - درج البث المباشر للقنوات الإخبارية
 * تلفاز صغير ينزلق من يمين الشاشة
 */
import React, { useState } from 'react';
import { Tv, X } from 'lucide-react';

// ===== قائمة القنوات =====
// مهم: استخدم صيغة embed فقط وليس watch
// الصيغة الصحيحة: https://www.youtube.com/embed/VIDEO_ID
// الصيغة الخاطئة: https://www.youtube.com/watch?v=VIDEO_ID
//
// لتحديث رابط قناة:
// 1. افتح يوتيوب وابحث عن البث المباشر للقناة
// 2. انسخ الـ VIDEO_ID من الرابط (الجزء بعد watch?v=)
// 3. ضعه هنا بصيغة: https://www.youtube.com/embed/VIDEO_ID
const CHANNELS = [
  {
    id: 'aljazeera',
    name: 'الجزيرة',
    icon: '\u{1F7E2}',
    embedUrl: 'https://www.youtube.com/embed/bNyUyrR0PHo',
  },
  {
    id: 'alarabiya',
    name: 'العربية',
    icon: '\u{1F7E0}',
    embedUrl: 'https://www.youtube.com/embed/n7eQejkXbnM',
  },
  {
    id: 'bbc_arabic',
    name: 'BBC عربي',
    icon: '\u{1F534}',
    embedUrl: 'https://www.youtube.com/embed/rJdP5Bo4kZs',
  },
];

export default function LiveTVDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [activeChannel, setActiveChannel] = useState(CHANNELS[0]);

  return (
    <>
      {/* ===== زر فتح الدرج ===== */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-64 right-0 z-[9999] flex items-center gap-1 bg-red-600 hover:bg-red-500 text-white pl-2.5 pr-1.5 py-2 rounded-l-lg shadow-lg transition-all group"
          title="البث المباشر"
        >
          <Tv className="w-4 h-4" />
          <span className="text-[9px] font-bold opacity-0 group-hover:opacity-100 transition-opacity">LIVE</span>
        </button>
      )}

      {/* ===== نافذة التلفاز الصغيرة ===== */}
      <div
        className={`fixed bottom-40 right-4 z-[9999] transition-all duration-300 ease-in-out ${
          isOpen
            ? 'opacity-100 scale-100 translate-x-0'
            : 'opacity-0 scale-90 translate-x-8 pointer-events-none'
        }`}
        style={{ width: '360px' }}
      >
        <div className="bg-[#0d1117] border border-[#1e293b] rounded-xl shadow-2xl overflow-hidden">
          {/* ===== الشريط العلوي ===== */}
          <div className="flex items-center justify-between px-3 py-1.5 bg-[#111827] border-b border-[#1e293b]">
            <div className="flex items-center gap-2">
              <Tv className="w-3.5 h-3.5 text-red-400" />
              <span className="text-xs font-bold text-white">{activeChannel.icon} {activeChannel.name}</span>
              <span className="text-[8px] bg-red-500 text-white px-1.5 py-0.5 rounded font-bold animate-pulse">
                LIVE
              </span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-0.5 rounded hover:bg-[#1e293b] text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* ===== مشغل الفيديو ===== */}
          <div className="bg-black" style={{ height: '200px' }}>
            <iframe
              key={activeChannel.id}
              src={activeChannel.embedUrl + '?autoplay=1&mute=0'}
              title={activeChannel.name}
              className="w-full h-full"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>

          {/* ===== أزرار القنوات ===== */}
          <div className="flex gap-1 px-2 py-1.5 bg-[#111827] border-t border-[#1e293b]">
            {CHANNELS.map((channel) => (
              <button
                key={channel.id}
                onClick={() => setActiveChannel(channel)}
                className={`flex-1 flex items-center justify-center gap-1 text-[10px] py-1 rounded transition-all ${
                  activeChannel.id === channel.id
                    ? 'bg-red-500/20 text-red-300 font-bold'
                    : 'bg-[#1e293b] text-slate-400 hover:text-white'
                }`}
              >
                <span>{channel.icon}</span>
                {channel.name}
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
