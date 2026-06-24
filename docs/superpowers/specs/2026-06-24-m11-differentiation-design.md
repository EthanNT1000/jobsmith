# M11 — 差異化 wow + 收尾 設計（Design Spec）

**狀態**：設計待使用者確認 → 通過後轉 writing-plans。

**目標**：在已完成的 M8（止血）/ M9（agent 深度）/ M10（英雄前端 + JD 抓取 + 匯出 + 4 來源 + CLI 上網查證）基礎上，加上「差異化 wow」與產品收尾，讓這個台灣 AI 求職 Co-pilot 更完整、更有作品集訊號。

**本里程碑範圍（依施作順序）**：
0. App shell 改側欄 rail + 本機 CLI chip（最先做，新分頁直接塞進 rail）
1. 多輪面試模擬器
2. 歷史紀錄／我的投遞包（sqlite，自動儲存）
3. 推薦職缺無上限 + 分頁
4. 技能缺口市場分析
5. Agent 記憶／個人化（履歷 + 偏好）
6. 公司職缺查詢（job boards 依公司過濾 + WebSearch 官網 careers）

## Global Constraints（沿用 M8–M10）

- 介面 zh-Hant；單人本機、無登入；維持本機 only。
- 串流端點用同步 `def`（避免 claude_cli 同步 subprocess 阻塞事件迴圈）。
- 前端閘門：`cd frontend && npm run build` 成功；型別匯入用 `import type`；圖示用 lucide（走 `ui/icons.ts`）；元件走 M10 原語（Card/Button/Badge/EmptyState/Skeleton）與 brand token。
- 不破壞既有：自動找職缺 / 履歷健檢 / 投遞包工作台 / 後端切換 / 優雅降級 / telemetry / 人工核可 / JD 抓取 / 匯出。
- 新依賴只用純 Python；sqlite 用標準庫。LLM 經 `app/llm.py`（分層 + 後端切換）；逐節點/呼叫成本記入 telemetry。
- 公司職缺/面試的上網查證走 `research_structured`（claude_cli WebSearch）；非 CLI 後端優雅降級。

## 資料儲存

新增 sqlite（與 checkpoints 分開）：`data/app.sqlite`（`COPILOT_APP_DB` 可覆寫，測試用 `:memory:`）。模組 `app/store/db.py` 提供連線（`check_same_thread=False`）。

- 表 `packages`（歷史投遞包）：`id INTEGER PK`、`created_at TEXT`、`job_title`、`company`、`match_score INT`、`jd_text`、`profile_json`、`package_json`（完整成品：parsed_job/match/company/resume/cover/interview/critique）、`approved INT`。
- 表 `user_memory`（單列，id=1）：`profile_json`、`preferences_json`（`{target_titles:[], seniority:"", tone:"", emphasize_skills:[]}`）、`updated_at`。

---

## ⓪ App shell：側欄 rail + 本機 CLI chip（仿 Open Design）

**目的**：把目前頂部橫向 tab 換成「左側 icon+文字 rail + 右側內容區」的產品級 shell（容納 M11 新分頁、可擴充），並把後端切換重樣式成 Open Design 風格的「本機 CLI」chip。

**佈局**：
```
┌────────┬──────────────────────────────────────────┐
│ Brand  │ 頂部列                 [ 本機 CLI · Claude Code ▾ ]│
│ 🔍自動找職缺                                          │
│ 📊履歷健檢   ← 右側＝當前功能畫面 →                    │
│ 🕸投遞包工作台                                        │
│ 💬面試模擬                                            │
│ 🗂我的投遞包                                          │
│ ⚙個人化(底)                                          │
└────────┴──────────────────────────────────────────┘
```
- **Rail**：圖示 + 中文標籤（寬約 200–220px）；頂部 Brand；區塊用 lucide 圖示；active 項 brand 底色（沿用 M10 segmented 風格，改直向）；底部「個人化」。所有分頁維持「全掛載只切顯示」以保留狀態。
- **頂部列**：右側「本機 CLI · {Claude Code|Codex CLI} ▾」chip（重樣式 `BackendSelector`），下拉**只露 claude_cli / codex_cli**（anthropic 不在主選單；env 有金鑰時仍可用，但不顯眼）。模型分層（haiku/sonnet/opus by tier）以 tooltip 說明，不在 chip 選單選單一 model。
- **行動裝置**：rail 收為底部 tab bar 或漢堡抽屜；頂部 chip 保留。

