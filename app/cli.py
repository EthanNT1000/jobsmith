"""終端機進入點：讀 JD → 跑圖 → 印匹配報告。"""
import json
import sys
from pathlib import Path

from app.models import Profile, MatchReport
from app.graph import build_graph


def load_profile(path: str = "data/demo_profile.json") -> Profile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Profile(**data)


def format_report(report: MatchReport, job_title: str) -> str:
    lines = [
        f"=== 匹配報告：{job_title} ===",
        f"分數：{report.score}/100",
        f"建議續做：{'是' if report.recommend_proceed else '否'}（{report.reason}）",
        "",
        "符合項：" + ("、".join(report.matched) or "（無）"),
        "落差項：" + ("、".join(report.gaps) or "（無）"),
        "補強建議：" + ("、".join(report.suggestions) or "（無）"),
    ]
    return "\n".join(lines)


def run(jd_path: str, profile_path: str = "data/demo_profile.json") -> MatchReport:
    jd_text = Path(jd_path).read_text(encoding="utf-8")
    profile = load_profile(profile_path)
    graph = build_graph()
    final = graph.invoke({
        "jd_text": jd_text,
        "profile": profile,
        "parsed_job": None,
        "match_report": None,
    })
    return final["match_report"]


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法：python -m app.cli <jd 檔案路徑>")
        return 1
    jd_path = argv[0]
    report = run(jd_path)
    title = Path(jd_path).stem
    print(format_report(report, job_title=title))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
