/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // رموز الثيم المستخدمة فعلاً (bg-rasad-bg / rasad-panel / rasad-border).
        // حُذفت الرموز الدلالية غير المستخدمة (accent/danger/… كانت صفر استعمال).
        // أرضية لوحة أجهزة قياس: رمادي-أزرق داكن تتّسق معه بلاطات الخريطة الداكنة
        rasad: {
          bg: '#0b1016',
          panel: '#121a22',
          raised: '#18222c',
          border: '#22303c',
        },
        // لونا مجالي الرصد: أصفر رمز الإشعاع للنووي، وأرجواني علامات الإشعاع
        // للإشعاعي. لا يُستعملان لأي غرض آخر في الواجهة.
        hazard: { DEFAULT: '#f2c230', soft: '#f7dc7a', dim: '#f2c23026' },
        radiant: { DEFAULT: '#e0609c', soft: '#f0a3c6' },
      },
      fontFamily: {
        // IBM Plex: عائلة هندسية صُمّمت للواجهات التقنية، وخطها العربي مُصمَّم
        // معها لا مُلحقًا بها — أنسب لمنصة رقابية من الخط المستدير السابق.
        arabic: ['"IBM Plex Sans Arabic"', 'Tajawal', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // مقاس النص الثانوي الوحيد. كانت الواجهة تستعمل `text-[10px]`
        // و`text-[11px]` بقيم عشوائية في 47 موضعًا، وأصغرها دون الحدّ المقروء
        // على خلفية داكنة. رمز واحد يرفع الأرضية ويجعل التغيير لاحقًا بموضع واحد.
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],   // 11px
      },
    },
  },
  plugins: [],
}
