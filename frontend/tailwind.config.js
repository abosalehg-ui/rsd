/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        rasad: {
          bg: '#0a0e17',
          panel: '#111827',
          border: '#1e293b',
          accent: '#22d3ee',
          danger: '#ef4444',
          warning: '#f59e0b',
          success: '#10b981',
          nuclear: '#eab308',
          diplomatic: '#3b82f6',
          humanitarian: '#f97316',
          military: '#ef4444',
          economic: '#10b981',
        },
      },
      fontFamily: {
        arabic: ['Tajawal', 'Cairo', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'flash': 'flash 1.5s ease-in-out infinite',
      },
      keyframes: {
        flash: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.3 },
        },
      },
    },
  },
  plugins: [],
}
