"""رصد - اختبارات طبقة قاعدة البيانات: الإدراج المانع للتكرار."""
import pytest
from sqlalchemy import func, select

from app.models.database import Event, get_session_factory, insert_event_if_new


async def _count(source_id: str) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        return (await session.execute(
            select(func.count(Event.id)).where(Event.source_id == source_id)
        )).scalar()


@pytest.mark.asyncio
async def test_insert_event_if_new_inserts_once():
    session_factory = get_session_factory()
    async with session_factory() as session:
        inserted = await insert_event_if_new(
            session, source="dedup_test", source_id="dedup_1", title="أول"
        )
        await session.commit()
    assert inserted is True
    assert await _count("dedup_1") == 1


@pytest.mark.asyncio
async def test_insert_event_if_new_is_a_noop_on_conflict():
    """التكرار يعيد False ولا يرمي ولا يُنشئ صفّاً ثانياً."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        await insert_event_if_new(session, source="dedup_test", source_id="dedup_2", title="أول")
        await session.commit()

    async with session_factory() as session:
        again = await insert_event_if_new(
            session, source="dedup_test", source_id="dedup_2", title="ثانٍ مختلف"
        )
        await session.commit()

    assert again is False
    assert await _count("dedup_2") == 1


@pytest.mark.asyncio
async def test_conflicting_insert_does_not_abort_the_batch():
    """انحدار: تعارض واحد كان يُسقط الدفعة كاملة في النمط القديم."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        await insert_event_if_new(session, source="dedup_test", source_id="batch_dup", title="موجود")
        await session.commit()

    results = []
    async with session_factory() as session:
        for sid in ("batch_a", "batch_dup", "batch_b"):
            results.append(
                await insert_event_if_new(session, source="dedup_test", source_id=sid, title=sid)
            )
        await session.commit()

    assert results == [True, False, True]
    assert await _count("batch_a") == 1
    assert await _count("batch_b") == 1


@pytest.mark.asyncio
async def test_cleanup_dedup_rows():
    """تنظيف صفوف هذا الملف كي لا تتسرّب إلى اختبارات أخرى."""
    from sqlalchemy import delete

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(Event).where(Event.source == "dedup_test"))
        await session.commit()
    assert await _count("dedup_1") == 0
