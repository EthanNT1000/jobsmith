# 台灣 AI 求職 Co-pilot — 設計規格（Design Spec）

- **文件日期**：2026-06-23
- **狀態**：已通過腦力激盪確認，待使用者最終審查
- **作者**：使用者 × Claude（brainstorming）
- **下一步**：通過審查後進入 writing-plans 產出實作計畫

---

## 1. 專案概述與定位

### 一句話定位
一個 **Multi-Agent** 系統：把一則繁中職缺（JD）＋使用者的背景，自動產出一份**高品質、ATS 友善、台灣在地化**的投遞包，並**主動上網查證該公司**，整個 agent 編排過程**看得見**，附帶**品管反思迴圈**與**人工核可關卡**。

### 雙重目標（portfolio-first, product-shaped）
1. **作品集／求職**（主要）：技術上展示 production 等級的 multi-agent 編排能力，幫使用者拿到 AI agent 相關工作。具備可公開點擊的 live demo + GitHub repo + 真實 LangSmith trace。
2. **真實可用產品**（次要但必要）：真的能用、夠 polished 能 demo 的台灣求職工具，具商業價值；但 v1 範圍刻意收斂，數週內可出貨。

### 故事線
「用一個 agent 群，去幫自己找 AI agent 的工作。」面試時可講：「我做了一個 multi-agent 系統來幫我找 agent 工作，而且它真的幫我拿到面試。」高度可記憶、可信。

### 差異化三支柱
1. **台灣在地化**：繁中履歷／JD／面試文化、台灣求職平台（104／Cake／yourator／LinkedIn）與在地評價來源。GitHub 上現有專案（AIHawk、ApplyPilot、autopilot-jobhunt、career-ops 等）全部綁 LinkedIn/Indeed，**無人處理台灣市場**。
2. **Multi-agent 編排深度**：supervisor 動態分派、並行 fan-out、反思迴圈、human-in-the-loop、tool use、可觀測性。
3. **透明可解釋 + 不踩法律紅線**：過程看得見、結果可解釋；資料以「使用者貼 URL/JD」與「搜尋 API」取得，**不爬蟲、不自動投履歷**。

---

## 2. 成功標準

### 作品集面
- 公開 demo URL，recruiter 點進來可用內建範例職缺立即試玩。
- GitHub repo：README（含架構圖與故事線）、ADR（架構決策紀錄）、逐 agent 說明、測試與 eval。
- 真實 LangSmith trace 連結可供檢視。
- 使用者能口頭講清楚：supervisor、handoff、fan-out、reflection loop、human-in-the-loop、tool use、observability、model tiering、agent eval 等概念與「為什麼這樣設計」。

### 產品面
- 貼上一則真實台灣 AI 職缺 JD（或 URL），3 分鐘內產出：匹配分析、客製履歷、求職信/自傳、面試準備、公司情報卡。
- 產出品質通過 Critic agent 門檻（見 §12）。
- 過程於 UI 即時可見（並行、反思、成本/延遲）。

---

## 3. 使用者與使用情境

### 主要使用者
- **求職者本人**（台灣，找 AI/agent/軟體相關職缺）。v1 為單一使用者／session，不做登入。

### 核心情境
1. **首次設定**：貼上/上傳自己的履歷、技能、經歷 → 存成 Profile（之後重複使用）。
2. **處理一則職缺**：貼 104/Cake/yourator/LinkedIn 的 URL 或直接貼 JD 文字（或選內建 demo 職缺）。
3. **觀看編排**：左欄看 agent 群即時工作，右欄看成品逐字串流。
4. **審閱與核可**：過目成品 → 手動微調 → 批准。
5. **匯出與回看**：匯出 PDF/Markdown/複製；整包存進「申請紀錄」，可回看、可比較。

---

## 4. 系統架構

**模式**：Supervisor / Orchestrator-Worker（主管 + 專才 agents），以 LangGraph 實作。

```
   貼 URL/JD ──► Supervisor ◄── 使用者 Profile
                    │  規劃、分派、彙整、決定是否重做/提早收手
     ┌──────────────┼───────────────────────────────┐
     ▼              ▼                                 ▼
 ① 解析 JD ──► ② 匹配評分                      ⑧ 公司情報 Agent 🔍
     │                                          (web search 工具)
     │              並行 fan-out ↓                    │ 餵事實給 ④⑤
     │        ┌──────────┬──────────┐                │
     ▼        ▼          ▼          ▼ ◄──────────────┘
        ③ 履歷客製   ④ 求職信/自傳  ⑤ 面試準備(含反向提問)
              └──────────┼──────────┘
                         ▼
              ⑥ 品管/反思 Agent（退件重寫，最多 N 次）
                         ▼
              ⑦ 人工核可 (Human-in-the-loop) → 匯出
```

