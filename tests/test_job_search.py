from app.models import Profile, JobPosting
from app.agents import job_search as mod
from tests.conftest import FakeLLM


def test_derive_queries(monkeypatch):
    canned = mod.SearchQueries(queries=["AI 工程師", "Python 後端"])
    monkeypatch.setattr(mod, "get_llm", lambda tier, **k: FakeLLM(canned))
    qs = mod.derive_queries(Profile(name="王", summary="後端", skills=["Python"], raw_text="r"))
    assert qs == ["AI 工程師", "Python 後端"]


def test_derive_queries_fallback_to_preferred_role(monkeypatch):
    canned = mod.SearchQueries(queries=[])
    monkeypatch.setattr(mod, "get_llm", lambda tier, **k: FakeLLM(canned))
    qs = mod.derive_queries(Profile(name="王", summary="x", preferred_roles=["資料工程師"], raw_text="r"))
    assert qs == ["資料工程師"]


def test_rank_jobs_sorts_desc_and_maps(monkeypatch):
    canned = mod._RankResult(rankings=[
        mod._RankItem(index=0, fit_score=40, reason="普通"),
        mod._RankItem(index=1, fit_score=90, matched=["Python"], reason="很合"),
    ])
    monkeypatch.setattr(mod, "get_llm", lambda tier, **k: FakeLLM(canned))
    jobs = [
        JobPosting(source="104", title="A", company="C1", url="u1"),
        JobPosting(source="yourator", title="B", company="C2", url="u2"),
    ]
    matches = mod.rank_jobs(Profile(name="王", summary="x", raw_text="r"), jobs)
    assert matches[0].job.title == "B" and matches[0].fit_score == 90
    assert matches[1].fit_score == 40
    assert "Python" in matches[0].matched


def test_rank_jobs_empty_returns_empty():
    assert mod.rank_jobs(Profile(name="x", summary="y", raw_text="z"), []) == []
