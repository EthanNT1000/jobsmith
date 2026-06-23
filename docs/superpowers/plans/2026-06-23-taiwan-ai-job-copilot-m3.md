# 台灣 AI 求職 Co-pilot — M3 實作計畫（Critic 反思迴圈 + human-in-the-loop）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 M2 的並行圖上加入 ⑥ 品管/反思 agent（對履歷/求職信/面試三份成品評分、未達標退回重寫，最多 N 次）與 ⑦ human-in-the-loop 人工核可關卡（LangGraph `interrupt()` + checkpointer），由 CLI 串接 interrupt/resume 流程。

**Architecture:** 把 M2 拓撲改成「company_research 先跑 → 三個生成節點並行 → join → critic → 條件分支（revise 退回 company_research / approve 進 human_gate）→ human_gate(interrupt) → END」。迴圈採「單節點回圈」(critic 退回 company_research)，company_research 在重寫時跳過搜尋；生成節點讀取 state 內的 critique.feedback 來改進。重寫覆寫既有 state key（last-write-wins，正是所需，不需 reducer）。human_gate 用 `interrupt()`，圖以 `MemorySaver` checkpointer compile，執行需帶 `thread_id`。

**Tech Stack:** 沿用既有（LangGraph、langchain-anthropic、Pydantic v2、pytest）。新增使用 `langgraph.checkpoint.memory.MemorySaver` 與 `langgraph.types.interrupt` / `Command`。

## Global Constraints

- Python 3.11+。繁中為主。Pydantic v2 結構化輸出。
- 模型分層：⑥ Critic 用 **deep**（`claude-opus-4-8`，硬判斷）；生成 agent 維持 standard。
- **匯入風格**：agent 以 `from app.llm import get_llm`；graph 以 `from app.agents.X import fn`；新 critic 以 `from app.agents.critic import critique_package`。一律名稱匯入（讓 monkeypatch 生效）。
- **迴圈安全**：`MAX_REVISIONS = 2`（最多 2 次評審＝至多 1 次重寫），用 `revision_count` 控制，防無限迴圈。
- **重寫覆寫**：重寫時生成節點覆寫 `tailored_resume`/`cover_letter`/`interview_kit`（last-write-wins，不需 reducer）；`revision_count` 只由 critic 寫。
- **human-in-the-loop**：`interrupt()` 需 checkpointer；`build_graph()` 以 `compile(checkpointer=MemorySaver())`；invoke 與 resume 都需同一 `config={"configurable":{"thread_id": ...}}`；resume 用 `Command(resume=<決定>)`。
- 金鑰由 env。測試以 monkeypatch 注入假 agent / 假 critic，不打 API；human gate 測試用 `Command(resume=...)`，CLI 測試 monkeypatch `builtins.input`。
- 環境 Windows+PowerShell；用 `.venv\Scripts\python.exe -m pytest`。TDD、DRY、YAGNI、頻繁 commit。

---

## File Structure（M3 變動）

```
app/
  models.py            # [改] 新增 CritiqueReport
  state.py             # [改] CopilotState 加 critique/revision_count/approved
  agents/
    resume.py          # [改] tailor_resume 加 feedback 參數
    cover_letter.py    # [改] write_cover_letter 加 feedback 參數
    interview.py       # [改] prepare_interview 加 feedback 參數
    critic.py          # [新] ⑥ critique_package
  graph.py             # [改] 反思迴圈 + human gate + checkpointer
  cli.py               # [改] interrupt/resume 流程 + 顯示 critique
tests/
  test_models.py       # [改] CritiqueReport 測試
  test_critic.py       # [新]
  test_resume.py       # [改] feedback 路徑測試
  test_cover_letter.py # [改] feedback 路徑測試
  test_interview.py    # [改] feedback 路徑測試
  test_graph.py        # [改] 反思迴圈 + interrupt/resume 測試
  test_cli.py          # [改] interrupt/resume + critique 顯示測試
```

---

### Task 1: CritiqueReport 模型 + 擴充 State

**Files:**
- Modify: `app/models.py`（append CritiqueReport）
- Modify: `app/state.py`（加 3 個 key）
- Test: `tests/test_models.py`（append 測試）

**Interfaces (Produces):**
- `app.models.CritiqueReport`（`resume_score: int 0-100`, `cover_letter_score: int 0-100`, `interview_score: int 0-100`, `overall_pass: bool`, `feedback: list[str]`）
- `app.state.CopilotState` 新增：`critique: CritiqueReport | None`, `revision_count: int`, `approved: bool | None`

- [ ] **Step 1: append 失敗測試到 `tests/test_models.py`**

