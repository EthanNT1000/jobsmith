# M8 — 止血 + 真實貫穿 實作計畫

> 產品級升級路線的第一個里程碑。方向：作品集訊號優先、本機 claude_cli、單人持久化（無登入/雲端）。
> 依據 2026-06-24 六面向產品級稽核（前端/功能/實用/創新/完整/agent 架構，全項 C/D），先修「會被當場抓包」的致命問題與穩定性。

**Goal:** 讓核心承諾為真且穩健——使用者上傳的真履歷一路貫穿投遞包、職缺資料正確、單一 agent 失敗不再拖垮整條流程。

**驗收總則:** 全測試綠燈（現況 93 passed），新增測試涵蓋每項修正；前端 `npm run build` 通過；live 端到端可跑。

## 任務

### T1 — 修 104 薪資（致命：薪資是第一決策欄位，現況 0/N 有值）
- `app/sources/source_104.py`：新增 `_format_salary(d)`，讀 `salaryLow/salaryHigh` 與薪資型態碼 `s10`（10=面議, 30=時薪, 40=日薪, 50=月薪, 60=年薪）；`s10==10` 或 low/high 皆 0 → `"面議"`；否則 `"{型態} NT${low:,}–{high:,}"`（單值不重複）。取代 `salary=d.get("salaryDesc")`。
- 測試 `tests/test_sources.py`：月薪/年薪/面議三案；確認不再讀 salaryDesc。

### T2 — 真履歷貫穿 pipeline（致命：投遞包目前是幫 demo 假人做）
- `app/server.py`：`RunBody` 增 `profile: dict | None = None`；`run()` 若有 profile 則 `Profile(**profile)`，否則沿用 `load_profile(profile_path)`（保留 CLI/測試後備）。
- 前端：`JobSearchView` 捕捉 `profile` SSE 事件存起來，`pick()` 連同 profile 經 `onPick` 上拋；`App` 的 `Seed` 帶 `profile`；`PipelineView.run()` POST `{jd_text, profile}`；`types.ts` 更新 `Seed` 與 `Profile`。
- 測試 `tests/test_server.py`：POST `/api/run` 帶自訂 profile，斷言 `tailor_resume` 收到的是該 profile 名字而非 demo。

### T3 — 修 SSE 端點阻塞事件迴圈（重要：單人請求會凍住整台）
- `app/server.py`：`resume_evaluate`、`jobs_auto` 由 `async def` 改 `def`（Starlette 自動丟 threadpool，與 `/api/run` 一致），檔案讀取改同步 `file.file.read()`。

### T4 — graph 優雅降級（重要：一個 agent 例外現在炸掉整條 SSE）
- `app/state.py`：增 `errors: Annotated[list[dict], operator.add]` 通道。
- `app/graph.py`：以 `_safe(node, fn, fallback)` 包每個 agent 呼叫；例外時回降級 artifact 並附 `errors=[{node,message}]`，不 raise。
- `app/server.py`：`_stream` 偵測 update 內 `errors` → 發 `{"type":"node_error",...}` SSE。
- 前端 `PipelineView`：渲染 node_error 警示；`error` 事件需把 phase 退出 running。
- 測試 `tests/test_server.py`：令某 agent 拋例外，斷言流程仍跑到 interrupt/done 且有 node_error。

### T5 — 公司情報誠實降級（重要：無 Tavily 金鑰時第 8 個 agent 產出空殼）
- `app/models.py`：`CompanyBrief` 增 `note: str | None = None`。
- `app/agents/company.py`：無金鑰 → 改用 LLM 一般知識產 brief，`data_limited=True` + `note="未設定搜尋金鑰，以下為模型一般知識，請自行查證"`。
- 前端 `CompanyCard` 顯示 note。

### T6 — 找職缺誠實化與後備（重要：來源全失敗時靜默空清單）
- `app/server.py` `jobs_auto`：來源全 blocked 且無 job → 發 `{"type":"all_blocked"}`，載入 `data/fallback_jobs.json` 後備職缺仍排序顯示並標記來源 `sample`。
- 新增 `data/fallback_jobs.json`（少量真實感樣本 AI 職缺）。
- 前端 `JobSearchView`：空清單明確訊息 + all_blocked/sample 標示。

### T7 — CLI 結構化輸出強化（重要：預設後端，正規表達式切大括號對巢狀模型會爆）
- `app/llm_cli.py`：`_extract_json` 改平衡括號掃描（支援巢狀）；`_CLIStructured`/`_CodexStructured` 重試時把 `exc.errors()` 欄位路徑回灌提示，而非通用嘮叨。
- 測試 `tests/test_llm_cli.py`：巢狀 JSON 擷取、夾雜前後文、欄位錯誤修復重試。

### T8 — 收尾
- `frontend` build；`sse` 中途 error 事件讓 view 退出 loading。
- 全測試 + live smoke。
