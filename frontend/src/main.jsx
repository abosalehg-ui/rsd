import React from 'react';
import ReactDOM from 'react-dom/client';
import { registerSW } from 'virtual:pwa-register';
import App from './App';
import './styles/index.css';
import './i18n';

// تسجيل Service Worker (v1.4) — autoUpdate يُفعّل النسخة الجديدة تلقائياً
// عند إطلاق Tauri (window.__TAURI__) أو في وضع dev نتخطّى التسجيل
if (!window.__TAURI__) {
  registerSW({
    immediate: true,
    onRegisterError(err) {
      console.warn('SW registration failed:', err);
    },
  });
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