```python
from app.models import CritiqueReport


def test_critique_report_defaults():
    c = CritiqueReport(resume_score=80, cover_letter_score=75, interview_score=70, overall_pass=True)
    assert c.feedback == []


def test_critique_report_score_bounds():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CritiqueReport(resume_score=101, cover_letter_score=0, interview_score=0, overall_pass=False)
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL（`ImportError: cannot import name 'CritiqueReport'`）

- [ ] **Step 3: append 到 `app/models.py`**

```python
class CritiqueReport(BaseModel):
    """⑥ 品管/反思評審報告。"""
    resume_score: int = Field(ge=0, le=100)
    cover_letter_score: int = Field(ge=0, le=100)
    interview_score: int = Field(ge=0, le=100)
    overall_pass: bool = Field(description="三份成品是否整體達標")
    feedback: list[str] = Field(default_factory=list, description="若未通過，給下一輪的具體修改指示")
```

- [ ] **Step 4: 執行確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v` → PASS

- [ ] **Step 5: 覆寫 `app/state.py`**

```python
"""LangGraph 共享狀態。"""
from typing import TypedDict

from app.models import (
    Profile, ParsedJob, MatchReport,
    CompanyBrief, TailoredResume, CoverLetter, InterviewKit, CritiqueReport,
)


class CopilotState(TypedDict):
    jd_text: str
    profile: Profile
    parsed_job: ParsedJob | None
    match_report: MatchReport | None
    company_brief: CompanyBrief | None
    tailored_resume: TailoredResume | None
    cover_letter: CoverLetter | None
    interview_kit: InterviewKit | None
    critique: CritiqueReport | None
    revision_count: int
    approved: bool | None
```

- [ ] **Step 6: 全套測試**

Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 7: Commit**

```bash
git add app/models.py app/state.py tests/test_models.py
git commit -m "feat(m3): add CritiqueReport model and extend state for reflection loop"
```

---

### Task 2: ⑥ Critic agent（critic）

**Files:**
- Create: `app/agents/critic.py`
- Test: `tests/test_critic.py`

**Interfaces:**
- Consumes: `app.llm.get_llm`、`app.models.ParsedJob/TailoredResume/CoverLetter/InterviewKit/CritiqueReport`
- Produces: `app.agents.critic.critique_package(job: ParsedJob, resume: TailoredResume, cover_letter: CoverLetter, interview_kit: InterviewKit) -> CritiqueReport`

- [ ] **Step 1: 失敗測試 — Create `tests/test_critic.py`**

```python
from app.models import (
    ParsedJob, TailoredResume, CoverLetter, InterviewKit, CritiqueReport,
)
from app.agents import critic as critic_mod
from tests.conftest import FakeLLM


def _artifacts():
    job = ParsedJob(title="AI 工程師", company="未來智能")
    resume = TailoredResume(summary="定位")
    cover = CoverLetter(body="敬啟者")
    kit = InterviewKit(technical_questions=["Q"])
    return job, resume, cover, kit


def test_critique_package_returns_report(monkeypatch):
    canned = CritiqueReport(resume_score=88, cover_letter_score=82, interview_score=80,
                            overall_pass=True, feedback=[])
    monkeypatch.setattr(critic_mod, "get_llm", lambda tier: FakeLLM(canned))

    report = critic_mod.critique_package(*_artifacts())

    assert isinstance(report, CritiqueReport)
    assert report.overall_pass is True


def test_critique_package_uses_deep_tier(monkeypatch):
    seen = {}
    canned = CritiqueReport(resume_score=50, cover_letter_score=50, interview_score=50,
                            overall_pass=False, feedback=["改具體一點"])

    def fake_get_llm(tier):
        seen["tier"] = tier
        return FakeLLM(canned)

    monkeypatch.setattr(critic_mod, "get_llm", fake_get_llm)
    critic_mod.critique_package(*_artifacts())
    assert seen["tier"] == "deep"
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_critic.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.agents.critic'`）

- [ ] **Step 3: 實作 — Create `app/agents/critic.py`**

```python
"""⑥ 品管/反思 Agent：對投遞包評分並給修改指示。"""
from app.llm import get_llm
from app.models import (
    ParsedJob, TailoredResume, CoverLetter, InterviewKit, CritiqueReport,
)

CRITIC_SYSTEM = (
    "你是嚴格的投遞包品管審查員。請依『職缺』，對『客製履歷、求職信、面試準備』"
    "三份成品逐項評分（0-100），並判斷整體是否達標（overall_pass）。"
    "評分依據：是否命中 JD 必備條件、ATS 關鍵字覆蓋、台灣在地規範與語氣、"
    "是否具體不空泛、是否有捏造未提供的經歷。"
    "若未達標，feedback 必須是可執行的具體修改指示（給下一輪重寫用）。"
)


def critique_package(
    job: ParsedJob,
    resume: TailoredResume,
    cover_letter: CoverLetter,
    interview_kit: InterviewKit,
) -> CritiqueReport:
    """評審投遞包（deep 分層）。"""
    llm = get_llm("deep").with_structured_output(CritiqueReport)
    human = (
        f"【職缺】\n{job.model_dump_json(indent=2)}\n\n"
        f"【客製履歷】\n{resume.model_dump_json(indent=2)}\n\n"
        f"【求職信】\n{cover_letter.model_dump_json(indent=2)}\n\n"
        f"【面試準備】\n{interview_kit.model_dump_json(indent=2)}"
    )
    return llm.invoke([("system", CRITIC_SYSTEM), ("human", human)])
```

