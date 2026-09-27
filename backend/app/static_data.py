"""رصد - قراءة ملفات البيانات الثابتة المشتركة بين الطبقات (`app/data/*.json`).

طبقة الـ API لا تستورد قائمة القادة من `collectors/iran_osint` (يسحب معه
`httpx` و`feedparser` لمجرد سرد عشرة أسماء). القائمة بيانات لا كود، فمكانها
JSON بجانب المنشآت والقواعد، ويقرأها الجامع والـ API من هنا.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def _leaders_file() -> dict:
    with (DATA_DIR / "iranian_leaders.json").open("r", encoding="utf-8") as fp:
        return json.load(fp)


def iranian_leaders() -> list[dict]:
    """قائمة القادة الإيرانيين المتابَعين (نسخة جديدة في كل استدعاء كي لا
    يعدّل مستدعٍ القائمة المخزّنة مؤقتًا)."""
    return [dict(leader) for leader in _leaders_file().get("leaders", [])]
