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
    },
  },
  plugins: [],
}