- [ ] **Step 4: 確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_critic.py -v` → PASS（2 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 5: Commit**

```bash
git add app/agents/critic.py tests/test_critic.py
git commit -m "feat(m3): add critic agent (reviews application package, deep tier)"
```

---

### Task 3: 生成 agent 加 feedback 參數

**Files:**
- Modify: `app/agents/resume.py`、`app/agents/cover_letter.py`、`app/agents/interview.py`
- Test: `tests/test_resume.py`、`tests/test_cover_letter.py`、`tests/test_interview.py`（各 append 一個 feedback 測試）

**目標：** 三個生成 agent 各加一個 optional 參數 `feedback: list[str] | None = None`，向後相容（既有呼叫不變）；當有 feedback 時，把它接到 human 訊息末尾，引導改進。

**Interfaces（變更後）：**
- `tailor_resume(job, profile, feedback: list[str] | None = None) -> TailoredResume`
- `write_cover_letter(job, profile, company, feedback: list[str] | None = None) -> CoverLetter`
- `prepare_interview(job, profile, company, feedback: list[str] | None = None) -> InterviewKit`

- [ ] **Step 1: append feedback 測試到三個測試檔**

到 `tests/test_resume.py` append：
```python
def test_tailor_resume_includes_feedback_when_revising(monkeypatch, demo_profile, sample_parsed_job):
    captured = {}
    canned = TailoredResume(summary="改好的")

    class _CapLLM:
        def with_structured_output(self, schema):
            return self
        def invoke(self, messages):
            captured["human"] = messages[-1][1]
            return canned

    monkeypatch.setattr(resume_mod, "get_llm", lambda tier: _CapLLM())
    resume_mod.tailor_resume(sample_parsed_job, demo_profile, ["把成果量化"])
    assert "把成果量化" in captured["human"]
```

到 `tests/test_cover_letter.py` append：
```python
def test_write_cover_letter_includes_feedback(monkeypatch, demo_profile, sample_parsed_job):
    captured = {}
    canned = CoverLetter(body="改好的")

    class _CapLLM:
        def with_structured_output(self, schema):
            return self
        def invoke(self, messages):
            captured["human"] = messages[-1][1]
            return canned

    monkeypatch.setattr(cl_mod, "get_llm", lambda tier: _CapLLM())
    cl_mod.write_cover_letter(sample_parsed_job, demo_profile, None, ["語氣更誠懇"])
    assert "語氣更誠懇" in captured["human"]
```

到 `tests/test_interview.py` append：
```python
def test_prepare_interview_includes_feedback(monkeypatch, demo_profile, sample_parsed_job):
    captured = {}
    canned = InterviewKit(technical_questions=["Q"])

    class _CapLLM:
        def with_structured_output(self, schema):
            return self
        def invoke(self, messages):
            captured["human"] = messages[-1][1]
            return canned

    monkeypatch.setattr(iv_mod, "get_llm", lambda tier: _CapLLM())
    iv_mod.prepare_interview(sample_parsed_job, demo_profile, None, ["多準備系統設計題"])
    assert "多準備系統設計題" in captured["human"]
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_resume.py tests/test_cover_letter.py tests/test_interview.py -v`
Expected: FAIL（feedback 尚未被接進 human 訊息 / 多了參數但未使用 → 字串不含）

- [ ] **Step 3: 實作 — 在每個 agent 加 feedback 參數並接進訊息**

`app/agents/resume.py` 的 `tailor_resume` 改為：
```python
def tailor_resume(job: ParsedJob, profile: Profile, feedback: list[str] | None = None) -> TailoredResume:
    """針對職缺客製履歷（standard 分層）；feedback 為上一輪品管意見。"""
    llm = get_llm("standard").with_structured_output(TailoredResume)
    human = (
        "【職缺】\n"
        f"{job.model_dump_json(indent=2)}\n\n"
        "【求職者背景】\n"
        f"{profile.model_dump_json(indent=2)}"
    )
    if feedback:
        human += "\n\n【品管意見，請據此改進】\n" + "\n".join(f"- {f}" for f in feedback)
    return llm.invoke([("system", RESUME_SYSTEM), ("human", human)])
```

`app/agents/cover_letter.py` 的 `write_cover_letter` 改為（在既有 human 組好後、invoke 前插入 feedback）：
```python
def write_cover_letter(job: ParsedJob, profile: Profile, company: CompanyBrief | None,
                       feedback: list[str] | None = None) -> CoverLetter:
    """撰寫求職信/自傳（standard 分層）；feedback 為上一輪品管意見。"""
    company_json = company.model_dump_json(indent=2) if company else "（無公司情報）"
    human = (
        "【職缺】\n"
        f"{job.model_dump_json(indent=2)}\n\n"
        "【求職者背景】\n"
        f"{profile.model_dump_json(indent=2)}\n\n"
        "【公司情報】\n"
        f"{company_json}"
    )
    if feedback:
        human += "\n\n【品管意見，請據此改進】\n" + "\n".join(f"- {f}" for f in feedback)
    llm = get_llm("standard").with_structured_output(CoverLetter)
    return llm.invoke([("system", COVER_SYSTEM), ("human", human)])
