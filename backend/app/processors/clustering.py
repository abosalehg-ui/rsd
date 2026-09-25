"""رصد - تجميع الأخبار المتشابهة في «قصص».

إزالة التكرار كانت بالرابط وحده، فالخبر نفسه من الجزيرة والعربية وسكاي
يظهر ثلاث مرات، ويُعدّ ثلاث مرات في مؤشر التصعيد. هنا يُنسب كل حدث إلى
«قصة» (`cluster_id` = معرّف أول حدث فيها) إن تشابه عنوانه مع عنوان حدث سابق
خلال نافذة زمنية.

التشابه: معامل التداخل بين مجموعتي الكلمات الدالّة (بعد حذف كلمات الربط
وسوابق الإلصاق العربية): |أ∩ب| / min(|أ|,|ب|) ≥ 0.6 مع ثلاث كلمات مشتركة
على الأقل. عتبة محافظة: ندمج أقل مما ينبغي ولا ندمج خبرين مختلفين.

لا يجمع بين لغتين (العربي والإنجليزي عن الحدث نفسه قصتان) — يحتاج ذلك
ترجمة أو تضمينًا دلاليًا، وهو خارج نطاق هذه الطبقة.
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta

from sqlalchemy import select, update

from .normalize import normalize_for_match

logger = logging.getLogger("rasad.clustering")

WINDOW = timedelta(hours=36)
MIN_SHARED = 3
MIN_OVERLAP = 0.6

_TOKEN_RE = re.compile(r"[\w%]+")
_AR_PREFIXES = ("وال", "بال", "فال", "كال", "لل", "ال", "و", "ف", "ب", "ل")

_STOPWORDS = {normalize_for_match(w) for w in (
    # إنجليزي
    "the a an of in on at to for from by with and or but as is are was were be been has have had "
    "it its this that these those after before over under about into amid says said say new live "
    "update updates latest breaking news report reports video watch photos how why what who will "
    "would could can may not no than more most up out off".split()
    # عربي
    + "في من على إلى الى عن مع بعد قبل حول ضد عند لدى هذا هذه ذلك تلك التي الذي الذين هو هي "
    "كان كانت يكون تكون قد لقد لم لن لا ما ماذا كيف لماذا أن إن أو ثم بين خلال منذ حتى عبر "
    "مباشر عاجل فيديو صور تقرير جديد قال يقول تقول أكد".split()
)}


def title_tokens(title: str) -> frozenset[str]:
    """الكلمات الدالّة في عنوان — مُطبّعة، بلا كلمات ربط، بلا سوابق عربية."""
    tokens = set()
    for tok in _TOKEN_RE.findall(normalize_for_match(title)):
        if tok in _STOPWORDS:
            continue
        for pre in _AR_PREFIXES:
            if tok.startswith(pre) and len(tok) - len(pre) >= 3:
                tok = tok[len(pre):]
                break
        if len(tok) >= 3 or tok.isdigit():
            tokens.add(tok)
    return frozenset(tokens)


def similar(a: frozenset[str], b: frozenset[str]) -> bool:
    if not a or not b:
        return False
    shared = len(a & b)
    return shared >= MIN_SHARED and shared / min(len(a), len(b)) >= MIN_OVERLAP


async def assign_story_clusters(session, since) -> int:
    """يُسند `cluster_id` لكل حدث بلا قصة منذ `since`. يعيد عدد المُسنَد.

    القصص المرشّحة: أحداث مُسنَدة في النافذة نفسها (+36 ساعة قبلها)، بفهرس
    معكوس كلمة → قصص كي لا نقارن كل حدث بكل قصة.
    """
    from ..models.database import Event

    rows = (await session.execute(
        select(Event.id, Event.title, Event.event_date, Event.cluster_id)
        .where(Event.event_date >= since - WINDOW)
        .order_by(Event.event_date.asc(), Event.id.asc())
    )).all()

    reps: dict[int, tuple[frozenset[str], object]] = {}   # cluster_id → (كلمات، تاريخ)
    index: dict[str, set[int]] = {}
    updates: dict[int, int] = {}

    def _register(cid: int, toks: frozenset[str], date) -> None:
        if cid in reps:
            return
        reps[cid] = (toks, date)
        for t in toks:
            index.setdefault(t, set()).add(cid)

    for ev_id, title, date, cluster_id in rows:
        toks = title_tokens(title or "")
        if cluster_id is not None:
            _register(cluster_id, toks, date)
            continue

        best = None
        candidates = set()
        for t in toks:
            candidates |= index.get(t, set())
        for cid in candidates:
            rtoks, rdate = reps[cid]
            if date is not None and rdate is not None and abs(date - rdate) > WINDOW:
                continue
            if similar(toks, rtoks):
                shared = len(toks & rtoks)
                if best is None or shared > best[1]:
                    best = (cid, shared)

        cid = best[0] if best else ev_id
        updates[ev_id] = cid
        _register(cid, toks, date)

    for ev_id, cid in updates.items():
        await session.execute(update(Event).where(Event.id == ev_id).values(cluster_id=cid))
    if updates:
        await session.commit()
    merged = sum(1 for ev_id, cid in updates.items() if ev_id != cid)
    if merged:
        logger.info("🧩 تجميع القصص: %s حدث أُلحق بقصص قائمة (من %s)", merged, len(updates))
    return len(updates)
