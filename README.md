# 🤖 Ettorino

> Assistente agente multimodale per la costruzione di progetti software.
> Loop autonomo **Claude × GPT** con router intelligente di difficoltà e stima costi live.

---

## Cosa fa

Ettorino prende un task in linguaggio naturale e lo esegue autonomamente attraverso un loop agente:

1. **Classifica** la difficoltà del task (easy / medium / hard)
2. **Seleziona** i modelli AI più adatti al tier — più semplice il task, meno si spende
3. **Ragiona** sul problema e produce specifiche tecniche (Claude)
4. **Implementa** il codice dalle specifiche (GPT)
5. **Verifica** il codice e itera fino a che non è corretto
6. **Chiede** chiarimenti all'utente se ha dubbi, senza bloccarsi

Tutto visibile in tempo reale nell'interfaccia web, con stima e conteggio dei costi live.

---

## Struttura del progetto

```
ettorino/
├── ettorino_assistant.py   ← backend Flask + motore agente
├── templates/
│   └── index.html          ← interfaccia web (feed live + costi)
├── workspace/              ← codice generato sessione per sessione
├── .env                    ← chiavi API e configurazione (da compilare)
├── .gitignore              ← esclude .env e workspace da git
├── README.md               ← questo file
└── docs/
    └── API_KEYS.md         ← guida completa per ottenere le API key
```

---

## Installazione

### 1. Prerequisiti

- **Python 3.10+** → scarica da [python.org](https://www.python.org/downloads/)
- Connessione internet
- Un account su Anthropic e uno su OpenAI (vedi [`docs/API_KEYS.md`](docs/API_KEYS.md))

### 2. Dipendenze Python

```bash
pip install flask anthropic openai python-dotenv
```

### 3. Configurazione API key

Apri il file `.env` nella cartella e sostituisci i placeholder con le tue chiavi reali:

```env
ANTHROPIC_API_KEY=sk-ant-...    ← la tua chiave Anthropic
OPENAI_API_KEY=sk-...           ← la tua chiave OpenAI
```

> Non sai come ottenerle? Leggi la guida completa → [`docs/API_KEYS.md`](docs/API_KEYS.md)

### 4. Avvio

```bash
cd ettorino
python ettorino_assistant.py
```

Apri il browser su **http://localhost:5000**

---

## Come si usa

1. Scrivi il task nella textarea a sinistra (in italiano o inglese va bene)
2. Clicca **AVVIA LOOP**
3. Ettorino classifica il task e mostra tier, modelli scelti e stima del costo
4. Segui il feed live a destra: i pensieri di Claude e il codice di GPT appaiono in streaming
5. Se Claude ha bisogno di chiarimenti, compare un box giallo — rispondi e il loop riparte
6. Il codice finale è salvato in `workspace/iteration_N.py`

---

## Router di difficoltà

| Tier      | Reasoner            | Implementer  | Quando                                       |
|-----------|---------------------|--------------|----------------------------------------------|
| 🟢 Easy   | Claude Haiku 4.5    | GPT-4o mini  | Script semplici, utility, < 100 righe        |
| 🟡 Medium | Claude Sonnet 4.5   | GPT-4o       | App multi-componente, API, 100–500 righe     |
| 🔴 Hard   | Claude Opus 4.5     | o3           | Sistemi complessi, ML/AI, > 500 righe        |

La classificazione usa sempre **Claude Haiku** (costo < $0.001) indipendentemente dal tier scelto.

---

## Costi indicativi

| Complessità | Costo per task completo |
|-------------|------------------------|
| 🟢 Easy     | ~$0.001 – $0.01        |
| 🟡 Medium   | ~$0.05 – $0.20         |
| 🔴 Hard     | ~$0.50 – $2.00         |

I costi sono visibili in tempo reale nel pannello sinistro dell'interfaccia.

---

## Opzioni di configurazione (.env)

| Variabile          | Default | Descrizione                                      |
|--------------------|---------|--------------------------------------------------|
| `ANTHROPIC_API_KEY`| —       | Chiave API Anthropic (obbligatoria)              |
| `OPENAI_API_KEY`   | —       | Chiave API OpenAI (obbligatoria)                 |
| `FLASK_PORT`       | `5000`  | Porta su cui gira l'interfaccia web              |
| `FLASK_DEBUG`      | `true`  | Modalità debug Flask (metti `false` in produzione) |
| `MAX_ITERATIONS`   | `10`    | Numero massimo di iterazioni del loop            |
| `HUMAN_TIMEOUT`    | `300`   | Secondi di attesa risposta utente prima del timeout |

---

## Note tecniche

- Il codice generato si accumula in `workspace/` — puliscila manualmente quando vuoi
- Per aggiornare i prezzi dei modelli, modifica il dizionario `MODELS` in `ettorino_assistant.py`
- Flask gira in modalità **threaded** per gestire SSE e richieste in parallelo
- Per deploy in produzione usa un server WSGI come `gunicorn`:
  ```bash
  pip install gunicorn
  gunicorn -w 1 --threads 4 ettorino_assistant:app
  ```
