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

## ⚠️ إجراء مطلوب: أسرار في تاريخ Git

ملف `.env` كان مرفوعاً في المستودع سابقاً وأُزيل من شجرة العمل في الـ commit
`f565426`، **لكنه ما يزال قابلاً للاسترجاع من تاريخ Git**:

```bash
git show f565426^:.env      # يُظهر NEWSAPI_KEY و OPENSKY_CLIENT_SECRET
```

الإزالة من الشجرة لا تُبطل مفتاحاً مكشوفاً. المطلوب من مالك المستودع:

1. **أبطِل المفتاحين فوراً وأصدر بديلين** — هذه الخطوة غير قابلة للتأجيل ولا
   تُغني عنها إعادة كتابة التاريخ:
   - NewsAPI: <https://newsapi.org/account>
   - OpenSky: <https://opensky-network.org/> → Account → API Clients
2. **نظّف التاريخ** (يُعيد كتابة الـ commits ويتطلّب دفعاً قسرياً — نسّق مع أي
   شخص لديه نسخة مستنسخة قبل التنفيذ):
   ```bash
   git filter-repo --path .env --invert-paths
   git push --force-with-lease --all
   ```
3. **فعّل الحماية الاستباقية:** Settings → Code security → Secret scanning +
   Push protection.

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
    الحلقة المحلية.
  - `API_KEY` يحمي `POST /api/refresh` (الترويسة `X-API-Key`).
  - حدّ معدل لكل IP على مسارات `/api` (`RATE_LIMIT_REQUESTS`).
  - ترويسات أمنية (CSP وغيرها) في `frontend/nginx.conf`.
  لا تعرضه للإنترنت العام دون وكيل عكسي بـ TLS ومصادقة أمامه.

## الإصدارات المدعومة | Supported Versions

يُدعم آخر إصدار على فرع `main` فقط.
Only the latest release on `main` is supported.
