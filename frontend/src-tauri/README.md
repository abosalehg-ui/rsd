# رصد — Tauri Desktop

تطبيق سطح المكتب الرسمي لـ **رصد**، مبني على [Tauri 2](https://tauri.app/) و WebView.

## المتطلبات

- Rust 1.77+ (`rustup install stable`)
- Node 18+
- بحسب نظام التشغيل:
  - **Linux**: `webkit2gtk-4.1`, `libayatana-appindicator3-1`, `librsvg2-dev`
  - **macOS**: Xcode Command Line Tools
  - **Windows**: WebView2 (مثبَّت افتراضياً على Windows 11)

## التطوير

من جذر المشروع (`/home/user/rsd/frontend`):

```bash
# تثبيت Tauri CLI (مرة واحدة)
cargo install tauri-cli --version "^2.0"

# تشغيل وضع التطوير (يفتح نافذة WebView + يعيد التحميل التلقائي)
cargo tauri dev

# بناء حزمة الإنتاج (.dmg / .deb / .msi / .AppImage)
cargo tauri build
```

> 💡 `cargo tauri dev` يُشغّل `npm run dev` تلقائياً ويفتح النافذة عند توفّر `localhost:3000`.

## ملاحظات

- ملف `tauri.conf.json` يضبط CSP يسمح بالاتصال بـ `http://localhost:8000` (الباك إند المحلي) وطبقات الخرائط (CartoDB tiles + unpkg three-globe textures).
- Service Worker معطّل في وضع Tauri عبر فحص `window.__TAURI__` في `src/main.jsx` لأن WebView له آلية تخزين منفصلة.
- مجلد `icons/` يحتاج إيقونات حقيقية للحزم النهائية — استعمل `cargo tauri icon path/to/source.png` لتوليدها تلقائياً.

## الحالة (v1.4)

scaffolding فقط — لم يُختبر فعلياً في هذه البيئة السحابية لعدم توفّر Rust toolchain. ابنِه محلياً للتجربة.
