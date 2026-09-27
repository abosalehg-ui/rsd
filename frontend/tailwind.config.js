import { THEME } from './src/utils/constants.js';

/** متغيّرات CSS (`--rsd-*`) في :root من THEME نفسه — لـ index.css. */
const cssVars = ({ addBase }) => addBase({
  ':root': Object.fromEntries(
    Object.entries(THEME).map(([key, value]) => [
      `--rsd-${key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`, value,
    ]),
  ),
});

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // رموز الثيم (bg-rasad-bg / rasad-panel / rasad-raised / rasad-border)
        // من `utils/constants.js::THEME` — المصدر الواحد للواجهة والقوالب الخام.
        rasad: {
          bg: THEME.bg,
          panel: THEME.panel,
          raised: THEME.raised,
          border: THEME.border,
        },
        // لونا مجالي الرصد: أصفر رمز الإشعاع للنووي، وأرجواني علامات الإشعاع
        // للإشعاعي. لا يُستعملان لأي غرض آخر في الواجهة.
        hazard: { DEFAULT: THEME.hazard, soft: THEME.hazardSoft, dim: `${THEME.hazard}26` },
        radiant: { DEFAULT: THEME.radiant, soft: THEME.radiantSoft },
      },
      fontFamily: {
        // IBM Plex: عائلة هندسية صُمّمت للواجهات التقنية، وخطها العربي مُصمَّم
        // معها لا مُلحقًا بها — أنسب لمنصة رقابية من الخط المستدير.
        arabic: ['"IBM Plex Sans Arabic"', 'Tajawal', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // مقاس النص الثانوي الوحيد (11px): رمز واحد بدل قيم عشوائية، وأرضية
        // مقروءة على خلفية داكنة، وتغييره لاحقًا بموضع واحد.
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
    },
  },
  plugins: [cssVars],
};
