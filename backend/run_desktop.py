"""
رصد (Rasad) — نقطة دخول تطبيق سطح المكتب (يُجمَّع عبر PyInstaller).

تشغّل خادم uvicorn محلياً (127.0.0.1:8000) الذي يقدّم الـ API والواجهة المبنية
معاً، ثم تفتح المتصفح تلقائياً على الواجهة. أغلق نافذة الكونسول لإيقاف التطبيق.
"""
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def _open_browser_when_ready() -> None:
    # انتظر حتى يستجيب الخادم ثم افتح المتصفح
    for _ in range(60):
        if _port_in_use(HOST, PORT):
            break
        time.sleep(0.5)
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def main() -> None:
    # إن كان التطبيق يعمل مسبقاً على المنفذ نفسه — افتح المتصفح فقط واخرج
    if _port_in_use(HOST, PORT):
        print(f"رصد يعمل بالفعل على {URL} — سيُفتح في المتصفح.")
        webbrowser.open(URL)
        return

    from app.main import app  # استيراد بعد ضبط المسارات

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    print("=" * 60)
    print(f"  رصد (Rasad) يعمل الآن على:  {URL}")
    print("  سيُفتح المتصفح تلقائياً خلال ثوانٍ.")
    print("  أبقِ هذه النافذة مفتوحة — أغلقها لإيقاف التطبيق.")
    print("=" * 60)

    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ تعذّر تشغيل الخادم: {exc}")
        input("اضغط Enter للخروج...")
        sys.exit(1)


if __name__ == "__main__":
    main()