### 編排設計重點
- **Supervisor 動態分派**：非寫死流水線。依匹配分數決定是否續跑；分數低於門檻時提早收手並說明原因，詢問是否仍要硬做（省 token/時間，展示決策力）。
- **並行 fan-out**：③④⑤ 同時執行（LangGraph 並行節點）；⑧ 在解析出公司名後即與 ② 並行啟動。
- **反思迴圈（reflection loop）**：⑥ Critic 對 ③④⑤ 評分，未達標退回重寫，計數防無限迴圈。
- **Human-in-the-loop**：⑦ 使用 LangGraph interrupt 機制。
- **共享狀態 + 記憶**：Profile、解析後 JD、各版草稿、Critic 評語、修訂次數存於 LangGraph state + DB，可重跑、可追溯。

---

## 5. 各 Agent 規格

每個 agent 回傳強型別 Pydantic 物件。模型分層見 §9。

### ① JD 解析 Agent（Intake/Parser）
- **輸入**：JD 文字或 URL（URL 為使用者發起的單頁抓取）。
- **輸出**：`ParsedJob`：職稱、公司名、地點、職責列、必備條件、加分條件、年資、技術棧、語言（中/英）、薪資（若有）。
- **模型**：Haiku 4.5（單純抽取）。
- **失敗處理**：URL 抓取失敗 → 退回請使用者貼文字。

### ② 匹配評分 Agent（Fit Scorer）
- **輸入**：`ParsedJob` + `Profile`。
- **輸出**：`MatchReport`：0–100 分、符合項、落差項、補強建議、是否建議續跑（布林 + 理由）。
- **模型**：Sonnet 4.6。
- **要求**：分數須有證據（引用 Profile 與 JD 對應點），避免空泛。

### ③ 履歷客製 Agent（Resume Tailor）
- **輸入**：`ParsedJob` + `Profile` +（可選）`MatchReport`。
- **輸出**：`TailoredResume`：針對此職缺挑選/改寫的條列、ATS 關鍵字命中清單、繁中版（可選中英對照）。
- **模型**：Sonnet 4.6。
- **約束**：不得捏造未在 Profile 出現的經歷（防幻覺造假）。

### ④ 求職信/自傳 Agent（Cover Letter）
- **輸入**：`ParsedJob` + `Profile` + `CompanyBrief`（來自 ⑧）。
- **輸出**：`CoverLetter`：台灣式求職信/自傳，引用真實公司事實。
- **模型**：Sonnet 4.6。

### ⑤ 面試準備 Agent（Interview Prep）
- **輸入**：`ParsedJob` + `Profile` + `CompanyBrief`。
- **輸出**：`InterviewKit`：技術題、行為題、台灣特有題（自傳、期望薪資、為什麼想加入）、STAR 擬答、**反向提問**、公司近況考點、避雷提醒。
- **模型**：Sonnet 4.6。

### ⑥ 品管/反思 Agent（Reviewer/Critic）
- **輸入**：③④⑤ 的產出 + `ParsedJob`。
- **輸出**：`CritiqueReport`：逐項評分（對 JD 命中率 / ATS / 在地規範）、是否達標、退件原因與修改指示。
- **模型**：Opus 4.8（硬判斷）。
- **約束**：退件次數上限 N（預設 2）。

### ⑦ 人工核可關卡（Human-in-the-loop）
- LangGraph interrupt：暫停等待使用者批准/微調，再續跑到匯出。

### ⑧ 公司情報 Agent（Company Research，tool use）
- **輸入**：公司名（來自 ①）。
- **工具**：web search API（Tavily 優先，或 Brave Search）。
- **資料源**：面試趣、比薪水(Salary)、Glassdoor、Dcard 工作版、公開資訊觀測站、經濟部商業司公司登記、新聞。僅取公開資料，不爬私有/登入內容。
- **輸出**：`CompanyBrief`：規模/產業/資金狀況、薪資範圍、福利、文化與評價摘要、面試評價、⚠️ 風險紅旗、近期新聞、來源連結。
- **模型**：Sonnet 4.6（彙整）；搜尋由工具完成。
- **失敗處理**：查無資料 → 標記「資料有限」，不阻斷流程。

