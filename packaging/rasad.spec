# -*- mode: python ; coding: utf-8 -*-
"""
رصد (Rasad) — مواصفات PyInstaller (وضع onedir).

يجمّع خادم الـ Backend (FastAPI + uvicorn) مع:
  - ملفات البيانات JSON (app/data) لطبقات النووي/القواعد/الأنابيب
  - الواجهة المبنية (frontend/dist) ليقدّمها الخادم على "/"

شغّله من جذر المستودع بعد بناء الواجهة:
    pyinstaller packaging/rasad.spec --noconfirm --clean

المُخرَج: dist/rasad/rasad.exe (+ ملفاته) — يلتقطه Inno Setup.
"""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent          # noqa: F821  (SPECPATH يوفّره PyInstaller)
BACKEND = ROOT / "backend"
DIST = ROOT / "frontend" / "dist"
ICON = ROOT / "packaging" / "rasad.ico"

# بيانات تُحزَم داخل التطبيق
datas = [(str(p), "app/data") for p in (BACKEND / "app" / "data").glob("*.json")]
if (DIST / "index.html").exists():
    datas.append((str(DIST), "frontend_dist"))
else:
    raise SystemExit(
        "frontend/dist غير موجود — ابنِ الواجهة أولاً:  cd frontend && npm run build"
    )

# استيرادات ديناميكية لا يكتشفها المحلّل تلقائياً
hiddenimports = [
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "websockets",
    "wsproto",
    "apscheduler.schedulers.asyncio",
    "apscheduler.executors.asyncio",
    "apscheduler.executors.pool",
    "apscheduler.triggers.interval",
    "apscheduler.triggers.cron",
    "apscheduler.triggers.date",
    "apscheduler.jobstores.memory",
    "aiosqlite",
    "feedparser",
    "dateutil",
]

a = Analysis(
    [str(BACKEND / "run_desktop.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "pytest_asyncio", "ruff", "PIL"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="rasad",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,                 # نافذة كونسول تُظهر السجلّ — أغلقها لإيقاف التطبيق
    disable_windowed_traceback=False,
    icon=str(ICON),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="rasad",
)
