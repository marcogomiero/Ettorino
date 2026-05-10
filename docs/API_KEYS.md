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

## 3. Google API Key (Gemini) — opzionale

Gemini è l'implementer più economico disponibile in Ettorino. I modelli Flash hanno un **free tier** senza carta di credito, utile per testare o per task semplici.

### Sign up e chiave API (gratis, nessuna carta)

1. Vai su [aistudio.google.com](https://aistudio.google.com)
2. Accedi con il tuo account Google
3. Menu a sinistra → **"Get API key"**
4. Clicca **"Create API key"** → seleziona o crea un progetto
5. **Copia la chiave** — la puoi sempre recuperare da questa pagina

La chiave looks like this:

```
AIzaSy-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### Free tier — cosa ottieni senza carta

| Modello | RPM | RPD | Note |
| --- | --- | --- | --- |
| Gemini 2.5 Flash-Lite | 15 | 1.000 | Più economico assoluto |
| Gemini 2.5 Flash | 10 | 500 | Ottimo per codice |

> I limiti free tier si sono ridotti da fine 2025. Sono sufficienti per prototipazione e uso personale leggero, ma non per uso intensivo.

> ⚠️ **Attenzione privacy:** Con il free tier, Google può usare i tuoi input/output per migliorare i propri modelli. Se il codice che generi è confidenziale, attiva il billing paid.

### Caricare crediti (quando esaurisci il free tier)

1. Vai su [aistudio.google.com](https://aistudio.google.com) → menu → **"Billing"**
2. Clicca **"Set up billing"**
3. Crea o collega un **Google Cloud Billing account**
4. Aggiungi la tua carta di credito/debito
5. Seleziona **Prepay** (obbligatorio per nuovi account da marzo 2026)
6. Acquista i crediti — **minimo $10, massimo $5.000**
7. I crediti vengono scalati in tempo reale durante l'uso

**Auto-reload (consigliato):** nelle impostazioni Billing puoi configurare una soglia automatica — es. "quando scendo sotto $5, ricarica $20" — così non ti blocchi a metà di un task.

> ⚠️ I crediti Google scadono dopo **12 mesi** dall'acquisto e non sono rimborsabili. Non caricare più di quanto prevedi di spendere nell'anno.

> ⚠️ I $300 di Google Cloud welcome credit **non coprono** la Gemini API — sono riservati ad altri servizi Google Cloud.

### Spending cap (protezione sorprese)

Dal pannello Billing → Projects puoi impostare un cap mensile per progetto. Raccomandato: impostalo subito dopo aver attivato il billing.

### Google Gemini model pricing (May 2026)

| Modello | Free tier | Input $/1M tok | Output $/1M tok | Contesto |
| --- | --- | --- | --- | --- |
| Gemini 2.5 Flash-Lite | ✓ | $0.10 | $0.40 | 1M tok |
| Gemini 2.5 Flash | ✓ | $0.30 | $2.50 | 1M tok |
| Gemini 2.5 Pro | ✗ | $1.25 | $10.00 | 1M tok |
| Gemini 3 Flash | ✗ | $0.50 | $3.00 | 1M tok |
| Gemini 3.1 Flash-Lite | ✗ | $0.25 | $1.50 | 1M tok |
| Gemini 3.1 Pro | ✗ | $2.00 | $12.00 | 1M tok |

> Tutti i modelli Gemini hanno una finestra di contesto da **1 milione di token** — utile per codebase grandi o task con molto codice di contesto.

---

## 4. Aggiungere le chiavi a Ettorino

Apri il file `.env` nella cartella di Ettorino e sostituisci i placeholder:

```env
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXX...
OPENAI_API_KEY=sk-proj-XXXXXXXX...
GOOGLE_API_KEY=AIzaSy-XXXXXXXX...   # opzionale — rimuovi la riga se non la usi
```

Salva il file. La prossima volta che avvii `ettorino.py`, le chiavi vengono caricate automaticamente. Se `GOOGLE_API_KEY` non è presente, Ettorino fa fallback automatico a GPT senza crashare.

---

## 5. Sicurezza — le basi

> ⚠️ Le chiavi API sono come password. Se qualcuno le ottiene, può spendere i tuoi crediti.

- **Non committare mai `.env` su git** (il `.gitignore` incluso lo esclude automaticamente)
- **Non condividere le chiavi** in chat, email o screenshot
- **Non metterle nel codice** — usa sempre il file `.env`
- Se pensi che una chiave sia compromessa, **disabilitala subito** dalla console e creane una nuova
- Imposta un **spending limit mensile** come precauzione:
  - Anthropic: Console → Billing → Usage limits
  - OpenAI: Platform → Billing → Usage limits
  - Google: AI Studio → Billing → Projects → Spend cap

---

## 6. Quanto spendo per testare?

Con $5 su Anthropic + $5 su OpenAI puoi fare moltissimo. Gemini Flash aggiunge capacità gratis:

| Scenario | Modelli | Costo stimato |
| --- | --- | --- |
| 50 task easy | Haiku + Gemini 2.5 Flash-Lite | **~$0.02** (quasi gratis) |
| 50 task easy | Haiku + GPT-4.1 mini | ~$0.10 |
| 20 task medium | Sonnet + Gemini 2.5 Flash | ~$0.30 |
| 20 task medium | Sonnet + GPT-4.1 | ~$1.00 |
| 5 task hard | Opus + o3 | ~$2.00 |

Ettorino mostra il **costo live per ogni chiamata** — Claude quanto, GPT quanto, Gemini quanto — così non ci sono sorprese.