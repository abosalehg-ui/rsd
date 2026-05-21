"""
رصد - test fixtures

نبني FastAPI app مصغّر للاختبار يتفادى lifespan الإنتاج (الذي يُشغّل
المجدول وجامعي البيانات الخارجيين). نستعمل قاعدة بيانات SQLite في الذاكرة.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# قاعدة بيانات اختبار في ملف مؤقّت (in-memory لا يصلح لأن aiosqlite لا يشاركها بين الاتصالات)
_TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP_DB.close()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB.name}"

from app.api.events import router as events_router  # noqa: E402
from app.api.infrastructure import router as infrastructure_router  # noqa: E402
from app.api.nuclear import router as nuclear_router  # noqa: E402
from app.models.database import Event, get_session_factory, init_db  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _init_database():
    """تهيئة قاعدة الاختبار مرة واحدة."""
    await init_db(os.environ["DATABASE_URL"])
    yield
    try:
        os.unlink(_TMP_DB.name)
    except OSError:
        pass


@pytest.fixture
def app() -> FastAPI:
    """تطبيق FastAPI نظيف بدون lifespan/scheduler/collectors."""
    test_app = FastAPI(title="rsd-test")
    test_app.include_router(events_router)
    test_app.include_router(infrastructure_router)
    test_app.include_router(nuclear_router)
    return test_app


@pytest_asyncio.fixture
async def client(app: FastAPI):
    """عميل HTTP غير متزامن مُرتبط بـ ASGI مباشرة."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_events():
    """يضع بضعة أحداث في قاعدة البيانات لاختبار /api/events/*"""
    session_factory = get_session_factory()
    now = datetime.now(timezone.utc)
    samples = [
        Event(
            source="test",
            title="هجوم تجريبي على نباطيم",
            description="حدث تجريبي عسكري حرج",
            url="https://example.com/a",
            category="military",
            severity="critical",
            confidence="HIGH",
            latitude=31.207,
            longitude=35.011,
            country="Israel",
            country_code="IL",
            event_date=now - timedelta(hours=2),
            collected_at=now,
        ),
        Event(
            source="test",
            title="إعلان دبلوماسي إيراني",
            description="بيان رسمي",
            url="https://example.com/b",
            category="diplomatic",
            severity="medium",
            confidence="MEDIUM",
            latitude=35.689,
            longitude=51.389,
            country="Iran",
            country_code="IR",
            event_date=now - timedelta(hours=5),
            collected_at=now,
        ),
        Event(
            source="test",
            title="تدريبات روسية في طرطوس",
            description="نشاط بحري عسكري",
            url="https://example.com/c",
            category="military",
            severity="high",
            confidence="LOW",
            latitude=34.895,
            longitude=35.872,
            country="Syria",
            country_code="SY",
            event_date=now - timedelta(hours=10),
            collected_at=now,
        ),
    ]
    async with session_factory() as session:
        # تنظيف أحداث الاختبار السابقة
        from sqlalchemy import delete
        await session.execute(delete(Event).where(Event.source == "test"))
        for ev in samples:
            session.add(ev)
        await session.commit()
    yield samples
    async with session_factory() as session:
        from sqlalchemy import delete
        await session.execute(delete(Event).where(Event.source == "test"))
        await session.commit()
