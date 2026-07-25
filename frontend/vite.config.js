import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// النشر على GitHub Pages تحت /<repo>/ — يمكن تجاوزه عبر VITE_BASE
const base = process.env.VITE_BASE || '/'

export default defineConfig({
  base,
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png'],
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico,woff2}'],
        // عدم تخزين Three.js المؤقت لأنه ضخم (~2.4MB) — يُحمَّل عند الحاجة فقط
        globIgnores: ['**/three-*.js'],
        runtimeCaching: [
          {
            // خطوط Google (CSS) — كي تعمل الطباعة دون اتصال
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'rsd-google-fonts-css',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // ملفات الخطوط نفسها (woff2) من gstatic
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'rsd-google-fonts-files',
              expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 365 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // طبقة بلاطات OpenStreetMap / CartoDB — تخزين مؤقت لمدة شهر
            urlPattern: /^https:\/\/[a-d]\.basemaps\.cartocdn\.com\/.*\.png/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'rsd-tiles',
              expiration: { maxEntries: 500, maxAgeSeconds: 60 * 60 * 24 * 30 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // الكرة الأرضية: nightside + topology من unpkg
            urlPattern: /^https:\/\/unpkg\.com\/three-globe\/.*/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'rsd-globe-textures',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
          {
            // مكالمات API — Stale-While-Revalidate لتجربة سريعة + بيانات حديثة
            urlPattern: /\/api\/.*/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'rsd-api',
              expiration: { maxEntries: 100, maxAgeSeconds: 60 * 5 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      manifest: {
        name: 'رصد — Rsd',
        short_name: 'رصد',
        description: 'منصة استخبارات المصادر المفتوحة للشرق الأوسط',
        lang: 'ar',
        dir: 'rtl',
        theme_color: '#0d1117',
        background_color: '#0a0e17',
        display: 'standalone',
        orientation: 'any',
        start_url: '.',
        scope: '.',
        icons: [
          { src: 'pwa-192x192.svg', sizes: '192x192', type: 'image/svg+xml', purpose: 'any' },
          { src: 'pwa-512x512.svg', sizes: '512x512', type: 'image/svg+xml', purpose: 'any maskable' },
        ],
      },
    }),
  ],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      // داخل docker compose الخلفية في حاوية أخرى، فـ localhost يشير للواجهة
      // نفسها ويفشل الوكيل. يضبط compose المتغيّر إلى http://backend:8000.
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // ملاحظة: react-leaflet و recharts أُزيلا — لم يكونا مستوردَين في أي
        // مكان، وكان recharts يُنتج chunk فارغاً بحجم 0.06 kB.
        manualChunks: {
          three: ['three', 'globe.gl'],
          leaflet: ['leaflet'],
          i18n: ['i18next', 'react-i18next', 'i18next-browser-languagedetector'],
        },
      },
    },
  },
})
