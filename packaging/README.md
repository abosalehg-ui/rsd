# 📦 بناء مثبّت ويندوز لـ رصد (PyInstaller + Inno Setup)

دليل تحويل **رصد** إلى تطبيق ويندوز يُثبَّت بنقرة واحدة، بلا حاجة لتثبيت Python أو Node لدى المستخدم النهائي.

---

## 🧩 الفكرة المعمارية

رصد تطبيق عميل/خادم (Backend بايثون + Frontend ويب). لتغليفه في ملف واحد:

1. **الواجهة** تُبنى إلى ملفات ثابتة (`frontend/dist`).
2. **الخادم** (FastAPI + uvicorn) يُعدَّل ليقدّم تلك الملفات على `/` بالإضافة إلى الـ API على `/api` — فيصبح كل شيء على أصل واحد (`http://127.0.0.1:8000`).
3. **PyInstaller** يجمّع الخادم + ملفات البيانات + الواجهة المبنية في `rasad.exe` (وضع onedir).
4. **Inno Setup** يلفّ الناتج في مثبّت `Rasad-Setup-x64.exe` مع اختصارات وأيقونة وأداة إزالة.

نقطة الدخول هي `backend/run_desktop.py`: تُشغّل الخادم محلياً وتفتح المتصفح تلقائياً.

---

## ✅ المتطلّبات (على جهاز البناء — ويندوز)

| الأداة | الإصدار | الرابط |
|--------|---------|--------|
| Python | 3.10+ | <https://www.python.org/downloads/> (فعّل "Add to PATH") |
| Node.js | 18+ | <https://nodejs.org/> |
| Inno Setup | 6.x | <https://jrsoftware.org/isdl.php> |

> بعد تثبيت Inno Setup، أضِف مجلّده إلى `PATH` (عادةً `C:\Program Files (x86)\Inno Setup 6`) ليعمل أمر `ISCC`. أو يمكنك فتح ملف `.iss` يدوياً في الواجهة والضغط Compile.

---

## 🚀 البناء السريع (موصى به)

من جذر المستودع، نقرة مزدوجة على الملف أو من الطرفية:

```bat
packaging\build_installer.bat
```

يقوم تلقائياً بـ: بناء الواجهة → تثبيت متطلّبات بايثون + PyInstaller → التجميع → بناء المثبّت.

**الناتج:** `packaging\Output\Rasad-Setup-x64.exe`

---

## 🔧 البناء اليدوي (خطوة بخطوة)

```bat
REM 1) بناء الواجهة (من جذر المستودع)
cd frontend
npm ci
npm run build
cd ..

REM 2) تجهيز بايثون + PyInstaller
cd backend
pip install -r requirements.txt
cd ..
pip install pyinstaller

REM 3) التجميع (onedir) — يُنتج dist\rasad\rasad.exe
pyinstaller packaging\rasad.spec --noconfirm --clean

REM 4) المثبّت
ISCC packaging\rasad.iss
```

> اختبار الناتج قبل صنع المثبّت: شغّل `dist\rasad\rasad.exe` — يجب أن يفتح المتصفح على `http://127.0.0.1:8000`.

---

## 🎨 الأيقونة — التصميم والإضافة

الأيقونة جاهزة في `packaging/rasad.ico` (متعددة الأحجام 16→256)، بطابع رادار يطابق ثيم التطبيق.

### إعادة توليدها أو تخصيصها
الأيقونة تُولَّد برمجياً (Pillow) من `packaging/make_icon.py`:

```bash
pip install pillow
python packaging/make_icon.py
```

يُنتج: `packaging/rasad.ico` و `frontend/public/favicon.ico` و معاينة PNG. عدّل الألوان/الأشكال داخل السكربت لتغيير التصميم.

> بديل: استبدل `packaging/rasad.ico` بأي ملف `.ico` خاص بك (يُفضّل أن يحوي الأحجام 16/32/48/256).

### أين تُربط الأيقونة (3 مواضع)