---

## 6. 資料流（完整流程）

```
[0] 設定一次：使用者貼/上傳履歷、技能、經歷 → 存成 Profile
[1] 輸入職缺：貼 URL 或 JD 文字（或選內建 demo 職缺）
[2] ① 解析 → ParsedJob
[3] ② 匹配 → MatchReport
        ├─ 分數 < 門檻 → Supervisor 提早收手，說明原因，問是否硬做
        └─ 分數 ≥ 門檻 → 並行 fan-out ③④⑤；⑧ 已於 [2] 後並行啟動，CompanyBrief 餵入 ④⑤
[4] ⑥ Critic 評分 → 未達標退回 ③④⑤ 重寫（最多 N 次）
[5] ⑦ 人工核可：使用者過目 → 微調 → 批准
[6] 匯出：PDF / Markdown / 複製；整包存入申請紀錄
```

---

## 7. 「看得見的編排」UI

讓使用者/面試官看到 agent 群在工作，是 demo 的致勝點。

```
┌────────────────────────────┬───────────────────────────────┐
│  左：即時編排追蹤 (Live)    │  右：成品分頁                 │
│ ● Supervisor  規劃中…       │  [匹配分析][履歷][求職信]     │
│   ├ ① 解析 JD      ✓ 1.2s   │  [面試題][公司情報]           │
│   ├ ② 匹配評分 82  ✓ 0.9s   │                               │
│   ├ ⑧ 公司情報 🔍 搜尋中…   │   ← 串流逐字輸出              │
│   ├ ③ 履歷客製   ⟳ 進行中   │   成品上方標：               │
│   ├ ④ 求職信     ⟳ 進行中   │   「Critic 評分 88/100」      │
│   ├ ⑤ 面試準備   ⟳ 進行中   │   「ATS 關鍵字命中 14/16」    │
│   └ ⑥ 品管: 退回③重寫(1/2) │   「核可」按鈕                │
│  Token: 12.3k  時間: 8.4s  │                               │
└────────────────────────────┴───────────────────────────────┘
```

- 以 streaming（SSE/WebSocket）即時推送每個 agent 的開始/結束/耗時/token/結果到左欄；右欄成品逐字串流。
- 視覺呈現並行（③④⑤⑧ 同時）、反思迴圈（⑥ 退件計數）、成本/延遲。

---

## 8. 技術棧

| 層 | 選用 | 理由 |
|---|---|---|
| 編排 | **LangGraph**（含 supervisor 範式）| 生產級、面試必問；內建並行/狀態/interrupt |
| 後端 | **Python + FastAPI** | AI 工具支援好；streaming 容易 |
| 結構化輸出 | **Pydantic v2** | 強型別、可測 |
| LLM | **Claude（分層）** | 見 §9 |
| 搜尋工具 | **Tavily**（或 Brave Search）| 為 LLM agent 設計、有免費額度 |
| 觀測 | **LangSmith** | 真實 trace 放 README |
| 前端 | **Next.js + Tailwind + shadcn/ui** | 專業外觀、AI 好生、SSE 串流 |
| 儲存 | **SQLite（v1）** | LangGraph checkpointer 直用；抽象化好換 Postgres |
| 部署 | 前端 Vercel／後端 Railway 或 Render | 一個公開 demo URL |

---

## 9. 模型分層策略（成本感知編排）

對 AI 應用一律採用最新、最強的 Claude，按難度分層以控成本：

- **① JD 解析**（抽取）→ **Haiku 4.5**（`claude-haiku-4-5`）
- **②③④⑤⑧ 匹配/生成/彙整**（主力）→ **Sonnet 4.6**（`claude-sonnet-4-6`）
- **⑥ Critic + Supervisor 規劃**（硬推理/判斷）→ **Opus 4.8**（`claude-opus-4-8`）
- 每個 agent 的模型於設定檔可切換，便於 demo 比較品質/成本。
- **Prompt caching** 快取 Profile，降低重複 token 成本。
- **確切定價、rate limit、caching 細節於實作計畫階段查 claude-api 參考再敲定，不憑記憶報價。**

---

## 10. 資料策略與合法性

