# المساهمة في رصد | Contributing to Rasad

شكراً لاهتمامك بالمساهمة! هذا الدليل يشرح كيفية إعداد البيئة وتشغيل الفحوص.

Thanks for your interest in contributing! This guide covers environment setup
and running the checks.

## الإعداد | Setup

```bash
git clone https://github.com/abosalehg-ui/rsd.git
cd rsd
cp .env.example .env      # ثم املأ مفاتيحك (راجع التعليقات داخل الملف)
```

### الخلفية | Backend (Python 3.10+)

```bash
cd backend
pip install -r requirements-dev.txt   # يشمل requirements.txt + أدوات الاختبار
uvicorn app.main:app --reload --port 8000
```

### الواجهة | Frontend (Node 18+)

```bash
cd frontend
npm install
npm run dev
```

## الفحوص قبل فتح PR | Checks before opening a PR

يجب أن تمرّ كل هذه محلياً (وهي نفسها التي يشغّلها CI):

All of the following must pass locally (CI runs the same):

```bash
# الخلفية | Backend
cd backend
ruff check app tests          # فحص الأسلوب
pytest                         # الاختبارات

# الواجهة | Frontend
cd frontend
npm run lint                   # eslint (0 تحذيرات)
npm test                       # vitest
npm run build                  # تأكيد نجاح البناء
```

## إرشادات الكود | Code guidelines

- **الأمن أولاً:** كل بيانات المصادر الخارجية غير موثوقة. عقّم أي رابط بـ
  `safeUrl` وأي نص يُحقن في `innerHTML` بـ `esc` (من `utils/security.js`).
- **الترجمة:** أي نص معروض للمستخدم يمرّ عبر `t()` — لا نصوص مضمّنة. أضف
  المفتاح إلى `locales/ar.json` و`locales/en.json` معاً.
- **الجامعون:** استخدم أدوات `processors/text_analysis.py` المشتركة للتصنيف
  والجغرافيا بدل تكرار المنطق، و`insert_event_if_new` لتفادي التكرار.
- **الرسائل:** رسائل commit وصفية. أنشئ فرعاً لكل تغيير ولا تدفع إلى `main`
  مباشرة.

## بنية المشروع | Project structure

```
backend/app/
  ├── api/          نقاط FastAPI (events, flights, iran, nuclear, infrastructure)
  ├── collectors/   جامعو المصادر (gdelt, news_api, rss_feeds, ucdp, adsb, iran_osint)
  ├── processors/   منطق مشترك (text_analysis)
  ├── models/       نماذج SQLAlchemy + الاحتفاظ بالبيانات
  ├── middleware/   ETag/Cache-Control
  ├── config.py     الإعدادات (pydantic-settings)
  └── scheduler.py  جدولة الجمع + التنظيف
frontend/src/
  ├── components/   مكوّنات الواجهة (Map, Stats, Iran, Layout, …)
  ├── hooks/        usePolling, useAudioAlert
  ├── utils/        api, constants, security
  └── i18n/         الترجمة (ar/en)
```
