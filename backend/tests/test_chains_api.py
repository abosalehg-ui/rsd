"""رصد - اختبارات تخزين سلاسل السبب والأثر ونقاطها: الحساب التزايدي وعدم
التكرار، والتنظيف مع الأحداث، و`/api/events/{id}/chain` و`/api/chains`،
وإدراج السلاسل ومؤشر الأثر في التقرير الدوري."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, func, select

from app.api import chains as chains_api
from app.models import database
from app.models.database import Event, EventLink, get_session_factory
from app.processors import causal

SOURCE = "chains_test"
# «الآن» ثابت في الماضي البعيد: أحداث الاختبارات الأخرى خارج نوافذ هذه الاختبارات
NOW = datetime(2001, 6, 1, 12, 0, tzinfo=timezone.utc)


def _event(title, *, hours_ago, n, source_name="Wire", **fields):
    return Event(
        source=SOURCE,
        source_id=f"{SOURCE}_{n}",
        title=title,
        description="",
        url=f"https://example.com/{n}",
        category=fields.pop("category", "military"),
        severity=fields.pop("severity", "high"),
        event_date=NOW - timedelta(hours=hours_ago),
        collected_at=fields.pop("collected_at", datetime.now(timezone.utc)),
        extra_data=json.dumps({"source_name": source_name}),
        **fields,
    )


async def _clear():
    async with get_session_factory()() as session:
        ids = select(Event.id).where(Event.source == SOURCE)
        await session.execute(delete(EventLink).where(
            EventLink.cause_id.in_(ids) | EventLink.effect_id.in_(ids)
        ))
        await session.execute(delete(Event).where(Event.source == SOURCE))
        await session.commit()
    causal._FACTS_CACHE.clear()


@pytest.fixture
async def chain_seed():
    """ضربة ← رد ← قفزة النفط، وخبر ثانٍ في قصة الرد، وخبر بلا صلة."""
    await _clear()
    async with get_session_factory()() as session:
        rows = {
            "strike": _event("Israel strikes targets in Iran", hours_ago=30, n=1),
            "retaliation": _event("Iran launches retaliatory strikes on Israel", hours_ago=20, n=2),
            "oil": _event("Oil prices jump as Iran retaliation spreads", hours_ago=10, n=3,
                          category="economic", severity="low"),
            "unrelated": _event("Ceasefire talks resume in Muscat", hours_ago=5, n=4,
                                category="diplomatic", severity="medium"),
        }
        session.add_all(rows.values())
        await session.commit()
        for ev in rows.values():
            ev.cluster_id = ev.id
        # خبر ثانٍ من مصدر آخر في قصة الرد نفسها
        # أقل شدة فلا يصير ممثّل القصة
        dup = _event("Iran fires missiles at Israel in response", hours_ago=19, n=5, source_name="Other",
                     severity="medium", cluster_id=rows["retaliation"].id)
        session.add(dup)
        await session.commit()
        ids = {k: v.id for k, v in rows.items()} | {"dup": dup.id}
    yield ids
    await _clear()


async def _link_now(**kw):
    async with get_session_factory()() as session:
        return await causal.link_story_chains(session, NOW, **kw)


async def _links(ids) -> list[EventLink]:
    mine = set(ids.values())
    async with get_session_factory()() as session:
        rows = (await session.execute(select(EventLink))).scalars().all()
    return [lk for lk in rows if lk.cause_id in mine or lk.effect_id in mine]


class TestLinking:
    async def test_creates_the_expected_links(self, chain_seed):
        stats = await _link_now()
        links = {(lk.cause_id, lk.effect_id): lk for lk in await _links(chain_seed)}
        s, r, o = chain_seed["strike"], chain_seed["retaliation"], chain_seed["oil"]
        assert set(links) == {(s, r), (s, o), (r, o)}
        assert stats["created"] == 3
        first = links[(s, r)]
        assert first.rule_id == "strike_retaliation"
        assert first.method == "rule"
        assert first.relation_ar == "ضربة ← رد انتقامي"
        assert 0.4 <= first.confidence <= 1
        evidence = json.loads(first.evidence)
        assert {e["key"] for e in evidence["shared"]} == {"IL", "IR"}
        assert evidence["hours"] == 10.0
        assert links[(r, o)].rule_id == "gulf_attack_energy_shipping"

    async def test_is_idempotent(self, chain_seed):
        await _link_now()
        before = sorted((lk.cause_id, lk.effect_id, lk.confidence) for lk in await _links(chain_seed))
        stats = await _link_now()
        after = sorted((lk.cause_id, lk.effect_id, lk.confidence) for lk in await _links(chain_seed))
        assert (stats["created"], stats["updated"], stats["removed"]) == (0, 0, 0)
        assert before == after

    async def test_recomputes_and_removes_stale_links(self, chain_seed):
        await _link_now()
        stats = await _link_now(min_confidence=0.99)
        assert stats["removed"] == 3
        assert await _links(chain_seed) == []
        stats = await _link_now()
        assert stats["created"] == 3

    async def test_only_recent_effects_are_recomputed(self, chain_seed):
        stats = await _link_now(hours=12)
        links = await _links(chain_seed)
        # نطاق آخر 12 ساعة يضم قفزة النفط وحدها أثرًا
        assert {lk.effect_id for lk in links} == {chain_seed["oil"]}
        assert stats["created"] == 2

    async def test_non_rule_links_are_left_alone(self, chain_seed):
        async with get_session_factory()() as session:
            session.add(EventLink(
                cause_id=chain_seed["strike"], effect_id=chain_seed["unrelated"], relation_ar="x",
                relation_en="x", confidence=0.9, method="llm", rule_id=None,
            ))
            await session.commit()
        await _link_now()
        assert any(lk.method == "llm" for lk in await _links(chain_seed))

    async def test_run_causal_linking_uses_settings(self, chain_seed, monkeypatch, caplog):
        from app.config import get_settings

        monkeypatch.setattr(get_settings(), "llm_assist_enabled", True)
        monkeypatch.setattr(database, "_llm_notice_logged", False)
        with caplog.at_level(logging.WARNING, logger="rasad.database"):
            stats = await database.run_causal_linking()
        assert "LLM_ASSIST_ENABLED" in caplog.text
        assert {"created", "updated", "removed", "scope"} <= set(stats)

    async def test_analysis_cycle_clusters_then_links(self, monkeypatch):
        calls = []

        async def fake_cluster(hours=72):
            calls.append("cluster")
            return 4

        async def fake_link(hours=72, min_confidence=None):
            calls.append("link")
            return {"created": 1}

        monkeypatch.setattr(database, "run_story_clustering", fake_cluster)
        monkeypatch.setattr(database, "run_causal_linking", fake_link)
        assert await database.run_analysis_cycle() == {"clustered": 4, "links": {"created": 1}}
        assert calls == ["cluster", "link"]

    async def test_analysis_cycle_survives_a_linking_failure(self, monkeypatch):
        async def fake_cluster(hours=72):
            return 0

        async def boom(hours=72, min_confidence=None):
            raise RuntimeError("x")

        monkeypatch.setattr(database, "run_story_clustering", fake_cluster)
        monkeypatch.setattr(database, "run_causal_linking", boom)
        assert await database.run_analysis_cycle() == {"clustered": 0, "links": {}}


class TestRetention:
    async def test_prune_removes_links_of_pruned_events(self, chain_seed):
        await _link_now()
        async with get_session_factory()() as session:
            oil = await session.get(Event, chain_seed["oil"])
            oil.collected_at = datetime.now(timezone.utc) - timedelta(days=40)
            await session.commit()
        removed = await database.prune_old_data(events_days=30)
        assert removed["event_links"] >= 2
        remaining = {(lk.cause_id, lk.effect_id) for lk in await _links(chain_seed)}
        assert remaining == {(chain_seed["strike"], chain_seed["retaliation"])}


class TestEventChainEndpoint:
    async def test_causes_and_effects(self, client, chain_seed):
        await _link_now()
        body = (await client.get(f"/api/events/{chain_seed['retaliation']}/chain")).json()
        assert body["story_id"] == chain_seed["retaliation"]
        assert [c["event"]["id"] for c in body["causes"]] == [chain_seed["strike"]]
        assert [e["event"]["id"] for e in body["effects"]] == [chain_seed["oil"]]
        cause = body["causes"][0]
        assert cause["rule_id"] == "strike_retaliation"
        assert cause["relation_en"] == "Strike → retaliation"
        assert cause["evidence"]["components"]["match"] > 0
        assert cause["event"]["title"] == "Israel strikes targets in Iran"

    async def test_member_of_a_story_resolves_to_its_story(self, client, chain_seed):
        await _link_now()
        body = (await client.get(f"/api/events/{chain_seed['dup']}/chain")).json()
        assert body["story_id"] == chain_seed["retaliation"]
        assert len(body["causes"]) == 1

    async def test_min_confidence_filter(self, client, chain_seed):
        await _link_now()
        body = (await client.get(f"/api/events/{chain_seed['oil']}/chain",
                                 params={"min_confidence": 0.99})).json()
        assert body["causes"] == [] and body["effects"] == []

    async def test_unknown_event(self, client):
        assert (await client.get("/api/events/987654321/chain")).status_code == 404

    async def test_validation(self, client, chain_seed):
        r = await client.get(f"/api/events/{chain_seed['oil']}/chain", params={"min_confidence": 2})
        assert r.status_code == 422


class TestChains:
    async def test_longest_chain_first(self, chain_seed):
        await _link_now()
        body = await chains_api.build_chains(72, 0.4, 10, now=NOW)
        assert body["links"] == 3
        top = body["chains"][0]
        assert top["length"] == 2
        assert [n["id"] for n in top["nodes"]] == [
            chain_seed["strike"], chain_seed["retaliation"], chain_seed["oil"],
        ]
        assert top["confidence"] == min(lk["confidence"] for lk in top["links"])
        # الرابط المباشر ضربة ← نفط ليس جزءًا من السلسلة الأطول فيظهر وحده
        assert [len(c["links"]) for c in body["chains"]] == [2, 1]

    async def test_hiding_weak_links_breaks_chains(self, chain_seed):
        await _link_now()
        links = await _links(chain_seed)
        weakest = min(lk.confidence for lk in links)
        body = await chains_api.build_chains(72, weakest + 0.001, 10, now=NOW)
        assert body["links"] == len(links) - sum(1 for lk in links if lk.confidence == weakest)

    async def test_period_filter(self, chain_seed):
        await _link_now()
        body = await chains_api.build_chains(5, 0.4, 10, now=NOW)
        assert body["chains"] == []

    async def test_http(self, client):
        body = (await client.get("/api/chains", params={"hours": 72})).json()
        assert body["period_hours"] == 72
        assert body["min_confidence"] == 0.4
        assert isinstance(body["chains"], list)
        assert (await client.get("/api/chains", params={"min_confidence": 1.5})).status_code == 422

    async def test_rules(self, client):
        body = (await client.get("/api/chains/rules")).json()
        assert len(body["rules"]) == 5
        assert body["formula"]["window_hours"] == 72
        assert body["formula"]["entity"]["facility"] == 1.0

    def test_rank_chains_drops_covered_paths_and_limits(self):
        links = [
            {"id": 1, "cause_id": 1, "effect_id": 2, "confidence": 0.6},
            {"id": 2, "cause_id": 2, "effect_id": 3, "confidence": 0.5},
            {"id": 3, "cause_id": 4, "effect_id": 2, "confidence": 0.7},
            {"id": 4, "cause_id": 5, "effect_id": 6, "confidence": 0.9},
        ]
        ranked = chains_api.rank_chains(links, 10)
        assert [[lk["id"] for lk in p] for p in ranked] == [[3, 2], [1, 2], [4]]
        assert len(chains_api.rank_chains(links, 1)) == 1


class TestBrief:
    async def test_brief_carries_narrative_inputs(self, client):
        body = (await client.get("/api/nuclear/brief", params={"hours": 24})).json()
        assert body["narrative_method"] == "template"
        ksa = body["ksa_impact"]
        assert {"index", "prev_index", "delta", "trend", "sectors", "top_events"} <= set(ksa)
        assert {"key", "delta", "trend"} <= set(ksa["sectors"][0])
        assert isinstance(body["chains"], list)


async def test_link_table_is_created(client):
    async with get_session_factory()() as session:
        assert (await session.execute(select(func.count(EventLink.id)))).scalar() >= 0
