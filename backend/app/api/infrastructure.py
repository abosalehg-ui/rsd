"""رصد - نقاط API للبنية التحتية (قواعد عسكرية + خطوط أنابيب)"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/infrastructure", tags=["infrastructure"])

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _load_bases() -> dict:
    with (_DATA_DIR / "military_bases.json").open("r", encoding="utf-8") as fp:
        return json.load(fp)


@lru_cache(maxsize=1)
def _load_pipelines() -> dict:
    with (_DATA_DIR / "pipelines.json").open("r", encoding="utf-8") as fp:
        return json.load(fp)


@router.get("/bases")
async def list_bases(
    country: Optional[str] = Query(default=None, max_length=10, description="ISO country code"),
    operator: Optional[str] = Query(default=None, max_length=50, description="e.g. US, Russia, IRGC"),
    base_type: Optional[str] = Query(default=None, max_length=20, description="air|naval|ground|joint"),
):
    """قائمة القواعد العسكرية"""
    data = _load_bases()
    bases = data.get("bases", [])
    if country:
        cc = country.upper()
        bases = [b for b in bases if b.get("country_code") == cc]
    if operator:
        bases = [b for b in bases if operator.lower() in (b.get("operator", "")).lower()]
    if base_type:
        bases = [b for b in bases if b.get("type") == base_type]
    return {"total": len(bases), "meta": data.get("_meta", {}), "bases": bases}


@router.get("/pipelines")
async def list_pipelines(
    pipeline_type: Optional[str] = Query(default=None, max_length=20, description="oil|gas"),
    status: Optional[str] = Query(default=None, max_length=20),
):
    """قائمة خطوط الأنابيب (مع waypoints)"""
    data = _load_pipelines()
    pipelines = data.get("pipelines", [])
    if pipeline_type:
        pipelines = [p for p in pipelines if p.get("type") == pipeline_type]
    if status:
        pipelines = [p for p in pipelines if p.get("status") == status]
    return {"total": len(pipelines), "meta": data.get("_meta", {}), "pipelines": pipelines}
