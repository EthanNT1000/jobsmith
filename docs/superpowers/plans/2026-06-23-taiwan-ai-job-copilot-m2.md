# 台灣 AI 求職 Co-pilot — M2 實作計畫（並行 fan-out + 公司情報 agent）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 M1 的 supervisor 骨架上，於「proceed」分支加入三個並行生成 agent（③ 履歷客製、④ 求職信/自傳、⑤ 面試準備）與一個會上網查證的 ⑧ 公司情報 agent（tool use），公司情報的結果餵給 ④⑤；全部收斂後由 CLI 印出完整投遞包。

**Architecture:** 沿用 M1 的 LangGraph `StateGraph`。`route_after_match` 在 proceed 時改為「條件分支扇出」到 `resume_tailor` 與 `company_research`（並行）；`company_research` 完成後再扇出到 `cover_letter` 與 `interview_prep`（它們需要 `CompanyBrief`）；`resume_tailor`/`cover_letter`/`interview_prep` 三者匯入 `join` 節點（fan-in barrier）後到 `END`。各並行節點寫入**不同的 state key**，因此**不需要 reducer**。

**Tech Stack:** 沿用 M1（Python 3.11+、LangGraph、langchain-anthropic、Pydantic v2、pytest）。新增 `requests`（呼叫 Tavily 搜尋 API）。

## Global Constraints

- **Python 版本**：3.11 以上。語言：產出與 prompt 以繁體中文為主。
- **資料策略**：不爬蟲、不自動投履歷。職缺由貼 JD 進入（沿用 M1）。公司情報用搜尋 API（Tavily）取得公開資料。
- **結構化輸出**：所有 agent 一律回傳 Pydantic v2 模型，不手刻 JSON 解析。
- **模型分層**（沿用 M1 `app/settings.py`）：本里程碑 ③④⑤⑧ 皆用 `standard`（`claude-sonnet-4-6`）。
- **金鑰**：`ANTHROPIC_API_KEY`、`TAVILY_API_KEY` 由環境變數/.env 提供，絕不寫進程式碼或 commit。
- **匯入風格（攸關測試 monkeypatch）**：agent 模組以 `from app.llm import get_llm` 匯入；公司 agent 以 `from app.tools.search import search_web` 匯入；graph 以 `from app.agents.X import fn` 匯入各 agent 函式。一律「名稱匯入」而非屬性呼叫。
- **並行寫入**：每個並行節點只寫自己的 state key（`tailored_resume`/`company_brief`/`cover_letter`/`interview_kit`），不共寫同一 key，故不需 `Annotated` reducer。
- **測試設計**：LLM 與搜尋一律以 monkeypatch 做確定性測試；真打 API 的測試標記 `@pytest.mark.live`，預設略過。
- **執行環境**：Windows + PowerShell。共用 venv 在 `D:\Multi-Agent\.venv`，一律以 `.venv\Scripts\python.exe -m pytest ...` 執行（不要 activate）。
- TDD、DRY、YAGNI、頻繁 commit。

---

## File Structure（M2 變動）

```
app/
  models.py            # [改] 新增 CompanyBrief / TailoredResume / CoverLetter / InterviewKit
  state.py             # [改] CopilotState 增 4 個 key
  tools/
    __init__.py        # [新]
    search.py          # [新] search_web(query) -> list[dict]（Tavily）
  agents/
    resume.py          # [新] ③ tailor_resume
    company.py         # [新] ⑧ research_company（用 search_web）
    cover_letter.py    # [新] ④ write_cover_letter
    interview.py       # [新] ⑤ prepare_interview
  graph.py             # [改] 並行 fan-out + join + route 改回傳 list
  cli.py               # [改] run 回傳完整 state；format 印全部成品
tests/
  test_models.py       # [改] 新模型測試
  test_resume.py       # [新]
  test_search.py       # [新]
  test_company.py      # [新]
  test_cover_letter.py # [新]
  test_interview.py    # [新]
  test_graph.py        # [改] 並行/依賴/stop 測試 + route 回傳 list
  test_cli.py          # [改] 配合 run 回傳 state
requirements.txt       # [改] 加 requests
.env.example           # [改] 加 TAVILY_API_KEY
```

---

### Task 1: 新增 Pydantic 模型 + 擴充 State

**Files:**
- Modify: `app/models.py`（append 四個新模型）
- Modify: `app/state.py`（CopilotState 加 4 個 key）
- Modify: `requirements.txt`（加 `requests`）
- Modify: `.env.example`（加 `TAVILY_API_KEY`）
- Test: `tests/test_models.py`（append 新測試）

