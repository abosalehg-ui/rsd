<div align="center">

# 🛰️ رصد (Rsd) v1.2

### منصة استخبارات المصادر المفتوحة للشرق الأوسط
**Open Source Intelligence (OSINT) Dashboard for the Middle East**

![Version](https://img.shields.io/badge/version-1.2.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Docker%20%7C%20Pages-lightgrey)
![Python](https://img.shields.io/badge/Python-3.10+-yellow)
![React](https://img.shields.io/badge/React-18-61DAFB)
![Deploy](https://img.shields.io/badge/Deploy-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

<br>

<img src="https://img.shields.io/badge/🔴_LIVE-البث_المباشر-red?style=for-the-badge" alt="Live"/>
<img src="https://img.shields.io/badge/🗺️_MAP-خريطة_تفاعلية-blue?style=for-the-badge" alt="Map"/>
<img src="https://img.shields.io/badge/✈️_FLIGHTS-تتبع_الطيران-orange?style=for-the-badge" alt="Flights"/>
<img src="https://img.shields.io/badge/🇮🇷_IRAN-متابعة_إيران_OSINT-darkred?style=for-the-badge" alt="Iran OSINT"/>
<img src="https://img.shields.io/badge/☢️_NUCLEAR-منشآت_نووية-yellow?style=for-the-badge" alt="Nuclear"/>
<img src="https://img.shields.io/badge/🔔_ALERTS-تنبيهات_صوتية-purple?style=for-the-badge" alt="Alerts"/>

</div>

---

## 📋 نظرة عامة | Overview

**رصد** هي لوحة تحكم شخصية لرصد الأحداث العسكرية والأمنية والجيوسياسية في الشرق الأوسط لحظياً. تجمع البيانات من مصادر متعددة وتعرضها على خريطة تفاعلية مع تصنيف ذكي.

**Rsd** is a personal OSINT dashboard for real-time monitoring of military, security, and geopolitical events across the Middle East. It aggregates data from multiple sources and displays them on an interactive map with intelligent classification.

---

## ⚡ التشغيل السريع | Quick Start

### 1) استنساخ المشروع | Clone

```bash
git clone https://github.com/abosalehg-ui/rsd.git
cd rsd
```

> 💡 لا توجد لديك Git؟ ثبّتها من [git-scm.com](https://git-scm.com/downloads).
>
> لتحديث نسختك لاحقًا: `git pull origin main`

### 2) التشغيل بـ Docker (الأسهل) | Run with Docker

```bash
docker compose up -d
# الواجهة: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### 3) أو تشغيل محلي للتطوير | Or local dev

```bash
# نافذة طرفية 1 — Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# نافذة طرفية 2 — Frontend
cd frontend
npm install
npm run dev
```

افتح <http://localhost:3000>.

---

## 📸 لقطات الشاشة | Screenshots

<div align="center">

| الواجهة الرئيسية | الخريطة والأحداث |
|:---:|:---:|
| ![الواجهة الرئيسية](assets/screenshots/rsd1.png) | ![الخريطة والأحداث](assets/screenshots/rsd2.png) |

</div>

---

## ✨ الميزات | Features

| الميزة | الوصف |
|--------|-------|
| 🗺️ **خريطة تفاعلية** | عرض الأحداث على خريطة Leaflet مع تجميع ذكي للعلامات وتصنيف بالألوان |
| 📰 **شريط أخبار عاجلة** | تدفق مباشر للأخبار مع فلاتر حسب التصنيف والخطورة والدولة |
| ✈️ **تتبع الطيران** | رصد الطائرات فوق المنطقة عبر ADS-B مع تمييز الطيران العسكري |
| ⏳ **خط زمني** | عرض الأحداث زمنياً مع إمكانية التصفية |
| 📊 **إحصائيات** | مؤشر التصعيد، توزيع حسب الدولة والتصنيف والمصدر |
| 📺 **البث المباشر** | مشغل مدمج للقنوات الإخبارية (الجزيرة، العربية، BBC) |
| 🔄 **تحديث تلقائي** | جلب الأخبار تلقائياً مع مؤشر "آخر فحص" |
| 🇮🇷 **متابعة إيران OSINT** | طبقة مخصصة لرصد الضربات والإطلاقات والتحركات الإيرانية مع تصنيف الثقة |
| ☢️ **منشآت نووية** *(جديد v1.2)* | علامات للمفاعلات ومراكز التخصيب والأبحاث في المنطقة + Popup بالتفاصيل والسعة |
| 🔔 **تنبيهات صوتية** *(جديد v1.2)* | صوت إنذار في المتصفح عند ورود خبر هام، مع عتبة خطورة وتصنيفات قابلة للتخصيص |
| 🚀 **نشر تلقائي** *(جديد v1.2)* | GitHub Actions workflow ينشر الواجهة إلى GitHub Pages عند كل push |

---

## ☢️ المنشآت النووية *(جديد في v1.2)*

طبقة جديدة على الخريطة تعرض **24+ منشأة نووية** في المنطقة وما حولها، مبنية من بيانات IAEA PRIS العامة:

- **محطات قوة**: بوشهر، براكة، آكويو، الضبعة، تارابور، شاشمة، روستوف …
- **مراكز تخصيب**: نطنز، فوردو
- **مفاعلات أبحاث**: طهران، سوريك، المركز الأردني JRTR
- **معامل تحويل وماء ثقيل**: أصفهان، آراك
- **مواقع حساسة**: ديمونا (إسرائيل)، زابوريجيا (تحت الاحتلال)

كل علامة تعرض: الاسم بالعربي والإنجليزي، نوع المفاعل، السعة (MW)، الحالة (عاملة/قيد الإنشاء/متوقفة)، المُشغّل، تاريخ بدء التشغيل. يمكن إخفاء/إظهار الطبقة من لوحة "طبقات" أسفل الخريطة.

> 🔄 لإضافة منشأة جديدة: حرّر `backend/app/data/nuclear_facilities.json`.

---

## 🔔 التنبيهات الصوتية *(جديد في v1.2)*

نظام تنبيه مدمج يُنبّهك صوتيًا عند ورود أخبار مهمة دون الحاجة لمتابعة الشاشة باستمرار.

- **صوت إنذار** يولّد عبر Web Audio API (لا يحتاج ملفات خارجية، يعمل offline)
- **عتبة خطورة قابلة للتخصيص**: منخفض / متوسط / مرتفع / حرج
- **تصفية بالتصنيفات**: عسكري، نووي، دبلوماسي، إنساني، اقتصادي
- **فاصل تكرار قابل للضبط** (5-120 ثانية) لتفادي إزعاج الإنذارات المتكررة
- **إشعارات سطح المكتب اختيارية** (Notification API)
- **سجل آخر 5 تنبيهات** قابل للضغط للانتقال للحدث

افتح إعدادات التنبيهات من أيقونة 🔔 في الشريط العلوي.

---

## 🇮🇷 متابعة إيران OSINT *(جديد في v1.1)*

ميزة مستوحاة من [iranstrikemap.com](https://iranstrikemap.com) و [live-iran-map.com](https://live-iran-map.com) تضيف طبقة متخصصة لمتابعة الأحداث الإيرانية.

### نظام تصنيف الثقة

| المستوى | الرمز | المعنى | أمثلة المصادر |
|---------|-------|--------|--------------|
| **HIGH** | 🟢 | موثوق - مصادر OSINT متخصصة | ISW, Calibre Obscura, The Drive War Zone |
| **MEDIUM** | 🟡 | متوسط - صحافة دفاعية | Breaking Defense, Defense One, Iran International |
| **LOW** | 🔵 | غير مؤكد - أخبار عامة | Reuters, BBC |

### أنواع الأحداث المرصودة

| النوع | الأيقونة | الوصف |
|-------|----------|-------|
| **strike** | 💥 | ضربات جوية وهجمات |
| **launch** | 🚀 | إطلاقات صاروخية واختبارات |
| **movement** | 🪖 | تحركات عسكرية ومناورات |
| **nuclear** | ☢️ | أحداث نووية وتخصيب |
| **diplomatic** | 🤝 | مفاوضات وعقوبات |

### متابعة القادة الإيرانيين

يتابع النظام آخر أخبار **10 قياديين إيرانيين** تلقائياً:

| القائد | المنصب |
|--------|--------|
| علي خامنئي | المرشد الأعلى |
| مسعود بزشكيان | الرئيس |
| حسين سلامي | قائد الحرس الثوري |
| محمد باقري | رئيس الأركان |
| أمير علي حاجي زاده | قائد الفضاء IRGC |
| عباس عراقچي | وزير الخارجية |
| إسماعيل قاآني | قائد قوة القدس |
| محمد إسلامي | رئيس منظمة الطاقة الذرية |
| عزيز نصيرزاده | قائد سلاح الجو |
| علي شمخاني | مستشار المرشد |

### مصادر Iran OSINT

<details>
<summary>اضغط للعرض</summary>

**HIGH CONFIDENCE:**
- ISW - Institute for the Study of War
- Calibre Obscura
- The Drive - War Zone
- OSINTdefender

**MEDIUM CONFIDENCE:**
- Breaking Defense
- Defense One
- Al-Monitor
- Iran International

**LOW CONFIDENCE:**
- Reuters - Middle East
- BBC - Middle East

</details>

---

## 🏷️ التصنيفات | Categories

| التصنيف | الأيقونة | الوصف |
|---------|----------|-------|
| عسكري | 💥 | هجمات، غارات، عمليات عسكرية |
| دبلوماسي | 🤝 | مفاوضات، هدنات، قمم |
| إنساني | 🆘 | أزمات، لاجئين، مساعدات |
| نووي | ☣️ | تخصيب، وكالة الطاقة الذرية |
| اقتصادي | 📊 | عقوبات، نفط، تجارة |
| عام | 📰 | أخبار عامة |

---

## 📡 مصادر البيانات | Data Sources

| المصدر | الوصف | التحديث |
|--------|-------|---------|
| **GDELT** | أحداث عالمية من تحليل الأخبار | كل 15 دقيقة |
| **NewsAPI** | أخبار من مصادر عالمية متعددة | كل 10 دقائق |
| **RSS Feeds** | خلاصات عربية ودولية (25+ مصدر) | كل دقيقتين |
| **Google Alerts** | تنبيهات مخصصة للمنطقة | كل دقيقتين |
| **UCDP** | بيانات النزاعات المسلحة (جامعة أوبسالا) | يومياً |
| **ADS-B** | تتبع الطيران (adsb.lol) | كل 30 ثانية |
| **Iran OSINT** | مصادر OSINT متخصصة بإيران والشرق الأوسط | كل 5 دقائق |

### 📰 مصادر RSS المدعومة

<details>
<summary>اضغط للعرض</summary>

**أخبار عربية:**
- الجزيرة (عربي + English)
- العربية
- BBC Arabic / Middle East
- France24 Arabic
- Sky News Arabia
- RT Arabic

**تحليلات دولية:**
- Al-Monitor
- Defense One
- War on the Rocks
- The Drive - War Zone
- Breaking Defense

**أخبار نووية:**
- World Nuclear News
- IAEA News
- Arms Control Association

**تنبيهات Google Alerts:**
- Middle East Airstrikes
- Gaza Yemen Syria
- Houthi / حوثي
- Red Sea
- Iran Nuclear / تخصيب يورانيوم
- Ceasefire / هدنة
- Humanitarian Crisis

</details>

---

## 🚀 التشغيل | Getting Started

### المتطلبات | Requirements

- **Python** 3.10+
- **Node.js** 18+
- **مفتاح NewsAPI** (اختياري) - [احصل على مفتاح مجاني](https://newsapi.org/)

### الطريقة 1: تشغيل سريع (Windows)

```batch
# انقر مرتين على:
start-rasad.bat
```

سيقوم السكربت بـ:
1. ✅ فحص Python و Node.js
2. ✅ تثبيت المكتبات تلقائياً
3. ✅ تشغيل Backend و Frontend
4. ✅ فتح المتصفح على http://localhost:3000

### الطريقة 2: Docker Compose

```bash
# 1. أنشئ ملف .env
cp .env.example .env
nano .env  # أضف NEWSAPI_KEY=xxxxx

# 2. شغّل
docker-compose up -d

# 3. افتح المتصفح
# الواجهة: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### الطريقة 3: تشغيل يدوي

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (terminal جديد)
cd frontend
npm install
npm run dev
```

---

## 📁 هيكل المشروع | Project Structure

```
rasad/
├── 📂 backend/
│   ├── 📂 app/
│   │   ├── 📄 main.py              # نقطة الدخول + API endpoints
│   │   ├── 📄 config.py            # الإعدادات (.env)
│   │   ├── 📄 scheduler.py         # جدولة جمع البيانات
│   │   ├── 📂 collectors/          # جامعات البيانات
│   │   │   ├── gdelt.py            # GDELT Project
│   │   │   ├── news_api.py         # NewsAPI
│   │   │   ├── rss_feeds.py        # RSS + Google Alerts
│   │   │   ├── ucdp.py             # UCDP Uppsala
│   │   │   ├── adsb.py             # ADS-B تتبع الطيران
│   │   │   └── iran_osint.py       # 🆕 Iran OSINT مصادر متخصصة
│   │   ├── 📂 api/
│   │   │   ├── events.py           # API الأحداث
│   │   │   ├── flights.py          # API الطيران
│   │   │   ├── iran.py             # API إيران OSINT
│   │   │   └── nuclear.py          # ☢️ API المنشآت النووية (v1.2)
│   │   ├── 📂 data/
│   │   │   └── nuclear_facilities.json  # ☢️ بيانات المفاعلات (v1.2)
│   │   └── 📂 models/
│   │       └── database.py         # SQLite + SQLAlchemy
│   └── 📄 requirements.txt
│
├── 📂 frontend/
│   ├── 📂 src/
│   │   ├── 📄 App.jsx              # التطبيق الرئيسي
│   │   ├── 📂 components/
│   │   │   ├── 📂 Layout/
│   │   │   │   ├── Header.jsx       # الشريط العلوي (+ جرس التنبيهات)
│   │   │   │   ├── LiveTVDrawer.jsx # البث المباشر
│   │   │   │   └── AlertSettings.jsx # 🔔 إعدادات التنبيهات (v1.2)
│   │   │   ├── 📂 Map/
│   │   │   │   └── RasadMap.jsx    # خريطة Leaflet (+ إيران + ☢️ نووية)
│   │   │   ├── 📂 NewsFeed/
│   │   │   │   └── NewsFeed.jsx    # قائمة الأخبار
│   │   │   ├── 📂 Timeline/
│   │   │   │   └── Timeline.jsx    # الخط الزمني
│   │   │   ├── 📂 Stats/
│   │   │   │   └── StatsPanel.jsx  # الإحصائيات
│   │   │   └── 📂 Iran/
│   │   │       └── IranPanel.jsx   # 🆕 لوحة إيران OSINT
│   │   ├── 📂 hooks/
│   │   │   ├── usePolling.js       # خطاف التحديث التلقائي
│   │   │   └── useAudioAlert.js    # 🔔 خطاف التنبيهات الصوتية (v1.2)
│   │   └── 📂 utils/
│   │       ├── api.js              # دوال API (+ Iran + Nuclear endpoints)
│   │       └── constants.js        # ثوابت (+ CONFIDENCE, IRAN_EVENT_TYPES)
│   ├── 📄 vite.config.js           # إعدادات Vite (base path للنشر)
│   └── 📄 package.json
│
├── 📂 .github/workflows/
│   └── deploy-frontend.yml          # 🚀 نشر تلقائي إلى GitHub Pages (v1.2)
├── 📂 data/                         # قاعدة البيانات (SQLite)
├── 📄 docker-compose.yml
├── 📄 start-rasad.bat               # تشغيل سريع Windows
├── 📄 stop-rasad.bat                # إيقاف Windows
├── 📄 .env                          # المتغيرات (أنشئه من .env.example)
└── 📄 README.md
```

---

## ⚙️ API Endpoints

### الأحداث | Events

| المسار | الوصف |
|--------|-------|
| `GET /api/events/` | الأحداث مع فلاتر (category, severity, country_code, hours, limit) |
| `GET /api/events/latest` | أحدث 20 حدث |
| `GET /api/events/map` | أحداث الخريطة (فقط التي لها إحداثيات) |
| `GET /api/events/stats` | إحصائيات شاملة |
| `GET /api/events/timeline` | بيانات الخط الزمني |

### الطيران | Flights

| المسار | الوصف |
|--------|-------|
| `GET /api/flights/live` | الرحلات الحية الآن |
| `GET /api/flights/military/history` | سجل الطيران العسكري |
| `GET /api/flights/military/stats` | إحصائيات الطيران |

### إيران OSINT *(جديد)* | Iran OSINT

| المسار | الوصف |
|--------|-------|
| `GET /api/iran/strikes` | الضربات والأحداث مع فلتر الثقة (confidence, event_type, hours) |
| `GET /api/iran/leaders` | قائمة القادة الإيرانيين مع آخر أخبارهم |
| `GET /api/iran/stats` | إحصائيات أحداث إيران حسب النوع والثقة |

### المنشآت النووية ☢️ *(جديد v1.2)* | Nuclear

| المسار | الوصف |
|--------|-------|
| `GET /api/nuclear/facilities` | قائمة المنشآت مع فلاتر (country, facility_type, status) |
| `GET /api/nuclear/facilities/{id}` | تفاصيل منشأة محددة |
| `GET /api/nuclear/stats` | إحصائيات إجمالية حسب الدولة والنوع والحالة |

### النظام | System

| المسار | الوصف |
|--------|-------|
| `GET /api/health` | فحص صحة النظام |
| `GET /api/sources` | المصادر المتاحة |
| `GET /api/collectors/status` | حالة جامعي البيانات |
| `POST /api/refresh` | تحديث يدوي من جميع المصادر |

---

## 🔧 الإعدادات | Configuration

أنشئ ملف `.env` في المجلد الرئيسي:

```env
# مفاتيح API (اختيارية)
NEWSAPI_KEY=your_newsapi_key_here

# قاعدة البيانات
DATABASE_URL=sqlite+aiosqlite:///./data/rasad.db

# فترات التحديث (بالثواني)
GDELT_INTERVAL=900        # 15 دقيقة
NEWSAPI_INTERVAL=600      # 10 دقائق
RSS_INTERVAL=120          # دقيقتين
UCDP_INTERVAL=86400       # يوم
ADSB_INTERVAL=30          # 30 ثانية
# Iran OSINT يتحدث كل 5 دقائق (مثبت في الكود)

# الخادم
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

---

## 🛠️ التقنيات | Tech Stack

### Backend
| التقنية | الاستخدام |
|---------|----------|
| FastAPI | إطار العمل الرئيسي |
| SQLAlchemy | ORM + قاعدة البيانات |
| aiosqlite | SQLite غير متزامن |
| APScheduler | جدولة المهام |
| httpx | طلبات HTTP غير متزامنة |
| feedparser | تحليل RSS |

### Frontend
| التقنية | الاستخدام |
|---------|----------|
| React 18 | واجهة المستخدم |
| Vite | أداة البناء |
| Tailwind CSS | التنسيق |
| Leaflet | الخريطة التفاعلية (4 طبقات: أحداث + طيران + إيران + ☢️ نووي) |
| Recharts | الرسوم البيانية |
| Lucide React | الأيقونات |
| Web Audio API | توليد صوت إنذار التنبيهات (بدون ملفات خارجية) |

---

## 🗄️ قاعدة البيانات | Database Schema

| الجدول | الوصف |
|--------|-------|
| `events` | جميع الأحداث من كل المصادر (+ حقلا confidence و video_url) |
| `flight_tracks` | سجل تتبع الطيران |
| `iranian_leader_news` | 🆕 أخبار القادة الإيرانيين المرصودة |

---

## 🌐 النشر | Deployment

### GitHub Pages (الواجهة فقط)

يأتي المشروع بـ workflow جاهز في `.github/workflows/deploy-frontend.yml` يبني واجهة Vite وينشرها على GitHub Pages عند كل push إلى `main`.

**الخطوات لتفعيله**:
1. اذهب إلى **Settings → Pages** على GitHub
2. اختر *Source: GitHub Actions*
3. (اختياري) أضف Secret باسم `VITE_API_BASE` (Settings → Secrets and variables → Actions) بقيمة عنوان الـ Backend الخارجي إن وُجد، مثل: `https://api.example.com/api`
4. ادفع تعديلات على `frontend/**` — سيبدأ النشر تلقائيًا

**القيد المهم**: الـ Backend (FastAPI + SQLite + APScheduler) **لا يعمل على GitHub Pages** لأنها للملفات الثابتة فقط. لنسخة كاملة عامة:
- استضف الباك على Railway / Render / Fly.io (نطاق مجاني متاح)
- اضبط `VITE_API_BASE` ليشير إليه
- أو شغّل المشروع كاملاً محليًا (الطريقة الموصى بها للاستخدام الشخصي)

### Docker (محلي أو خادم خاص)

```bash
docker compose up -d --build
```

ينشر الـ Backend على `8000` والواجهة على `3000`. مناسب للتشغيل على VPS بسيط.

---

## 🤝 المساهمة | Contributing

```bash
# 1. Fork المشروع على GitHub
# 2. استنسخ نسختك
git clone https://github.com/<your-username>/rsd.git
cd rsd

# 3. أنشئ فرعاً للميزة
git checkout -b feat/my-feature

# 4. عدّل، اختبر، ثم commit
git add .
git commit -m "feat: وصف التغيير"

# 5. ادفع وافتح Pull Request
git push origin feat/my-feature
```

أنماط الـ commit messages: `feat:`, `fix:`, `docs:`, `refactor:`, `style:`, `test:`.

---

## 🗺️ خارطة الطريق | Roadmap

### ✅ v1.2 (الإصدار الحالي)
- [x] ☢️ طبقة المنشآت النووية على الخريطة
- [x] 🔔 نظام تنبيهات صوتية في المتصفح
- [x] 🚀 GitHub Actions workflow للنشر
- [x] 🔧 دعم `VITE_API_BASE` لباك خارجي

### 🔄 v1.3 — ترقية الخريطة والتصوّر
- [ ] 🌍 وضع كرة أرضية ثلاثية الأبعاد (globe.gl)
- [ ] 🗺️ طبقات بيانات إضافية (قواعد عسكرية، خطوط أنابيب)
- [ ] 🌐 i18n كامل (عربي/إنجليزي)
- [ ] 📊 Country Intelligence Index — مؤشر تقييم لكل دولة

### 🔄 v1.4 — البنية التحتية والجودة
- [ ] 🧪 اختبارات pytest + vitest
- [ ] 🔄 CI workflow للـ lint والاختبارات
- [ ] 💾 طبقة caching (ETags + Service Worker)
- [ ] 📦 PWA (عمل دون اتصال)
- [ ] 🖥️ تطبيق Tauri لسطح المكتب

### 🔮 v2.0 — ذكاء وتحليل
- [ ] 🤖 **Ollama/Qwen AI** — تصنيف وتلخيص ذكي للأخبار العربية
- [ ] 🧠 **تحليل المشاعر** والكيانات (NER)
- [ ] 📡 **Telegram** + **Twitter/X** كمصادر إضافية
- [ ] 🎯 **Signal Convergence** — اكتشاف تقارب الإشارات تلقائيًا
- [ ] 📄 **تقارير PDF** تلقائية
- [ ] 📍 تحديد موقع جغرافي دقيق (بدل مراكز الدول)

> 💡 خارطة الطريق هذه مستوحاة جزئيًا من المشروع المفتوح [worldmonitor](https://github.com/koala73/worldmonitor) كمصدر أفكار معمارية (مع الالتزام بترخيص رصد MIT).

---

## 🐛 استكشاف الأخطاء | Troubleshooting

### لا تظهر أخبار جديدة
1. تأكد من تشغيل Backend: `curl http://localhost:8000/api/health`
2. افحص حالة الجامعات: `curl http://localhost:8000/api/collectors/status`
3. جرب التحديث اليدوي: اضغط زر 🔄 في الواجهة

### طبقة إيران OSINT فارغة
1. تحقق من البيانات: `curl http://localhost:8000/api/iran/strikes`
2. إذا `total: 0` — انتظر دقيقة بعد تشغيل الباكند ثم اضغط 🔄
3. البيانات تظهر بعد أول دورة جمع (تلقائي عند التشغيل)

### خطأ في NewsAPI
- تأكد من وجود `NEWSAPI_KEY` في `.env`
- المفتاح المجاني يعطي أخبار قديمة فقط (24+ ساعة)

### الخريطة لا تعمل
- تأكد من اتصال الإنترنت (Leaflet يحتاج tiles من CartoCDN)
- افحص Console في المتصفح للأخطاء

---

## 📝 الترخيص | License

هذا المشروع للاستخدام الشخصي والتعليمي.

---

<div align="center">

**رصد** 🛰️ - صُنع بـ ❤️ للمعرفة والتوثيق

**Rsd** - Made with ❤️ for Knowledge and Documentation

---

المطور | Developer: **عبدالكريم العبود**

📧 abo.saleh.g@gmail.com

![GitHub](https://img.shields.io/badge/GitHub-abosalehg--ui-black?logo=github)

</div>
