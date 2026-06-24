from app.agents.skill_gap import analyze_skill_gap
from app.models import Profile, JobPosting


def test_gap_and_demand():
    jobs = [
        JobPosting(source="x", title="t", company="c", url="u", requirements=["Python", "LLM"]),
        JobPosting(source="x", title="t", company="c", url="u2", requirements=["Python", "Docker"]),
    ]
    prof = Profile(name="a", summary="", skills=["Python"], raw_text="")
    rep = analyze_skill_gap(prof, jobs)
    demand = {d.skill: d.count for d in rep.top_demand}
    assert demand["Python"] == 2
    gaps = {g.skill for g in rep.your_gaps}
    assert "LLM" in gaps and "Docker" in gaps and "Python" not in gaps   # 已具備不算缺口
    assert "Python" in rep.have


def test_skill_owned_as_substring_not_a_gap():
    # 履歷寫「AI 工程師」「LLM 應用」，職缺要求「AI」「LLM」應算已具備、不列缺口。
    jobs = [JobPosting(source="x", title="t", company="c", url="u",
                       requirements=["AI", "LLM", "Kubernetes"])]
    prof = Profile(name="a", summary="", skills=["AI 工程師", "LLM 應用"], raw_text="")
    rep = analyze_skill_gap(prof, jobs)
    gaps = {g.skill for g in rep.your_gaps}
    assert "AI" not in gaps and "LLM" not in gaps      # 已具備
    assert "Kubernetes" in gaps                         # 真的缺
    assert "AI" in rep.have and "LLM" in rep.have


def test_skill_in_summary_counts_as_owned():
    # 技能只出現在摘要/職稱（不在 skills 欄位）也算具備：AI 工程師 → 具備「AI」。
    jobs = [JobPosting(source="x", title="t", company="c", url="u", requirements=["AI", "Rust"])]
    prof = Profile(name="a", summary="AI 工程師，專長 LLM 應用與多代理系統",
                   skills=["Python"], raw_text="")
    rep = analyze_skill_gap(prof, jobs)
    gaps = {g.skill for g in rep.your_gaps}
    assert "AI" not in gaps and "AI" in rep.have   # 摘要已涵蓋
    assert "Rust" in gaps                            # 真的沒有


def test_short_ascii_skill_uses_word_boundary():
    # 「ai」不應誤中含 ai 的無關字（rail / domain）。
    jobs = [JobPosting(source="x", title="t", company="c", url="u", requirements=["AI"])]
    prof = Profile(name="a", summary="", skills=["Rails", "domain driven design"], raw_text="")
    rep = analyze_skill_gap(prof, jobs)
    assert {g.skill for g in rep.your_gaps} == {"AI"}   # 仍算缺口（沒被 rails/domain 誤判）


def test_case_insensitive_and_empty():
    jobs = [JobPosting(source="x", title="t", company="c", url="u", requirements=["python", ""])]
    prof = Profile(name="a", summary="", skills=["PYTHON"], raw_text="")
    rep = analyze_skill_gap(prof, jobs)
    assert not rep.your_gaps                # python 已具備（大小寫不敏感），空字串忽略
    assert rep.top_demand[0].skill == "python"
