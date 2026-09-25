"""
رصد (Rasad) — نقطة الدخول الوحيدة للتشغيل (Rasad.bat، والمثبّت عبر PyInstaller).

عملية واحدة: خادم uvicorn يقدّم الـ API والواجهة المبنية معًا، ثم يُفتح المتصفح.
أغلق النافذة لإيقاف التطبيق.

- **المنفذ**: 8000 افتراضًا. إن كان مشغولًا نتحقّق هل الذي عليه رصد نفسه (نفتح
  المتصفح عليه ونخرج) أم برنامج آخر (ننتقل لأول منفذ حرّ). كان مجرد انشغال
  المنفذ يُفسَّر «رصد يعمل بالفعل» فيُفتح المتصفح على برنامج غريب، وكانت
  الواجهة تعرض «تعذّر الاتصال بالخادم».
- **الواجهة**: خارج المثبّت نبني `frontend/dist` تلقائيًا إن كان غائبًا أو أقدم
  من المصدر (يتطلّب Node.js لذلك فقط؛ إن غاب Node ووُجدت نسخة مبنية نستعملها).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from app.config import get_settings

_settings = get_settings()
HOST = _settings.backend_host
PREFERRED_PORT = _settings.backend_port
PORT_TRIES = 20
FROZEN = getattr(sys, "frozen", False)
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def _url(port: int) -> str:
    return f"http://{'127.0.0.1' if HOST == '0.0.0.0' else HOST}:{port}"


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1" if HOST == "0.0.0.0" else HOST, port)) == 0


def _is_rasad(port: int) -> bool:
    """هل الخادم على هذا المنفذ رصد؟ (لا يكفي أن يكون المنفذ مشغولًا)."""
    try:
        with urllib.request.urlopen(f"{_url(port)}/api/health", timeout=2) as r:
            return "Rasad" in json.loads(r.read().decode("utf-8")).get("name", "")
    except Exception:  # noqa: BLE001 - أي فشل = ليس رصد
        return False


def _choose_port() -> tuple[int, bool]:
    """(المنفذ، هل رصد يعمل عليه مسبقًا)."""
    for port in range(PREFERRED_PORT, PREFERRED_PORT + PORT_TRIES):
        if not _port_in_use(port):
            return port, False
        if _is_rasad(port):
            return port, True
        print(f"  المنفذ {port} مشغول ببرنامج آخر — تجربة التالي…")
    raise SystemExit(f"لا يوجد منفذ حرّ بين {PREFERRED_PORT} و{PREFERRED_PORT + PORT_TRIES - 1}")


def _newest_mtime(root: Path) -> float:
    return max((p.stat().st_mtime for p in root.rglob("*") if p.is_file()), default=0.0)


def _ensure_frontend() -> None:
    """يبني الواجهة إن كانت غائبة أو أقدم من مصدرها."""
    if FROZEN or not (FRONTEND / "package.json").exists():
        return
    index = FRONTEND / "dist" / "index.html"
    sources = [FRONTEND / "src", FRONTEND / "index.html", FRONTEND / "package-lock.json"]
    newest_src = max(_newest_mtime(p) if p.is_dir() else p.stat().st_mtime for p in sources if p.exists())
    if index.exists() and index.stat().st_mtime >= newest_src:
        return

    npm = shutil.which("npm")
    if not npm:
        if index.exists():
            print("  تنبيه: الواجهة أقدم من مصدرها ولا يوجد Node.js لإعادة بنائها — تُستعمل النسخة الحالية.")
            return
        raise SystemExit(
            "الواجهة غير مبنية ولا يوجد Node.js لبنائها.\n"
            "ثبّت Node.js من https://nodejs.org ثم أعد تشغيل Rasad.bat (مرة واحدة فقط)."
        )

    print("  تجهيز الواجهة (مرة واحدة بعد كل تحديث)…")
    if not (FRONTEND / "node_modules").exists():
        subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=FRONTEND, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND, check=True)


def _open_browser_when_ready(url: str) -> None:
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1):
                break
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    port, already = _choose_port()
    url = _url(port)
    if already:
        print(f"رصد يعمل بالفعل على {url} — سيُفتح في المتصفح.")
        webbrowser.open(url)
        return

    try:
        _ensure_frontend()
    except subprocess.CalledProcessError as exc:
        print(f"\n❌ تعذّر بناء الواجهة: {exc}")
        if not FROZEN:
            input("اضغط Enter للخروج...")
        sys.exit(1)

    # الخادم يقبل أصل المنفذ المختار (CORS) حتى لو لم يكن 8000
    os.environ.setdefault("CORS_ORIGINS", f"{_settings.cors_origins},{url}")
    get_settings.cache_clear()

    from app.main import app  # بعد ضبط البيئة والواجهة

    threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()

    print("=" * 60)
    print(f"  رصد (Rasad) يعمل الآن على:  {url}")
    print("  سيُفتح المتصفح تلقائياً خلال ثوانٍ.")
    print("  أبقِ هذه النافذة مفتوحة — أغلقها لإيقاف التطبيق.")
    print("=" * 60)

    try:
        uvicorn.run(app, host=HOST, port=port, log_level="warning")
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ تعذّر تشغيل الخادم: {exc}")
        input("اضغط Enter للخروج...")
        sys.exit(1)


if __name__ == "__main__":
    main()