**Interfaces (Produces):**
- `app.models.CompanyBrief`（`company: str`, `size: str|None`, `industry: str|None`, `funding: str|None`, `salary_range: str|None`, `benefits: list[str]`, `culture_summary: str|None`, `interview_reviews: str|None`, `red_flags: list[str]`, `recent_news: list[str]`, `sources: list[str]`, `data_limited: bool=False`）
- `app.models.TailoredResume`（`summary: str`, `bullets: list[str]`, `ats_keywords_hit: list[str]`, `ats_keywords_missing: list[str]`, `notes: str|None=None`）
- `app.models.CoverLetter`（`subject: str|None=None`, `body: str`, `company_facts_used: list[str]`）
- `app.models.InterviewKit`（`technical_questions: list[str]`, `behavioral_questions: list[str]`, `taiwan_specific_questions: list[str]`, `sample_answers: list[str]`, `reverse_questions: list[str]`, `company_focus_points: list[str]`, `cautions: list[str]`）
- `app.state.CopilotState` 新增：`company_brief: CompanyBrief|None`, `tailored_resume: TailoredResume|None`, `cover_letter: CoverLetter|None`, `interview_kit: InterviewKit|None`

- [ ] **Step 1: 寫新模型的失敗測試 — append 到 `tests/test_models.py`**

```python
from app.models import CompanyBrief, TailoredResume, CoverLetter, InterviewKit


def test_company_brief_minimal_and_defaults():
    c = CompanyBrief(company="未來智能")
    assert c.data_limited is False
    assert c.benefits == [] and c.red_flags == [] and c.sources == []


def test_tailored_resume_requires_summary():
    r = TailoredResume(summary="針對 AI 工程師的定位", bullets=["做過 RAG"])
    assert r.ats_keywords_hit == []


def test_cover_letter_requires_body():
    cl = CoverLetter(body="敬啟者……")
    assert cl.company_facts_used == []


def test_interview_kit_defaults_empty_lists():
    k = InterviewKit()
    assert k.technical_questions == [] and k.reverse_questions == []
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL（`ImportError: cannot import name 'CompanyBrief'`）

- [ ] **Step 3: 實作四個模型 — append 到 `app/models.py`**

```python
class CompanyBrief(BaseModel):
    """⑧ 公司情報卡。"""
    company: str
    size: str | None = None
    industry: str | None = None
    funding: str | None = Field(default=None, description="資金/募資狀況")
    salary_range: str | None = None
    benefits: list[str] = Field(default_factory=list)
    culture_summary: str | None = None
    interview_reviews: str | None = Field(default=None, description="面試評價摘要")
    red_flags: list[str] = Field(default_factory=list, description="避雷/負評")
    recent_news: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="來源連結")
    data_limited: bool = Field(default=False, description="查無足夠公開資料時為 True")


class TailoredResume(BaseModel):
    """③ 針對單一職缺客製的履歷。"""
    summary: str = Field(description="針對此職缺的定位句")
    bullets: list[str] = Field(default_factory=list, description="改寫後的經歷條列")
    ats_keywords_hit: list[str] = Field(default_factory=list)
    ats_keywords_missing: list[str] = Field(default_factory=list)
    notes: str | None = None


class CoverLetter(BaseModel):
    """④ 求職信/自傳。"""
    subject: str | None = None
    body: str = Field(description="繁中求職信/自傳全文")
    company_facts_used: list[str] = Field(default_factory=list, description="引用的公司事實")


class InterviewKit(BaseModel):
    """⑤ 面試準備包。"""
    technical_questions: list[str] = Field(default_factory=list)
    behavioral_questions: list[str] = Field(default_factory=list)
    taiwan_specific_questions: list[str] = Field(default_factory=list, description="自傳/期望薪資/為什麼想加入等")
    sample_answers: list[str] = Field(default_factory=list, description="STAR 擬答")
    reverse_questions: list[str] = Field(default_factory=list, description="反向提問")
    company_focus_points: list[str] = Field(default_factory=list, description="公司近況考點")
    cautions: list[str] = Field(default_factory=list, description="避雷提醒")
```

- [ ] **Step 4: 執行測試確認通過**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: PASS（含既有測試）

- [ ] **Step 5: 擴充 `app/state.py`**

把 import 與 CopilotState 改成：

```python
"""LangGraph 共享狀態。"""
from typing import TypedDict