```

`app/agents/interview.py` 的 `prepare_interview` 改為：
```python
def prepare_interview(job: ParsedJob, profile: Profile, company: CompanyBrief | None,
                      feedback: list[str] | None = None) -> InterviewKit:
    """準備面試包（standard 分層）；feedback 為上一輪品管意見。"""
    company_json = company.model_dump_json(indent=2) if company else "（無公司情報）"
    human = (
        "【職缺】\n"
        f"{job.model_dump_json(indent=2)}\n\n"
        "【求職者背景】\n"
        f"{profile.model_dump_json(indent=2)}\n\n"
        "【公司情報】\n"
        f"{company_json}"
    )
    if feedback:
        human += "\n\n【品管意見，請據此改進】\n" + "\n".join(f"- {f}" for f in feedback)
    llm = get_llm("standard").with_structured_output(InterviewKit)
    return llm.invoke([("system", INTERVIEW_SYSTEM), ("human", human)])
```

- [ ] **Step 4: 確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_resume.py tests/test_cover_letter.py tests/test_interview.py -v` → PASS（含既有，各檔 +1）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 5: Commit**

```bash
git add app/agents/resume.py app/agents/cover_letter.py app/agents/interview.py tests/test_resume.py tests/test_cover_letter.py tests/test_interview.py
git commit -m "feat(m3): generation agents accept optional critique feedback"
```

---

### Task 4: 圖改寫（反思迴圈 + human gate + checkpointer）

**Files:**
- Modify: `app/graph.py`（整檔覆寫）
- Modify: `tests/test_graph.py`（整檔覆寫）

**Interfaces (Produces):**
- 節點：`parse_node`、`match_node`、`company_research_node`（重寫時跳過搜尋）、`resume_tailor_node`/`cover_letter_node`/`interview_prep_node`（讀 critique.feedback）、`join_node`、`critic_node`（寫 critique 並 +1 revision_count）、`human_gate_node`（`interrupt()`）
- `route_after_match(state) -> str`：`"company_research"` 或 `"stop"`
- `route_after_critic(state) -> str`：`"approve"`（通過或達上限）或 `"revise"`
- `PROCEED_SCORE_THRESHOLD = 60`、`MAX_REVISIONS = 2`
- `build_graph()`：以 `MemorySaver` checkpointer compile 的圖

**圖拓撲：**
```
START → parse → match → route_after_match
   "stop" → END
   "company_research" → company_research
company_research → resume_tailor, cover_letter, interview_prep  (並行)
resume_tailor / cover_letter / interview_prep → join
join → critic
critic → route_after_critic
   "revise"  → company_research   (單節點回圈；company_research 跳過搜尋、生成節點帶 feedback 重寫)
   "approve" → human_gate
human_gate (interrupt) → END
```

- [ ] **Step 1: 覆寫 `tests/test_graph.py` 全檔**

