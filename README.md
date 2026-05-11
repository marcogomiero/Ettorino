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

Models without a configured API key are shown with a `⚠ no key` label and are disabled in the dropdown. If the router's suggested model has no key, Ettorino automatically falls back to the best available model in the same tier — no crash, no silent failure.

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

Ettorino runs as a plain Python process — locally on your machine or on any Linux VM.
No containers required.

**Prerequisites:** Python 3.10+, an Anthropic API key (required), at least one between OpenAI and Google API key.

### Step 1 — Clone the repo

```bash
git clone https://github.com/marcogomiero/Ettorino.git
cd Ettorino
```

### Step 2 — Create a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install flask anthropic openai google-genai python-dotenv
```

### Step 4 — Configure API keys

Create a `.env` file in the project root (never commit this file):

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...          # optional if using Gemini only
GOOGLE_API_KEY=AIza...         # optional if using GPT only
ETTORINO_VERSION=0.1.0
```

For step-by-step instructions on getting each key, see [`docs/API_KEYS.md`](docs/API_KEYS.md).

### Step 5 — Run

```bash
python ettorino.py
```

Open **http://localhost:5000** in your browser — Ettorino does the rest.

> **Tip:** if you use PyCharm or VS Code, just open the project folder and run `ettorino.py`
> from the IDE. The `.env` file is picked up automatically.

---

## Running on a cloud VM

If you want Ettorino always-on and accessible from any device, a small Linux VM works perfectly.
Any provider works — DigitalOcean, Hetzner, AWS EC2, Google Cloud, Azure.
A 2 vCPU / 2 GB RAM instance is more than enough.

### Recommended: Hetzner CX22 (~€4/month) or DigitalOcean Basic Droplet ($6/month)

```bash
# 1. SSH into your VM
ssh user@your-vm-ip

# 2. Install Python 3.10+ (Ubuntu 22.04 or later already has it)
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git

# 3. Clone and set up
git clone https://github.com/marcogomiero/Ettorino.git
cd Ettorino
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Create your .env
nano .env   # paste your keys, save with Ctrl+X

# 5. Run with gunicorn (more stable than the dev server)
pip install gunicorn
gunicorn -w 1 --threads 16 --timeout 600 -b 0.0.0.0:5000 ettorino:app
```

Ettorino is now reachable at **http://your-vm-ip:5000**.

### Keep it running with systemd

Create `/etc/systemd/system/ettorino.service`:

```ini
[Unit]
Description=Ettorino AI Agent
After=network.target

[Service]
User=your-user
WorkingDirectory=/home/your-user/Ettorino
EnvironmentFile=/home/your-user/Ettorino/.env
ExecStart=/home/your-user/Ettorino/.venv/bin/gunicorn \
    -w 1 --threads 16 --timeout 600 \
    -b 0.0.0.0:5000 ettorino:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ettorino
sudo systemctl start ettorino

# Check status
sudo systemctl status ettorino

# View logs live
sudo journalctl -u ettorino -f
```

### HTTPS with nginx + Let's Encrypt (optional)

If you point a domain at the VM, you can get free HTTPS in a few minutes:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# Create nginx config for your domain
sudo nano /etc/nginx/sites-available/ettorino
```

```nginx
server {
    server_name ettorino.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;           # required for SSE streaming
        proxy_cache off;
        proxy_read_timeout 600s;       # long-running agent loops
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ettorino /etc/nginx/sites-enabled/
sudo certbot --nginx -d ettorino.yourdomain.com
sudo systemctl reload nginx
```

> **SSE note:** the `proxy_buffering off` directive is mandatory. Without it, nginx
> buffers the event stream and the UI appears frozen until the task completes.

### Firewall

```bash
# Allow SSH, HTTP, HTTPS — block everything else
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# If you're NOT using nginx and want direct access on port 5000:
sudo ufw allow 5000
```

> **Security note:** never expose port 5000 directly to the internet without a password
> or firewall rule limiting access to your IP. Ettorino has no built-in authentication.
> If you use nginx + HTTPS, add HTTP Basic Auth for a quick layer of protection:
> `sudo htpasswd -c /etc/nginx/.htpasswd your-username`
> then add `auth_basic` directives to the nginx config.

### Updating

```bash
cd Ettorino
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ettorino
```

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
├── requirements.txt
├── MEMORY.md               ← persistent instructions injected into Claude every session
├── .env                    ← keys and configuration (do not commit)
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
FLASK_DEBUG=true               # set to false in production
MAX_ITERATIONS=10              # max loop iterations per task
HUMAN_TIMEOUT=300              # seconds before timeout on user response
```

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
        │     └── done              → saves state, emits loop_end + reflection
        │
        └── [continue?]         /continue → reclassifies + new model confirm card
```

All events travel over **Server-Sent Events (SSE)** — no polling, no websockets.
In-memory session state means a single process handles all concurrent requests safely —
do not run multiple gunicorn workers.

---

## Roadmap

- [ ] MEMORY.md editor UI — edit preferences directly from the Ettorino web interface
- [ ] Gemini 3.1 Pro as default for hard tasks (when GA pricing confirmed)
- [ ] Mixed-provider parallel runs (some chunks GPT, some Gemini)
- [ ] Automatic quality/cost benchmark per task
- [ ] Optional HTTP Basic Auth for VM deployments
- [ ] One-click deploy scripts for Hetzner and DigitalOcean
- [ ] Plugin system for external tools (browser, terminal, git)