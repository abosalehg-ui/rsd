<div align="center">

# 🛰️ رصد (Rsd) v2.0

### منصة استخبارات المصادر المفتوحة للشرق الأوسط
**Open Source Intelligence (OSINT) Dashboard for the Middle East**

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows_Installer_%7C_Docker_%7C_Pages-lightgrey)
![Python](https://img.shields.io/badge/Python-3.10+-yellow)
![React](https://img.shields.io/badge/React-18-61DAFB)
![Deploy](https://img.shields.io/badge/Deploy-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

<br>

<img src="https://img.shields.io/badge/🖥️_DESKTOP-مثبّت_ويندوز-2563eb?style=for-the-badge" alt="Desktop"/>
<img src="https://img.shields.io/badge/🔴_LIVE-البث_المباشر-red?style=for-the-badge" alt="Live"/>
<img src="https://img.shields.io/badge/🗺️_MAP-خريطة_تفاعلية-blue?style=for-the-badge" alt="Map"/>
<img src="https://img.shields.io/badge/🌍_3D_GLOBE-كرة_أرضية-blue?style=for-the-badge" alt="3D Globe"/>
<img src="https://img.shields.io/badge/✈️_FLIGHTS-تتبع_الطيران-orange?style=for-the-badge" alt="Flights"/>
<img src="https://img.shields.io/badge/🇮🇷_IRAN-متابعة_إيران_OSINT-darkred?style=for-the-badge" alt="Iran OSINT"/>
<img src="https://img.shields.io/badge/☢️_NUCLEAR-منشآت_نووية-yellow?style=for-the-badge" alt="Nuclear"/>
<img src="https://img.shields.io/badge/🔔_ALERTS-تنبيهات_صوتية-purple?style=for-the-badge" alt="Alerts"/>
<img src="https://img.shields.io/badge/🌐_i18n-عربي_/_English-green?style=for-the-badge" alt="i18n"/>
<img src="https://img.shields.io/badge/📦_PWA-عمل_دون_اتصال-cyan?style=for-the-badge" alt="PWA"/>

</div>

---

## 📋 نظرة عامة | Overview

**رصد** لوحة تحكم شخصية لرصد الأحداث العسكرية والأمنية والجيوسياسية في الشرق الأوسط لحظياً. تجمع البيانات من مصادر متعددة وتعرضها على خريطة تفاعلية (2D و 3D) مع تصنيف ذكي وتنبيهات صوتية.

**Rsd** is a personal OSINT dashboard for real-time monitoring of military, security, and geopolitical events across the Middle East. It aggregates data from multiple sources and displays them on an interactive 2D/3D map with intelligent classification and audio alerts.

<div align="center">

| الواجهة الرئيسية | الخريطة والأحداث |
|:---:|:---:|
| ![الواجهة الرئيسية](assets/screenshots/rsd1.png) | ![الخريطة والأحداث](assets/screenshots/rsd2.png) |

</div>

---

## 🇸🇦 الجديد: عدسة «الأثر على المملكة» وإعادة التشغيل الزمني

| الميزة | الوصف |
|--------|-------|
| 🇸🇦 **مؤشر الأثر على المملكة** | 0-100 لكل الأحداث (لا النووية وحدها) بصيغة المؤشر النووي، مع الفترة السابقة والاتجاه والسلسلة الزمنية |
| 🧮 **درجة أثر مفسَّرة لكل حدث** | 100 × الشدة × القرب × الإشارة المباشرة (أرامكو، المطارات، الموانئ، هرمز، باب المندب…) × ثقة المصدر — المعادلة بأرقامها في لوحة التفاصيل |
| 🏷️ **8 قطاعات** | أمن، طاقة، طيران، ملاحة وموانئ، أسواق، غذاء ومياه، صحة، دبلوماسية — بمعجم عربي/إنجليزي بحدود الكلمة، وفلتر «حسب القطاع» في شريط الأحداث |
| 👁️ **بنود «راقِب»** | قاعدية لا مولَّدة: كل قطاع ارتفع مؤشره 10 نقاط فأكثر عن الفترة السابقة وبلغ 25 |
| ⏯️ **إعادة التشغيل الزمني** | شريط تحت الخريطة والكرة يعيد آخر 48 أو 72 ساعة ساعةً بساعة، بزر تشغيل ومنزلق وكثافة الأحداث لكل ساعة |
| 🔗 **رابط مشاركة لكل حدث** | `?event=ID` يفتح لوحة التفاصيل مباشرة، وزر «نسخ رابط الحدث» |
| ⏱️ **جدول المزامنة في الرأس** | وقت آخر تحليل وعدّاد تنازلي للتحديث القادم |
| 🔢 **عدّادات التصنيفات** | عدد أحداث الفترة بجانب كل تصنيف وقطاع |

يعمل كله دون اتصال وبلا مفاتيح. المنهجية الكاملة وحدودها:
**[`docs/ksa-impact-methodology.md`](docs/ksa-impact-methodology.md)**.

---

## ☢️ الجديد في v2.0: الرصد النووي والإشعاعي

صار الرصد النووي والإشعاعي والتطورات السياسية المرتبطة به هو المحور الأول للمنصة:

| الميزة | الوصف |
|--------|-------|
| 📈 **مؤشر المخاطر النووية والإشعاعية** | 0-100 على تدريج بأربعة نطاقات، مع قيمة الفترة السابقة والاتجاه وسلسلة زمنية، ومعادلته معروضة بأرقامها |
| 🏷️ **12 موضوعًا** | انبعاث إشعاعي، تهديد عسكري لمنشأة، مصدر مشع مفقود، أمن نووي، حادث أمان، تخصيب وتسلّح، ضمانات، مفاوضات وعقوبات، تأهب، تنظيم، استخدامات طبية، برامج طاقة |
| 🧮 **درجة خطر مفسَّرة لكل خبر** | أساس الموضوع + الشدة − التخفيف ± القرب من المملكة × ثقة المصدر — المكوّنات ظاهرة في لوحة التفاصيل |
| 🇸🇦 **المسافة إلى المملكة** | لكل منشأة وخبر: المسافة إلى أقرب نقطة سعودية، وفلتر «قرب المملكة» |
| 🏭 **رصد المنشآت** | المنشآت المذكورة بالاسم في الأخبار مرتّبة بالخطر |
| ⭕ **مسافات التخطيط للطوارئ** | دوائر PAZ/UPZ/EPD/ICPD الاسترشادية (IAEA EPR-NPP) حول محطات القوى |
| 📡 **جامع نووي متخصص** | IAEA، World Nuclear News، NucNet، ANS، ACA، Arms Control Wonk + بحث Google News بالعربية والإنجليزية (بما فيه الجهات الرقابية الإقليمية) |
| 🧩 **تجميع القصص** | الخبر نفسه من عدة مصادر قصة واحدة بعدد مصادرها |
| 📄 **التقرير الدوري** | 24 ساعة / 3 أيام / أسبوع — طباعة/PDF، HTML مستقل، Markdown |

وإصلاحات جودة البيانات: مطابقة بحدود الكلمة (كانت "warning" تُعدّ حربًا و«يقتلع» قتلًا)، دول الخليج
في تحديد الموقع، اختيار الهدف لا الأسبق ذكرًا، دقة الموقع (منشأة/مدينة/دولة)، فكّ `&quot;`
و`<b>` من العناوين، إعادة تحليل البيانات المخزّنة تلقائيًا عند الترقية.

المنهجية الكاملة وحدودها: **[`docs/nuclear-risk-methodology.md`](docs/nuclear-risk-methodology.md)**.

> **الخريطة الأساس:** صارت CARTO تعيد صورة «API KEY REQUIRED» للطلبات بلا مفتاح، فانتقلت الخريطة
> إلى Esri World Dark Gray. لاستعمال مزوّد آخر: `VITE_TILE_URL` و`VITE_TILE_ATTRIBUTION` عند البناء
> (مع إضافة نطاقه إلى `img-src` في سياسات CSP الثلاث).

---

## ⚡ التشغيل | Getting Started

استنسخ المشروع أولاً (للتحديث لاحقاً: `git pull origin main`):

```bash
git clone https://github.com/abosalehg-ui/rsd.git
cd rsd
```

### ▶️ الأسهل: نقرة واحدة على `Rasad.bat` (ويندوز)

انقر مرتين على **`Rasad.bat`** في جذر المستودع. عملية واحدة تقدّم الواجهة والبيانات معًا
ويُفتح المتصفح تلقائيًا؛ أغلق النافذة لإيقافه.

- **أول تشغيل** يجهّز كل شيء بنفسه (بيئة Python خاصة + بناء الواجهة) — بضع دقائق. بعدها ثوانٍ.
- يتطلّب **Python 3.10+**، و**Node.js** لبناء الواجهة في أول تشغيل وبعد كل تحديث فقط.
- إن كان المنفذ 8000 مشغولًا ببرنامج آخر ينتقل تلقائيًا إلى أول منفذ حرّ (8001، 8002…)؛
  وإن كان رصد نفسه يعمل يفتح المتصفح عليه بدل تشغيل نسخة ثانية.

أو اختر إحدى الطرق التالية:

### 🖥️ الطريقة A — تطبيق سطح المكتب (ويندوز، الأسهل للمستخدم النهائي)

نزّل وثبّت `Rasad-Setup-x64.exe` — تطبيق مستقل لا يحتاج Python أو Node. بعد التثبيت يعمل كل شيء من `http://127.0.0.1:8000` ويفتح المتصفح تلقائياً.

> لبناء المثبّت بنفسك: راجع **[`packaging/README.md`](packaging/README.md)** ثم شغّل `packaging\build_installer.bat`.

> أولاً انسخ ملف المتغيّرات البيئية واملأ مفاتيحك (كلها اختيارية):
> ```bash
> cp .env.example .env
> ```
> راجع التعليقات داخل `.env.example` لمعرفة مصدر كل مفتاح.

### 🐳 الطريقة B — Docker

**تطوير** (خوادم dev + HMR):
```bash
docker compose up -d
# الواجهة:  http://localhost:3000   •   API Docs: http://localhost:8000/docs
```

**إنتاج** (واجهة مبنية عبر nginx + خلفية بلا reload):
```bash
docker compose -f docker-compose.prod.yml up -d --build
# الواجهة:  http://localhost:3000  (nginx يوكّل /api إلى الخلفية)
```

### 🧑‍💻 الطريقة C — تشغيل محلي للتطوير

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

> للمساهمة وتشغيل الفحوص: راجع **[`CONTRIBUTING.md`](CONTRIBUTING.md)**.

> مراجعات المستودع وخطط الإصلاح: **[`docs/reviews/`](docs/reviews/)**.

> 💡 للاستخدام العادي على ويندوز يكفي `Rasad.bat` (أعلاه). الطريقة C لتطوير الواجهة مع إعادة التحميل الفوري.

### 📋 المتطلّبات | Requirements

- **Python** 3.10+ و **Node.js** 18+ (للتطوير/البناء)
- **مفتاح NewsAPI** (اختياري) — [احصل على مفتاح مجاني](https://newsapi.org/)
- **رمز UCDP** (اختياري) — [توثيق UCDP](https://ucdp.uu.se/apidocs/) (الـ API لم يعد مفتوحاً بلا رمز)
- لبناء المثبّت: **Inno Setup 6** ([تنزيل](https://jrsoftware.org/isdl.php))

---

## ✨ الميزات | Features

| الميزة | الوصف |
|--------|-------|
| 🗺️ **خريطة 2D تفاعلية** | Leaflet مع تجميع ذكي للعلامات و6 طبقات (أحداث + طيران + إيران + نووي + قواعد + أنابيب) |
| 🌍 **كرة أرضية 3D** | globe.gl + Three.js — نقاط متوهّجة + **حلقات رادار متحرّكة** للأحداث العاجلة + arcs للضربات (تحميل كسول) |
| 📰 **شريط أخبار عاجلة** | تدفق مباشر مع فلاتر حسب التصنيف (بعدد أحداثه) والقطاع والخطورة والدولة |
| 🇸🇦 **عدسة الأثر على المملكة** | مؤشر 0-100 مفسَّر لكل الأحداث، وتوزيع حسب ثمانية قطاعات، وأعلى الأحداث أثرًا، وبنود «راقِب» |
| ⏯️ **إعادة التشغيل الزمني** | آخر 48/72 ساعة ساعةً بساعة على الخريطة 2D والكرة 3D |
| 🔗 **روابط مشاركة** | `?event=ID` يفتح تفاصيل الحدث مباشرة |
| ✈️ **تتبع الطيران** | رصد الطائرات عبر ADS-B مع تمييز الطيران العسكري |
| ⏳ **خط زمني + 📊 إحصائيات** | عرض زمني للأحداث + مؤشر تصعيد وتوزيعات |
| 📺 **البث المباشر** | مشغّل مدمج للقنوات (الجزيرة، العربية، BBC) عبر `youtube-nocookie` |
| 🔔 **تنبيهات صوتية** | صوت تنبيه **جرسي راقٍ** (Web Audio API، يعمل offline) مع عتبة خطورة وتصنيفات قابلة للتخصيص |
| 🇮🇷 **متابعة إيران OSINT** | طبقة لرصد الضربات/الإطلاقات/التحركات مع تصنيف الثقة + متابعة 10 قياديين |
| ☢️ **منشآت نووية** | 24+ منشأة (مفاعلات/تخصيب/أبحاث) مع تفاصيل وسعة |
| ⚔️ **قواعد عسكرية + 🛢️ أنابيب** | 19 قاعدة رئيسية + 10 خطوط نفط/غاز |
| 📊 **مؤشر استخبارات الدول** | تقييم 0-100 لكل دولة بناءً على عدد ونوع الأحداث |
| 🌐 **ثنائي اللغة** | عربي/إنجليزي كامل مع تبديل RTL/LTR |
| 🖥️ **تطبيق سطح المكتب** *(جديد v1.5)* | مثبّت ويندوز كامل (PyInstaller + Inno Setup) — exe واحد يقدّم الـ API والواجهة معاً |
| 📦 **PWA** | يعمل دون اتصال — تخزين مؤقت للبلاطات وقوام الكرة + Service Worker |
| 💾 **ETag caching** | استجابات 304 Not Modified + Cache-Control حسب المسار |
| 🧪 **اختبارات + CI** | pytest (backend) + vitest (frontend) عبر GitHub Actions عند كل PR |

---

## 🖥️ تطبيق سطح المكتب *(جديد في v1.5)*

يمكن تغليف رصد كتطبيق ويندوز يُثبَّت بنقرة واحدة، دون حاجة لتثبيت Python أو Node لدى المستخدم.

**الفكرة:** الـ Backend (FastAPI) يقدّم الواجهة المبنية أيضاً، فيصبح كل شيء في **ملف `.exe` واحد** على `http://127.0.0.1:8000`. يجمّع **PyInstaller** الخادم + البيانات + الواجهة، ثم يلفّه **Inno Setup** في مثبّت مع اختصارات وأيقونة وأداة إزالة.

```bat
:: من جذر المستودع (يتطلّب Inno Setup 6 في PATH)
packaging\build_installer.bat
:: الناتج: packaging\Output\Rasad-Setup-x64.exe
```

- 📂 بعد التثبيت تُحفظ قاعدة البيانات والمفاتيح في `%LOCALAPPDATA%\Rasad\` (قابل للكتابة).
- 🎨 الأيقونة (طابع رادار) تُولَّد عبر `packaging/make_icon.py` وتُربط في الـ exe والمثبّت والاختصارات وأيقونة المتصفح.
- 📖 التفاصيل الكاملة (التخصيص، الأيقونة، التوقيع، SmartScreen) في **[`packaging/README.md`](packaging/README.md)**.

---

## ☢️ المنشآت النووية

طبقة على الخريطة تعرض **24+ منشأة نووية** في المنطقة، مبنية من بيانات IAEA PRIS العامة:

- **محطات قوة**: بوشهر، براكة، آكويو، الضبعة، تارابور، شاشمة، روستوف …
- **مراكز تخصيب**: نطنز، فوردو
- **مفاعلات أبحاث**: طهران، سوريك، المركز الأردني JRTR
- **معامل تحويل وماء ثقيل**: أصفهان، آراك
- **مواقع حساسة**: ديمونا (إسرائيل)، زابوريجيا (تحت الاحتلال)

كل علامة تعرض: الاسم بالعربي والإنجليزي، نوع المفاعل، السعة (MW)، الحالة، المُشغّل، تاريخ بدء التشغيل. يمكن إخفاء/إظهار الطبقة من لوحة "طبقات" أسفل الخريطة.

> 🔄 لإضافة منشأة جديدة: حرّر `backend/app/data/nuclear_facilities.json`.

---

## 🔔 التنبيهات الصوتية

نظام تنبيه مدمج يُنبّهك صوتيًا عند ورود أخبار مهمة دون متابعة الشاشة باستمرار.

- **صوت تنبيه جرسي راقٍ** يُولَّد عبر Web Audio API (نغمات `sine`/`triangle` تصاعدية، بلا ملفات خارجية، يعمل offline)
- **عتبة خطورة قابلة للتخصيص**: منخفض / متوسط / مرتفع / حرج
- **تصفية بالتصنيفات**: عسكري، نووي، دبلوماسي، إنساني، اقتصادي
- **فاصل تكرار قابل للضبط** (5-120 ثانية) لتفادي الإزعاج
- **إشعارات سطح المكتب اختيارية** (Notification API)
- **سجل آخر 5 تنبيهات** قابل للضغط للانتقال للحدث

افتح إعدادات التنبيهات من أيقونة 🔔 في الشريط العلوي (زر اختبار الصوت بالداخل).

---

## 🇮🇷 متابعة إيران OSINT

ميزة مستوحاة من [iranstrikemap.com](https://iranstrikemap.com) و [live-iran-map.com](https://live-iran-map.com) تضيف طبقة متخصصة لمتابعة الأحداث الإيرانية.

### نظام تصنيف الثقة

| المستوى | الرمز | المعنى | أمثلة المصادر |
|---------|-------|--------|--------------|
| **HIGH** | 🟢 | موثوق - مصادر OSINT متخصصة | The War Zone, Bellingcat, Long War Journal, Oryx |
| **MEDIUM** | 🟡 | متوسط - صحافة دفاعية | Breaking Defense, Defense One |
| **LOW** | 🔵 | غير مؤكد - أخبار عامة | BBC |

### أنواع الأحداث المرصودة

| النوع | الأيقونة | الوصف |
|-------|----------|-------|
| **strike** | 💥 | ضربات جوية وهجمات |
| **launch** | 🚀 | إطلاقات صاروخية واختبارات |
| **movement** | 🪖 | تحركات عسكرية ومناورات |
| **nuclear** | ☢️ | أحداث نووية وتخصيب |
| **diplomatic** | 🤝 | مفاوضات وعقوبات |

### متابعة القادة الإيرانيين

يتابع النظام آخر أخبار **10 قياديين إيرانيين** تلقائياً (القائمة مُحدَّثة حتى يوليو 2026):

| القائد | المنصب | | القائد | المنصب |
|--------|--------|---|--------|--------|
| مجتبى خامنئي | المرشد الأعلى | | عباس عراقچي | وزير الخارجية |
| مسعود بزشكيان | الرئيس | | إسماعيل قاآني | قائد قوة القدس |
| أحمد وحيدي | قائد الحرس الثوري | | محمد إسلامي | رئيس منظمة الطاقة الذرية |
| حبيب الله سياري | رئيس الأركان | | عزيز نصيرزاده | وزير الدفاع |
| ماجد موسوي | قائد الفضاء IRGC | | علي شمخاني | مستشار المرشد |

<details>
<summary>📚 مصادر Iran OSINT (اضغط للعرض)</summary>

**HIGH:** The War Zone (TWZ) · Bellingcat · FDD's Long War Journal · Oryx
**MEDIUM:** Breaking Defense · Defense One
**LOW:** BBC (Middle East)

الخلاصات الإقليمية العامة (TWZ، Breaking Defense، Defense One، BBC) تُجمع هنا وحدها: ما يُصنَّف حدثًا إيرانيًا يُخزَّن بثقته ونوعه، وما عداه يُخزَّن خبر RSS عاديًا. حيويّة الخلاصات تُفحص أسبوعيًا في CI (`feed-health.yml`).

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
| **NewsAPI** | أخبار من مصادر عالمية متعددة *(يحتاج `NEWSAPI_KEY`)* | كل ساعة |
| **RSS Feeds** | خلاصات عربية ودولية (25+ مصدر) | كل دقيقتين |
| **Google Alerts** | تنبيهات مخصصة (تُضاف من `.env`) | كل دقيقتين |
| **UCDP** | بيانات النزاعات المسلحة (جامعة أوبسالا) *(يحتاج `UCDP_ACCESS_TOKEN` — الـ API لم يعد عاماً)* | يومياً |
| **ADS-B** | تتبع الطيران (adsb.lol) | كل 30 ثانية |
| **Iran OSINT** | مصادر OSINT متخصصة بإيران والشرق الأوسط | كل 30 دقيقة |

<details>
<summary>📰 مصادر RSS المدعومة (اضغط للعرض)</summary>

**أخبار عربية:** الجزيرة (عربي + English) · BBC Arabic/Middle East · France24 Arabic · Sky News Arabia · RT Arabic
**تحليلات دولية:** War on the Rocks (بقية المصادر الدفاعية — Breaking Defense · Defense One · The War Zone — في جامع إيران OSINT)
**أخبار نووية:** World Nuclear News · IAEA News · Arms Control Association
**Google Alerts:** تُضبَط عبر `GOOGLE_ALERT_FEEDS` في `.env` (روابط الخلاصات شخصية بحسابك ولا تُوضع في المستودع). أمثلة مقترحة: Middle East Airstrikes · Gaza/Yemen/Syria · Houthi/حوثي · Red Sea · Iran Nuclear/تخصيب يورانيوم · Ceasefire/هدنة · Humanitarian Crisis

</details>

---

## 📁 هيكل المشروع | Project Structure

```
rsd/
├── 📂 backend/
│   ├── 📂 app/
│   │   ├── 📄 main.py              # مصنع التطبيق: دورة الحياة، الطبقات، تخديم الواجهة في وضع سطح المكتب
│   │   ├── 📄 config.py            # الإعدادات (.env) + مسارات قابلة للكتابة عند التجميد
│   │   ├── 📄 scheduler.py         # جدولة جمع البيانات (APScheduler)
│   │   ├── 📄 auth.py              # حارس CSRF + مفتاح API للنقاط المكلفة
│   │   ├── 📄 static_data.py       # قراءة ملفات data/*.json المشتركة
│   │   ├── 📂 collectors/          # gdelt · news_api · rss_feeds · ucdp · adsb · iran_osint · nuclear_watch (+ _feed_base)
│   │   ├── 📂 processors/          # matching · normalize · gazetteer · nuclear · impact · text_analysis · clustering · dates
│   │   ├── 📂 api/                 # system (+schedule) · events (+country-index) · flights · iran · nuclear · impact · infrastructure (+ _stories/_serializers)
│   │   ├── 📂 data/                # nuclear_facilities · military_bases · pipelines · iranian_leaders (JSON)
│   │   ├── 📂 middleware/          # cache (ETag) · ratelimit · security_headers
│   │   └── 📂 models/database.py   # SQLite + SQLAlchemy + ترقية الأعمدة + الاحتفاظ
│   ├── 📂 tests/                   # pytest (تغطية ≥ 75% في CI)
│   ├── 📂 scripts/check_feeds.py   # فحص حيويّة الخلاصات (يشغّله CI أسبوعيًا)
│   ├── 📄 run_desktop.py           # 🖥️ نقطة دخول التشغيل بنقرة واحدة وتطبيق سطح المكتب
│   └── 📄 requirements.txt · requirements-dev.txt
│
├── 📂 frontend/
│   ├── 📂 src/
│   │   ├── 📄 App.jsx
│   │   ├── 📂 components/
│   │   │   ├── 📂 Layout/          # Header · LiveTVDrawer · AlertSettings
│   │   │   ├── 📂 Map/             # RasadMap (2D) · RasadGlobe (3D، lazy) · ReplayBar · popups · globeSprites · LayerToggles
│   │   │   ├── 📂 Nuclear/         # NuclearPanel · RiskGauge · FacilityWatch · Sparkline
│   │   │   ├── 📂 Impact/          # KsaLens · ImpactBreakdown (عدسة الأثر على المملكة)
│   │   │   ├── 📂 Events/          # EventCard · StoryList · EventDrawer
│   │   │   ├── 📂 Report/          # ReportView (طباعة / HTML / Markdown)
│   │   │   ├── 📂 NewsFeed/        # NewsFeed.jsx
│   │   │   ├── 📂 Timeline/        # Timeline.jsx
│   │   │   ├── 📂 Stats/           # StatsPanel.jsx · CountryIndex.jsx
│   │   │   └── 📂 Iran/            # IranPanel.jsx
│   │   ├── 📂 hooks/               # usePolling.js · useAudioAlert.js
│   │   ├── 📂 i18n/                # index.js + locales/{ar,en}.json
│   │   └── 📂 utils/               # api · constants (THEME) · security · icons · report · replay · deepLink
│   ├── 📂 public/                  # favicon.ico + أيقونات PWA
│   └── 📄 vite.config.js · index.html · package.json
│
├── 📂 packaging/                   # 🖥️ بناء مثبّت ويندوز (v1.5)
│   ├── 📄 build_installer.bat      # بناء كامل بأمر واحد
│   ├── 📄 rasad.spec               # مواصفات PyInstaller (onedir)
│   ├── 📄 rasad.iss                # سكربت Inno Setup
│   ├── 📄 make_icon.py             # مولّد الأيقونة (Pillow)
│   ├── 🖼️ rasad.ico                # الأيقونة الجاهزة
│   └── 📄 README.md                # دليل البناء
│
├── 📂 docs/                        # nuclear-risk-methodology.md · ksa-impact-methodology.md · proposals/ · reviews/ (سجل المراجعات)
├── 📂 .github/workflows/           # ci.yml (lint+tests+build) · deploy-frontend.yml · feed-health.yml (فحص الخلاصات أسبوعيًا)
├── 📄 docker-compose.yml · docker-compose.prod.yml
├── 📄 Rasad.bat                          # تشغيل بنقرة واحدة (Windows) — عملية واحدة للواجهة والبيانات
└── 📄 README.md
```

---

## ⚙️ API Endpoints

<details open>
<summary><b>الأحداث | Events</b></summary>

| المسار | الوصف |
|--------|-------|
| `GET /api/events/` | الأحداث مطويّة في قصص مع فلاتر (category, severity, country_code, source, search, topic, sector, hours, limit, collapse) |
| `GET /api/events/{id}` | حدث واحد بقصته ومصادرها (لرابط المشاركة `?event=ID`) |
| `GET /api/events/latest?limit=20` | أحدث الأحداث الخام (تيار التنبيهات) |
| `GET /api/events/map?hours=24&limit=200` | أحداث الخريطة (ممثّل واحد لكل قصة، بإحداثيات) |
| `GET /api/events/stats` | إحصائيات شاملة (منها العدّ حسب التصنيف والقطاع) + مؤشر التصعيد باتجاهه وسلسلته |
| `GET /api/events/timeline` | بيانات الخط الزمني |
| `GET /api/events/country-index?hours=72&top=20` | ترتيب الدول حسب درجة 0-100 |

</details>

<details>
<summary><b>الأثر على المملكة · الطيران · إيران · النووي · البنية التحتية · النظام</b></summary>

**الأثر على المملكة 🇸🇦**
| المسار | الوصف |
|--------|-------|
| `GET /api/impact/ksa?hours=48` | المؤشر (0-100) وقيمة الفترة السابقة والاتجاه والسلسلة الزمنية، والتوزيع حسب القطاع، وأعلى الأحداث أثرًا بمكوّناتها، وبنود «راقِب» |
| `GET /api/impact/sectors` | القطاعات ومعاملات المعادلة |

**الطيران | Flights**
| المسار | الوصف |
|--------|-------|
| `GET /api/flights/live` | الرحلات الحية الآن |
| `GET /api/flights/military/history` | سجل الطيران العسكري |
| `GET /api/flights/military/stats` | إحصائيات الطيران |

**إيران OSINT**
| المسار | الوصف |
|--------|-------|
| `GET /api/iran/strikes` | الضربات (confidence, event_type, hours) |
| `GET /api/iran/leaders` | القادة الإيرانيون مع آخر أخبارهم |
| `GET /api/iran/stats` | إحصائيات حسب النوع والثقة |

**الرصد النووي والإشعاعي ☢️**
| المسار | الوصف |
|--------|-------|
| `GET /api/nuclear/risk?hours=24` | مؤشر المخاطر النووية والإشعاعية (0-100) مع مكوّناته واتجاهه وسلسلته |
| `GET /api/nuclear/events` | الأخبار النووية/الإشعاعية مطويّة في قصص (topic, min_risk, near_ksa_km) |
| `GET /api/nuclear/brief?hours=24` | التقرير الدوري (بيانات منظّمة تصدّرها الواجهة) |
| `GET /api/nuclear/topics` | الموضوعات وأوزان أساسها |
| `GET /api/nuclear/facilities` | قائمة المنشآت + المسافة إلى المملكة + مسافات التخطيط (country, facility_type, status) |
| `GET /api/nuclear/facilities/watch` | المنشآت المذكورة في الأخبار مرتّبة بالخطر |
| `GET /api/nuclear/facilities/{id}` | تفاصيل منشأة |
| `GET /api/nuclear/stats` | إحصائيات حسب الدولة/النوع/الحالة |

**البنية التحتية ⚔️ 🛢️**
| المسار | الوصف |
|--------|-------|
| `GET /api/infrastructure/bases` | قواعد عسكرية (country, operator, base_type) |
| `GET /api/infrastructure/pipelines` | خطوط أنابيب (pipeline_type, status) |

**النظام | System**
| المسار | الوصف |
|--------|-------|
| `GET /api/health` | فحص صحة النظام |
| `GET /api/sources` | المصادر المتاحة |
| `GET /api/collectors/status` | حالة جامعي البيانات |
| `GET /api/schedule` | وقت آخر تحليل وموعد المزامنة القادمة (للعدّاد في الرأس) |
| `POST /api/refresh` | تحديث يدوي من جميع المصادر |

</details>

> 📚 توثيق تفاعلي كامل عبر Swagger على `http://localhost:8000/docs`.

---

## 🔧 الإعدادات | Configuration

أنشئ ملف `.env` في المجلد الرئيسي (أو في `%LOCALAPPDATA%\Rasad\.env` لتطبيق سطح المكتب):

```env
# مفاتيح API (اختيارية)
NEWSAPI_KEY=your_newsapi_key_here

# خلاصات Google Alerts — روابط شخصية بحسابك، تُعامَل كأسرار ولا تُوضع في المصدر.
# الصيغة: "الاسم|التصنيف|الرابط" مفصولة بفواصل.
GOOGLE_ALERT_FEEDS=

# قاعدة البيانات (الافتراضي: ملف محلي ./rasad.db ؛ تطبيق سطح المكتب يستخدم %LOCALAPPDATA%\Rasad)
DATABASE_URL=sqlite+aiosqlite:///./rasad.db

# فترات التحديث (بالثواني)
# رمز UCDP — بدونه يُتخطّى المصدر ويظهر disabled في /api/sources
UCDP_ACCESS_TOKEN=

# فترات التحديث (بالثواني)
GDELT_INTERVAL=900        # 15 دقيقة
NEWSAPI_INTERVAL=3600     # ساعة (الحصة المجانية 100 طلب/يوم)
RSS_INTERVAL=120          # دقيقتان
UCDP_INTERVAL=86400       # يوم
ADSB_INTERVAL=30          # 30 ثانية

# الخادم — الافتراضي محلي فقط
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# أصول CORS المسموح لها (مفصولة بفواصل)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# مفتاح حماية /api/refresh — فارغ = معطّل (مناسب للتشغيل المحلي).
# عند ضبطه أرسل الترويسة X-API-Key من العميل (VITE_API_KEY في الواجهة).
# ملاحظة: /api/refresh يشترط دائماً الترويسة X-Rasad-Client: 1 (حارس CSRF).
API_KEY=

# حدّ المعدل لكل IP على مسارات /api
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
```

> ⚠️ **قبل عرض الخادم على شبكة:** الـ API بلا حسابات مستخدمين. اضبط `API_KEY`،
> وأبقِ `BACKEND_HOST=127.0.0.1` خلف وكيل عكسي يوفّر TLS. ملفّا compose يربطان
> المنافذ على `127.0.0.1` افتراضياً لهذا السبب.

---

## 🛠️ التقنيات | Tech Stack

| الطبقة | التقنيات |
|--------|----------|
| **Backend** | FastAPI · SQLAlchemy · aiosqlite · APScheduler · httpx · feedparser |
| **Frontend** | React 18 · Vite · Tailwind CSS · react-i18next (RTL) · Recharts · Lucide |
| **الخرائط** | Leaflet (2D، 6 طبقات) · globe.gl + Three.js (3D: نقاط + حلقات رادار + arcs) |
| **الصوت/PWA** | Web Audio API (توليد التنبيه) · vite-plugin-pwa + Workbox |
| **التغليف** | PyInstaller + Inno Setup (مثبّت ويندوز) · Pillow (الأيقونة) |
| **الجودة** | pytest · vitest · ruff · GitHub Actions CI |

---

## 🗄️ قاعدة البيانات | Database Schema

| الجدول | الوصف |
|--------|-------|
| `events` | جميع الأحداث من كل المصادر (+ حقلا confidence و video_url) |
| `flight_tracks` | سجل تتبع الطيران |
| `iranian_leader_news` | أخبار القادة الإيرانيين المرصودة |

---

## 🌐 النشر | Deployment

### 🖥️ تطبيق سطح المكتب (Windows)
ابنِ مثبّتاً مستقلاً عبر `packaging\build_installer.bat` (راجع [`packaging/README.md`](packaging/README.md)). الأنسب للاستخدام الشخصي بلا اعتماديات.

### 🐳 Docker (محلي أو VPS)
```bash
docker compose up -d --build
```
ينشر الـ Backend على `8000` والواجهة على `3000`.

### 📄 GitHub Pages (الواجهة فقط)
workflow جاهز في `.github/workflows/deploy-frontend.yml` يبني الواجهة وينشرها عند كل push إلى `main`.

1. **Settings → Pages** → اختر *Source: GitHub Actions*
2. (اختياري) أضف Secret باسم `VITE_API_BASE` يشير لـ Backend خارجي، مثل: `https://api.example.com/api`
3. ادفع تعديلات على `frontend/**` — يبدأ النشر تلقائياً

> ⚠️ **قيد مهم:** الـ Backend (FastAPI + SQLite + APScheduler) **لا يعمل على GitHub Pages** (ملفات ثابتة فقط). لنسخة عامة كاملة استضف الباك على Railway / Render / Fly.io واضبط `VITE_API_BASE`، أو شغّل المشروع محلياً.

---

## 🤝 المساهمة | Contributing

```bash
git checkout -b feat/my-feature
# عدّل، اختبر (pytest / npm test)، ثم:
git commit -m "feat: وصف التغيير"
git push origin feat/my-feature   # ثم افتح Pull Request
```

أنماط رسائل الـ commit: `feat:` · `fix:` · `docs:` · `refactor:` · `style:` · `test:` · `chore:`.

---

## 🗺️ خارطة الطريق | Roadmap

<details>
<summary>✅ الإصدارات السابقة (v1.1 → v1.4)</summary>

- **v1.1** — طبقة إيران OSINT + تصنيف الثقة + متابعة القادة
- **v1.2** — المنشآت النووية + التنبيهات الصوتية + نشر GitHub Pages
- **v1.3** — كرة 3D + i18n عربي/إنجليزي + مؤشر استخبارات الدول + قواعد/أنابيب
- **v1.4** — اختبارات (pytest + vitest) + CI + ETag caching + PWA

</details>

### ✅ v1.5 — تطبيق سطح المكتب وتحسينات (الحالي)
- [x] 🖥️ مثبّت ويندوز كامل (PyInstaller + Inno Setup) — exe واحد يقدّم الـ API والواجهة
- [x] 🎨 أيقونة تطبيق (طابع رادار) + favicon
- [x] 🖼️ تحسين عرض 3D — نقاط متوهّجة + حلقات رادار للأحداث العاجلة (بدل الأعمدة)
- [x] 🔔 صوت تنبيه جرسي محسّن (بدل الموجة المربّعة القاسية)
- [x] 🐛 إصلاحات: ظهور اللوحة الجانبية في وضع 3D · تنظيف `docker-compose` · `youtube-nocookie`

### 🔮 v2.0 — ذكاء وتحليل
- [ ] 🤖 **Ollama/Qwen AI** — تصنيف وتلخيص ذكي للأخبار العربية
- [ ] 🧠 **تحليل المشاعر** والكيانات (NER)
- [ ] 📡 **Telegram** + **Twitter/X** كمصادر إضافية
- [ ] 🎯 **Signal Convergence** — اكتشاف تقارب الإشارات تلقائياً
- [ ] 📄 **تقارير PDF** تلقائية
- [ ] 📍 تحديد موقع جغرافي دقيق (بدل مراكز الدول)

> 💡 خارطة الطريق مستوحاة جزئياً من المشروع المفتوح [worldmonitor](https://github.com/koala73/worldmonitor) كمصدر أفكار معمارية (مع الالتزام بترخيص رصد MIT).

---

## 🐛 استكشاف الأخطاء | Troubleshooting

| المشكلة | الحل |
|---------|------|
| **لا تظهر أخبار جديدة** | تأكد من تشغيل Backend (`/api/health`)، افحص `/api/collectors/status`، ثم اضغط 🔄 |
| **طبقة إيران OSINT فارغة** | تظهر بعد أول دورة جمع — انتظر دقيقة بعد التشغيل واضغط 🔄 (`/api/iran/strikes`) |
| **خطأ NewsAPI** | أضف `NEWSAPI_KEY` في `.env` (المفتاح المجاني يعطي أخباراً قديمة 24+ ساعة) |
| **UCDP لا يجمع شيئاً** | الـ API صار يتطلّب رمزاً — أضف `UCDP_ACCESS_TOKEN`، وإلا يظهر المصدر `disabled` في `/api/sources` |
| **الخريطة 2D لا تعمل** | تحقق من الإنترنت (Leaflet يحتاج tiles من CartoCDN) وافحص Console |
| **🖥️ المثبّت: تحذير SmartScreen/مكافح فيروسات** | طبيعي لتطبيق غير موقّع — اختر "Run anyway" (للتوقيع: شهادة Code Signing) |
| **🖥️ المنفذ 8000 مشغول** | أغلق أي نسخة عاملة (أو خادم تطوير) — التطبيق يكتفي بفتح المتصفح على النسخة العاملة |
| **🖥️ لا يُعثر على ISCC أثناء البناء** | ثبّت Inno Setup 6 وأضف مجلّده إلى PATH (أو افتح `rasad.iss` يدوياً واضغط Compile) |

---

## 📝 الترخيص | License

هذا المشروع للاستخدام الشخصي والتعليمي (MIT).

---

<div align="center">

**رصد** 🛰️ — صُنع بـ ❤️ للمعرفة والتوثيق
**Rsd** — Made with ❤️ for Knowledge and Documentation

---

المطور | Developer: **عبدالكريم العبود**

📧 abo.saleh.g@gmail.com

![GitHub](https://img.shields.io/badge/GitHub-abosalehg--ui-black?logo=github)

</div>