| الموضع | الملف | السطر |
|--------|------|-------|
| أيقونة ملف `rasad.exe` | `packaging/rasad.spec` | `icon=str(ICON)` في كتلة `EXE(...)` |
| أيقونة المثبّت + الاختصارات | `packaging/rasad.iss` | `SetupIconFile=rasad.ico` و `IconFilename: "{app}\rasad.ico"` |
| أيقونة تبويب المتصفح (favicon) | `frontend/index.html` | `<link rel="icon" href="/favicon.ico">` |

كلّها تشير إلى الأيقونة نفسها، فيكفي تحديث `rasad.ico`/`favicon.ico` ثم إعادة البناء.

---

## 📁 أين تُحفظ البيانات بعد التثبيت

التطبيق يُثبَّت في `C:\Program Files\Rasad` (للقراءة فقط)، لذا تُكتب البيانات في مجلّد المستخدم:

```
%LOCALAPPDATA%\Rasad\
 ├─ rasad.db      ← قاعدة بيانات الأحداث (SQLite)
 └─ .env          ← (اختياري) مفاتيح API، مثل: NEWSAPI_KEY=xxxx
```

لإضافة مفتاح NewsAPI مثلاً: أنشئ `%LOCALAPPDATA%\Rasad\.env` وضع فيه `NEWSAPI_KEY=مفتاحك`.

---

## ⚠️ ملاحظات مهمة

- **المنفذ 8000**: التطبيق يعمل على `127.0.0.1:8000` فقط (لا يُعرَّض للشبكة، لا حاجة لإذن جدار حماية). إن كان المنفذ مشغولاً (مثلاً خادم تطوير يعمل) سيكتفي بفتح المتصفح على النسخة العاملة.
- **اختصار سطح المكتب**: يعرض المعالِج خانة "إنشاء اختصار على سطح المكتب" **مؤشَّرة افتراضياً**، فتُنشأ الأيقونة تلقائياً ما لم يُزل المستخدم العلامة. لجعلها إجبارية دائماً (بلا خانة) احذف سطر `desktopicon` من `[Tasks]` وأزل `Tasks: desktopicon` من سطر `{autodesktop}` في `[Icons]`؛ ولإخفائها افتراضياً أعِد `Flags: unchecked`.
- **مكافح الفيروسات / SmartScreen**: ملفات PyInstaller غير الموقّعة قد تُنبّه (تحذير "ناشر غير معروف"). هذا طبيعي لتطبيق غير موقّع رقمياً؛ اختر "Run anyway". للتوقيع، استخدم شهادة Code Signing مع `signtool`.
- **حجم المثبّت**: ~80–150MB (يتضمّن بايثون + المكتبات + الواجهة). يُفعّل ضغط `lzma2` في المثبّت.
- **الإيقاف**: أغلق نافذة الكونسول السوداء لإيقاف الخادم.
- **عربية المعالِج (اختياري)**: لجعل واجهة المثبّت عربية، نزّل `Arabic.isl` إلى مجلّد `Languages` في Inno Setup ثم أزِل التعليق عن سطر `arabic` في `rasad.iss`.
- **`console=True`**: الإصدار الحالي يُظهر نافذة كونسول بالسجلّ (مفيد للتشخيص). بعد الاستقرار يمكن جعلها `console=False` في `rasad.spec` لإخفائها.

---

## 🗂️ ملفات هذا المجلّد

| الملف | الوظيفة |
|------|---------|
| `rasad.spec` | مواصفات PyInstaller (تجميع الخادم + البيانات + الواجهة) |
| `rasad.iss` | سكربت Inno Setup (المثبّت + الاختصارات + الإزالة) |
| `build_installer.bat` | بناء كامل بأمر واحد |
| `make_icon.py` | مولّد الأيقونة (Pillow) |
| `rasad.ico` | الأيقونة الجاهزة |
| `rasad-icon-preview.png` | معاينة الأيقونة |
