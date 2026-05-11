# 🔑 Getting your API Keys

Ettorino needs three API keys: one from **Anthropic** (for Claude), one from **OpenAI** (for GPT/o3), and one from **Google** (for Gemini — optional but recommended).
All work on a pay-per-use basis — you only pay for what you use, no subscription required.

---

## 1. Anthropic API Key (Claude)

### Sign up

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Click **Sign Up** and create an account (email + password)
3. Verify your email

### Generate the key

1. Open the console → sidebar **API Keys**
2. Click **Create Key**
3. Give it a name (e.g. `ettorino`)
4. **Copy the key immediately** — it's only shown once!

The key looks like this:

```
sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### Credits and billing

| Situation | What happens |
| --- | --- |
| New account | ~$5 in free credits to get started |
| Credits exhausted | Add more manually |
| No subscription | You only pay for the API calls you make |

To top up: **Console → Billing → Add Credits** (minimum $5)

### Anthropic model pricing (May 2026)

| Model | Role | Input $/1M tok | Output $/1M tok |
| --- | --- | --- | --- |
| Claude Haiku 4.5 | Reasoner / Implementer | $1.00 | $5.00 |
| Claude Sonnet 4.6 | Reasoner / Implementer | $3.00 | $15.00 |
| Claude Opus 4.6 | Reasoner / Implementer | $5.00 | $25.00 |
| Claude Opus 4.7 | Reasoner / Implementer | $5.00 | $25.00 |

> **Note:** The Claude Max plan ($100/month) is for the claude.ai web interface only — it does **not** include API credits. They are separate billing systems.

---

## 2. OpenAI API Key (GPT / o3)

### Sign up

1. Go to [platform.openai.com](https://platform.openai.com)
2. Click **Sign Up** and create an account
3. Verify your email

### Add a payment method

Unlike Anthropic, OpenAI **does not offer automatic free credits** to new accounts (the program was discontinued in mid-2025).

1. Go to **Billing → Payment methods**
2. Add a credit card
3. Go to **Billing → Add to credit balance**
4. Top up the minimum ($5 is more than enough to get started)

### Generate the key

1. Go to **API Keys** in the sidebar
2. Click **Create new secret key**
3. Give it a name (e.g. `ettorino`)
4. **Copy the key immediately** — it's only shown once!

The key looks like this:

```
sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### OpenAI model pricing (May 2026)

| Model | Input $/1M tok | Output $/1M tok |
| --- | --- | --- |
| GPT-4.1 mini | $0.40 | $1.60 |
| GPT-4.1 | $2.00 | $8.00 |
| o3 | $15.00 | $60.00 |

> **Note:** The ChatGPT Pro plan ($200/month) is for chat.openai.com only — it does **not** include API credits. They are separate billing systems.

---

## 3. Google API Key (Gemini) — optional

Gemini is the most cost-effective implementer available in Ettorino. Flash models have a **free tier** with no credit card required, making them ideal for testing or simple tasks.

### Sign up and API key (free, no card required)

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with your Google account
3. Left sidebar → **"Get API key"**
4. Click **"Create API key"** → select or create a project
5. **Copy the key** — you can always retrieve it from this page

The key looks like this:

```
AIzaSy-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### Free tier — what you get without a credit card

| Model | RPM | RPD | Notes |
| --- | --- | --- | --- |
| Gemini 2.5 Flash-Lite | 15 | 1,000 | Cheapest option available |
| Gemini 2.5 Flash | 10 | 500 | Excellent for code generation |

> Free tier limits were reduced in late 2025. They are sufficient for prototyping and light personal use, but not for intensive workloads.

> ⚠️ **Privacy note:** With the free tier, Google may use your inputs and outputs to improve its models. If the code you generate is confidential, enable paid billing.

### Adding credits (when you exceed the free tier)

1. Go to [aistudio.google.com](https://aistudio.google.com) → menu → **"Billing"**
2. Click **"Set up billing"**
3. Create or link a **Google Cloud Billing account**
4. Add your credit or debit card
5. Select **Prepay** (mandatory for new accounts since March 2026)
6. Purchase credits — **minimum $10, maximum $5,000**
7. Credits are deducted in real time as you use the API

**Auto-reload (recommended):** in the Billing settings you can configure an automatic threshold — e.g. "when my balance drops below $5, reload $20" — so you never get blocked mid-task.

> ⚠️ Google credits expire after **12 months** from purchase and are non-refundable. Do not load more than you expect to spend within the year.

> ⚠️ The $300 Google Cloud welcome credit does **not** cover the Gemini API — it is reserved for other Google Cloud services.

### Spending cap (protection against surprises)

From the Billing → Projects panel you can set a monthly cap per project. Recommended: do this immediately after enabling billing.

### Google Gemini model pricing (May 2026)

| Model | Free tier | Input $/1M tok | Output $/1M tok | Context |
| --- | --- | --- | --- | --- |
| Gemini 2.5 Flash-Lite | ✓ | $0.10 | $0.40 | 1M tok |
| Gemini 2.5 Flash | ✓ | $0.30 | $2.50 | 1M tok |
| Gemini 2.5 Pro | ✗ | $1.25 | $10.00 | 1M tok |
| Gemini 3 Flash | ✗ | $0.50 | $3.00 | 1M tok |
| Gemini 3.1 Flash-Lite | ✗ | $0.25 | $1.50 | 1M tok |
| Gemini 3.1 Pro | ✗ | $2.00 | $12.00 | 1M tok |

> All Gemini models have a **1 million token context window** — useful for large codebases or tasks with a lot of existing code as context.

---

## 4. Adding the keys to Ettorino

Open the `.env` file in the Ettorino folder and replace the placeholders:

```env
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXX...
OPENAI_API_KEY=sk-proj-XXXXXXXX...
GOOGLE_API_KEY=AIzaSy-XXXXXXXX...   # optional — remove this line if not using Gemini
```

Save the file. The next time you start `ettorino.py`, the keys are loaded automatically. If `GOOGLE_API_KEY` is not present, Ettorino automatically falls back to GPT without crashing. Models without a configured key are shown as disabled in the model selection UI.

---

## 5. Security — the basics

> ⚠️ API keys are like passwords. If someone gets hold of them, they can spend your credits.

- **Never commit `.env` to git** (the included `.gitignore` excludes it automatically)
- **Never share your keys** in chats, emails, or screenshots
- **Never hardcode them** — always use the `.env` file
- If you think a key has been compromised, **disable it immediately** from the console and create a new one
- Set a **monthly spending limit** as a precaution:
  - Anthropic: Console → Billing → Usage limits
  - OpenAI: Platform → Billing → Usage limits
  - Google: AI Studio → Billing → Projects → Spend cap

---

## 6. How much will I spend testing?

With $5 on Anthropic + $5 on OpenAI you can do a lot. Gemini Flash adds free capacity on top:

| Scenario | Models | Estimated cost |
| --- | --- | --- |
| 50 easy tasks | Haiku + Gemini 2.5 Flash-Lite | **~$0.02** (essentially free) |
| 50 easy tasks | Haiku + GPT-4.1 mini | ~$0.10 |
| 20 medium tasks | Sonnet + Gemini 2.5 Flash | ~$0.30 |
| 20 medium tasks | Sonnet + GPT-4.1 | ~$1.00 |
| 5 hard tasks | Opus + o3 | ~$2.00 |

Ettorino shows the **live cost per call** — Claude, GPT, and Gemini broken down separately — so there are no surprises.