```python
from langgraph.types import Command

from app.models import (
    ParsedJob, MatchReport, CompanyBrief, TailoredResume, CoverLetter,
    InterviewKit, CritiqueReport,
)
from app import graph as graph_mod

CONFIG = {"configurable": {"thread_id": "test-thread"}}


def _patch_base(monkeypatch, report: MatchReport):
    monkeypatch.setattr(graph_mod, "parse_job",
                        lambda jd_text: ParsedJob(title="AI 工程師", company="未來智能"))
    monkeypatch.setattr(graph_mod, "match_profile", lambda job, profile: report)
    monkeypatch.setattr(graph_mod, "research_company",
                        lambda name: CompanyBrief(company=name, funding="B 輪"))
    monkeypatch.setattr(graph_mod, "tailor_resume",
                        lambda job, profile, feedback=None: TailoredResume(summary="履歷"))
    monkeypatch.setattr(graph_mod, "write_cover_letter",
                        lambda job, profile, company, feedback=None: CoverLetter(body="信"))
    monkeypatch.setattr(graph_mod, "prepare_interview",
                        lambda job, profile, company, feedback=None: InterviewKit(technical_questions=["Q"]))


def _passing_critic(monkeypatch):
    monkeypatch.setattr(graph_mod, "critique_package",
                        lambda job, r, c, k: CritiqueReport(
                            resume_score=90, cover_letter_score=88, interview_score=85,
                            overall_pass=True, feedback=[]))


def _initial(profile):
    return {
        "jd_text": "（任意）", "profile": profile,
        "parsed_job": None, "match_report": None, "company_brief": None,
        "tailored_resume": None, "cover_letter": None, "interview_kit": None,
        "critique": None, "revision_count": 0, "approved": None,
    }


def test_proceed_runs_to_human_gate_then_resumes(monkeypatch, demo_profile):
    _patch_base(monkeypatch, MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    _passing_critic(monkeypatch)
    g = graph_mod.build_graph()

    result = g.invoke(_initial(demo_profile), CONFIG)
    assert "__interrupt__" in result            # 停在人工關卡

    final = g.invoke(Command(resume="y"), CONFIG)
    assert final["approved"] is True
    assert final["tailored_resume"].summary == "履歷"
    assert final["company_brief"].funding == "B 輪"
    assert final["critique"].overall_pass is True


def test_stop_path_no_interrupt(monkeypatch, demo_profile):
    _patch_base(monkeypatch, MatchReport(score=40, recommend_proceed=False, reason="不符"))
    _passing_critic(monkeypatch)
    g = graph_mod.build_graph()

    result = g.invoke(_initial(demo_profile), CONFIG)
    assert "__interrupt__" not in result
    assert result["match_report"].score == 40
    assert result["tailored_resume"] is None


def test_failing_critic_loops_then_stops_at_max(monkeypatch, demo_profile):
    _patch_base(monkeypatch, MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    calls = {"resume": 0, "critic": 0}

    def counting_resume(job, profile, feedback=None):
        calls["resume"] += 1
        return TailoredResume(summary=f"v{calls['resume']}")

    def always_fail(job, r, c, k):
        calls["critic"] += 1
        return CritiqueReport(resume_score=10, cover_letter_score=10, interview_score=10,
                              overall_pass=False, feedback=["再加強"])

    monkeypatch.setattr(graph_mod, "tailor_resume", counting_resume)
    monkeypatch.setattr(graph_mod, "critique_package", always_fail)
    g = graph_mod.build_graph()

    result = g.invoke(_initial(demo_profile), CONFIG)
    # critic 跑滿 MAX_REVISIONS 次（2），resume 生成 2 次（初版 + 1 次重寫），最後仍到人工關卡
    assert calls["critic"] == 2
    assert calls["resume"] == 2
    assert "__interrupt__" in result


def test_revise_passes_feedback_to_generators(monkeypatch, demo_profile):
    _patch_base(monkeypatch, MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    seen = {"feedback": None}

    def resume_capture(job, profile, feedback=None):
        if feedback:
            seen["feedback"] = feedback
        return TailoredResume(summary="x")

    critic_calls = {"n": 0}

    def fail_once(job, r, c, k):
        critic_calls["n"] += 1
        if critic_calls["n"] == 1:
            return CritiqueReport(resume_score=10, cover_letter_score=10, interview_score=10,
                                  overall_pass=False, feedback=["把成果量化"])
        return CritiqueReport(resume_score=90, cover_letter_score=90, interview_score=90,
                              overall_pass=True, feedback=[])

    monkeypatch.setattr(graph_mod, "tailor_resume", resume_capture)
    monkeypatch.setattr(graph_mod, "critique_package", fail_once)
    g = graph_mod.build_graph()

    g.invoke(_initial(demo_profile), CONFIG)
    assert seen["feedback"] == ["把成果量化"]


def test_route_after_match():
    assert graph_mod.route_after_match(
        {"match_report": MatchReport(score=80, recommend_proceed=True, reason="高")}
    ) == "company_research"
    assert graph_mod.route_after_match(
        {"match_report": MatchReport(score=50, recommend_proceed=True, reason="低")}
    ) == "stop"


def test_route_after_critic():
    passing = {"critique": CritiqueReport(resume_score=90, cover_letter_score=90,
               interview_score=90, overall_pass=True), "revision_count": 1}
    assert graph_mod.route_after_critic(passing) == "approve"

    failing_under = {"critique": CritiqueReport(resume_score=10, cover_letter_score=10,
                     interview_score=10, overall_pass=False), "revision_count": 1}
    assert graph_mod.route_after_critic(failing_under) == "revise"

    failing_at_max = {"critique": CritiqueReport(resume_score=10, cover_letter_score=10,
                      interview_score=10, overall_pass=False), "revision_count": 2}
    assert graph_mod.route_after_critic(failing_at_max) == "approve"
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_graph.py -v`
Expected: FAIL（新節點/路由/checkpointer 尚未實作）

- [ ] **Step 3: 覆寫 `app/graph.py` 全檔**

