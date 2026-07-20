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

## نطاق | Scope

رصد أداة OSINT شخصية تجمع بيانات عامة من مصادر خارجية. النقاط الحسّاسة:

- **الأسرار:** مفاتيح API تُحفظ في `.env` محلي فقط (غير مُتتبَّع في Git). راجع
  `.env.example`. لا تُدرج مفاتيح حقيقية في أي Issue أو PR أو لقطة شاشة.
- **المدخلات الخارجية:** محتوى الخلاصات (RSS/OSINT) غير موثوق ويُعقَّم قبل العرض
  (`utils/security.js` في الواجهة). أبلغ عن أي مسار يتجاوز هذا التعقيم.
- **الشبكة:** الخادم افتراضياً بلا مصادقة — لا تعرضه للإنترنت العام دون طبقة
  حماية أمامك (عكس وكيل + مصادقة).

## الإصدارات المدعومة | Supported Versions

يُدعم آخر إصدار على فرع `main` فقط.
Only the latest release on `main` is supported.