**元件**：新增 `frontend/src/ui/Sidebar.tsx`（rail）；`App.tsx` 改 shell 佈局（rail + `<main>`）；`BackendSelector` 改為 chip 樣式並過濾為兩個 CLI。

**測試**：`npm run build` 綠；切換分頁狀態保留；切換後端後續呼叫採用新後端（既有 `/api/backend` 行為不變）。

> 後續 ①–⑥ 的新畫面（面試模擬、我的投遞包）都以 rail 分頁呈現；技能缺口/公司職缺/個人化依各自說明嵌入既有畫面或小面板。

---

## ① 多輪面試模擬器

**目的**：把一次性的面試準備卡升級成互動式模擬：agent 出題 → 你作答 → 即時回饋 → 下一題 → 總評。展現 stateful agentic 互動。

**架構**（無狀態、前端持對話）：`app/agents/interview_sim.py`
- `generate_questions(jd, profile, n=6) -> list[InterviewQuestion]`：依面試準備卡風格抽技術/行為/台灣特有題（`InterviewQuestion{category, question}`）。
- `evaluate_answer(question, answer, jd, profile) -> AnswerFeedback`：`{score:int, strengths:[], improvements:[], model_answer:str}`。
- `summarize(transcript) -> InterviewSummary`：`{overall_score:int, summary:str, advice:[]}`。
- 新增 models：`InterviewQuestion / AnswerFeedback / InterviewSummary`。

**端點**（同步 def）：
- `POST /api/interview/start`（`{jd_text, profile}`）→ `{questions:[...]}`
- `POST /api/interview/answer`（`{jd_text, profile, question, answer}`）→ `AnswerFeedback`
- `POST /api/interview/summary`（`{jd_text, profile, transcript:[{question,answer}]}`）→ `InterviewSummary`

**UI**（新分頁「面試模擬」）：JD 來源＝貼上或從「我的投遞包」帶入；聊天式：問題卡 → 作答 textarea → 送出 → 回饋卡（ScoreRing + 優點/可改進/示範答法）→ 下一題（進度 Qn/N）→ 結束顯示總評卡。每次呼叫記 telemetry。

**降級/錯誤**：LLM 失敗回友善訊息；非 claude_cli 後端照常（純生成，不需上網）。

**測試**：mock LLM 驗 generate/evaluate/summary 結構與端點。

---

## ② 歷史紀錄／我的投遞包

**目的**：跨重啟保存每次完成的投遞包，可回查/重開/刪除。展現產品完整度與持久化。

**架構**：`app/store/history.py`
- `save_package(state_dict) -> int`、`list_packages() -> list[dict]`（摘要：id/時間/職稱/公司/分數）、`get_package(id) -> dict`、`delete_package(id)`。
- **自動儲存時機**：pipeline 抵達終局（`/api/run` 或 `/api/resume` 的 `_stream` 結束、`snapshot.next` 為空）時，用 `GRAPH.get_state(config)` 取最終 state → `save_package`。只存有實際成品者。

**端點**：`GET /api/history`、`GET /api/history/{id}`、`DELETE /api/history/{id}`。

**UI**（新分頁「我的投遞包」）：清單卡（職稱/公司/匹配分/日期 + 刪除）→ 點開唯讀檢視（重用 `Documents` 卡）+ 下載 Word/列印（重用 M10 匯出）+「重新開啟」載回投遞包工作台 / 帶入面試模擬。空狀態用 EmptyState。

**測試**：用 `:memory:` DB 驗 save/list/get/delete；端點測試。

---

## ③ 推薦職缺無上限 + 分頁

**目的**：移除目前 `rank_jobs(top_k=12)` 的硬上限，顯示全部排序結果，但前端分頁避免頁面過長。

**後端**：`rank_jobs` 預設 `top_k` 拉高（顯示全部）；為控 LLM prompt 大小，排序輸入上限約 40–50（超過先以關鍵字/來源初篩）。每來源 `limit` 與查詢數適度增加以擴大來源池。

**前端**：`JobSearchView` 職缺清單分頁（每頁約 8–10 筆 + 上一頁/下一頁/頁碼）；切頁不重打 API（已在記憶體）。

**測試**：rank_jobs 不再截斷在 12（回傳數 = 輸入數，受排序上限約束）；前端 build 綠。

---

## ④ 技能缺口市場分析

**目的**：從搜到的職缺彙整市場需求技能，比對你的履歷 → 指出你最缺且最熱門的技能。展現資料思維。