```python
"""Supervisor 反思迴圈圖：parse → match →（proceed）company_research → 三生成並行
→ join → critic →（revise 回圈 / approve）→ human_gate(interrupt) → END。

迴圈採單節點回圈（critic→company_research）；company_research 重寫時跳過搜尋；
生成節點讀 state 的 critique.feedback 改進；重寫覆寫各自 state key（last-write-wins，不需 reducer）。
human_gate 用 interrupt()，故圖以 MemorySaver checkpointer compile，執行需帶 thread_id。
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.state import CopilotState
from app.agents.parse import parse_job
from app.agents.match import match_profile
from app.agents.company import research_company
from app.agents.resume import tailor_resume
from app.agents.cover_letter import write_cover_letter
from app.agents.interview import prepare_interview
from app.agents.critic import critique_package

PROCEED_SCORE_THRESHOLD = 60
MAX_REVISIONS = 2  # 最多評審次數（至多 1 次重寫），防無限迴圈


def parse_node(state: CopilotState) -> dict:
    return {"parsed_job": parse_job(state["jd_text"])}


def match_node(state: CopilotState) -> dict:
    return {"match_report": match_profile(state["parsed_job"], state["profile"])}


def company_research_node(state: CopilotState) -> dict:
    if state.get("company_brief") is not None:
        return {}  # 重寫回圈時不重複搜尋
    return {"company_brief": research_company(state["parsed_job"].company)}


def _feedback(state: CopilotState):
    critique = state.get("critique")
    return critique.feedback if critique else None


def resume_tailor_node(state: CopilotState) -> dict:
    return {"tailored_resume": tailor_resume(
        state["parsed_job"], state["profile"], _feedback(state))}


def cover_letter_node(state: CopilotState) -> dict:
    return {"cover_letter": write_cover_letter(
        state["parsed_job"], state["profile"], state.get("company_brief"), _feedback(state))}


def interview_prep_node(state: CopilotState) -> dict:
    return {"interview_kit": prepare_interview(
        state["parsed_job"], state["profile"], state.get("company_brief"), _feedback(state))}


def join_node(state: CopilotState) -> dict:
    return {}


def critic_node(state: CopilotState) -> dict:
    critique = critique_package(
        state["parsed_job"], state["tailored_resume"],
        state["cover_letter"], state["interview_kit"])
    return {"critique": critique, "revision_count": state.get("revision_count", 0) + 1}


def human_gate_node(state: CopilotState) -> dict:
    decision = interrupt({
        "message": "請審閱投遞包並決定是否核可",
        "match_score": state["match_report"].score,
        "critique_pass": state["critique"].overall_pass,
    })
    approved = str(decision).strip().lower() in ("y", "yes", "approve", "是", "核可")
    return {"approved": approved}


def route_after_match(state: CopilotState) -> str:
    report = state["match_report"]
    if report.recommend_proceed and report.score >= PROCEED_SCORE_THRESHOLD:
        return "company_research"
    return "stop"


def route_after_critic(state: CopilotState) -> str:
    critique = state["critique"]
    if critique.overall_pass or state.get("revision_count", 0) >= MAX_REVISIONS:
        return "approve"
    return "revise"


def build_graph():
    g = StateGraph(CopilotState)
    g.add_node("parse", parse_node)
    g.add_node("match", match_node)
    g.add_node("company_research", company_research_node)
    g.add_node("resume_tailor", resume_tailor_node)
    g.add_node("cover_letter", cover_letter_node)
    g.add_node("interview_prep", interview_prep_node)
    g.add_node("join", join_node)
    g.add_node("critic", critic_node)
    g.add_node("human_gate", human_gate_node)

    g.add_edge(START, "parse")
    g.add_edge("parse", "match")
    g.add_conditional_edges(
        "match", route_after_match,
        {"company_research": "company_research", "stop": END},
    )
    g.add_edge("company_research", "resume_tailor")
    g.add_edge("company_research", "cover_letter")
    g.add_edge("company_research", "interview_prep")
    g.add_edge("resume_tailor", "join")
    g.add_edge("cover_letter", "join")
    g.add_edge("interview_prep", "join")
    g.add_edge("join", "critic")
    g.add_conditional_edges(
        "critic", route_after_critic,
        {"revise": "company_research", "approve": "human_gate"},
    )
    g.add_edge("human_gate", END)
    return g.compile(checkpointer=MemorySaver())
```

- [ ] **Step 4: 確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_graph.py -v` → PASS（7 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

**重要：** 若安裝的 LangGraph 版本對 `interrupt`/`Command`/`MemorySaver`/`compile(checkpointer=...)`/`__interrupt__` 鍵/單節點條件回圈的行為與此處不符而測試無法通過，**停下回報 BLOCKED 與確切錯誤訊息**，不要自行換 API（例如不要改用舊版 `interrupt_before=` breakpoint 寫法），由 controller 決定。

- [ ] **Step 5: Commit**

```bash
git add app/graph.py tests/test_graph.py
git commit -m "feat(m3): reflection loop (critic) + human-in-the-loop interrupt with checkpointer"
```

---

### Task 5: CLI 串 interrupt/resume + 顯示 critique

**Files:**
- Modify: `app/cli.py`（整檔覆寫）
- Modify: `tests/test_cli.py`（整檔覆寫）

**Interfaces（變更）：**
- `run(jd_path, profile_path="data/demo_profile.json") -> CopilotState`：建圖、帶 `thread_id` config invoke；若回傳含 `__interrupt__`，印出投遞包、用 `input()` 問核可、以 `Command(resume=...)` 續跑；回傳最終 state（`graph.get_state(config).values`）。
- `format_output(state, job_title)`：在既有區塊後加「品管評審」區塊（若 `critique` 存在）與「核可狀態」（若 `approved` 存在）。
- `load_profile`、`main` 維持。

- [ ] **Step 1: 覆寫 `tests/test_cli.py` 全檔**

```python
from app.models import (
    ParsedJob, MatchReport, CompanyBrief, TailoredResume, CoverLetter,
    InterviewKit, CritiqueReport,
)
from app import cli as cli_mod
from app import graph as graph_mod


