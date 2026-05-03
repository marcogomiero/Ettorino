# 🔑 Come ottenere le API Key

Ettorino ha bisogno di due chiavi API: una di **Anthropic** (per Claude) e una di **OpenAI** (per GPT/o3).
Entrambe funzionano a consumo — paghi solo quello che usi, nessun abbonamento obbligatorio.

---

## 1. Anthropic API Key (Claude)

### Registrazione

1. Vai su [console.anthropic.com](https://console.anthropic.com)
2. Clicca **Sign Up** e crea un account (email + password)
3. Verifica l'email

### Genera la chiave

1. Entra nella console → menu laterale **API Keys**
2. Clicca **Create Key**
3. Daile un nome (es. `ettorino`)
4. **Copia subito la chiave** — viene mostrata una sola volta!

La chiave ha questo formato:
```
sk-ant-api03-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### Crediti e costi

| Situazione | Cosa succede |
|---|---|
| Nuovo account | ~$5 di crediti gratuiti per testare |
| Crediti esauriti | Devi ricaricare manualmente |
| Nessun abbonamento | Paghi solo le chiamate API che fai |

Per ricaricare: **Console → Billing → Add Credits** (minimo $5)

### Prezzi modelli Anthropic (maggio 2026)

| Modello | Input $/1M tok | Output $/1M tok |
|---|---|---|
| Claude Haiku 4.5 | $0.80 | $4.00 |
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| Claude Opus 4.5 | $15.00 | $75.00 |

> **Nota**: Il piano Claude Max ($100/mese) riguarda solo l'interfaccia web claude.ai — **non include crediti API**. Sono sistemi di fatturazione separati.

---

## 2. OpenAI API Key (GPT / o3)

### Registrazione

1. Vai su [platform.openai.com](https://platform.openai.com)
2. Clicca **Sign Up** e crea un account
3. Verifica l'email

### Aggiungi un metodo di pagamento

A differenza di Anthropic, OpenAI **non offre crediti gratuiti automatici** ai nuovi account (il programma è stato discontinuato a metà 2025).

1. Vai su **Billing → Payment methods**
2. Aggiungi una carta di credito
3. Vai su **Billing → Add to credit balance**
4. Ricarica il minimo ($5 sono più che sufficienti per iniziare)

### Genera la chiave

1. Vai su **API Keys** nel menu laterale
2. Clicca **Create new secret key**
3. Daile un nome (es. `ettorino`)
4. **Copia subito la chiave** — viene mostrata una sola volta!

La chiave ha questo formato:
```
sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### Prezzi modelli OpenAI (maggio 2026)

| Modello | Input $/1M tok | Output $/1M tok |
|---|---|---|
| GPT-4o mini | $0.15 | $0.60 |
| GPT-4o | $2.50 | $10.00 |
| o3 | $10.00 | $40.00 |

> **Nota**: Il piano ChatGPT Pro ($200/mese) riguarda solo il sito chat.openai.com — **non include crediti API**. Sono sistemi di fatturazione separati.

---

## 3. Inserire le chiavi in Ettorino

Apri il file `.env` nella cartella di Ettorino e sostituisci i placeholder:

```env
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXX...
OPENAI_API_KEY=sk-proj-XXXXXXXX...
```

Salva il file. La prossima volta che avvii `ettorino_assistant.py` le chiavi vengono caricate automaticamente.

---

## 4. Sicurezza — regole fondamentali

> ⚠️ Le chiavi API sono come password. Se qualcuno le ottiene, può spendere i tuoi crediti.

- **Non committare mai `.env` su git** (il `.gitignore` incluso lo esclude automaticamente)
- **Non condividere le chiavi** in chat, email, o screenshot
- **Non inserirle nel codice** — usa sempre il file `.env`
- Se pensi che una chiave sia compromessa, **disabilitala subito** dalla console e creane una nuova
- Imposta un **spending limit mensile** come precauzione:
  - Anthropic: Console → Billing → Usage limits
  - OpenAI: Platform → Billing → Usage limits

---

## 5. Quanto spendo per testare?

Con $5 su ciascuna piattaforma puoi fare moltissimo:

| Scenario | Costo stimato |
|---|---|
| 50 task easy (Haiku + GPT-4o mini) | ~$0.10 totale |
| 20 task medium (Sonnet + GPT-4o) | ~$1.00 totale |
| 5 task hard (Opus + o3) | ~$2.00 totale |

Il **pannello costi live** di Ettorino ti mostra esattamente quanto stai spendendo a ogni chiamata, così non ci sono sorprese.

---

## 6. Alternativa gratuita per testare (senza carta)

Se vuoi provare Ettorino a costo zero prima di caricare crediti, puoi usare **Google Gemini** come implementer al posto di GPT. Gemini offre un tier gratuito generoso (1.500 richieste/giorno) senza carta di credito.

Per abilitarlo installa:
```bash
pip install google-generativeai
```

E chiedi a Ettorino di aggiungere il supporto Gemini — è un buon primo task da dargli! 😄
