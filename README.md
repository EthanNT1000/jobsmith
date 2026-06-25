<div align="center">

<img src="frontend/public/logo512.png" alt="Jobsmith logo" width="84" height="84" />

# Jobsmith

**An open-source, multi-agent AI co-pilot for the Taiwan job market.**

Find jobs, audit your résumé, and generate tailored application packages — résumé, cover letter, interview prep, and company research — end to end, with a human approval gate.

Runs **locally** on your own **Claude Code / Codex CLI** subscription (no API key, no quota) — or **bring your own key** for any OpenAI-compatible model.

[繁體中文](README.zh-TW.md) · [**Download (Windows)**](#download) · [Quick Start](#quick-start-from-source) · [Architecture](#architecture)

![License](https://img.shields.io/badge/License-MIT-green)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-1C3C3C)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Platform](https://img.shields.io/badge/Windows-64--bit-0078D6?logo=windows&logoColor=white)

</div>

> The app UI is in Traditional Chinese, tailored to Taiwan's job-search conventions (104 / Cake / Yourator / LinkedIn). Your résumé and data never leave your machine.

---

## Download

**[⬇ Download Jobsmith for Windows (64-bit)](https://github.com/kevin333353/jobsmith/releases/latest)** — a single `.exe`. No Python or Node.js required.

1. Grab `Jobsmith.exe` from the [latest release](https://github.com/kevin333353/jobsmith/releases/latest).
2. Double-click it. A native window opens (the first launch unpacks for ~10–30s).
3. In the **top-right control panel**, choose your AI engine:
   - **Local CLI** — a logged-in **Claude Code** (`claude`) or **Codex CLI** (`codex`) on your `PATH`, **or**
   - **BYOK** — `base_url` + `api_key` + `model` for any OpenAI-compatible endpoint (OpenAI, DeepSeek, Gemini, Groq, OpenRouter, Ollama, LM Studio, vLLM…).

> **Requirements:** Windows 10/11 (64-bit; WebView2 is built into Windows 11). Your history, settings, and `.env` are saved next to the `.exe` — nothing is uploaded.

## Quick Start (from source)

> **Prerequisites:** Python 3.11+, Node.js 18+, and a logged-in **Claude Code** (`claude`) or **Codex CLI** (`codex`) on your `PATH` (or a BYOK key).

```bash
git clone https://github.com/kevin333353/jobsmith.git
cd jobsmith

setup.bat            # Windows  — one-time setup (venv + deps + frontend build)
# ./setup.sh         # macOS / Linux / Git Bash

desktop.bat          # launch as a native desktop window (recommended)
# run.bat            # or web mode → http://localhost:8000
```

| Mode             | Command                                                        | Notes                                                              |
| ---------------- | ------------------------------------------------------------- | ----------------------------------------------------------------- |
| **Desktop app**  | `desktop.bat` (or `python desktop.py`)                        | Native window; first run shows a backend picker.                   |
| **Web**          | `run.bat` (or `python -m uvicorn app.server:app --port 8000`) | Open <http://localhost:8000>.                                     |
| **CLI (one JD)** | `python -m app.cli data/demo_jobs/ai_engineer.txt`           | Headless single-JD run.                                            |

To build your own `.exe`: `pip install pyinstaller && pyinstaller jobsmith.spec --noconfirm` → `dist/Jobsmith.exe`.

## Table of Contents

- [Download](#download)
- [Quick Start](#quick-start-from-source)
- [Features](#features)
- [LLM Backends](#llm-backends)
- [Architecture](#architecture)
- [Evaluation](#evaluation)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)
- [License](#license)

## Features

- **Auto job search** — paste or upload a résumé; the system derives keywords and searches 104 / Yourator / LinkedIn / Cake **in parallel**, ranking by fit in **streaming batches** (results appear as they're scored). Pick your **region(s) before searching** (applied at-source on 104, result-side on the others), filter by **fit band** (high / mid-and-up / all), set pages per source, and track named companies in a separate section.
- **Search history** — every search is auto-saved; revisit it, regenerate a package, or delete it.
- **Résumé health check** — scores against Taiwan ATS conventions with concrete fixes and before/after rewrites.
- **Application-package workbench** — a multi-agent pipeline (parse JD → match score → company research → tailored résumé → cover letter → interview kit → critique) with a **human approval gate** and a live agent-orchestration trace. Documents are **editable inline**, you can **discuss changes with the AI** per document, and export to **Word (.docx)** (PDF via the browser's print dialog).
- **Mock interview** — generates questions from the JD and your résumé, with per-answer feedback and scores; launchable directly from an approved package.
- **Personalization** — remembers your most recent résumé (no re-upload) and preferences (target titles, tone, skills to emphasize) across sessions, and applies them to outputs.

## LLM Backends

Pick your AI engine from the **top-right control panel** — a **local CLI subscription** (no API key) or **BYOK** (any OpenAI-compatible endpoint). Selecting a backend takes effect immediately; the **Test** button is an optional connection check, never a gate. Local CLIs offer a **rescan** action and a **selectable model**.

| Backend      | Auth                                   | Notes                                                                                                    |
| ------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `claude_cli` | Claude Code subscription               | **Default.** No API key; strips `ANTHROPIC_*` env. Model selectable (auto-tiered by default).            |
| `codex_cli`  | Codex subscription                     | No API key. Model selectable; defaults to your Codex config.                                             |
| `openai`     | BYOK — any OpenAI-compatible endpoint  | `base_url` + `api_key` + `model`. Works with OpenAI, DeepSeek, Gemini, Groq, OpenRouter, Ollama, LM Studio, vLLM… |

CLI subscriptions run **locally** and bind to the logged-in CLI on your machine, so your résumé never leaves your computer. BYOK credentials are written only to your local `.env` and never transmitted. An API-key backend (`anthropic`) also exists for self-hosting or CI.

## Architecture

```
React SPA (Vite)  ──HTTP/SSE──►  FastAPI
                                   │
                  ┌────────────────┼─────────────────────┐
                  ▼                ▼                     ▼
          LangGraph StateGraph   Job sources        App SQLite
          (agents + human gate)  104/Yourator/      (history /
          SqliteSaver checkpoint  LinkedIn/Cake      memory / searches)
                  │
                  ▼
          Pluggable LLM backend
          claude_cli · codex_cli · openai (BYOK)
```

- A LangGraph `StateGraph` orchestrates the agents; `SqliteSaver` persists checkpoints and powers the human-in-the-loop approval gate via `interrupt()` / `Command(resume=…)`.
- The server streams progress to the browser over **Server-Sent Events**.
- An application-level SQLite database (separate from the LangGraph checkpoint store) holds package history, user memory, and saved searches.
- On the CLI backends, models are tiered automatically: **haiku** for extraction, **sonnet** for matching/generation, **opus** for the Critic/Supervisor (overridable per backend).

## Evaluation

Does the Supervisor reflection loop (Critic → revise un-passed documents → re-critique) actually improve output quality? A small golden set of 5 job/résumé pairs is run with reflection **off** (no revisions) and **on**, and the resulting Critic scores are compared:

<!-- EVAL:START -->
| Reflection | Critic pass rate | Mean quality score |
| ---------- | ---------------- | ------------------ |
| Off        | 60% (3/5)        | 85.6               |
| **On**     | **100% (5/5)**   | **87.5**           |

Reflection lifts the Critic pass rate by **+40pp** (60% → 100%) and mean quality by **+1.9** (85.6 → 87.5) across the 5 golden cases. Both "off" failures were cover letters making **unverified company claims** or an **unsupported experience claim** — exactly what the Critic → revise loop catches. _(One harness run; LLM calls are non-deterministic, so exact numbers vary run to run.)_
<!-- EVAL:END -->

```bash
python -m app.evals.harness     # runs the graph on each golden case, writes app/evals/results.json
```

The `summarize()` step is a pure function with its own unit tests, so the aggregation logic is verified independently of the (non-deterministic) LLM calls.

## Tech Stack

| Layer    | Technologies                                                               |
| -------- | -------------------------------------------------------------------------- |
| Backend  | Python, FastAPI, LangGraph, LangChain, Pydantic v2, SQLite, BeautifulSoup  |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, lucide-react                     |
| LLM      | Claude Code CLI / Codex CLI (local) · any OpenAI-compatible endpoint (BYOK) |
| Desktop  | pywebview (native window) · PyInstaller (single-file `.exe`)               |

## Project Structure

```
app/
  agents/     # résumé eval, job search, company research, refine chat, interview sim, …
  sources/    # 104 / Yourator / LinkedIn / Cake search + registry + region map
  store/      # app-level SQLite: history, memory, searches
  intake/     # résumé/JD parsing and fetching
  export/     # Word (.docx) export
  graph.py    # LangGraph StateGraph (agents + human gate)
  server.py   # FastAPI + SSE endpoints
  llm.py      # pluggable LLM backend resolution
frontend/     # Vite + React + TS + Tailwind SPA
tests/        # pytest suite
desktop.py    # native-window launcher    jobsmith.spec  # PyInstaller build
```

## Testing

```bash
pytest                         # unit/integration suite (live API tests skipped by default)
pytest -m live                 # include tests that call the real API
cd frontend && npm run build   # type-check + production build
```

## Roadmap

- [x] Single-file Windows desktop app (PyInstaller)
- [x] BYOK — any OpenAI-compatible backend
- [ ] **Batch queue** — generate packages for multiple jobs with sequential auto-advance (v0.2)
- [ ] macOS / Linux builds
- [ ] More job sources

## Contributing

Issues and pull requests are welcome. For non-trivial changes, please open an issue first to discuss the approach. Run `pytest` and `npm run build` before submitting.

## Disclaimer

This project is for **personal, educational, and research use**. It queries public job listings from 104 / Yourator / LinkedIn / Cake at low frequency to help an individual job seeker. You are responsible for complying with each site's Terms of Service and `robots.txt`; do **not** use it for bulk scraping or commercial data harvesting. The software is provided "as is", without warranty of any kind. LLM-generated content (résumés, cover letters, company research) may contain inaccuracies — always review before use.

## License

Released under the [MIT License](LICENSE).
