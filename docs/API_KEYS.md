# 🔑 Getting your API Keys

Ettorino needs two API keys: one from **Anthropic** (for Claude) and one from **OpenAI** (for GPT/o3).
Both work on a pay-per-use basis — you only pay for what you use, no subscription required.

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
|---|---|
| New account | ~$5 in free credits to get started |
| Credits exhausted | Add more manually |
| No subscription | You only pay for the API calls you make |

To top up: **Console → Billing → Add Credits** (minimum $5)

### Anthropic model pricing (May 2026)

| Model | Input $/1M tok | Output $/1M tok |
|---|---|---|
| Claude Haiku 4.5 | $1.00 | $5.00 |
| Claude Sonnet 4.6 | $3.00 | $15.00 |
| Claude Opus 4.6 | $5.00 | $25.00 |
| Claude Opus 4.7 | $5.00 | $25.00 |

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
|---|---|---|
| GPT-4.1 mini | $0.40 | $1.60 |
| GPT-4.1 | $2.00 | $8.00 |
| o3 | $15.00 | $60.00 |

> **Note:** The ChatGPT Pro plan ($200/month) is for chat.openai.com only — it does **not** include API credits. They are separate billing systems.

---

## 3. Adding your keys to Ettorino

Open the `.env` file in the Ettorino folder and replace the placeholders:

```env
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXX...
OPENAI_API_KEY=sk-proj-XXXXXXXX...
```

Save the file. The next time you start `ettorino_assistant.py`, the keys are loaded automatically.

---

## 4. Security — the basics

> ⚠️ API keys are like passwords. If someone gets them, they can spend your credits.

- **Never commit `.env` to git** (the included `.gitignore` excludes it automatically)
- **Never share your keys** in chat, email, or screenshots
- **Never hardcode them** — always use the `.env` file
- If you think a key has been compromised, **disable it immediately** from the console and create a new one
- Set a **monthly spending limit** as a safeguard:
  - Anthropic: Console → Billing → Usage limits
  - OpenAI: Platform → Billing → Usage limits

---

## 5. How much will I spend testing?

With $5 on each platform you can do a lot:

| Scenario | Estimated cost |
|---|---|
| 50 easy tasks (Haiku + GPT-4.1 mini) | ~$0.10 total |
| 20 medium tasks (Sonnet + GPT-4.1) | ~$1.00 total |
| 5 hard tasks (Opus + o3) | ~$2.00 total |

Ettorino's **live cost panel** shows you exactly what each call costs in real time — no surprises.