- **職缺資料**：以「使用者貼 URL 或貼 JD 文字」為主（單頁、使用者發起，等同其自行開啟）。內建一包真實 AI 職缺範例資料集，供 demo 即時試玩。
- **公司資料**：以搜尋 API 取得公開資料，僅彙整公開內容，不爬登入/私有頁面。
- **明確不做**：不爬蟲大量抓職缺、不自動投履歷。避免 ToS/法律/維運風險，也避免淪為現有專案的 clone。

---

## 11. 錯誤處理

- **結構化驗證**：Pydantic 解析失敗 → 帶錯誤自動重試一次。
- **反思迴圈上限**：⑥ 退件最多 N 次（預設 2），計數防無限迴圈。
- **單一 agent 失敗不拖垮全局**：supervisor 收部分結果可續跑或標記重試。
- **URL 抓不到** → 退回請使用者貼 JD 文字。
- **公司查無資料** → 標記「資料有限」，不阻斷。
- **公開 demo 防破產**：每日 token 上限 + 每 session 上限 + 速率限制。
- **LLM API**：timeout、指數退避重試。

---

## 12. 測試與 Eval

- **單元測試**：每個 agent 的結構化輸出，用固定 fixtures（樣本 JD + 樣本 Profile）。
- **Eval harness（黃金資料集）**：JD+Profile → 預期匹配分區間 / 預期 ATS 關鍵字，驗證 ② 匹配 與 ⑥ Critic（展示稀缺的 agent eval 技能）。
- **整合測試**：跑完整 LangGraph 圖於 demo 資料集，斷言有產出且 Critic 達標。
- **前端**：基本 smoke test。

---

## 13. 文件層（「邊做邊學懂」，面試可守）

- **README**：故事線（用 agent 找 agent 工作）+ 架構圖 + live demo/trace 連結。
- **ADR（架構決策紀錄）**：為什麼選 LangGraph、為什麼貼 JD 不爬蟲、為什麼模型分層、為什麼反思迴圈——預先寫好面試常見題的答案。
- **逐 agent「它怎麼運作」說明**。

---

## 14. 範圍（YAGNI）

### v1 做
- 單一使用者/session（不做登入）
- 貼 URL/JD + 內建 demo 資料集
- ①～⑧ 八個 agent + 看得見的編排 UI
- 匯出 PDF/Markdown
- 繁中為主，履歷可選中英對照
- 部署成公開 demo URL

### v1 不做（未來擴充，架構預留）
- 自動投履歷、爬蟲大量抓職缺
- 多租戶登入/金流/訂閱
- App、瀏覽器外掛
- 薪資談判 agent、內推/人脈 agent

---

## 15. 里程碑（每個皆可單獨 demo）

| 里程碑 | 內容 | 可 demo |
|---|---|---|
| **M1** | supervisor + ① 解析 + ② 匹配，終端機跑 | 貼 JD → 出匹配分數 |
| **M2** | 加 ③④⑤ 並行 fan-out + ⑧ 公司情報(tool use) | 一次出履歷+信+面試題+公司卡 |
| **M3** | 加 ⑥ 反思迴圈 + ⑦ 人工關卡 | Critic 退件重寫 |
| **M4** | FastAPI 串流 + Next.js 看得見的編排 UI | 致勝畫面 |
| **M5** | 匯出 + 紀錄保存 + 打磨 | 完整產品流程 |
| **M6** | 部署 + README/ADR + 錄 demo | 公開 URL + 作品集 |

---

## 16. 風險與緩解

| 風險 | 緩解 |
|---|---|
| 範圍膨脹拖垮求職時程 | 嚴守 §14 YAGNI；里程碑可隨時停在能 demo 的狀態 |
| 使用者主要靠 AI 寫程式、面試守不住 | §13 文件層 + ADR，邊做邊學懂；架構切小、模組清楚 |
| LLM 成本失控 | §9 模型分層 + prompt caching + §11 demo 防破產上限 |
| 公司資料品質參差 | 標記「資料有限」+ 附來源連結，由使用者判讀 |
| 反思迴圈無限循環 | 退件次數上限 + 計數 |
| 產出幻覺造假經歷 | ③ 約束不得捏造 Profile 外經歷；⑥ Critic 查核 |

---

## 17. 未來擴充（v2+）

- 薪資談判建議 agent、內推/人脈 agent
- 多使用者登入與雲端 Profile
- 可插拔職缺連接器（合法/合規前提下）
- 申請進度追蹤與提醒
