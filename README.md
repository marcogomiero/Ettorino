# Ettorino 🟠

**An AI agent that thinks, plans and builds software — in parallel.**

Claude reasons. GPT or Gemini implement. Ettorino orchestrates everything.

[![Ettorino UI](https://github.com/marcogomiero/Ettorino/raw/master/docs/screen_ui.png)](https://github.com/marcogomiero/Ettorino/blob/master/docs/screen_ui.png)

---

## What happens when you run a task

```
You →  "Build a web application monitoring system with daemon process,
        SQLite storage, Flask REST API, email alerts and YAML config"

         ┌─────────────────────────────────────────────────────┐
         │                     ETTORINO                        │
         │                                                     │
         │  1. Router classifies → HARD                        │
         │  2. Proposes models + cost estimate → you confirm   │
         │                                                     │
         │  3. Claude Opus 4.7 (Architect)                     │
         │     "Splitting into 3 parallelizable chunks..."     │
         │                                                     │
         │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
         │  │  GPT /   │  │  GPT /   │  │  GPT /   │         │
         │  │ Gemini   │  │ Gemini   │  │ Gemini   │         │
         │  │ Chunk A  │  │ Chunk B  │  │ Chunk C  │         │
         │  │config+db │  │monitor+  │  │api+daemon│         │
         │  │          │  │alerter   │  │          │         │
         │  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
         │       └─────────────┴─────────────┘               │
         │                     │                              │
         │  4. Claude Integrator checks coherence             │
         │     imports, naming, interfaces → ✓ done           │
         └─────────────────────────────────────────────────────┘

→  workspace/build_a_web_application/   (8 files ready)
   webmon/__init__.py
   webmon/config.py
   webmon/database.py
   webmon/monitor.py
   webmon/alerter.py
   webmon/api.py
   webmon/daemon.py
   config.example.yaml
```

---

## Screenshots

### Clean interface

Minimal terminal-style UI — JetBrains Mono throughout, log rows with left-border accents per agent (red for Claude, green for GPT, blue for Gemini), timestamps on every line.

[![Ettorino UI](https://github.com/marcogomiero/Ettorino/raw/master/docs/screen_ui.png)](https://github.com/marcogomiero/Ettorino/blob/master/docs/screen_ui.png)

### Routing & model selection

The router classifies the task difficulty and proposes the optimal model pair. You can swap either model before the loop starts — including choosing a Gemini model as implementer. Includes cost estimate and reasoning.

[![Confirm card — difficulty MEDIUM, model selection](https://github.com/marcogomiero/Ettorino/raw/master/docs/screen_confirm.png)](https://github.com/marcogomiero/Ettorino/blob/master/docs/screen_confirm.png)

### Parallel execution

On hard tasks, up to 3 implementer workers run simultaneously. Each worker card shows its own live progress bar with token and line counters streaming in real time.

[![Parallel dashboard — 3 workers completed, file chips](https://github.com/marcogomiero/Ettorino/raw/master/docs/screen_parallel.png)](https://github.com/marcogomiero/Ettorino/blob/master/docs/screen_parallel.png)

---

## Features

|  |  |
| --- | --- |
| 🧠 **Smart router** | Classifies every task (easy/medium/hard) and selects optimal models for quality/cost |
| 🔵 **Google Gemini support** | Gemini 2.5 Flash free tier available — no credit card required to start |
| ⚡ **Parallel implementation** | Up to 3 GPT/Gemini workers run simultaneously |
| 📊 **Per-worker live bars** | Each parallel worker streams its own token/line counter in real time |
| 💬 **Conversational loop** | Claude asks for clarification when needed, without blocking |
| 🔄 **Continue the conversation** | After completion, request changes — restarts with fresh classification |
| 🛑 **Stop anytime** | Floating button, interrupts the loop without losing context |
| 💰 **Real-time cost tracking** | Tokens and dollars per provider (Claude / GPT / Gemini), updated live |
| 📁 **Multi-file structure** | Code saved in the exact folder structure planned by Claude |
| ⬇️ **Direct download** | Download the project as a `.zip` at the end of each run |
| 🔁 **Auto-continuation** | If output is truncated, resumes automatically (up to 3 attempts) |
| 🌍 **EN / IT localization** | Full interface translation, language preference persisted in localStorage |
| 🌙 **Dark mode** | One click, persisted in localStorage |
| 🧠 **MEMORY.md** | Persistent instructions injected into Claude every session — edit once, applied forever |
| 💡 **Task examples** | Built-in easy/medium/hard examples to get started quickly |
| 🐳 **Container-ready** | Multi-stage Chainguard image, runs anywhere with Docker |

---

## Models

### Reasoner (always Claude)

Claude is the sole orchestrator — it reasons, plans, reviews and decides. It never gets swapped out.

| Tier | Model | When |
| --- | --- | --- |
| 🟢 Easy | Claude Haiku 4.5 | Scripts, utilities, single functions |
| 🟡 Medium | Claude Sonnet 4.6 | Multi-component apps, APIs, 100–500 lines |
| 🟠 Hard-mid | Claude Opus 4.6 | Complex systems, multi-file architectures |
| 🔴 Hard | Claude Opus 4.7 | Very complex systems, ML/AI, 600+ lines |

### Implementer (GPT or Gemini — your choice)

| Provider | Model | Tier | Free tier | Input $/1M | Output $/1M |
| --- | --- | --- | --- | --- | --- |
| OpenAI | GPT-4.1 mini | Easy | ✗ | $0.40 | $1.60 |
| OpenAI | GPT-4.1 | Medium | ✗ | $2.00 | $8.00 |
| OpenAI | o3 | Hard | ✗ | $15.00 | $60.00 |
| Google | Gemini 2.5 Flash-Lite | Easy | ✓ | $0.10 | $0.40 |
| Google | Gemini 2.5 Flash | Medium | ✓ | $0.30 | $2.50 |
| Google | Gemini 2.5 Pro | Hard-mid | ✗ | $1.25 | $10.00 |
| Google | Gemini 3 Flash | Medium | ✗ | $0.50 | $3.00 |
| Google | Gemini 3.1 Flash-Lite | Easy | ✗ | $0.25 | $1.50 |
| Google | Gemini 3.1 Pro | Hard | ✗ | $2.00 | $12.00 |

All Gemini models have a **1M token context window** — useful for large codebases and multi-file tasks.

The classifier uses **Claude Haiku 4.5** for routing regardless of tier (cost < $0.01 per task).

---

## Parallel execution — how it works

On hard/hard-mid tasks Claude splits the work into exactly 3 chunks and runs them simultaneously:

```
Claude decides:
  Chunk A — foundations (config, db, models)      → worker 1
  Chunk B — core logic (monitor, scheduler)        → worker 2
  Chunk C — external interfaces (API, alerter)     → worker 3

All 3 run in parallel, then Claude reviews coherence:
  imports, naming, interfaces → ✓ done  (or → fix round)
```

Each worker streams its progress live. The implementer provider (GPT or Gemini) applies to all workers — the UI turns blue for Gemini, green for GPT.

---

## Estimated costs

| Task | GPT implementer | Gemini Flash implementer |
| --- | --- | --- |
| Simple function or script | ~$0.002 | ~$0.0005 |
| CLI with 4 commands | ~$0.05–0.15 | ~$0.01–0.05 |
| Multi-component system | ~$0.50–2.00 | ~$0.10–0.50 |
| 3-worker parallel, hard task | ~$1.50–5.00 | ~$0.30–1.50 |

> Easy and medium tasks routed to **Gemini 2.5 Flash** are free until you exceed the free tier limits (~500 requests/day). No credit card needed.

---

## Installation

### Option A — Python (local dev)

**Prerequisites:** Python 3.10+, Anthropic API key (required), OpenAI and/or Google API key (at least one)

```bash
# 1. Install dependencies
pip install flask anthropic openai google-genai python-dotenv

# 2. Set your keys in .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...          # optional if using Gemini only
GOOGLE_API_KEY=AIza...         # optional if using GPT only
ETTORINO_VERSION=0.1.0

# 3. Run
python ettorino.py
```

Open **http://localhost:5000** — Ettorino does the rest.

> If `GOOGLE_API_KEY` is not set, Gemini models are silently disabled and the system falls back to GPT. If `OPENAI_API_KEY` is not set, only Gemini models appear in the implementer dropdown.

---

### Option B — Docker

**Prerequisites:** Docker, API keys

```bash
# 1. Clone and enter the repo
git clone https://github.com/marcogomiero/Ettorino.git && cd Ettorino

# 2. Create your .env
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ETTORINO_VERSION=0.1.0
EOF

# 3. Build and run
docker compose up --build
```

Open **http://localhost:8080**

The `workspace/` folder is persisted in a named Docker volume (`ettorino_workspace`) so generated projects survive container restarts.

#### Manual docker run (without compose)

```bash
docker build -t ettorino .
docker run -p 8080:5000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e OPENAI_API_KEY=sk-... \
  -e GOOGLE_API_KEY=AIza... \
  -v ettorino_workspace:/app/workspace \
  ettorino
```

> **Why `-w 1`?** The agent loop uses in-memory state per session (`event_queues`, `session_costs`, `human_responses`). Multiple workers = isolated processes = broken sessions. One worker + 16 threads handles all concurrent requests safely.

> **Port note:** avoid port 6000 — Chrome and Edge block it (`ERR_UNSAFE_PORT`). Use 8080, 8888, or any port ≥ 1024 not in the browser unsafe list.

---

## Project structure

```
Ettorino/
├── ettorino.py             ← Flask backend + agent engine + parallel loop
├── templates/
│   └── index.html          ← UI: terminal aesthetic, i18n, dark mode, parallel dashboard
├── workspace/              ← generated projects, organized by task slug
│   └── build_a_web_/
│       ├── webmon/
│       └── config.yaml
├── docs/
│   ├── API_KEYS.md         ← how to get and configure Anthropic, OpenAI, Google keys
│   ├── screen_ui.png
│   ├── screen_confirm.png
│   └── screen_parallel.png
├── Dockerfile              ← multi-stage Chainguard build (no shell in runtime)
├── docker-compose.yml      ← ports, env vars, workspace volume
├── requirements.txt
├── MEMORY.md              ← persistent instructions injected into Claude every session
├── .env                    ← keys and configuration (do not commit)
├── .dockerignore
└── .gitignore
```

---

## Configuration (.env)

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# At least one implementer key required
OPENAI_API_KEY=sk-...          # enables GPT-4.1 mini, GPT-4.1, o3
GOOGLE_API_KEY=AIza...         # enables all Gemini models (2.5 Flash free tier available)

# Optional
ETTORINO_VERSION=0.1.0
FLASK_PORT=5000
FLASK_DEBUG=true
MAX_ITERATIONS=10              # max loop iterations per task
HUMAN_TIMEOUT=300              # seconds before timeout on user response
```

For step-by-step instructions on obtaining each key, see [`docs/API_KEYS.md`](docs/API_KEYS.md).

### MEMORY.md — persistent instructions

`MEMORY.md` lives next to `ettorino.py` and is injected verbatim into Claude's system
prompt at the start of every session. Use it to set permanent preferences — coding style,
language, architectural patterns, things Claude should never do. The file has three sections:

| Section | Purpose |
| --- | --- |
| **Preferences** | Your standing instructions to Claude — language, code style, structure |
| **Patterns that work** | Auto-populated by Ettorino after each session |
| **Errors to avoid** | Auto-populated by Ettorino after each session |

After every successful task, Ettorino runs a lightweight reflection step (Haiku 4.5,
~$0.001) and proposes 1–3 bullet points to add. Each suggestion appears in the feed
one at a time — you approve or skip each one individually before it is written to disk.

---

## Internal architecture

```
POST /run
  │
  ├── classify_task()           Claude Haiku 4.5 → easy/medium/hard-mid/hard
  │                             also suggests best implementer (GPT or Gemini)
  │
  ├── [model confirm UI]        user can swap models before the loop starts
  │                             implementer dropdown grouped by provider
  │
  └── run_agent_loop()
        │
        ├── claude_reason()     Claude streams reasoning (only "thoughts" shown in UI)
        │     │
        │     ├── implement          → run_implementer() sequential
        │     │                        branches on provider: anthropic / openai / google
        │     ├── implement_parallel → run_implementer_parallel() × 3 workers
        │     │                        same provider branch, all workers use same model
        │     │                        each worker streams parallel_chunk_stream events
        │     ├── fix               → run_implementer() with corrective feedback
        │     ├── ask               → waits for user input via SSE
        │     └── done              → saves state, emits loop_end
        │
        └── [continue?]         /continue → reclassifies + new model confirm card
```

All events travel over **Server-Sent Events (SSE)** — no polling, no websockets.

---

## Production

```bash
# Local
gunicorn -w 1 --threads 16 --timeout 600 ettorino:app

# Docker (recommended)
docker compose up -d
```

---

## Roadmap

- [ ] MEMORY.md editor UI — edit preferences directly from the Ettorino web interface
- [ ] Gemini 3.1 Pro as default for hard tasks (when GA pricing confirmed)
- [ ] Mixed-provider parallel runs (some chunks GPT, some Gemini)
- [ ] Automatic quality/cost benchmark per task
- [ ] Session persistence on Redis (enables multi-worker scaling)
- [ ] One-click deploy on Railway / Render
- [ ] Plugin system for external tools (browser, terminal, git)