**架構**：`app/agents/skill_gap.py`：`analyze_skill_gap(profile, jobs) -> SkillGapReport`
- `SkillGapReport{ top_demand:[{skill,count}], your_gaps:[{skill,count}], have:[...] }`。
- 以職缺 `requirements`/`required_skills` 彙整頻率＝市場需求；比對 profile 技能（命中=have、缺少且高頻=gap）。純彙整為主；可選一次 LLM 正規化同義詞（v1 先純頻率，避免額外成本）。

**端點**：`jobs_auto` 在排序後加發一個 `skill_gap` SSE 事件（重用既有搜尋結果，不另開請求）。

**UI**：`JobSearchView` 結果上方一張「技能缺口分析」卡——你的缺口（rose chips，附需求次數）+ 市場熱門技能長條（重用 ScoreBars 風格）。

**測試**：純函式測 `analyze_skill_gap`（給 profile + jobs 驗 gaps/top_demand 正確）。

---

## ⑤ Agent 記憶／個人化（履歷 + 偏好）

**目的**：跨 session 記住最近履歷與偏好，免每次重傳；偏好讓產出更貼身。

**架構**：`app/store/memory.py`：`get_memory() -> dict`、`save_profile(profile_dict)`、`save_preferences(prefs_dict)`（操作 `user_memory` 單列）。
- 履歷自動存：`/api/jobs/auto`、`/api/resume/evaluate` 解析出 profile 後 `save_profile`。
- 偏好套用：`RunBody` 增 `preferences: dict | None`；`CopilotState` 增 `preferences`；resume/cover/interview agent 讀 `state["preferences"]` 併入 system 提示（語氣、強調技能、目標年資）。缺省＝現行行為。

**端點**：`GET /api/memory`（回 profile + preferences）、`POST /api/memory`（存 preferences）。

**UI**：開 app 時 `GET /api/memory` → 若有 profile 自動帶入共享狀態（投遞包工作台不再顯示「範例履歷」警告）；頁首或工作台一個「個人化」小面板可編輯偏好（目標職稱/年資/語氣/強調技能）。

**測試**：`:memory:` DB 驗 get/save；偏好併入 pipeline 的 RunBody 解析。

---

## ⑥ 公司職缺查詢（boards 依公司 + WebSearch 官網 careers）

**目的**：輸入公司名，查該公司目前有無開缺——含 job boards 上的職缺與**公司官網 careers** 的職缺。

**架構**：`app/agents/company_jobs.py`：`find_company_jobs(company_name, profile=None) -> list[JobPosting]`
- **A（boards）**：`search_all(company_name)` 後過濾 `job.company` 與輸入名稱模糊相符者。
- **B（官網 careers）**：`research_structured`（claude_cli WebSearch）找「{公司} 徵才/careers 現有職缺」，回 `list[JobPosting]`（source="careers"，url 指向公司官網）。非 CLI 後端則略過 B、只回 A。
- 合併去重（url / title+company）；可選用 `rank_jobs` 依 profile 排序。

**端點**：`POST /api/company/jobs`（`{company, profile?}`）→ SSE（progress + jobs + done）或 JSON。

**UI**：在「自動找職缺」加模式切換——「依履歷找」/「依公司找」；後者輸入公司名 → 列出該公司職缺（來源徽章：官網/104/LinkedIn/…），可一鍵「產生投遞包」。

**降級**：boards 全 blocked 且非 CLI 後端 → 提示「查無，或改用 LinkedIn 公司頁」。

**測試**：mock search_all + research_structured 驗合併/去重/過濾；端點測試。

---

## 施作順序與測試策略

順序：⓪ App shell（側欄 rail + CLI chip）→ ① 面試模擬 → ② 歷史 → ③ 職缺分頁 → ④ 技能缺口 → ⑤ 記憶個人化 → ⑥ 公司職缺。
每項：後端 TDD（pytest）＋前端 `npm run build` 閘門；每項完成即 commit。全 milestone 結束跑對抗式審查 + 全套測試 + 使用者 run.bat 驗收。

## 風險與取捨

- 面試/公司職缺的 WebSearch 走 claude_cli；切到 codex_cli 時面試照常（純生成）、公司職缺只剩 boards（會標示）。
- 技能缺口 v1 純頻率（不做同義詞正規化）以省成本；日後可加 LLM 正規化。
- 職缺無上限：排序輸入設約 40–50 上限以控 LLM prompt 大小與成本（顯示全部、分頁呈現）。
- 多分頁（5 個）：segmented nav 會 wrap；可接受，日後若擁擠再分組。
