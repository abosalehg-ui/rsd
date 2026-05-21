import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// النشر على GitHub Pages تحت /<repo>/ — يمكن تجاوزه عبر VITE_BASE
const base = process.env.VITE_BASE || '/'

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three', 'globe.gl'],
          leaflet: ['leaflet', 'react-leaflet'],
          recharts: ['recharts'],
          i18n: ['i18next', 'react-i18next', 'i18next-browser-languagedetector'],
        },
      },
    },
  },
})