from app.models import (
    Profile, ParsedJob, MatchReport,
    CompanyBrief, TailoredResume, CoverLetter, InterviewKit,
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
```

- [ ] **Step 6: 更新 `requirements.txt` 與 `.env.example`**

`requirements.txt` append 一行：
```
requests>=2.31
```
`.env.example` append：
```
# 公司情報 agent 用的搜尋 API（Tavily）
TAVILY_API_KEY=tvly-xxxxx
```
然後安裝新依賴：`.venv\Scripts\python.exe -m pip install requests`

- [ ] **Step 7: 全套測試確認沒弄壞既有**

Run: `.venv\Scripts\python.exe -m pytest`
Expected: 全部 PASS（live deselected）

- [ ] **Step 8: Commit**

```bash
git add app/models.py app/state.py tests/test_models.py requirements.txt .env.example
git commit -m "feat(m2): add CompanyBrief/TailoredResume/CoverLetter/InterviewKit models and extend state"
```

---

### Task 2: ③ 履歷客製 agent（resume）

**Files:**
- Create: `app/agents/resume.py`
- Test: `tests/test_resume.py`

**Interfaces:**
- Consumes: `app.llm.get_llm`、`app.models.ParsedJob/Profile/TailoredResume`
- Produces: `app.agents.resume.tailor_resume(job: ParsedJob, profile: Profile) -> TailoredResume`

- [ ] **Step 1: 失敗測試 — Create `tests/test_resume.py`**

```python
from app.models import TailoredResume
from app.agents import resume as resume_mod
from tests.conftest import FakeLLM


def test_tailor_resume_returns_tailored_resume(monkeypatch, demo_profile, sample_parsed_job):
    canned = TailoredResume(
        summary="三年後端 + 一年 LLM，貼合此 AI 工程師職缺",
        bullets=["用 LangChain 建 RAG 客服，工單降 25%"],
        ats_keywords_hit=["Python", "LangChain"],
        ats_keywords_missing=["LangGraph"],
    )
    monkeypatch.setattr(resume_mod, "get_llm", lambda tier: FakeLLM(canned))

    result = resume_mod.tailor_resume(sample_parsed_job, demo_profile)

    assert isinstance(result, TailoredResume)
    assert "Python" in result.ats_keywords_hit


def test_tailor_resume_uses_standard_tier(monkeypatch, demo_profile, sample_parsed_job):
    seen = {}
    canned = TailoredResume(summary="x")

    def fake_get_llm(tier):
        seen["tier"] = tier
        return FakeLLM(canned)

    monkeypatch.setattr(resume_mod, "get_llm", fake_get_llm)
    resume_mod.tailor_resume(sample_parsed_job, demo_profile)
    assert seen["tier"] == "standard"
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_resume.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.agents.resume'`）

- [ ] **Step 3: 實作 — Create `app/agents/resume.py`**

```python
"""③ 履歷客製 Agent：針對單一職缺改寫履歷。"""
from app.llm import get_llm
from app.models import ParsedJob, Profile, TailoredResume

RESUME_SYSTEM = (
    "你是資深履歷顧問。請依『職缺』改寫『求職者』的履歷，"
    "挑選並重寫最相關的經歷條列，命中 JD 的 ATS 關鍵字，"
    "並列出已命中與尚缺的關鍵字。"
    "嚴禁捏造求職者沒有的經歷；只能重組與強調既有內容。"
)


def tailor_resume(job: ParsedJob, profile: Profile) -> TailoredResume:
    """針對職缺客製履歷（standard 分層）。"""
    llm = get_llm("standard").with_structured_output(TailoredResume)
    human = (
        "【職缺】\n"
        f"{job.model_dump_json(indent=2)}\n\n"
        "【求職者背景】\n"
        f"{profile.model_dump_json(indent=2)}"
    )
    return llm.invoke([("system", RESUME_SYSTEM), ("human", human)])
```

- [ ] **Step 4: 執行確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_resume.py -v` → PASS（2 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 5: Commit**

```bash
git add app/agents/resume.py tests/test_resume.py
git commit -m "feat(m2): add resume tailor agent"
```

---

### Task 3: 搜尋工具 `search_web`（Tavily）

**Files:**
- Create: `app/tools/__init__.py`（空檔）
- Create: `app/tools/search.py`
- Test: `tests/test_search.py`

**Interfaces:**
- Produces: `app.tools.search.search_web(query: str, max_results: int = 5) -> list[dict]`（每個 dict 含 `title`/`url`/`content`）

- [ ] **Step 1: 失敗測試 — Create `tests/test_search.py`**

```python
import pytest

from app.tools import search as search_mod


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_search_web_parses_results(monkeypatch):
    payload = {"results": [
        {"title": "未來智能 評價", "url": "https://x.com/a", "content": "福利不錯"},
        {"title": "薪資", "url": "https://x.com/b", "content": "月薪 6 萬起"},
    ]}
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(search_mod.requests, "post", lambda *a, **k: _FakeResp(payload))

    results = search_mod.search_web("未來智能")

    assert len(results) == 2
    assert results[0]["title"] == "未來智能 評價"
    assert results[0]["url"] == "https://x.com/a"
    assert "福利" in results[0]["content"]


def test_search_web_raises_without_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        search_mod.search_web("未來智能")
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_search.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.tools'`）

- [ ] **Step 3: 實作 — Create `app/tools/__init__.py`（空檔）與 `app/tools/search.py`**

```python
"""網路搜尋工具（Tavily）：供 ⑧ 公司情報 agent 使用。"""
import os

import requests

TAVILY_URL = "https://api.tavily.com/search"


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """以 Tavily 搜尋公開資料，回傳 [{title, url, content}, ...]。"""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY 未設定，無法執行搜尋")
    resp = requests.post(
        TAVILY_URL,
        json={"api_key": api_key, "query": query, "max_results": max_results},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        }
        for r in data.get("results", [])
    ]
```

- [ ] **Step 4: 執行確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_search.py -v` → PASS（2 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 5: Commit**

```bash
git add app/tools/__init__.py app/tools/search.py tests/test_search.py
git commit -m "feat(m2): add Tavily web search tool"
```

---

### Task 4: ⑧ 公司情報 agent（company，tool use）

**Files:**
- Create: `app/agents/company.py`
- Test: `tests/test_company.py`

**Interfaces:**
- Consumes: `app.tools.search.search_web`、`app.llm.get_llm`、`app.models.CompanyBrief`
- Produces: `app.agents.company.research_company(company_name: str) -> CompanyBrief`

**行為規格：** 先用 `search_web` 查公司（查詢字串含「評價 薪資 福利 面試」）；若搜尋丟例外或回傳空清單 → 回傳 `CompanyBrief(company=company_name, data_limited=True)`（不呼叫 LLM）；否則把搜尋結果丟給 LLM 彙整成 `CompanyBrief`。

- [ ] **Step 1: 失敗測試 — Create `tests/test_company.py`**

```python
from app.models import CompanyBrief
from app.agents import company as company_mod
from tests.conftest import FakeLLM


def test_research_company_summarizes_results(monkeypatch):
    monkeypatch.setattr(
        company_mod, "search_web",
        lambda q, **k: [{"title": "評價", "url": "https://x/a", "content": "福利好"}],
    )
    canned = CompanyBrief(company="未來智能", salary_range="月薪 6 萬起", benefits=["彈性工時"])
    monkeypatch.setattr(company_mod, "get_llm", lambda tier: FakeLLM(canned))

    brief = company_mod.research_company("未來智能")

    assert isinstance(brief, CompanyBrief)
    assert brief.data_limited is False
    assert "彈性工時" in brief.benefits


def test_research_company_marks_data_limited_on_empty(monkeypatch):
    monkeypatch.setattr(company_mod, "search_web", lambda q, **k: [])
    # get_llm 不應被呼叫；若被呼叫就讓測試爆掉
    def boom(tier):
        raise AssertionError("LLM should not be called when no search results")
    monkeypatch.setattr(company_mod, "get_llm", boom)

    brief = company_mod.research_company("查無公司")

    assert brief.company == "查無公司"
    assert brief.data_limited is True


def test_research_company_handles_search_failure(monkeypatch):
    def raise_err(q, **k):
        raise RuntimeError("搜尋失敗")
    monkeypatch.setattr(company_mod, "search_web", raise_err)

    brief = company_mod.research_company("壞掉公司")

    assert brief.data_limited is True
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_company.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.agents.company'`）

- [ ] **Step 3: 實作 — Create `app/agents/company.py`**

```python
"""⑧ 公司情報 Agent：上網查證公司並彙整成 CompanyBrief。"""
from app.tools.search import search_web
from app.llm import get_llm
from app.models import CompanyBrief

COMPANY_SYSTEM = (
    "你是企業情報分析師。根據提供的公開搜尋結果，彙整出公司情報卡："
    "規模、產業、資金/募資狀況、薪資範圍、福利、文化與評價摘要、"
    "面試評價、避雷紅旗、近期新聞，並附上來源連結。"
    "只根據提供的資料作答，不要臆測；資料不足的欄位留空。"
)


def research_company(company_name: str) -> CompanyBrief:
    """查證公司並回傳 CompanyBrief（standard 分層）；查無資料則標記 data_limited。"""
    try:
        results = search_web(f"{company_name} 公司 評價 薪資 福利 面試")
    except Exception:
        results = []

    if not results:
        return CompanyBrief(company=company_name, data_limited=True)

    context = "\n\n".join(
        f"- {r['title']}\n{r['content']}\n來源: {r['url']}" for r in results
    )
    human = f"公司名稱：{company_name}\n\n公開搜尋結果：\n{context}"
    llm = get_llm("standard").with_structured_output(CompanyBrief)
    return llm.invoke([("system", COMPANY_SYSTEM), ("human", human)])
```

- [ ] **Step 4: 執行確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_company.py -v` → PASS（3 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 5: Commit**

```bash
git add app/agents/company.py tests/test_company.py
git commit -m "feat(m2): add company research agent with web search tool"
```

---

### Task 5: ④ 求職信/自傳 agent（cover_letter）

**Files:**
- Create: `app/agents/cover_letter.py`
- Test: `tests/test_cover_letter.py`

**Interfaces:**
- Consumes: `app.llm.get_llm`、`app.models.ParsedJob/Profile/CompanyBrief/CoverLetter`
- Produces: `app.agents.cover_letter.write_cover_letter(job: ParsedJob, profile: Profile, company: CompanyBrief | None) -> CoverLetter`

**行為規格：** `company` 可能為 `None`（公司情報不足）；有就引用公司事實，沒有就只根據職缺與求職者撰寫。

- [ ] **Step 1: 失敗測試 — Create `tests/test_cover_letter.py`**

```python
from app.models import CoverLetter, CompanyBrief
from app.agents import cover_letter as cl_mod
from tests.conftest import FakeLLM


def test_write_cover_letter_returns_letter(monkeypatch, demo_profile, sample_parsed_job):
    canned = CoverLetter(body="敬啟者，我對貴司的 AI 職缺深感興趣……",
                         company_facts_used=["剛完成 B 輪募資"])
    monkeypatch.setattr(cl_mod, "get_llm", lambda tier: FakeLLM(canned))
    company = CompanyBrief(company="未來智能", funding="B 輪")

    letter = cl_mod.write_cover_letter(sample_parsed_job, demo_profile, company)

    assert isinstance(letter, CoverLetter)
    assert letter.body


def test_write_cover_letter_handles_none_company(monkeypatch, demo_profile, sample_parsed_job):
    canned = CoverLetter(body="敬啟者……")
    monkeypatch.setattr(cl_mod, "get_llm", lambda tier: FakeLLM(canned))

    letter = cl_mod.write_cover_letter(sample_parsed_job, demo_profile, None)

    assert isinstance(letter, CoverLetter)


def test_write_cover_letter_uses_standard_tier(monkeypatch, demo_profile, sample_parsed_job):
    seen = {}
    canned = CoverLetter(body="x")

    def fake_get_llm(tier):
        seen["tier"] = tier
        return FakeLLM(canned)

    monkeypatch.setattr(cl_mod, "get_llm", fake_get_llm)
    cl_mod.write_cover_letter(sample_parsed_job, demo_profile, None)
    assert seen["tier"] == "standard"
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cover_letter.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.agents.cover_letter'`）

- [ ] **Step 3: 實作 — Create `app/agents/cover_letter.py`**

```python
"""④ 求職信/自傳 Agent。"""
from app.llm import get_llm
from app.models import ParsedJob, Profile, CompanyBrief, CoverLetter

COVER_SYSTEM = (
    "你是求職文案專家。請以台灣求職文化撰寫一封繁中求職信/自傳，"
    "對應職缺需求、凸顯求職者的相關經歷。"
    "若提供了公司情報，請自然地引用真實公司事實（例如募資、產品、文化），"
    "並把引用到的事實列在 company_facts_used。沒有公司情報就不要杜撰。"
)


def write_cover_letter(job: ParsedJob, profile: Profile, company: CompanyBrief | None) -> CoverLetter:
    """撰寫求職信/自傳（standard 分層）。"""
    company_json = company.model_dump_json(indent=2) if company else "（無公司情報）"
    human = (
        "【職缺】\n"
        f"{job.model_dump_json(indent=2)}\n\n"
        "【求職者背景】\n"
        f"{profile.model_dump_json(indent=2)}\n\n"
        "【公司情報】\n"
        f"{company_json}"
    )
    llm = get_llm("standard").with_structured_output(CoverLetter)
    return llm.invoke([("system", COVER_SYSTEM), ("human", human)])
```

- [ ] **Step 4: 執行確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cover_letter.py -v` → PASS（3 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 5: Commit**

```bash
git add app/agents/cover_letter.py tests/test_cover_letter.py
git commit -m "feat(m2): add cover letter agent"
```

---

### Task 6: ⑤ 面試準備 agent（interview）

**Files:**
- Create: `app/agents/interview.py`
- Test: `tests/test_interview.py`

**Interfaces:**
- Consumes: `app.llm.get_llm`、`app.models.ParsedJob/Profile/CompanyBrief/InterviewKit`
- Produces: `app.agents.interview.prepare_interview(job: ParsedJob, profile: Profile, company: CompanyBrief | None) -> InterviewKit`

- [ ] **Step 1: 失敗測試 — Create `tests/test_interview.py`**

```python
from app.models import InterviewKit, CompanyBrief
from app.agents import interview as iv_mod
from tests.conftest import FakeLLM


def test_prepare_interview_returns_kit(monkeypatch, demo_profile, sample_parsed_job):
    canned = InterviewKit(
        technical_questions=["解釋 RAG 流程"],
        reverse_questions=["團隊目前的 agent 架構是？"],
        cautions=["注意加班文化"],
    )
    monkeypatch.setattr(iv_mod, "get_llm", lambda tier: FakeLLM(canned))
    company = CompanyBrief(company="未來智能", red_flags=["加班多"])

    kit = iv_mod.prepare_interview(sample_parsed_job, demo_profile, company)

    assert isinstance(kit, InterviewKit)
    assert kit.reverse_questions


def test_prepare_interview_handles_none_company(monkeypatch, demo_profile, sample_parsed_job):
    canned = InterviewKit(technical_questions=["Q1"])
    monkeypatch.setattr(iv_mod, "get_llm", lambda tier: FakeLLM(canned))

    kit = iv_mod.prepare_interview(sample_parsed_job, demo_profile, None)

    assert isinstance(kit, InterviewKit)


def test_prepare_interview_uses_standard_tier(monkeypatch, demo_profile, sample_parsed_job):
    seen = {}
    canned = InterviewKit()

    def fake_get_llm(tier):
        seen["tier"] = tier
        return FakeLLM(canned)

    monkeypatch.setattr(iv_mod, "get_llm", fake_get_llm)
    iv_mod.prepare_interview(sample_parsed_job, demo_profile, None)
    assert seen["tier"] == "standard"
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_interview.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.agents.interview'`）

- [ ] **Step 3: 實作 — Create `app/agents/interview.py`**

```python
"""⑤ 面試準備 Agent。"""
from app.llm import get_llm
from app.models import ParsedJob, Profile, CompanyBrief, InterviewKit

INTERVIEW_SYSTEM = (
    "你是面試教練。請依職缺與求職者背景，準備面試包："
    "技術題、行為題、台灣特有題（自傳、期望薪資、為什麼想加入）、"
    "對應的 STAR 擬答、給求職者用的反向提問。"
    "若提供公司情報，請加入公司近況考點與避雷提醒（依紅旗）。"
)


def prepare_interview(job: ParsedJob, profile: Profile, company: CompanyBrief | None) -> InterviewKit:
    """準備面試包（standard 分層）。"""
    company_json = company.model_dump_json(indent=2) if company else "（無公司情報）"
    human = (
        "【職缺】\n"
        f"{job.model_dump_json(indent=2)}\n\n"
        "【求職者背景】\n"
        f"{profile.model_dump_json(indent=2)}\n\n"
        "【公司情報】\n"
        f"{company_json}"
    )
    llm = get_llm("standard").with_structured_output(InterviewKit)
    return llm.invoke([("system", INTERVIEW_SYSTEM), ("human", human)])
```

- [ ] **Step 4: 執行確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_interview.py -v` → PASS（3 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

- [ ] **Step 5: Commit**

```bash
git add app/agents/interview.py tests/test_interview.py
git commit -m "feat(m2): add interview prep agent"
```

---

### Task 7: 圖改寫（並行 fan-out + 依賴 + join）

**Files:**
- Modify: `app/graph.py`（整檔改寫）
- Modify: `tests/test_graph.py`（改寫 route 測試 + 新增並行/依賴/stop 測試）

**Interfaces:**
- Consumes: 全部 agent 函式 + `CopilotState`
- Produces:
  - 節點函式：`parse_node`、`match_node`、`company_research_node`、`resume_tailor_node`、`cover_letter_node`、`interview_prep_node`、`join_node`
  - `route_after_match(state) -> list[str] | str`：proceed 時回傳 `["resume_tailor", "company_research"]`，否則 `"stop"`
  - `PROCEED_SCORE_THRESHOLD`（沿用 M1，值 60）
  - `build_graph()`：compile 後的並行圖

**圖拓撲：**
```
START → parse → match → (route_after_match)
   "stop" → END
   proceed → resume_tailor   ┐(並行)
   proceed → company_research ┘
   company_research → cover_letter   ┐(並行，需 company_brief)
   company_research → interview_prep ┘
   resume_tailor, cover_letter, interview_prep → join → END
```

- [ ] **Step 1: 改寫測試 — 覆寫 `tests/test_graph.py` 全檔**

```python
from app.models import (
    ParsedJob, MatchReport, CompanyBrief, TailoredResume, CoverLetter, InterviewKit,
)
from app import graph as graph_mod


def _patch_all(monkeypatch, report: MatchReport):
    monkeypatch.setattr(graph_mod, "parse_job",
                        lambda jd_text: ParsedJob(title="AI 工程師", company="未來智能"))
    monkeypatch.setattr(graph_mod, "match_profile", lambda job, profile: report)
    monkeypatch.setattr(graph_mod, "research_company",
                        lambda name: CompanyBrief(company=name, funding="B 輪"))
    monkeypatch.setattr(graph_mod, "tailor_resume",
                        lambda job, profile: TailoredResume(summary="客製履歷"))
    monkeypatch.setattr(graph_mod, "write_cover_letter",
                        lambda job, profile, company: CoverLetter(body="求職信"))
    monkeypatch.setattr(graph_mod, "prepare_interview",
                        lambda job, profile, company: InterviewKit(technical_questions=["Q"]))


def _initial_state(profile):
    return {
        "jd_text": "（任意）", "profile": profile,
        "parsed_job": None, "match_report": None, "company_brief": None,
        "tailored_resume": None, "cover_letter": None, "interview_kit": None,
    }


def test_proceed_path_produces_all_outputs(monkeypatch, demo_profile):
    _patch_all(monkeypatch, MatchReport(score=82, recommend_proceed=True, reason="吻合"))
    final = graph_mod.build_graph().invoke(_initial_state(demo_profile))

    assert final["match_report"].score == 82
    assert final["company_brief"].funding == "B 輪"
    assert final["tailored_resume"].summary == "客製履歷"
    assert final["cover_letter"].body == "求職信"
    assert final["interview_kit"].technical_questions == ["Q"]


def test_stop_path_skips_fanout(monkeypatch, demo_profile):
    _patch_all(monkeypatch, MatchReport(score=40, recommend_proceed=False, reason="不符"))
    final = graph_mod.build_graph().invoke(_initial_state(demo_profile))

    assert final["match_report"].score == 40
    assert final["tailored_resume"] is None
    assert final["cover_letter"] is None
    assert final["interview_kit"] is None
    assert final["company_brief"] is None


def test_cover_and_interview_receive_company_brief(monkeypatch, demo_profile):
    seen = {}
    _patch_all(monkeypatch, MatchReport(score=80, recommend_proceed=True, reason="ok"))

    def cover(job, profile, company):
        seen["cover_company"] = company
        return CoverLetter(body="x")

    def interview(job, profile, company):
        seen["interview_company"] = company
        return InterviewKit()

    monkeypatch.setattr(graph_mod, "write_cover_letter", cover)
    monkeypatch.setattr(graph_mod, "prepare_interview", interview)

    graph_mod.build_graph().invoke(_initial_state(demo_profile))

    assert seen["cover_company"] is not None
    assert seen["cover_company"].funding == "B 輪"
    assert seen["interview_company"] is not None


def test_route_after_match_proceeds_returns_list():
    state = {"match_report": MatchReport(score=80, recommend_proceed=True, reason="高")}
    assert graph_mod.route_after_match(state) == ["resume_tailor", "company_research"]


def test_route_after_match_stops_low_score():
    state = {"match_report": MatchReport(score=50, recommend_proceed=True, reason="分數不足")}
    assert graph_mod.route_after_match(state) == "stop"


def test_route_after_match_stops_when_not_recommended():
    state = {"match_report": MatchReport(score=90, recommend_proceed=False, reason="不合")}
    assert graph_mod.route_after_match(state) == "stop"
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_graph.py -v`
Expected: FAIL（route 回傳值或新節點不存在）

- [ ] **Step 3: 改寫 — 覆寫 `app/graph.py` 全檔**

```python
"""Supervisor 並行圖：parse -> match -> (proceed: fan-out / stop) -> join。

proceed 時扇出到 resume_tailor 與 company_research（並行）；
company_research 完成後再扇出 cover_letter 與 interview_prep（需 company_brief）；
三個生成節點匯入 join（fan-in barrier）後到 END。
各節點寫入不同 state key，故不需 reducer。
"""
from langgraph.graph import StateGraph, START, END

from app.state import CopilotState
from app.agents.parse import parse_job
from app.agents.match import match_profile
from app.agents.company import research_company
from app.agents.resume import tailor_resume
from app.agents.cover_letter import write_cover_letter
from app.agents.interview import prepare_interview

# 匹配分數門檻：低於此分數即使 LLM 建議續做也提早收手（對應設計規格 §6）。
PROCEED_SCORE_THRESHOLD = 60


def parse_node(state: CopilotState) -> dict:
    return {"parsed_job": parse_job(state["jd_text"])}


def match_node(state: CopilotState) -> dict:
    return {"match_report": match_profile(state["parsed_job"], state["profile"])}


def company_research_node(state: CopilotState) -> dict:
    return {"company_brief": research_company(state["parsed_job"].company)}


def resume_tailor_node(state: CopilotState) -> dict:
    return {"tailored_resume": tailor_resume(state["parsed_job"], state["profile"])}


def cover_letter_node(state: CopilotState) -> dict:
    return {"cover_letter": write_cover_letter(
        state["parsed_job"], state["profile"], state.get("company_brief"))}


def interview_prep_node(state: CopilotState) -> dict:
    return {"interview_kit": prepare_interview(
        state["parsed_job"], state["profile"], state.get("company_brief"))}


def join_node(state: CopilotState) -> dict:
    """fan-in 匯合點：等三個生成節點都完成。"""
    return {}


def route_after_match(state: CopilotState):
    """proceed（通過分數門檻且 LLM 建議）→ 扇出；否則收手。"""
    report = state["match_report"]
    if report.recommend_proceed and report.score >= PROCEED_SCORE_THRESHOLD:
        return ["resume_tailor", "company_research"]
    return "stop"


def build_graph():
    g = StateGraph(CopilotState)
    g.add_node("parse", parse_node)
    g.add_node("match", match_node)
    g.add_node("company_research", company_research_node)
    g.add_node("resume_tailor", resume_tailor_node)
    g.add_node("cover_letter", cover_letter_node)
    g.add_node("interview_prep", interview_prep_node)
    g.add_node("join", join_node)

    g.add_edge(START, "parse")
    g.add_edge("parse", "match")
    g.add_conditional_edges(
        "match",
        route_after_match,
        {
            "resume_tailor": "resume_tailor",
            "company_research": "company_research",
            "stop": END,
        },
    )
    # company_research 完成後扇出需要 company_brief 的兩個節點
    g.add_edge("company_research", "cover_letter")
    g.add_edge("company_research", "interview_prep")
    # fan-in：三個生成節點匯入 join
    g.add_edge("resume_tailor", "join")
    g.add_edge("cover_letter", "join")
    g.add_edge("interview_prep", "join")
    g.add_edge("join", END)
    return g.compile()
```

- [ ] **Step 4: 執行確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_graph.py -v` → PASS（6 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠

> 若 LangGraph 對「條件分支回傳 list + path_map」或「多邊匯入 join」的行為與此處不符而測試無法通過，**停下並回報 BLOCKED 與確切錯誤**，不要自行改成不同 API。

- [ ] **Step 5: Commit**

```bash
git add app/graph.py tests/test_graph.py
git commit -m "feat(m2): parallel fan-out graph (resume + company -> cover/interview -> join)"
```

---

### Task 8: CLI 輸出全部成品

**Files:**
- Modify: `app/cli.py`
- Modify: `tests/test_cli.py`

**Interfaces（變更）:**
- `app.cli.run(jd_path: str, profile_path: str = "data/demo_profile.json") -> CopilotState`（**改為回傳完整 final state dict**，不再只回 MatchReport）
- `app.cli.format_output(state: dict, job_title: str) -> str`（**取代 M1 的 format_report**；印匹配/公司情報/履歷/求職信/面試）
- `load_profile`、`main` 維持，但 `main` 改用 `format_output`

- [ ] **Step 1: 改寫測試 — 覆寫 `tests/test_cli.py` 全檔**

```python
from app.models import (
    ParsedJob, MatchReport, CompanyBrief, TailoredResume, CoverLetter, InterviewKit,
)
from app import cli as cli_mod


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
    }


def test_format_output_includes_all_sections():
    text = cli_mod.format_output(_full_state(), job_title="AI 工程師")
    assert "AI 工程師" in text
    assert "82" in text              # 匹配分數
    assert "月薪 6 萬起" in text       # 公司情報
    assert "客製定位" in text          # 履歷
    assert "敬啟者" in text            # 求職信
    assert "解釋 RAG" in text          # 面試題


def test_format_output_handles_stop_path():
    # stop：只有匹配，沒有後續成品
    state = {
        "parsed_job": ParsedJob(title="X", company="Y"),
        "match_report": MatchReport(score=30, recommend_proceed=False, reason="不符"),
        "company_brief": None, "tailored_resume": None,
        "cover_letter": None, "interview_kit": None,
    }
    text = cli_mod.format_output(state, job_title="X")
    assert "30" in text
    assert "不符" in text


def test_run_invokes_graph_and_returns_state(monkeypatch, tmp_path):
    jd_file = tmp_path / "jd.txt"
    jd_file.write_text("一些 JD", encoding="utf-8")
    fake_final = _full_state()

    class FakeGraph:
        def invoke(self, state):
            return fake_final

    monkeypatch.setattr(cli_mod, "build_graph", lambda: FakeGraph())

    result = cli_mod.run(str(jd_file))
    assert result["match_report"].score == 82
```

- [ ] **Step 2: 執行確認失敗**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: FAIL（`AttributeError: module 'app.cli' has no attribute 'format_output'` 或 run 回傳型別不符）

- [ ] **Step 3: 改寫 — 覆寫 `app/cli.py` 全檔**

```python
"""終端機進入點：讀 JD → 跑並行圖 → 印完整投遞包。"""
import json
import sys
from pathlib import Path

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

    return "\n".join(lines)


def run(jd_path: str, profile_path: str = "data/demo_profile.json") -> CopilotState:
    jd_text = Path(jd_path).read_text(encoding="utf-8")
    profile = load_profile(profile_path)
    graph = build_graph()
    return graph.invoke({
        "jd_text": jd_text,
        "profile": profile,
        "parsed_job": None,
        "match_report": None,
        "company_brief": None,
        "tailored_resume": None,
        "cover_letter": None,
        "interview_kit": None,
    })


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("用法：python -m app.cli <jd 檔案路徑>")
        return 1
    jd_path = argv[0]
    state = run(jd_path)
    title = Path(jd_path).stem
    print(format_output(state, job_title=title))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 執行確認通過 + 全套**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v` → PASS（4 passed）
Run: `.venv\Scripts\python.exe -m pytest` → 全綠（回報總數）

- [ ] **Step 5: Commit**

```bash
git add app/cli.py tests/test_cli.py
git commit -m "feat(m2): CLI prints full application package (match/company/resume/letter/interview)"
```

---

## Self-Review（對照規格檢查）

**1. Spec coverage（M2 範圍，對照設計規格 §5/§6）：**
- ③ 履歷客製 → Task 2 ✓
- ④ 求職信/自傳（引用公司事實）→ Task 5 ✓
- ⑤ 面試準備（含反向提問/避雷）→ Task 6 ✓
- ⑧ 公司情報 + web search 工具 → Task 3（工具）+ Task 4（agent）✓
- 並行 fan-out + 依賴（⑧→④⑤）+ 收斂 → Task 7 ✓
- supervisor 分數門檻決定是否扇出 → Task 7 `route_after_match` ✓
- CLI 呈現完整投遞包 → Task 8 ✓
- 不爬蟲/不自動投、搜尋用 API → 全程遵守 ✓
- （M3 才做：⑥ Critic 反思迴圈、⑦ human-in-the-loop、串流 UI、FastAPI、前端）→ 明確排除 ✓

**2. Placeholder scan：** 無 TBD/TODO；每個 code step 皆有完整可執行程式碼。✓

**3. Type consistency：**
- 新模型欄位於 models / 各 agent / 測試 / CLI 一致。
- `route_after_match` 回傳 `["resume_tailor","company_research"]` 或 `"stop"`，與 path_map 鍵一致（`resume_tailor`/`company_research`/`stop`）。✓
- 各 agent 函式簽名（`tailor_resume(job,profile)`、`research_company(name)`、`write_cover_letter(job,profile,company)`、`prepare_interview(job,profile,company)`、`search_web(query,max_results)`）於 graph 節點與測試一致。✓
- `run` 回傳型別由 `MatchReport` 改為 `CopilotState`，Task 8 測試已配合改寫。✓
- graph 以 `from app.agents.X import fn` 匯入，使 Task 7 測試的 `monkeypatch.setattr(graph_mod, "fn", ...)` 生效。✓

無發現缺漏。
