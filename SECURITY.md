# سياسة الأمن | Security Policy

## الإبلاغ عن ثغرة | Reporting a Vulnerability

إذا اكتشفت ثغرة أمنية في **رصد (Rasad)**، نرجو **عدم فتح Issue عام**.
بدلاً من ذلك أبلغ عنها بشكل خاص عبر:

- **GitHub Security Advisories:** بوّابة *Security → Report a vulnerability* في المستودع.
- أو راسل مالك المستودع مباشرة.

If you discover a security vulnerability in **Rasad**, please **do not open a
public issue**. Report it privately via GitHub Security Advisories
(*Security → Report a vulnerability*) or by contacting the maintainer directly.

سنحاول الرد خلال **72 ساعة** والإفصاح المنسّق بعد توفّر إصلاح.
We aim to respond within **72 hours** and to coordinate disclosure once a fix
is available.

## حالة الأسرار في تاريخ Git

سبق أن رُفع ملف `.env` إلى المستودع وأُزيل، **ثم نُظّف تاريخ Git من الملف
وأُبطلت المفاتيح المكشوفة وأُصدرت بدائل**. فحص التاريخ الكامل الآن لا يُظهر أي
commit أضاف `.env`:

```bash
git log --all --diff-filter=A -- .env    # لا نتائج
```

فلا حاجة لإعادة كتابة التاريخ. (كان هذا القسم يوجّه إلى `git filter-repo`
ودفعٍ قسري استنادًا إلى commit لم يعد موجودًا — إجراء مدمّر بلا سبب.)

الحماية الاستباقية المطلوبة تبقى: تفعيل Secret scanning و Push protection من
Settings → Code security.

روابط خلاصات Google Alerts كانت أيضاً مثبّتة في المصدر (وهي أسرار شخصية لأنها
تتضمّن معرّف الحساب)؛ نُقلت إلى `GOOGLE_ALERT_FEEDS` في `.env`. إن كنت تستخدم
الروابط القديمة فاحذف تلك التنبيهات من <https://www.google.com/alerts> وأنشئ
غيرها.

## نطاق | Scope

رصد أداة OSINT شخصية تجمع بيانات عامة من مصادر خارجية. النقاط الحسّاسة:

- **الأسرار:** مفاتيح API تُحفظ في `.env` محلي فقط (غير مُتتبَّع في Git). راجع
  `.env.example`. لا تُدرج مفاتيح حقيقية في أي Issue أو PR أو لقطة شاشة.
- **المدخلات الخارجية:** محتوى الخلاصات (RSS/OSINT) غير موثوق ويُعقَّم قبل العرض
  (`utils/security.js` في الواجهة). أبلغ عن أي مسار يتجاوز هذا التعقيم.
- **الشبكة:** الخادم بلا حسابات مستخدمين. الضوابط المتاحة:
  - `BACKEND_HOST` افتراضه `127.0.0.1`، وملفّا compose يربطان المنافذ على
    الحلقة المحلية. يُسجَّل تحذير عند البدء إن كان المضيف غير محلي بلا `API_KEY`.
  - حارس CSRF: `POST /api/refresh` يشترط الترويسة `X-Rasad-Client` دائماً.
    ترويسة غير بسيطة تُلزم المتصفح بطلب preflight يرفضه الخادم لأي أصل خارج
    `CORS_ORIGINS`، فلا تستطيع صفحة خارجية إطلاق الجامعين على جهاز المستخدم
    (CORS يمنع *قراءة* الرد لا *إرساله*).
  - `API_KEY` يحمي `POST /api/refresh` إضافةً لذلك (الترويسة `X-API-Key`).
  - حدّ معدل لكل IP على مسارات `/api` (`RATE_LIMIT_REQUESTS`). لا يُوثَق بترويسة
    `X-Forwarded-For` إلا عند ضبط `TRUST_PROXY_HEADERS=true` (وضع الإنتاج خلف
    nginx فقط)، وإلا يمكن انتحال IP لتجاوز الحدّ.
  - ترويسات أمنية (CSP وغيرها) في ثلاثة مواضع بحسب هدف النشر:
    `frontend/security-headers.conf` (nginx)، و`<meta>` في `index.html` (نشر
    GitHub Pages بلا خادم)، و`backend/app/middleware/security_headers.py`
    (وضع سطح المكتب حيث تُقدَّم الواجهة من FastAPI). `script-src` بلا
    `'unsafe-inline'` ولا `'unsafe-eval'`.
  لا تعرضه للإنترنت العام دون وكيل عكسي بـ TLS ومصادقة أمامه.
- **مفتاح الواجهة `VITE_API_KEY`:** أي متغيّر `VITE_*` **يُدمَج في حزمة
  JavaScript المبنية** فيصبح عاماً لكل زائر. اضبطه فقط لبناء محلي/سطح مكتب،
  **ولا تضبطه أبداً لنشر عام** (GitHub Pages) فذلك ينشر مفتاح الخادم للعالم.

## الإصدارات المدعومة | Supported Versions

يُدعم آخر إصدار على فرع `main` فقط.
Only the latest release on `main` is supported.
