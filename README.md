# 台灣 AI 求職 Co-pilot

一套多代理（multi-agent）求職助理：從**找職缺**、**履歷健檢**、**客製投遞包**到**模擬面試**一條龍，
針對台灣求職與 104/Cake/LinkedIn 生態設計。預設用你本機的 **Claude Code / Codex CLI 訂閱**當 AI 引擎，
**免 API key、不吃 API 額度**。

## 功能

- **自動找職缺**：貼/上傳履歷 → AI 推導關鍵字 → **並行**搜尋 104 / Yourator / LinkedIn / Cake →
  **分批串流**依適配度排序（邊評邊顯示）；可用滑桿只看「≥ N 分」；可加「公司名單」單獨列出指定公司開缺；
  附**技能缺口分析**（市場熱門技能 vs 你的缺口）。
- **搜尋紀錄**：每次搜尋自動存整包結果，可回看 / 重新產生投遞包 / 刪除（不怕好職缺重找就不見）。
- **履歷健檢**：依台灣 ATS 慣例評分 + 具體修改建議與改寫範例。
- **投遞包工作台**：多代理流程（解析 JD → 匹配評分 → 公司情報 → 客製履歷 → 求職信 → 面試準備 → 品管反思），
  中途**人工核可**；成品可線上編輯、匯出 Word / PDF。完成自動存進「我的投遞包」。
- **面試模擬**：依 JD 與你的履歷出題，逐題即時回饋與評分 + 總評。
- **個人化**：跨 session 記住最近履歷（免重傳）與偏好（目標職稱/語氣/想強調技能），套用到產出。

## 技術架構

- **後端**：FastAPI + SSE 串流；LangGraph `StateGraph` 編排代理、`SqliteSaver` 做 checkpoint 與 human-in-the-loop；
  應用層 sqlite 存歷史/記憶/搜尋紀錄（與 checkpoint 分開）。
- **前端**：Vite + React 19 + TypeScript + Tailwind；lucide 圖示。
- **LLM 後端可切換**：`claude_cli`（Claude Code 訂閱，預設）/ `codex_cli`（Codex 訂閱）/ `anthropic`（API key）。
  模型自動分層：解析用 haiku、匹配/生成用 sonnet、深思（Critic/Supervisor）用 opus。

## 安裝

1. 後端：`python -m venv .venv`（Windows 用 `.venv\Scripts\activate`）→ `pip install -r requirements.txt`
2. 前端（建置產物供伺服器與桌面視窗載入）：`cd frontend && npm install && npm run build`
3. AI 後端（擇一）：
   - **CLI 訂閱（推薦，免金鑰）**：安裝並登入 `claude`（Claude Code）或 `codex`（Codex CLI），確保在 PATH。
   - **API key**：複製 `.env.example` 為 `.env`，設 `LLM_BACKEND=anthropic` 與 `ANTHROPIC_API_KEY=...`。

## 執行

- **桌面 App（原生視窗，不用開瀏覽器）**：雙擊 `desktop.bat`。第一次會有引導畫面讓你選 CLI 後端並**測試連線**。
- **Web**：雙擊 `run.bat`（或 `.venv\Scripts\python.exe -m uvicorn app.server:app --port 8000`）→ 開 http://localhost:8000
- **CLI（單一 JD）**：`python -m app.cli data/demo_jobs/ai_engineer.txt`

> 後端切換：開場引導畫面、右上角選單，或 `.env` 的 `LLM_BACKEND` 皆可。

## 測試

`pytest`（預設略過 live API 測試；要真打 API 的測試：`pytest -m live`）
