<div align="center">

<img src="frontend/public/logo512.png" alt="Jobsmith logo" width="84" height="84" />

# Jobsmith

**針對台灣求職市場的開源多代理（multi-agent）AI 求職 co-pilot。**

找職缺、履歷健檢、產生客製投遞包（履歷・求職信・面試準備・公司情報）、模擬面試——一條龍，中途還有人工核可關卡。

預設用你本機的 **Claude Code / Codex CLI 訂閱**當 AI 引擎（**免 API key、不吃額度**），也能**自備金鑰**接任何 OpenAI 相容模型。

[English](README.md) · [**下載（Windows）**](#下載) · [快速開始](#快速開始從原始碼) · [系統架構](#系統架構)

![License](https://img.shields.io/badge/License-MIT-green)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-1C3C3C)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Platform](https://img.shields.io/badge/Windows-64--bit-0078D6?logo=windows&logoColor=white)

</div>

> 應用程式介面為繁體中文，貼合台灣求職生態（104 / Cake / Yourator / LinkedIn）。你的履歷與資料都不會離開你的電腦。

---

## 下載

**[⬇ 下載 Jobsmith for Windows（64 位元）](https://github.com/kevin333353/jobsmith/releases/latest)** — 單一 `.exe`，免裝 Python / Node.js。

1. 從 [最新 release](https://github.com/kevin333353/jobsmith/releases/latest) 下載 `Jobsmith.exe`。
2. 雙擊開啟，會跳出原生視窗（第一次啟動會解壓約 10–30 秒）。
3. 在**右上角控制台**選你的 AI 引擎：
   - **本機 CLI**——PATH 上已登入的 **Claude Code**（`claude`）或 **Codex CLI**（`codex`），或
   - **BYOK**——填 `base_url` + `api_key` + `model` 接任何 OpenAI 相容端點（OpenAI、DeepSeek、Gemini、Groq、OpenRouter、Ollama、LM Studio、vLLM…）。

> **需求：** Windows 10/11（64 位元；WebView2 為 Windows 11 內建）。歷史、設定、`.env` 都存在 exe 旁邊——不會上傳任何東西。

## 快速開始（從原始碼）

> **環境需求：** Python 3.11+、Node.js 18+，以及 PATH 上已登入的 **Claude Code**（`claude`）或 **Codex CLI**（`codex`）（或一組 BYOK 金鑰）。

```bash
git clone https://github.com/kevin333353/jobsmith.git
cd jobsmith

setup.bat            # Windows  — 一鍵安裝（venv + 相依 + 前端建置）
# ./setup.sh         # macOS / Linux / Git Bash

desktop.bat          # 以原生桌面視窗啟動（推薦）
# run.bat            # 或網頁版 → http://localhost:8000
```

| 模式           | 指令                                                          | 說明                                       |
| -------------- | ------------------------------------------------------------- | ------------------------------------------ |
| **桌面 App**   | `desktop.bat`（或 `python desktop.py`）                       | 原生視窗；第一次會有後端選擇。             |
| **網頁版**     | `run.bat`（或 `python -m uvicorn app.server:app --port 8000`） | 開 <http://localhost:8000>。               |
| **CLI（單一 JD）** | `python -m app.cli data/demo_jobs/ai_engineer.txt`        | 無介面、單一 JD 跑一次。                   |

自己打包 `.exe`：`pip install pyinstaller && pyinstaller jobsmith.spec --noconfirm` → `dist/Jobsmith.exe`。

## 目錄

- [下載](#下載)
- [快速開始](#快速開始從原始碼)
- [功能](#功能)
- [LLM 後端](#llm-後端)
- [系統架構](#系統架構)
- [成效評測](#成效評測)
- [技術棧](#技術棧)
- [專案結構](#專案結構)
- [測試](#測試)
- [Roadmap](#roadmap)
- [貢獻](#貢獻)
- [免責聲明](#免責聲明)
- [授權](#授權)

## 功能

- **自動找職缺**：貼上或上傳履歷 → AI 推導關鍵字 → **並行**搜尋 104 / Yourator / LinkedIn / Cake → **分批串流**依適配度排序（邊評邊顯示）。可在**搜尋前先選縣市**（104 於來源端篩、其餘來源於結果端篩）、依**適配色帶**（高／中以上／全部）篩選、調整每來源頁數，並把指定公司的開缺列在獨立區塊。
- **搜尋紀錄**：每次搜尋自動存整包，可回看、重新產生投遞包、刪除——不怕好職缺重找就不見。
- **履歷健檢**：依台灣 ATS 慣例評分，給具體修改建議與改寫前後範例。
- **投遞包工作台**：多代理流程（解析 JD → 匹配評分 → 公司情報 → 客製履歷 → 求職信 → 面試準備 → 品管反思），中途**人工核可**，並有即時的多代理編排追蹤。成品可**線上編輯**、可**逐份跟 AI 討論修改**、匯出 **Word（.docx）**（PDF 透過瀏覽器列印）。
- **模擬面試**：依 JD 與你的履歷出題，逐題即時回饋與評分；可直接從核可過的投遞包開跑。
- **個人化**：跨 session 記住最近履歷（免重傳）與偏好（目標職稱／語氣／想強調技能），並套用到產出。

## LLM 後端

從**右上角控制台**選你的 AI 引擎——**本機 CLI 訂閱**（免 API key）或 **BYOK**（任何 OpenAI 相容端點）。選了即生效；「測試」只是選用的連線檢查、非門檻。本機 CLI 可**重新掃描**、並可**自選模型**：

| 後端         | 認證方式                          | 說明                                                                                  |
| ------------ | --------------------------------- | ------------------------------------------------------------------------------------- |
| `claude_cli` | Claude Code 訂閱                  | **預設。** 免 API key；會移除 `ANTHROPIC_*` 環境變數。模型可自選（預設自動分層）。     |
| `codex_cli`  | Codex 訂閱                        | 免 API key。模型可自選；預設沿用你的 Codex 設定。                                      |
| `openai`     | BYOK——任何 OpenAI 相容端點        | `base_url` + `api_key` + `model`。可接 OpenAI、DeepSeek、Gemini、Groq、OpenRouter、Ollama、LM Studio、vLLM…  |

CLI 訂閱在**本機**執行、綁定你機器上登入的 CLI，履歷不會離開你的電腦。BYOK 金鑰只寫進你本機的 `.env`、不會外傳。另有 API key 後端（`anthropic`）供自架或 CI 使用。

## 系統架構

```
React SPA (Vite)  ──HTTP/SSE──►  FastAPI
                                   │
                  ┌────────────────┼─────────────────────┐
                  ▼                ▼                     ▼
          LangGraph StateGraph   職缺來源            App SQLite
          (代理 + 人工核可)       104/Yourator/      (歷史 /
          SqliteSaver checkpoint  LinkedIn/Cake      記憶 / 搜尋)
                  │
                  ▼
          可切換的 LLM 後端
          claude_cli · codex_cli · openai (BYOK)
```

- 以 LangGraph `StateGraph` 編排各代理；`SqliteSaver` 保存 checkpoint，並以 `interrupt()` / `Command(resume=…)` 實作 human-in-the-loop 核可。
- 伺服器以 **Server-Sent Events** 將進度串流到瀏覽器。
- 應用層 SQLite（與 LangGraph checkpoint 分開）存放投遞包歷史、使用者記憶與搜尋紀錄。
- CLI 後端下模型自動分層：解析用 **haiku**、匹配／生成用 **sonnet**、深思（Critic/Supervisor）用 **opus**（可於各後端覆寫）。

## 成效評測

Supervisor 反思迴圈（Critic → 重寫未過文件 → 再評）到底有沒有提升品質？用 5 組職缺／履歷的 golden set，分別在反思**關**（不重寫）與**開**兩種設定下跑，比較 Critic 分數：

<!-- EVAL:START -->
| 反思 | Critic 通過率 | 平均品質分數 |
| ---- | ------------- | ------------ |
| 關   | 60%（3/5）    | 85.6         |
| **開** | **100%（5/5）** | **87.5**   |

反思讓 Critic 通過率提升 **+40 個百分點**（60% → 100%）、平均品質 **+1.9**（85.6 → 87.5）。關閉反思時的兩個失敗案例，都是求職信出現**未經查證的公司事實**或**履歷未支持的經歷宣稱**——正是 Critic → 重寫迴圈會抓出來的問題。_（單次 harness 執行；LLM 呼叫非確定性，實際數字每次略有不同。）_
<!-- EVAL:END -->

```bash
python -m app.evals.harness     # 對每個 golden 案例跑整張 graph，寫入 app/evals/results.json
```

彙整用的 `summarize()` 是純函式、有獨立單元測試，因此聚合邏輯不受（非確定性的）LLM 呼叫影響、可單獨驗證。

## 技術棧

| 層級     | 技術                                                                       |
| -------- | -------------------------------------------------------------------------- |
| 後端     | Python、FastAPI、LangGraph、LangChain、Pydantic v2、SQLite、BeautifulSoup   |
| 前端     | React 19、TypeScript、Vite、Tailwind CSS、lucide-react                      |
| LLM      | Claude Code CLI / Codex CLI（本機）· 任何 OpenAI 相容端點（BYOK）          |
| 桌面     | pywebview（原生視窗）· PyInstaller（單檔 `.exe`）                          |

## 專案結構

```
app/
  agents/     # 履歷健檢、職缺搜尋、公司情報、文件對話、面試模擬…
  sources/    # 104 / Yourator / LinkedIn / Cake 搜尋 + registry + 縣市對應
  store/      # 應用層 SQLite：歷史、記憶、搜尋紀錄
  intake/     # 履歷／JD 解析與抓取
  export/     # Word（.docx）匯出
  graph.py    # LangGraph StateGraph（代理 + 人工核可）
  server.py   # FastAPI + SSE 端點
  llm.py      # 可切換 LLM 後端
frontend/     # Vite + React + TS + Tailwind 前端
tests/        # pytest 測試
desktop.py    # 原生視窗啟動器      jobsmith.spec  # PyInstaller 打包
```

## 測試

```bash
pytest                         # 單元/整合測試（預設略過 live API 測試）
pytest -m live                 # 含真打 API 的測試
cd frontend && npm run build   # 型別檢查 + 正式建置
```

## Roadmap

- [x] 單檔 Windows 桌面 App（PyInstaller）
- [x] BYOK——任何 OpenAI 相容後端
- [ ] **批次佇列**——一次對多個職缺產生投遞包，依序自動推進（v0.2）
- [ ] macOS / Linux 版本
- [ ] 更多職缺來源

## 貢獻

歡迎 issue 與 pull request。較大的變更請先開 issue 討論方向。提交前請跑 `pytest` 與 `npm run build`。

## 免責聲明

本專案僅供**個人、教育與研究用途**，以低頻方式查詢 104 / Yourator / LinkedIn / Cake 的公開職缺，協助個別求職者。使用者需自行遵守各網站的服務條款與 `robots.txt`，**請勿**用於大量爬取或商業性資料蒐集。軟體按「現狀」提供，不附任何擔保。AI 生成內容（履歷、求職信、公司情報）可能有誤，使用前請務必自行檢視。

## 授權

採用 [MIT 授權條款](LICENSE)。
