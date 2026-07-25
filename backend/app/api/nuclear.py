"""رصد - نقاط API للمنشآت النووية"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/nuclear", tags=["nuclear"])

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "nuclear_facilities.json"


@lru_cache(maxsize=1)
def _load_data() -> dict:
    with _DATA_FILE.open("r", encoding="utf-8") as fp:
        return json.load(fp)


@router.get("/facilities")
async def list_facilities(
    country: Optional[str] = Query(default=None, description="ISO country code, e.g. IR"),
    facility_type: Optional[str] = Query(default=None, description="power|research|enrichment|conversion|heavy_water|fuel"),
    status: Optional[str] = Query(default=None, description="operational|construction|planned|shutdown|modified"),
):
    """قائمة المنشآت النووية (مفاعلات قوة، أبحاث، تخصيب، تحويل)"""
    data = _load_data()
    facilities = data.get("facilities", [])

    if country:
        cc = country.upper()
        facilities = [f for f in facilities if f.get("country_code") == cc]
    if facility_type:
        facilities = [f for f in facilities if f.get("type") == facility_type]
    if status:
        facilities = [f for f in facilities if f.get("status") == status]

    return {
        "total": len(facilities),
        "meta": data.get("_meta", {}),
        "facilities": facilities,
    }


@router.get("/facilities/{facility_id}")
async def get_facility(facility_id: str):
    """تفاصيل منشأة نووية محددة"""
    data = _load_data()
    for facility in data.get("facilities", []):
        if facility.get("id") == facility_id:
            return facility
    # كان يعيد {"error": ...} بحالة 200 فيظنّها العميل نجاحاً
    raise HTTPException(status_code=404, detail=f"منشأة غير موجودة: {facility_id}")


@router.get("/stats")
async def nuclear_stats():
    """إحصائيات إجمالية للمنشآت النووية"""
    data = _load_data()
    facilities = data.get("facilities", [])

    by_country: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total_capacity_mw = 0

    for fac in facilities:
        by_country[fac.get("country", "Unknown")] = by_country.get(fac.get("country", "Unknown"), 0) + 1
        by_type[fac.get("type", "unknown")] = by_type.get(fac.get("type", "unknown"), 0) + 1
        by_status[fac.get("status", "unknown")] = by_status.get(fac.get("status", "unknown"), 0) + 1
        if isinstance(fac.get("capacity_mw"), (int, float)):
            total_capacity_mw += fac["capacity_mw"]

    return {
        "total": len(facilities),
        "total_capacity_mw": round(total_capacity_mw, 1),
        "by_country": by_country,
        "by_type": by_type,
        "by_status": by_status,
    }
