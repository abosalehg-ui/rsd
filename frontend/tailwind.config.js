/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // رموز الثيم المستخدمة فعلاً (bg-rasad-bg / rasad-panel / rasad-border).
        // حُذفت الرموز الدلالية غير المستخدمة (accent/danger/… كانت صفر استعمال).
        rasad: {
          bg: '#0a0e17',
          panel: '#111827',
          border: '#1e293b',
        },
      },
      fontFamily: {
        arabic: ['Tajawal', 'Cairo', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
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