def test_load_profile_reads_demo():
    p = cli_mod.load_profile("data/demo_profile.json")
    assert p.name == "陳小安"


def _full_state():
    return {
        "parsed_job": ParsedJob(title="AI 工程師", company="未來智能"),
        "match_report": MatchReport(score=82, matched=["Python"], gaps=["年資"],
                                    suggestions=["補強 X"], recommend_proceed=True, reason="吻合"),
        "company_brief": CompanyBrief(company="未來智能", salary_range="月薪 6 萬起",
                                      benefits=["彈性工時"], red_flags=["加班多"]),
        "tailored_resume": TailoredResume(summary="客製定位", bullets=["做過 RAG"],
                                          ats_keywords_hit=["Python"]),
        "cover_letter": CoverLetter(body="敬啟者……"),
        "interview_kit": InterviewKit(technical_questions=["解釋 RAG"],
                                      reverse_questions=["團隊架構？"]),
        "critique": CritiqueReport(resume_score=88, cover_letter_score=85,
                                   interview_score=82, overall_pass=True),
        "revision_count": 1,
        "approved": True,
    }


def test_format_output_includes_critique_and_approval():
    text = cli_mod.format_output(_full_state(), job_title="AI 工程師")
    assert "88" in text          # 品管分數
    assert "核可" in text         # 核可狀態字樣
    assert "客製定位" in text


def test_format_output_handles_stop_path():
    state = {
        "parsed_job": ParsedJob(title="X", company="Y"),
        "match_report": MatchReport(score=30, recommend_proceed=False, reason="不符"),
        "company_brief": None, "tailored_resume": None, "cover_letter": None,
        "interview_kit": None, "critique": None, "revision_count": 0, "approved": None,
    }
    text = cli_mod.format_output(state, job_title="X")
    assert "30" in text


def _patch_graph_agents(monkeypatch):
    monkeypatch.setattr(graph_mod, "parse_job",
                        lambda jd_text: ParsedJob(title="AI 工程師", company="未來智能"))
    monkeypatch.setattr(graph_mod, "match_profile",
                        lambda job, profile: MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    monkeypatch.setattr(graph_mod, "research_company",
                        lambda name: CompanyBrief(company=name))
    monkeypatch.setattr(graph_mod, "tailor_resume",
                        lambda job, profile, feedback=None: TailoredResume(summary="履歷"))
    monkeypatch.setattr(graph_mod, "write_cover_letter",
                        lambda job, profile, company, feedback=None: CoverLetter(body="信"))
    monkeypatch.setattr(graph_mod, "prepare_interview",
                        lambda job, profile, company, feedback=None: InterviewKit())
    monkeypatch.setattr(graph_mod, "critique_package",
                        lambda job, r, c, k: CritiqueReport(resume_score=90, cover_letter_score=90,
                                                            interview_score=90, overall_pass=True))


def test_run_handles_interrupt_and_resume(monkeypatch, tmp_path):
    jd_file = tmp_path / "jd.txt"
    jd_file.write_text("一些 JD", encoding="utf-8")
    _patch_graph_agents(monkeypatch)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "y")

    result = cli_mod.run(str(jd_file))
    assert result["approved"] is True
    assert result["tailored_resume"].summary == "履歷"


def test_run_stop_path_no_prompt(monkeypatch, tmp_path):
    jd_file = tmp_path / "jd.txt"
    jd_file.write_text("一些 JD", encoding="utf-8")
    _patch_graph_agents(monkeypatch)
    monkeypatch.setattr(graph_mod, "match_profile",
                        lambda job, profile: MatchReport(score=30, recommend_proceed=False, reason="不符"))

    def no_input(*a, **k):
        raise AssertionError("stop 路徑不應該詢問核可")
    monkeypatch.setattr("builtins.input", no_input)

    result = cli_mod.run(str(jd_file))
    assert result["tailored_resume"] is None
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: FAIL（run 尚未處理 interrupt/resume；format_output 無品管區塊）

- [ ] **Step 3: 覆寫 `app/cli.py` 全檔**

