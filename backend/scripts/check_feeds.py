"""رصد - فحص حيويّة خلاصات الإنتاج (RSS · إيران OSINT · الرصد النووي).

يجلب كل خلاصة مسجّلة في الجامعين ويتحقق أنها تردّ 200 وتحوي إدخالًا واحدًا
على الأقل. يخرج بحالة غير صفرية عند أي خلاصة ميتة ويطبع تقريرًا — يشغّله CI
أسبوعيًا (`.github/workflows/feed-health.yml`) فتظهر الخلاصات المعطّلة في
Issue بدل أن تفشل بصمت كل نصف ساعة في السجل.

التشغيل يدويًا من مجلد backend:
    python scripts/check_feeds.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import httpx  # noqa: E402

from app.collectors._feed_base import FEED_HEADERS, parse_feed_async  # noqa: E402
from app.collectors.iran_osint import IRAN_OSINT_FEEDS  # noqa: E402
from app.collectors.nuclear_watch import NUCLEAR_FEEDS  # noqa: E402
from app.collectors.rss_feeds import RSS_FEEDS  # noqa: E402

TIMEOUT = 25.0
CONCURRENCY = 6


def all_feeds() -> list[tuple[str, str, str]]:
    feeds: list[tuple[str, str, str]] = []
    for group in RSS_FEEDS.values():
        feeds.extend(("rss", f["name"], f["url"]) for f in group)
    feeds.extend(("iran_osint", f["name"], f["url"]) for f in IRAN_OSINT_FEEDS)
    feeds.extend(("nuclear_watch", f["name"], f["url"]) for f in NUCLEAR_FEEDS)
    return feeds


async def check(client: httpx.AsyncClient, sem: asyncio.Semaphore, collector: str, name: str, url: str) -> dict:
    async with sem:
        try:
            response = await client.get(url)
        except httpx.HTTPError as exc:
            return {"collector": collector, "name": name, "url": url, "ok": False, "detail": type(exc).__name__}
        if response.status_code != 200:
            return {"collector": collector, "name": name, "url": url, "ok": False, "detail": f"HTTP {response.status_code}"}
        feed = await parse_feed_async(response.text)
        entries = len(feed.entries)
        return {
            "collector": collector, "name": name, "url": url,
            "ok": entries > 0, "detail": f"{entries} entries" if entries else "no entries",
        }


async def main() -> int:
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=FEED_HEADERS) as client:
        results = await asyncio.gather(*(check(client, sem, *feed) for feed in all_feeds()))

    dead = [r for r in results if not r["ok"]]
    print(f"{len(results)} feeds checked — {len(results) - len(dead)} alive, {len(dead)} dead\n")
    for r in results:
        mark = "OK " if r["ok"] else "DEAD"
        print(f"[{mark}] {r['collector']:14} {r['name']:40} {r['detail']:14} {r['url']}")
    if dead:
        print("\nDEAD FEEDS:")
        for r in dead:
            print(f"- {r['collector']} · {r['name']} · {r['detail']} · {r['url']}")
    return 1 if dead else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
