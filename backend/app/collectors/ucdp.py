"""رصد - جامع بيانات UCDP (Uppsala Conflict Data Program)

يتطلّب رمز وصول: منذ أن أغلقت UCDP الـ API العام صار كل طلب بلا ترويسة
`x-ucdp-access-token` يُردّ بـ 401، فالمصدر بلا رمز لا يجمع شيئًا إطلاقًا.
لذلك نتعامل معه كمصدر اختياري مثل NewsAPI: بلا رمز نتخطّاه بسطر سجل واحد،
و`/api/sources` يعلنه `disabled` بدل `active`.

نطلب أحداث الشرق الأوسط وحدها ضمن نافذة الاحتفاظ، ثم نُسقط أي حدث خارجها —
حارس أخير يضمن ألّا نُخزّن صفوفًا أقدم من أوسع نافذة تعرضها الواجهة.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from ..config import get_settings
from ..models.database import get_session_factory, insert_event_if_new
from ..processors.text_analysis import COUNTRY_COORDS, ME_COUNTRY_NAMES

logger = logging.getLogger("rasad.ucdp")

UCDP_API_BASE = "https://ucdpapi.pcr.uu.se/api/gedevents"

# اسم الدولة كما يكتبه UCDP → رمز ISO. الإحداثيات والاسم العربي يأتيان من
# `text_analysis` (مصدر واحد) بدل نسختين محليّتين هنا.
UCDP_COUNTRY_CODES = {
    "Palestine": "PS",
    "Israel": "IL",
    "Yemen (North Yemen)": "YE",
    "Yemen": "YE",
    "Syria": "SY",
    "Lebanon": "LB",
    "Iran": "IR",
    "Iraq": "IQ",
    "Saudi Arabia": "SA",
    "Egypt": "EG",
    "Jordan": "JO",
    "Turkey (Ottoman Empire)": "TR",
    "Turkey": "TR",
    "Libya": "LY",
    "Sudan": "SD",
}

_PAGE_SIZE = 100


def _parse_ucdp_date(value) -> datetime | None:
    """تاريخ UCDP `YYYY-MM-DD[ HH:MM:SS]` → datetime واعٍ، أو None عند التعذّر.

    لا نقع على "الآن" عند الفشل (كما تفعل `parse_ymd` العامة): حدث بلا تاريخ
    صالح كان يظهر كخبر عاجل هذه اللحظة.
    """
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _severity_for(total_deaths: int) -> str:
    if total_deaths > 50:
        return "critical"
    if total_deaths > 10:
        return "high"
    if total_deaths > 0:
        return "medium"
    return "low"


def _request_params(settings, page: int, since: datetime) -> dict:
    """معاملات الاستعلام. الفلاتر قابلة للضبط لأن ترقيم مجموعات UCDP
    ومعرّفات الدول تتغيّر بين الإصدارات — راجع توثيق UCDP عند تعديلها."""
    params: dict[str, object] = {
        "pagesize": _PAGE_SIZE,
        "page": page,
        "StartDate": since.strftime("%Y-%m-%d"),
    }
    country_ids = settings.ucdp_country_ids.strip()
    if country_ids:
        params["Country"] = country_ids
    return params


async def collect_ucdp_events() -> int:
    """جمع أحداث النزاعات الحديثة من UCDP.

    يعيد 0 بلا رمز وصول (مصدر معطّل بالإعداد، ليس فشلًا)، ويرفع استثناءً عند
    فشل الطلب فعليًا كي يُميّز `/api/collectors/status` المعطّل من الهادئ.
    """
    settings = get_settings()
    if not settings.ucdp_access_token:
        logger.info("UCDP: لا رمز وصول (UCDP_ACCESS_TOKEN) — المصدر متخطّى")
        return 0

    session_factory = get_session_factory()
    if not session_factory:
        return 0

    count = 0
    skipped_old = 0
    fetched = 0
    since = datetime.now(timezone.utc) - timedelta(days=settings.retention_events_days)
    url = f"{UCDP_API_BASE}/{settings.ucdp_dataset}"
    headers = {"x-ucdp-access-token": settings.ucdp_access_token}

    try:
        async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
            async with session_factory() as session:
                for page in range(settings.ucdp_max_pages):
                    response = await client.get(url, params=_request_params(settings, page, since))

                    if response.status_code == 401:
                        raise RuntimeError(
                            "UCDP: رمز الوصول مرفوض (401) — تحقّق من UCDP_ACCESS_TOKEN"
                        )
                    if response.status_code != 200:
                        raise RuntimeError(f"UCDP: HTTP {response.status_code}")

                    events = response.json().get("Result", [])
                    fetched += len(events)

                    for event_data in events:
                        try:
                            stored, too_old = await _store_event(session, event_data, since)
                            count += int(stored)
                            skipped_old += int(too_old)
                        except Exception as e:
                            logger.error(f"خطأ في حدث UCDP: {e}")
                            continue

                    if len(events) < _PAGE_SIZE:
                        break

                await session.commit()

    except Exception as e:
        logger.error(f"خطأ عام في UCDP: {e}")
        raise  # إشارة فشل صادقة بدل 0 صامت

    if fetched and not count and skipped_old == fetched:
        logger.warning(
            "UCDP: كل الأحداث المُعادة (%s) أقدم من نافذة الاحتفاظ (%s يومًا) — "
            "غالبًا UCDP_DATASET يشير إلى مجموعة سنوية قديمة بدل مجموعة المرشّحين الشهرية",
            fetched, settings.retention_events_days,
        )

    logger.info(f"UCDP: تم جمع {count} حدث نزاع جديد من {fetched} صفًا")
    return count


async def _store_event(session, event_data: dict, since: datetime) -> tuple[bool, bool]:
    """يخزّن حدث UCDP واحدًا. يعيد (أُدرِج، تُخطّي لقِدَمه)."""
    code = UCDP_COUNTRY_CODES.get(event_data.get("country", ""))
    if not code:
        return False, False

    event_date = _parse_ucdp_date(event_data.get("date_start"))
    if event_date is None:
        return False, False
    if event_date < since:
        # أقدم من أوسع نافذة تعرضها الواجهة — تخزينه يعني صفًا لا يراه أحد
        return False, True

    event_id = event_data.get("id", "")
    default_lat, default_lon, _ = COUNTRY_COORDS[code]
    lat = event_data.get("latitude")
    lon = event_data.get("longitude")

    deaths_a = event_data.get("deaths_a", 0) or 0
    deaths_b = event_data.get("deaths_b", 0) or 0
    deaths_civilians = event_data.get("deaths_civilians", 0) or 0
    total_deaths = deaths_a + deaths_b + deaths_civilians

    side_a = event_data.get("side_a", "")
    side_b = event_data.get("side_b", "")

    inserted = await insert_event_if_new(
        session,
        source="ucdp",
        source_id=f"ucdp_{event_id}",
        title=f"نزاع مسلح: {side_a} vs {side_b} - {event_data.get('country', '')}",
        description=f"وفيات: {total_deaths} (مدنيون: {deaths_civilians})",
        url=f"https://ucdp.uu.se/event/{event_id}",
        category="military",
        severity=_severity_for(total_deaths),
        # `is None` وليس `or`: حدث على خط الاستواء (0.0) إحداثي صحيح
        latitude=float(lat) if isinstance(lat, (int, float, str)) and str(lat) != "" else default_lat,
        longitude=float(lon) if isinstance(lon, (int, float, str)) and str(lon) != "" else default_lon,
        country=ME_COUNTRY_NAMES.get(code, ""),
        country_code=code,
        location_name=event_data.get("where_description", ""),
        event_date=event_date,
        extra_data=json.dumps({
            "deaths_total": total_deaths,
            "deaths_civilians": deaths_civilians,
            "side_a": side_a,
            "side_b": side_b,
            "type_of_violence": event_data.get("type_of_violence", ""),
        }),
    )
    return bool(inserted), False
