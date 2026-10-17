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

**ملف `.env`:** رُفع سابقًا ثم أُزيل، ونُظّف تاريخ Git منه وأُبطلت مفاتيحه. فحص
التاريخ الكامل لا يُظهر أي commit أضاف `.env`:

```bash
git log --all --diff-filter=A -- .env    # لا نتائج
```

**وثيقة مراجعة 2026-07-30:** اقتبست مفتاح NewsAPI وسرّ عميل OpenSky **بنصّهما
الكامل**. حُجبت القيم في الشجرة الحالية (`docs/reviews/2026-07-30-code-review.md`)،
لكنها **ما زالت في تاريخ `main`**: الـ commit `ffd8cca` (الملف باسمه القديم
`CODE_REVIEW-2026-07-30.md`) وما بعده حتى الحجب. كل من يستنسخ المستودع يستطيع
قراءتها، فهي **مكشوفة** ما لم تُدوَّر. المطلوب من المالك، بالترتيب:

1. **دوِّر المفتاحين** من لوحتي NewsAPI وOpenSky (ثم ضع البديلين في `.env`).
   بعد التدوير لا تصلح القيم القديمة لشيء، وبقاؤها في التاريخ بلا أثر.
2. *(اختياري بعد التدوير)* إعادة كتابة التاريخ بـ
   `git filter-repo --replace-text <ملف القيمتين>` ثم دفع قسري وإبلاغ كل من
   استنسخ — إجراء مدمّر يكسر النسخ القائمة، فلا يُنفَّذ بديلًا عن التدوير.
3. فعّل **Secret scanning** و**Push protection** من Settings → Code security كي
   يُمنع دفع مفتاح جديد قبل أن يصل التاريخ.

لا يمكن التحقق من التدوير من داخل المستودع؛ حين يتم، حدّث هذه الفقرة بتاريخه.

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
  - فحص ترويسة `Host` (`middleware/trusted_host.py`): يُقبل فقط الحلقة المحلية
    ومضيفات `CORS_ORIGINS` و`BACKEND_HOST` و`ALLOWED_HOSTS`. يمنع **DNS rebinding**:
    صفحة خارجية تعيد توجيه نطاقها إلى 127.0.0.1 فتقرأ الـ API كأنها من الأصل نفسه
    (CORS لا يحمي هنا لأن المتصفح يراها الأصل نفسه).
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