```python
"""終端機進入點：讀 JD → 跑反思迴圈圖 → 人工核可 → 印完整投遞包。"""
import json
import sys
import uuid
from pathlib import Path

from langgraph.types import Command

from app.models import Profile
from app.state import CopilotState
from app.graph import build_graph


def load_profile(path: str = "data/demo_profile.json") -> Profile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Profile(**data)


def _join(items: list[str]) -> str:
    return "、".join(items) if items else "（無）"


def format_output(state: dict, job_title: str) -> str:
    report = state["match_report"]
    lines = [
        f"=== 匹配報告：{job_title} ===",
        f"分數：{report.score}/100",
        f"建議續做：{'是' if report.recommend_proceed else '否'}（{report.reason}）",
        "符合項：" + _join(report.matched),
        "落差項：" + _join(report.gaps),
        "補強建議：" + _join(report.suggestions),
    ]

    company = state.get("company_brief")
    if company is not None:
        lines += [
            "",
            f"=== 公司情報：{company.company} ===",
            f"薪資範圍：{company.salary_range or '（無）'}",
            "福利：" + _join(company.benefits),
            "避雷紅旗：" + _join(company.red_flags),
        ]
        if company.data_limited:
            lines.append("（註：公開資料有限）")

    resume = state.get("tailored_resume")
    if resume is not None:
        lines += [
            "",
            "=== 客製履歷 ===",
            f"定位：{resume.summary}",
            "重點條列：" + _join(resume.bullets),
            "ATS 命中：" + _join(resume.ats_keywords_hit),
            "ATS 尚缺：" + _join(resume.ats_keywords_missing),
        ]

    letter = state.get("cover_letter")
    if letter is not None:
        lines += ["", "=== 求職信/自傳 ===", letter.body]

    kit = state.get("interview_kit")
    if kit is not None:
        lines += [
            "",
            "=== 面試準備 ===",
            "技術題：" + _join(kit.technical_questions),
            "行為題：" + _join(kit.behavioral_questions),
            "台灣特有題：" + _join(kit.taiwan_specific_questions),
            "反向提問：" + _join(kit.reverse_questions),
            "避雷提醒：" + _join(kit.cautions),
        ]

    critique = state.get("critique")
    if critique is not None:
        lines += [
            "",
            "=== 品管評審 ===",
            f"履歷 {critique.resume_score}／求職信 {critique.cover_letter_score}／面試 {critique.interview_score}",
            f"整體達標：{'是' if critique.overall_pass else '否'}",
            "修改意見：" + _join(critique.feedback),
        ]

    approved = state.get("approved")
    if approved is not None:
        lines += ["", f"=== 核可狀態：{'已核可' if approved else '未核可'} ==="]

    return "\n".join(lines)


def run(jd_path: str, profile_path: str = "data/demo_profile.json") -> CopilotState:
    jd_text = Path(jd_path).read_text(encoding="utf-8")
    profile = load_profile(profile_path)
    graph = build_graph()
    config = {"configurable": {"thread_id": uuid.uuid4().hex}}
    initial = {
        "jd_text": jd_text,
        "profile": profile,
        "parsed_job": None,
        "match_report": None,
        "company_brief": None,
        "tailored_resume": None,
        "cover_letter": None,
        "interview_kit": None,
        "critique": None,
        "revision_count": 0,
        "approved": None,
    }
    result = graph.invoke(initial, config)

    if "__interrupt__" in result:
        # 停在人工關卡：先給使用者看投遞包，再問核可
        state_values = graph.get_state(config).values
        print(format_output(state_values, job_title=Path(jd_path).stem))
        decision = input("\n核可這份投遞包嗎？(y/n)：")
        result = graph.invoke(Command(resume=decision), config)

    return graph.get_state(config).values


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法：python -m app.cli <jd 檔案路徑>")
        return 1
    jd_path = argv[0]
    state = run(jd_path)
    print(format_output(state, job_title=Path(jd_path).stem))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 確認通過 + 全套（最後一個任務，回報全套總數）**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v` → PASS（5 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠（回報總數）

- [ ] **Step 5: Commit**

```bash
git add app/cli.py tests/test_cli.py
git commit -m "feat(m3): CLI interrupt/resume human approval + critique display"
```

---

## Self-Review（對照規格檢查）

**1. Spec coverage（M3 範圍，對照設計規格 §5⑥⑦、§6）：**
- ⑥ Critic 評分 → Task 2 ✓
- 反思迴圈（未達標退回重寫、計數防無限）→ Task 4 `critic`/`route_after_critic`/`MAX_REVISIONS` ✓
- 重寫帶入品管意見 → Task 3（feedback 參數）+ Task 4（`_feedback`）✓
- ⑦ human-in-the-loop（interrupt + 核可）→ Task 4 `human_gate` + Task 5 CLI resume ✓
- checkpointer → Task 4 `compile(checkpointer=MemorySaver())` ✓
- CLI 顯示品管與核可 → Task 5 ✓
- 重寫不重複搜尋公司 → Task 4 `company_research_node` 跳過 ✓
- （M4+ 才做：FastAPI、串流 UI、URL 抓取、PDF 匯出）→ 排除 ✓

**2. Placeholder scan：** 無 TBD/TODO；每步含完整程式碼。✓

**3. Type consistency：**
- `CritiqueReport` 欄位於 models/critic/graph/cli/tests 一致。
- 生成 agent 新增 `feedback=None`（向後相容，M2 既有呼叫不變）；graph 節點以第 3/4 參數傳 feedback，與簽名一致。
- `route_after_match` 回傳 `"company_research"`/`"stop"`，與 path_map 鍵一致。
- `route_after_critic` 回傳 `"approve"`/`"revise"`，與 path_map 鍵一致。
- `build_graph()` 回傳帶 checkpointer 的圖；所有 invoke（graph 測試、CLI）皆帶 `config` thread_id；resume 用 `Command`。
- `CopilotState` 新增 `critique/revision_count/approved`，初始 state 於 graph 測試與 CLI 一致提供。

無發現缺漏。
