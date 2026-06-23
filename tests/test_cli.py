from pathlib import Path

from app.models import ParsedJob, MatchReport
from app import cli as cli_mod


def test_load_profile_reads_demo(tmp_path):
    p = cli_mod.load_profile("data/demo_profile.json")
    assert p.name == "陳小安"


def test_format_report_contains_score_and_reason():
    report = MatchReport(
        score=82, matched=["Python"], gaps=["年資"],
        suggestions=["補強 X"], recommend_proceed=True, reason="吻合",
    )
    text = cli_mod.format_report(report, job_title="AI 工程師")
    assert "82" in text
    assert "吻合" in text
    assert "AI 工程師" in text


def test_run_invokes_graph(monkeypatch, tmp_path):
    jd_file = tmp_path / "jd.txt"
    jd_file.write_text("一些 JD", encoding="utf-8")

    fake_final = {
        "parsed_job": ParsedJob(title="AI 工程師", company="未來智能"),
        "match_report": MatchReport(score=70, recommend_proceed=True, reason="ok"),
    }

    class FakeGraph:
        def invoke(self, state):
            return fake_final

    monkeypatch.setattr(cli_mod, "build_graph", lambda: FakeGraph())

    report = cli_mod.run(str(jd_file))
    assert report.score == 70
