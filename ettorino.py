import os
import json
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from flask import Flask, render_template, request, Response, jsonify
import anthropic
import openai
from dotenv import load_dotenv

import ssl
import httpx
import urllib3
import re
from dataclasses import dataclass, field
from typing import Optional

# Silenzia i warning SSL (proxy aziendali con self-signed cert)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

app = Flask(__name__)

WORKSPACE = Path("workspace")
WORKSPACE.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
# MODEL REGISTRY
# prezzi in $ per milione di token
# ─────────────────────────────────────────────
MODELS = {
    # Anthropic — dual role (reasoner OR implementer)
    "claude-haiku-4-5": {
        "provider": "anthropic",
        "label": "Claude Haiku 4.5",
        "role": ["reasoner", "implementer"],
        "tier": "easy",
        "input_cost": 1.00,
        "output_cost": 5.00,
    },
    "claude-sonnet-4-6": {
        "provider": "anthropic",
        "label": "Claude Sonnet 4.6",
        "role": ["reasoner", "implementer"],
        "tier": "medium",
        "input_cost": 3.00,
        "output_cost": 15.00,
    },
    "claude-opus-4-7": {
        "provider": "anthropic",
        "label": "Claude Opus 4.7",
        "role": ["reasoner", "implementer"],
        "tier": "hard",
        "input_cost": 5.00,
        "output_cost": 25.00,
    },
    "claude-opus-4-6": {
        "provider": "anthropic",
        "label": "Claude Opus 4.6",
        "role": ["reasoner", "implementer"],
        "tier": "hard-mid",
        "input_cost": 5.00,
        "output_cost": 25.00,
    },
    # OpenAI — implementer only
    "gpt-4.1-mini": {
        "provider": "openai",
        "label": "GPT-4.1 mini",
        "role": ["implementer"],
        "tier": "easy",
        "input_cost": 0.40,
        "output_cost": 1.60,
    },
    "gpt-4.1": {
        "provider": "openai",
        "label": "GPT-4.1",
        "role": ["implementer"],
        "tier": "medium",
        "input_cost": 2.00,
        "output_cost": 8.00,
    },
    "o3": {
        "provider": "openai",
        "label": "o3",
        "role": ["implementer"],
        "tier": "hard",
        "input_cost": 15.00,
        "output_cost": 60.00,
    },
}

# Tier → modelli di default
TIER_MODELS = {
    "easy":   {"reasoner": "claude-haiku-4-5",   "implementer": "gpt-4.1-mini"},
    "medium": {"reasoner": "claude-sonnet-4-6",  "implementer": "gpt-4.1"},
    "hard":   {"reasoner": "claude-opus-4-7",    "implementer": "o3"},
}

# State globale sessioni
event_queues   = {}
session_costs  = {}
human_responses = {}
model_overrides = {}  # session_id → {"reasoner": ..., "implementer": ...}
session_state  = {}  # session_id → {"code": str, "task": str, "reasoner": str, "implementer": str, "iteration": int}
stop_flags     = {}  # session_id → bool — set True to abort loop

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _make_http_client() -> httpx.Client:
    """Client httpx senza verifica SSL — necessario per proxy aziendali con certificati self-signed."""
    return httpx.Client(
        transport=httpx.HTTPTransport(verify=False),
        verify=False,
        timeout=120.0,
    )

def get_anthropic_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY mancante nel .env")
    return anthropic.Anthropic(api_key=key, http_client=_make_http_client())

def get_openai_client():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY mancante nel .env")
    return openai.OpenAI(api_key=key, http_client=_make_http_client())

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def calc_cost(model_id: str, input_tok: int, output_tok: int) -> tuple[float, float]:
    m = MODELS.get(model_id, {})
    cost = (input_tok * m.get("input_cost", 0) + output_tok * m.get("output_cost", 0)) / 1_000_000
    return cost, cost

def add_cost(session_id: str, model_id: str, input_tok: int, output_tok: int) -> float:
    cost, _ = calc_cost(model_id, input_tok, output_tok)
    if session_id not in session_costs:
        session_costs[session_id] = {"total": 0.0, "by_model": {}}
    session_costs[session_id]["total"] += cost
    prev = session_costs[session_id]["by_model"].get(model_id, {"cost": 0.0, "tokens": 0})
    session_costs[session_id]["by_model"][model_id] = {
        "cost": prev["cost"] + cost,
        "tokens": prev["tokens"] + input_tok + output_tok,
    }
    return session_costs[session_id]["total"]

def emit(q: queue.Queue, event_type: str, data: dict):
    q.put({"type": event_type, "data": data})

def wait_for_human(session_id: str, timeout: int = 300) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if session_id in human_responses:
            val = human_responses.pop(session_id)
            if val == "__stop__":
                return None  # treat as timeout/abort
            return val
        time.sleep(0.3)
    return None

# ─────────────────────────────────────────────
# FASE 0 — CLASSIFIER
# Usa sempre Sonnet per la classificazione: abbastanza smart, non troppo caro
# ─────────────────────────────────────────────
CLASSIFIER_MODEL = "claude-haiku-4-5"
# ─────────────────────────────────────────────
# CHUNK MANAGEMENT
# ─────────────────────────────────────────────
@dataclass
class Chunk:
    id: str
    title: str
    spec: str
    dependencies: list = field(default_factory=list)  # IDs dei chunk da cui dipende
    is_critical: bool = False

@dataclass
class ChunkResult:
    chunk_id: str
    code: str
    error: Optional[str] = None

class ChunkManager:
    @staticmethod
    def from_claude_result(result: dict) -> list:
        """Parsa i chunk dal risultato JSON di Claude."""
        return [
            Chunk(
                id=ch["id"],
                title=ch["title"],
                spec=ch["spec"],
                dependencies=ch.get("dependencies", []),
                is_critical=ch.get("is_critical", False),
            )
            for ch in result.get("parallel_chunks", [])
        ]

    @staticmethod
    def validate(chunks: list) -> None:
        ids = {c.id for c in chunks}
        for c in chunks:
            for dep in c.dependencies:
                if dep not in ids:
                    raise ValueError(f"Chunk '{c.id}': dipendenza '{dep}' non trovata")

    @staticmethod
    def execution_waves(chunks: list) -> list:
        """Topological sort → lista di onde eseguibili in parallelo."""
        remaining = {c.id: set(c.dependencies) for c in chunks}
        waves = []
        while remaining:
            ready = [cid for cid, deps in remaining.items() if not deps]
            if not ready:
                raise ValueError(f"Ciclo nelle dipendenze: {list(remaining.keys())}")
            waves.append(ready)
            for cid in ready:
                del remaining[cid]
            for deps in remaining.values():
                deps -= set(ready)
        return waves

    @staticmethod
    def combine_code(results: dict) -> str:
        """Combina i codici di tutti i chunk per la review di Claude."""
        return "\n\n".join(
            f"=== CHUNK {cid} ===\n{results[cid].code}"
            for cid in sorted(results)
            if results[cid].code
        )

    @staticmethod
    def build_review_context(results: dict, iteration: int) -> str:
        """Costruisce il contesto strutturato per la review parallela di Claude."""
        summaries = []
        for cid in sorted(results):
            r = results[cid]
            if r.error:
                summaries.append(f"Chunk {cid}: ❌ ERRORE — {r.error}")
            else:
                files = re.findall(r"###\s*FILE\s*[:\-]?\s*([\w./\-]+\.\w+)", r.code)
                lines = r.code.count("\n")
                s = f"Chunk {cid}: ✅ {lines} righe"
                if files:
                    s += " — " + ", ".join(files[:6])
                    if len(files) > 6:
                        s += f" (+{len(files)-6} altri)"
                summaries.append(s)

        parts = [
            f"Codice prodotto in parallelo (iterazione {iteration}):",
            "SOMMARIO:\n" + "\n".join(summaries),
            "\nCODICE COMPLETO PER CHUNK:",
        ]
        for cid in sorted(results):
            r = results[cid]
            parts.append(f"\n=== CHUNK {cid} ({len(r.code)} chars) ===\n{r.code}")
        parts.append(
            "\nVerifica: 1) file completi, 2) import incrociati corretti, "
            "3) naming consistency, 4) interfacce compatibili. "
            "Se tutto OK → done. Se problemi → fix con dettagli per chunk specifico."
        )
        return "\n".join(parts)



def classify_task(client: anthropic.Anthropic, session_id: str, task: str, q: queue.Queue, silent: bool = False) -> dict:
    if not silent:
        emit(q, "agent_start", {"agent": "router", "label": "Router"})
        emit(q, "agent_chunk", {"agent": "router", "text": "Analizzo il task..."})

    system = """Sei il router intelligente di Ettorino, un assistente agente Claude×GPT.
Il tuo compito è analizzare il task dell'utente e decidere:
1. La difficoltà: easy / medium / hard
2. I modelli migliori per massimizzare qualità e minimizzare costi
3. Se hai dubbi sul task, formula una domanda di chiarimento
4. Una stima realistica di token e costo

Criteri difficoltà:
- easy: script semplice, funzione singola, utility < 100 righe, nessuna dipendenza esterna complessa
- medium: app multi-componente, API integration, logica non banale, 100-500 righe
- hard-mid: sistemi complessi ma circoscritti, architetture multi-componente, 300-600 righe — usa Opus 4.6
- hard: sistemi molto complessi, ML/AI, architetture multi-file, algoritmi avanzati, > 600 righe — usa Opus 4.7

Suggerisci sempre il modello più adatto al task specifico, non il più economico di default.
Se il task è ambiguo, formulare UNA domanda precisa è più utile che procedere a caso.

Rispondi SOLO con JSON valido, nessun testo fuori:
{
  "difficulty": "easy|medium|hard-mid|hard",
  "confidence": 0.0-1.0,
  "reasoning": "spiegazione breve",
  "suggested_reasoner": "claude-haiku-4-5|claude-sonnet-4-6|claude-opus-4-6|claude-opus-4-7",
  "suggested_implementer": "gpt-4.1-mini|gpt-4.1|o3",
  "model_rationale": "perché questi modelli per questo task",
  "estimated_input_tokens": 1000,
  "estimated_output_tokens": 2000,
  "estimated_cost_usd": 0.05,
  "needs_clarification": true|false,
  "clarification_question": "domanda se needs_clarification è true, altrimenti null",
  "complexity_factors": ["fattore1", "fattore2"]
}"""

    response = client.messages.create(
        model=CLASSIFIER_MODEL,
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": f"Task da classificare:\n\n{task}"}]
    )

    raw = response.content[0].text.strip()
    input_tok = response.usage.input_tokens
    output_tok = response.usage.output_tokens
    total = add_cost(session_id, CLASSIFIER_MODEL, input_tok, output_tok)

    emit(q, "cost_update", {
        "model_id": CLASSIFIER_MODEL,
        "model_label": MODELS[CLASSIFIER_MODEL]["label"],
        "provider": "anthropic",
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "call_cost": calc_cost(CLASSIFIER_MODEL, input_tok, output_tok)[0],
        "total_cost": total,
    })

    try:
        clean = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
    except Exception:
        result = {"difficulty": "medium", "confidence": 0.5, "reasoning": raw,
                  "suggested_reasoner": "claude-sonnet-4-6",
                  "suggested_implementer": "gpt-4.1",
                  "needs_clarification": False}

    if not silent:
        emit(q, "agent_end", {"agent": "router"})
    return result

# ─────────────────────────────────────────────
# FASE 1 — CLAUDE REASONER
# Ragiona, specifica, verifica, tiene GPT sui binari
# ─────────────────────────────────────────────
def claude_reason(client: anthropic.Anthropic, session_id: str, task: str,
                  context: str, model_id: str, iteration: int, q: queue.Queue) -> dict:

    emit(q, "agent_start", {"agent": "claude", "label": "Claude", "model": MODELS[model_id]["label"]})

    system = """Sei Claude, il Reasoner di Ettorino. Il tuo ruolo è:
1. RAGIONARE sul task e produrre specifiche tecniche precise per GPT
2. VERIFICARE il codice prodotto da GPT ad ogni iterazione
3. TENERE GPT SUI BINARI: se GPT ha deviato dal task, correggi esplicitamente
4. CHIEDERE all'utente se hai dubbi genuini prima di procedere
5. DICHIARARE DONE solo quando il codice è completo, corretto e testabile

Quando scrivi le spec per GPT sii MOLTO specifico:
- Struttura esatta dei file
- Firme delle funzioni
- Casi edge da gestire
- Formato dell'output atteso

Se GPT ha prodotto codice che non soddisfa le spec, indica ESATTAMENTE cosa correggere.
IMPORTANTE — output troncato: Se un file termina bruscamente, NON mandare status "fix" per troncamento.
Valuta il codice parziale: se il chunk è abbastanza completo da funzionare, dichiaralo OK.

REVIEW PARALLELA: Quando ricevi codice da chunk multipli (=== CHUNK A ===, === CHUNK B ===, ecc.):
1. Leggi TUTTI i chunk prima di decidere
2. Verifica import incrociati: se chunk A importa da chunk B, controlla che B esporti quella cosa
3. Verifica naming: stesse variabili/classi chiamate uguale in tutti i chunk
4. Se tutto coerente → status "done"
5. Se ci sono problemi specifici → status "fix" con feedback che indica QUALE chunk correggere e COSA

FILE NEL WORKSPACE: Se nel contesto vedi "FILE GIÀ PRESENTI NEL WORKSPACE", quei file esistono
già su disco con il loro contenuto completo. NON chiedere all'utente di fornirli, NON usare
status "ask" per ottenerli — sono già disponibili. Valuta il codice che hai nel contesto.

Rispondi SOLO con JSON valido:
{
  "status": "implement|implement_parallel|fix|ask|done",
  "thoughts": "il tuo ragionamento interno (visibile all'utente)",
  "spec": "specifiche dettagliate per GPT (solo se status=implement, singolo chunk)",
  "parallel_chunks": [
    {"id": "A", "title": "titolo feature A", "spec": "spec dettagliata per GPT worker 1"},
    {"id": "B", "title": "titolo feature B", "spec": "spec dettagliata per GPT worker 2"},
    {"id": "C", "title": "titolo feature C", "spec": "spec dettagliata per GPT worker 3"}
  ],
  "feedback": "feedback correttivo preciso per GPT (solo se status=fix)",
  "question": "domanda per l'utente (solo se status=ask)",
  "summary": "riepilogo finale (solo se status=done)",
  "gpt_alignment": "valutazione se GPT ha seguito le spec: ok|deviated|partial"
}

REGOLA OBBLIGATORIA — implement_parallel:
Su task hard/hard-mid con 4+ file DEVI usare implement_parallel. MAI implement singolo.
Le dipendenze unidirezionali NON impediscono la parallelizzazione: specifica le interfacce
attese nel chunk dipendente e GPT le implementerà coerentemente.

Usa ESATTAMENTE 3 chunk, sempre:
- Chunk A: fondamenta (config, db, modelli dati, utils condivise)
- Chunk B: logica core (monitor, checker, business logic principale)
- Chunk C: interfacce esterne (API REST, alerter, daemon entry point)

Puoi usare implement_parallel più volte nello stesso task (multi-round):
- Round 1: fondamenta con implement normale se A è prerequisito
- Round 2: 3 chunk paralleli per il resto
- Round 3 se necessario: fix o integrazione

Specifica in ogni chunk quali interfacce/funzioni gli altri chunk devono aspettarsi."""

    user_content = f"""TASK ORIGINALE:
{task}

CONTESTO ATTUALE (iterazione {iteration}):
{context}

Analizza, ragiona e decidi il prossimo passo."""

    full_text = ""
    input_tok = 0
    output_tok = 0

    with client.messages.stream(
        model=model_id,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user_content}]
    ) as stream:
        for text in stream.text_stream:
            full_text += text
            emit(q, "agent_chunk", {"agent": "claude", "text": text})
        final_msg = stream.get_final_message()
        input_tok = final_msg.usage.input_tokens
        output_tok = final_msg.usage.output_tokens

    total = add_cost(session_id, model_id, input_tok, output_tok)

    emit(q, "cost_update", {
        "model_id": model_id,
        "model_label": MODELS[model_id]["label"],
        "provider": "anthropic",
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "call_cost": calc_cost(model_id, input_tok, output_tok)[0],
        "total_cost": total,
    })
    emit(q, "agent_end", {"agent": "claude"})

    def _parse_claude_json(text: str) -> dict:
        """Estrae JSON robusto dalla risposta di Claude, gestendo markdown, testo extra e JSON parziale."""
        import re

        # 1. Prova prima a estrarre da blocco ```json ... ```
        md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if md_match:
            try:
                return json.loads(md_match.group(1))
            except Exception:
                pass

        # 2. Prova a trovare il JSON più lungo (primo { all'ultimo })
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            candidate = text[start:end]
            return json.loads(candidate)
        except Exception:
            pass

        # 3. Cerca tutti i blocchi {...} e prova ognuno dal più lungo al più corto
        candidates = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}", text, re.DOTALL)
        candidates.sort(key=len, reverse=True)
        for cand in candidates:
            try:
                parsed = json.loads(cand)
                if "status" in parsed:
                    return parsed
            except Exception:
                continue

        # 4. Fallback: inferisci lo status dal testo e costruisci JSON sintetico
        text_lower = text.lower()
        if any(w in text_lower for w in ["implementa", "implement", "spec", "specifich"]):
            return {"status": "implement", "thoughts": text, "spec": text, "gpt_alignment": "ok"}
        elif any(w in text_lower for w in ["completato", "done", "finito", "corretto", "funziona"]):
            return {"status": "done", "thoughts": text, "summary": text, "gpt_alignment": "ok"}
        elif any(w in text_lower for w in ["correggi", "fix", "errore", "problema", "manca"]):
            return {"status": "fix", "thoughts": text, "feedback": text, "gpt_alignment": "partial"}
        else:
            return {"status": "implement", "thoughts": text, "spec": text, "gpt_alignment": "ok"}

    return _parse_claude_json(full_text)

# ─────────────────────────────────────────────
# FASE 2 — GPT IMPLEMENTER
# ─────────────────────────────────────────────
def run_implementer(anthropic_client: anthropic.Anthropic, openai_client: openai.OpenAI,
                    session_id: str, task: str, spec: str,
                    feedback: str, iteration: int, model_id: str, q: queue.Queue) -> str:
    """Implementer unificato: usa Claude o GPT a seconda del provider del modello scelto."""

    provider = MODELS.get(model_id, {}).get("provider", "openai")

    # Fallback se modello non disponibile
    if not MODELS.get(model_id, {}).get("available", True):
        fallback = "gpt-4.1" if provider == "openai" else "claude-sonnet-4-6"
        emit(q, "agent_chunk", {"agent": "gpt", "text": f"⚠ {MODELS[model_id]['label']} non disponibile — fallback a {fallback}"})
        model_id = fallback
        provider = MODELS[model_id]["provider"]

    agent_key = "claude" if provider == "anthropic" else "gpt"
    emit(q, "agent_start", {"agent": agent_key, "label": "Implementer", "model": MODELS[model_id]["label"]})

    system = """Sei l'Implementer di Ettorino. Il tuo ruolo è:
1. Implementare ESATTAMENTE le specifiche che ti fornisce il Reasoner
2. NON aggiungere funzionalità non richieste
3. NON omettere nulla di ciò che è nelle spec
4. Scrivere codice pulito, commentato, immediatamente eseguibile
5. Se le spec sono ambigue, implementa la versione più ragionevole e documentala

FORMATO OUTPUT — OBBLIGATORIO:
Se il progetto ha più file, usa SEMPRE questo formato per separare i file:

### FILE: percorso/relativo/file.py
(codice completo del file)

### FILE: altro/file.py
(codice completo)

Esempio:
### FILE: webmon/__init__.py
__version__ = "1.0.0"

### FILE: webmon/config.py
import yaml
...

Se il progetto è un singolo file, scrivi solo il codice Python puro senza intestazione FILE.
Ogni file deve essere COMPLETO e funzionante. Non troncare MAI il codice — se hai bisogno di
molto spazio, produci un file alla volta in modo completo prima di passare al successivo."""

    prompt = f"SPECIFICHE DA IMPLEMENTARE:\n{spec}"
    if feedback:
        prompt += f"\n\nFEEDBACK CORRETTIVO:\n{feedback}\nCorreggi il codice rispettando questo feedback."

    tier = MODELS.get(model_id, {}).get("tier", "medium")
    max_tok_map = {"easy": 4000, "medium": 8000, "hard": 16000, "hard-mid": 12000}
    max_tok = max_tok_map.get(tier, 8000)

    full_code = ""
    truncated = False
    input_tok = estimate_tokens(system + prompt)
    output_tok = 0

    if provider == "anthropic":
        # ── Claude implementer ──────────────────────────────────────────────
        with anthropic_client.messages.stream(
            model=model_id,
            max_tokens=max_tok,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                full_code += text
                emit(q, "agent_chunk", {"agent": agent_key, "text": text})
            final_msg = stream.get_final_message()
            input_tok = final_msg.usage.input_tokens
            output_tok = final_msg.usage.output_tokens
            truncated = (final_msg.stop_reason == "max_tokens")

        # Auto-continuazione se troncato
        MAX_CONTINUATIONS = 3
        cont = 0
        while truncated and cont < MAX_CONTINUATIONS:
            cont += 1
            emit(q, "agent_chunk", {"agent": agent_key, "text": f"\n\n[⚠ output troncato — continuo ({cont}/{MAX_CONTINUATIONS})...]\n"})
            with anthropic_client.messages.stream(
                model=model_id,
                max_tokens=max_tok,
                system=system,
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": full_code},
                    {"role": "user", "content": "Continua esattamente da dove ti sei fermato. Non ripetere il codice già scritto."},
                ]
            ) as cont_stream:
                cont_text = ""
                for text in cont_stream.text_stream:
                    cont_text += text
                    emit(q, "agent_chunk", {"agent": agent_key, "text": text})
                final_cont = cont_stream.get_final_message()
                input_tok += final_cont.usage.input_tokens
                output_tok += final_cont.usage.output_tokens
                truncated = (final_cont.stop_reason == "max_tokens")
            full_code += cont_text

    else:
        # ── OpenAI implementer (logica originale) ───────────────────────────
        if model_id == "o3":
            response = openai_client.chat.completions.create(
                model=model_id,
                max_completion_tokens=max_tok,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ]
            )
            full_code = response.choices[0].message.content or ""
            truncated = (response.choices[0].finish_reason == "length")
            input_tok = response.usage.prompt_tokens
            output_tok = response.usage.completion_tokens
            emit(q, "agent_chunk", {"agent": agent_key, "text": full_code})
        else:
            stream = openai_client.chat.completions.create(
                model=model_id,
                max_tokens=max_tok,
                stream=True,
                stream_options={"include_usage": True},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ]
            )
            last_finish_reason = None
            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content or ""
                    full_code += delta
                    output_tok += 1
                    if delta:
                        emit(q, "agent_chunk", {"agent": agent_key, "text": delta})
                    if chunk.choices[0].finish_reason:
                        last_finish_reason = chunk.choices[0].finish_reason
                if hasattr(chunk, "usage") and chunk.usage:
                    input_tok = chunk.usage.prompt_tokens
                    output_tok = chunk.usage.completion_tokens
            truncated = (last_finish_reason == "length")

        # Auto-continuazione OpenAI
        MAX_CONTINUATIONS = 3
        cont = 0
        while truncated and cont < MAX_CONTINUATIONS:
            cont += 1
            emit(q, "agent_chunk", {"agent": agent_key, "text": f"\n\n[⚠ output troncato — continuo ({cont}/{MAX_CONTINUATIONS})...]\n"})
            cont_messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": full_code},
                {"role": "user", "content": "Continua esattamente da dove ti sei fermato. Non ripetere il codice già scritto."}
            ]
            if model_id == "o3":
                cr = openai_client.chat.completions.create(
                    model=model_id, max_completion_tokens=max_tok, messages=cont_messages)
                full_code += cr.choices[0].message.content or ""
                truncated = (cr.choices[0].finish_reason == "length")
                input_tok += cr.usage.prompt_tokens
                output_tok += cr.usage.completion_tokens
            else:
                cs = openai_client.chat.completions.create(
                    model=model_id, max_tokens=max_tok, stream=True,
                    stream_options={"include_usage": True}, messages=cont_messages)
                cont_text = ""
                last_finish_reason = None
                for cev in cs:
                    if cev.choices:
                        delta = cev.choices[0].delta.content or ""
                        cont_text += delta
                        if delta:
                            emit(q, "agent_chunk", {"agent": agent_key, "text": delta})
                        if cev.choices[0].finish_reason:
                            last_finish_reason = cev.choices[0].finish_reason
                    if hasattr(cev, "usage") and cev.usage:
                        input_tok += cev.usage.prompt_tokens
                        output_tok += cev.usage.completion_tokens
                truncated = (last_finish_reason == "length")
                full_code += cont_text

    if truncated:
        emit(q, "agent_chunk", {"agent": agent_key, "text": "\n\n[⚠ raggiunto limite massimo continuazioni — il codice potrebbe essere incompleto]"})

    total = add_cost(session_id, model_id, input_tok, output_tok)
    emit(q, "cost_update", {
        "model_id": model_id,
        "model_label": MODELS[model_id]["label"],
        "provider": provider,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "call_cost": calc_cost(model_id, input_tok, output_tok)[0],
        "total_cost": total,
    })
    emit(q, "agent_end", {"agent": agent_key})

    # ── Salva output ────────────────────────────────────────────────────────
    import re as _re, time as _t
    words = _re.findall(r"[a-zA-Z]+", task)[:3]
    slug  = "_".join(w.lower() for w in words) or "task"
    proj_dir = WORKSPACE / slug
    proj_dir.mkdir(parents=True, exist_ok=True)

    file_blocks = _re.findall(
        r"###\s*FILE\s*(?:\d+\s*)?[:\-]?\s*([\w./\-]+\.\w+)\s*\n([\s\S]*?)(?=###\s*FILE|$)",
        full_code
    )
    saved_paths = []
    if file_blocks:
        for rel_path, content in file_blocks:
            rel_path = rel_path.strip().lstrip("/")
            dest = proj_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content.strip(), encoding="utf-8")
            saved_paths.append(str(dest))
    else:
        dest = proj_dir / f"v{iteration}.py"
        if dest.exists():
            dest = proj_dir / f"v{iteration}_{int(_t.time()) % 9999}.py"
        dest.write_text(full_code, encoding="utf-8")
        saved_paths.append(str(dest))

    emit(q, "file_saved", {
        "path":       str(proj_dir),
        "files":      saved_paths,
        "multi_file": len(saved_paths) > 1,
        "iteration":  iteration,
    })

    return full_code


# ─────────────────────────────────────────────
# PARALLEL IMPLEMENTATION
# ─────────────────────────────────────────────
def run_implementer_parallel(anthropic_client: anthropic.Anthropic, openai_client: openai.OpenAI,
                             session_id: str, task: str,
                             chunks: list, iteration: int, model_id: str,
                             q: queue.Queue) -> dict:
    """
    Lancia N worker in parallelo (uno per chunk) usando Claude o GPT
    a seconda del provider del modello scelto.
    """
    MAX_WORKERS = 3
    chunk_results = {}
    chunk_errors  = {}
    provider = MODELS.get(model_id, {}).get("provider", "openai")

    shared_context = "\n".join(
        f"- Chunk {ch['id']} ({ch['title']}): implementato da un altro worker in parallelo"
        for ch in chunks
    )

    def run_chunk(chunk):
        cid   = chunk["id"]
        title = chunk["title"]
        spec  = chunk["spec"]

        emit(q, "parallel_chunk_running", {"chunk_id": cid})
        system = (
            "Sei l'Implementer parallelo di Ettorino.\n"
            "Stai implementando UN SOLO chunk di un progetto più grande.\n"
            "Altri worker stanno implementando gli altri chunk in parallelo.\n\n"
            "FORMATO OUTPUT — OBBLIGATORIO:\n"
            "Usa SEMPRE questo formato per ogni file:\n"
            "### FILE: percorso/relativo/file.py\n"
            "(codice completo)\n\n"
            "CONTESTO PROGETTO — gli altri chunk in parallelo:\n"
            + shared_context +
            "\n\nOgni file deve essere COMPLETO. Non troncare mai il codice."
        )
        prompt = f"TASK ORIGINALE: {task}\n\nIL TUO CHUNK — {title}:\n{spec}"

        tier    = MODELS.get(model_id, {}).get("tier", "hard")
        max_tok = {"easy": 4000, "medium": 8000, "hard": 16000, "hard-mid": 12000}.get(tier, 8000)

        full_code = ""
        truncated = False
        input_tok_c = output_tok_c = 0

        try:
            if provider == "anthropic":
                # ── Claude parallel worker ──────────────────────────────────
                with anthropic_client.messages.stream(
                    model=model_id,
                    max_tokens=max_tok,
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    for text in stream.text_stream:
                        full_code += text
                    final_msg = stream.get_final_message()
                    input_tok_c  = final_msg.usage.input_tokens
                    output_tok_c = final_msg.usage.output_tokens
                    truncated    = (final_msg.stop_reason == "max_tokens")

                MAX_CONT = 2
                cont = 0
                while truncated and cont < MAX_CONT:
                    cont += 1
                    emit(q, "parallel_chunk_continuation", {"chunk_id": cid, "attempt": cont})
                    with anthropic_client.messages.stream(
                        model=model_id,
                        max_tokens=max_tok,
                        system=system,
                        messages=[
                            {"role": "user",      "content": prompt},
                            {"role": "assistant", "content": full_code},
                            {"role": "user",      "content": "Continua esattamente da dove ti sei fermato."},
                        ]
                    ) as cs:
                        cont_text = ""
                        for text in cs.text_stream:
                            cont_text += text
                        final_cont = cs.get_final_message()
                        input_tok_c  += final_cont.usage.input_tokens
                        output_tok_c += final_cont.usage.output_tokens
                        truncated     = (final_cont.stop_reason == "max_tokens")
                    full_code += cont_text

            else:
                # ── OpenAI parallel worker ──────────────────────────────────
                if model_id == "o3":
                    resp = openai_client.chat.completions.create(
                        model=model_id,
                        max_completion_tokens=max_tok,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user",   "content": prompt},
                        ]
                    )
                    full_code     = resp.choices[0].message.content or ""
                    truncated     = resp.choices[0].finish_reason == "length"
                    input_tok_c   = resp.usage.prompt_tokens
                    output_tok_c  = resp.usage.completion_tokens
                else:
                    stream = openai_client.chat.completions.create(
                        model=model_id,
                        max_tokens=max_tok,
                        stream=True,
                        stream_options={"include_usage": True},
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user",   "content": prompt},
                        ]
                    )
                last_finish = None
                input_tok_c = output_tok_c = 0
                for chunk_ev in stream:
                    if chunk_ev.choices:
                        delta = chunk_ev.choices[0].delta.content or ""
                        full_code += delta
                        if chunk_ev.choices[0].finish_reason:
                            last_finish = chunk_ev.choices[0].finish_reason
                    if hasattr(chunk_ev, "usage") and chunk_ev.usage:
                        input_tok_c  = chunk_ev.usage.prompt_tokens
                        output_tok_c = chunk_ev.usage.completion_tokens
                truncated = (last_finish == "length")

                # Auto-continuazione OpenAI
                MAX_CONT = 2
                cont = 0
                while truncated and cont < MAX_CONT:
                    cont += 1
                    emit(q, "parallel_chunk_continuation", {"chunk_id": cid, "attempt": cont})
                    cont_msgs = [
                        {"role": "system",    "content": system},
                        {"role": "user",      "content": prompt},
                        {"role": "assistant", "content": full_code},
                        {"role": "user",      "content": "Continua esattamente da dove ti sei fermato."},
                    ]
                    if model_id == "o3":
                        cr = openai_client.chat.completions.create(
                            model=model_id, max_completion_tokens=max_tok, messages=cont_msgs)
                        full_code += cr.choices[0].message.content or ""
                        truncated  = cr.choices[0].finish_reason == "length"
                        input_tok_c  += cr.usage.prompt_tokens
                        output_tok_c += cr.usage.completion_tokens
                    else:
                        cs = openai_client.chat.completions.create(
                            model=model_id, max_tokens=max_tok, stream=True,
                            stream_options={"include_usage": True}, messages=cont_msgs)
                        last_finish = None
                        for cev in cs:
                            if cev.choices:
                                full_code += cev.choices[0].delta.content or ""
                                if cev.choices[0].finish_reason:
                                    last_finish = cev.choices[0].finish_reason
                            if hasattr(cev, "usage") and cev.usage:
                                input_tok_c  += cev.usage.prompt_tokens
                                output_tok_c += cev.usage.completion_tokens
                        truncated = (last_finish == "length")

            add_cost(session_id, model_id, input_tok_c, output_tok_c)
            emit(q, "cost_update", {
                "model_id":    model_id,
                "model_label": MODELS[model_id]["label"],
                "provider":    provider,
                "input_tokens":  input_tok_c,
                "output_tokens": output_tok_c,
                "call_cost":     calc_cost(model_id, input_tok_c, output_tok_c)[0],
                "total_cost":    session_costs[session_id]["total"],
            })
            emit(q, "parallel_chunk_done", {"chunk_id": cid, "title": title, "lines": full_code.count("\n")})
            return cid, full_code, None

        except Exception as e:
            emit(q, "parallel_chunk_error", {"chunk_id": cid, "error": str(e)})
            return cid, "", str(e)

    # Lancia i worker in parallelo (può essere chiamato più volte nel loop)
    # Converti in oggetti Chunk se hanno dipendenze, altrimenti usa flat list
    chunk_objs = [Chunk(id=ch["id"], title=ch["title"], spec=ch["spec"],
                        dependencies=ch.get("dependencies", []),
                        is_critical=ch.get("is_critical", False)) for ch in chunks]

    # Calcola le onde di esecuzione (topological sort)
    try:
        ChunkManager.validate(chunk_objs)
        waves = ChunkManager.execution_waves(chunk_objs)
    except ValueError:
        # Fallback: tutto in una wave unica se ci sono problemi col grafo
        waves = [[ch["id"] for ch in chunks]]

    emit(q, "parallel_start", {
        "chunks": [{"id": ch["id"], "title": ch["title"]} for ch in chunks],
        "workers": min(MAX_WORKERS, len(chunks))
    })
    time.sleep(0.2)

    # Pre-emit tutti i chunk come "waiting" subito
    for ch in chunks:
        emit(q, "parallel_chunk_start", {"chunk_id": ch["id"], "title": ch["title"]})
    time.sleep(0.15)

    # Esegui onda per onda
    for wave in waves:
        wave_chunks = [ch for ch in chunks if ch["id"] in wave]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(run_chunk, ch): ch["id"] for ch in wave_chunks}
            for future in as_completed(futures):
                cid, code, err = future.result()
                if err:
                    chunk_errors[cid] = err
                    # Se critico, interrompi
                    chunk_obj = next((c for c in chunk_objs if c.id == cid), None)
                    if chunk_obj and chunk_obj.is_critical:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                else:
                    chunk_results[cid] = code

    emit(q, "parallel_end", {
        "completed": list(chunk_results.keys()),
        "failed":    list(chunk_errors.keys()),
    })

    # Salva i file di ogni chunk nel workspace
    import re as _re
    words = _re.findall(r"[a-zA-Z]+", task)[:3]
    slug  = "_".join(w.lower() for w in words) or "task"
    proj_dir = WORKSPACE / slug
    proj_dir.mkdir(parents=True, exist_ok=True)

    all_saved = []
    for cid in sorted(chunk_results.keys()):
        chunk_code = chunk_results[cid]
        # Try multiple FILE header patterns GPT might use
        file_blocks = _re.findall(
            r"###\s*FILE\s*(?:\d+\s*)?[:\-]?\s*([\w./\-]+\.\w+)\s*\n([\s\S]*?)(?=###\s*FILE|$)",
            chunk_code
        )
        if not file_blocks:
            # Try without the \n separator (some models don't add newline)
            file_blocks = _re.findall(
                r"###\s*FILE\s*(?:\d+\s*)?[:\-]?\s*([\w./\-]+\.\w+)\s*([\s\S]*?)(?=###\s*FILE|$)",
                chunk_code
            )
        if file_blocks:
            for rel_path, content in file_blocks:
                dest = proj_dir / rel_path.strip().lstrip("/")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content.strip(), encoding="utf-8")
                all_saved.append(str(dest))
        else:
            dest = proj_dir / f"chunk_{cid}_v{iteration}.py"
            dest.write_text(chunk_code, encoding="utf-8")
            all_saved.append(str(dest))

    if all_saved:
        emit(q, "file_saved", {
            "path": str(proj_dir),
            "files": all_saved,
            "multi_file": len(all_saved) > 1,
            "iteration": iteration,
        })

    return chunk_results

def get_project_files_summary(task: str, include_content: bool = True, max_file_bytes: int = 8000) -> str:
    """
    Restituisce l'elenco dei file nel workspace + contenuto per file piccoli.
    Claude può così verificare il codice senza chiedere all'utente.
    """
    import re as _re
    words = _re.findall(r"[a-zA-Z]+", task)[:3]
    slug = "_".join(w.lower() for w in words) or "task"
    proj_dir = WORKSPACE / slug
    if not proj_dir.exists():
        return ""
    files = sorted(f for f in proj_dir.rglob("*") if f.is_file())
    if not files:
        return ""

    lines = [f"\n\nFILE GIÀ PRESENTI NEL WORKSPACE ({proj_dir}) — NON chiedere questi file all'utente:"]
    text_exts = {".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml",
                 ".toml", ".txt", ".md", ".sh", ".env", ".cfg", ".ini", ".xml"}

    for f in files:
        rel = str(f.relative_to(proj_dir))
        size = f.stat().st_size
        if include_content and f.suffix.lower() in text_exts and size <= max_file_bytes:
            try:
                content = f.read_text(encoding="utf-8")
                lines.append(f"\n### FILE: {rel} ({size} bytes)\n```\n{content}\n```")
            except Exception:
                lines.append(f"  - {rel} ({size} bytes) [errore lettura]")
        else:
            lines.append(f"  - {rel} ({size} bytes){' [troppo grande per mostrare]' if size > max_file_bytes else ''}")

    return "\n".join(lines)

# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
def run_agent_loop(session_id: str, task: str, q: queue.Queue):
    try:
        claude_client = get_anthropic_client()
        openai_client = get_openai_client()
    except ValueError as e:
        emit(q, "error", {"message": str(e)})
        return

    session_costs[session_id] = {"total": 0.0, "by_model": {}}
    emit(q, "loop_start", {"task": task})

    # ── FASE 0: classifica ──────────────────────
    classification = classify_task(claude_client, session_id, task, q)

    difficulty             = classification.get("difficulty", "medium")
    suggested_reasoner     = classification.get("suggested_reasoner", TIER_MODELS["medium"]["reasoner"])
    suggested_implementer  = classification.get("suggested_implementer", TIER_MODELS["medium"]["implementer"])
    needs_clarification    = classification.get("needs_clarification", False)
    clarification_question = classification.get("clarification_question")
    est_cost               = classification.get("estimated_cost_usd", 0.0)
    reasoning              = classification.get("reasoning", "")
    model_rationale        = classification.get("model_rationale", "")
    complexity_factors     = classification.get("complexity_factors", [])

    # Se ha dubbi sul task → chiede prima di proporre i modelli
    if needs_clarification and clarification_question:
        emit(q, "waiting_human", {
            "question": clarification_question,
            "session_id": session_id,
            "context": "clarification"
        })
        clarification = wait_for_human(session_id, timeout=300)
        if clarification is None:
            emit(q, "timeout", {})
            return
        emit(q, "human_response", {"text": clarification})
        # Riclassifica con il chiarimento
        task = f"{task}\n\nChiarimento dell'utente: {clarification}"
        classification = classify_task(claude_client, session_id, task, q, silent=True)
        difficulty             = classification.get("difficulty", "medium")
        suggested_reasoner     = classification.get("suggested_reasoner", TIER_MODELS[difficulty]["reasoner"])
        suggested_implementer  = classification.get("suggested_implementer", TIER_MODELS[difficulty]["implementer"])
        est_cost               = classification.get("estimated_cost_usd", 0.0)
        reasoning              = classification.get("reasoning", "")
        model_rationale        = classification.get("model_rationale", "")

    # ── CONFERMA MODELLI ───────────────────────
    # Applica eventuali override utente
    override = model_overrides.get(session_id, {})
    reasoner_model    = override.get("reasoner", suggested_reasoner)
    implementer_model = override.get("implementer", suggested_implementer)

    emit(q, "confirm_models", {
        "session_id":         session_id,
        "difficulty":         difficulty,
        "reasoning":          reasoning,
        "model_rationale":    model_rationale,
        "complexity_factors": complexity_factors,
        "reasoner_model":     reasoner_model,
        "reasoner_label":     MODELS[reasoner_model]["label"],
        "implementer_model":  implementer_model,
        "implementer_label":  MODELS[implementer_model]["label"],
        "estimated_cost":     est_cost,
        "available_reasoners": [
            {"id": k, "label": v["label"], "tier": v["tier"]}
            for k, v in MODELS.items() if "reasoner" in v["role"]
        ],
        "available_implementers": [
            {"id": k, "label": v["label"], "tier": v["tier"], "provider": v["provider"]}
            for k, v in MODELS.items() if "implementer" in v["role"]
        ],
    })

    # Aspetta conferma o cambio modelli
    confirmation = wait_for_human(session_id, timeout=600)
    if confirmation is None:
        emit(q, "timeout", {})
        return

    try:
        conf_data = json.loads(confirmation)
        if conf_data.get("action") == "change":
            reasoner_model    = conf_data.get("reasoner", reasoner_model)
            implementer_model = conf_data.get("implementer", implementer_model)
            emit(q, "models_updated", {
                "reasoner_label":    MODELS[reasoner_model]["label"],
                "implementer_label": MODELS[implementer_model]["label"],
            })
        # se action == "confirm" procediamo con i modelli scelti
    except Exception:
        pass  # risposta non JSON → procedi con i modelli suggeriti

    # ── LOOP PRINCIPALE ────────────────────────
    context = "Nessun codice ancora prodotto. Prima iterazione."
    code = ""
    feedback = ""
    iteration = 0
    max_iterations = int(os.environ.get("MAX_ITERATIONS", 10))

    while iteration < max_iterations:
        iteration += 1
        emit(q, "iteration_start", {"n": iteration, "max": max_iterations})

        # Check if user requested stop
        if stop_flags.get(session_id):
            stop_flags.pop(session_id, None)
            emit(q, "loop_end", {"success": False, "summary": "Interrotto dall'utente.",
                                  "iterations": iteration, "total_cost": session_costs.get(session_id, {}).get("total", 0),
                                  "by_model": session_costs.get(session_id, {}).get("by_model", {})})
            return

        # Claude ragiona
        result = claude_reason(claude_client, session_id, task, context,
                               reasoner_model, iteration, q)
        status = result.get("status", "ask")
        alignment = result.get("gpt_alignment", "ok")

        emit(q, "claude_result", {
            "status":    status,
            "thoughts":  result.get("thoughts", ""),
            "alignment": alignment,
            "iteration": iteration,
        })

        if status == "done":
            total = session_costs[session_id]["total"]
            # salva stato per eventuale continuazione
            session_state[session_id] = {
                "code": code, "task": task,
                "reasoner": reasoner_model, "implementer": implementer_model,
                "iteration": iteration,
            }
            emit(q, "loop_end", {
                "success":    True,
                "summary":    result.get("summary", ""),
                "iterations": iteration,
                "total_cost": total,
                "by_model":   session_costs[session_id]["by_model"],
            })
            return

        elif status == "ask":
            emit(q, "waiting_human", {
                "question":   result.get("question", ""),
                "session_id": session_id,
                "context":    "loop",
            })
            human_resp = wait_for_human(session_id, timeout=int(os.environ.get("HUMAN_TIMEOUT", 300)))
            if human_resp is None:
                emit(q, "timeout", {})
                return
            emit(q, "human_response", {"text": human_resp})
            context = f"Codice attuale:\n{code}\n\nRisposta utente: {human_resp}"

        elif status == "implement":
            spec = result.get("spec", "")
            emit(q, "spec_ready", {"spec": spec})
            code = run_implementer(claude_client, openai_client, session_id, task, spec, "",
                                 iteration, implementer_model, q)
            context = (f"Codice prodotto (iterazione {iteration}):\n```python\n{code}\n```\n"
                       "Verifica correttezza e completezza rispetto al task originale."
                       + get_project_files_summary(task))

        elif status == "implement_parallel":
            chunks_raw = result.get("parallel_chunks", [])
            chunk_results = {}
            if not chunks_raw or len(chunks_raw) < 2:
                # fallback a implement normale se chunks mancanti
                spec = result.get("spec", "") or "Implementa il task come specificato."
                emit(q, "spec_ready", {"spec": spec})
                code = run_implementer(claude_client, openai_client, session_id, task, spec, "",
                                     iteration, implementer_model, q)
                context = (f"Codice prodotto (iterazione {iteration}):\n```python\n{code}\n```\n"
                           "Verifica correttezza e completezza rispetto al task originale."
                           + get_project_files_summary(task))
            else:
                raw_results = run_implementer_parallel(
                    claude_client, openai_client, session_id, task, chunks_raw, iteration, implementer_model, q
                )
                # Converti in ChunkResult per build_review_context
                from dataclasses import fields as dc_fields
                chunk_results = {cid: ChunkResult(chunk_id=cid, code=code_str)
                                 for cid, code_str in raw_results.items()}
                code = ChunkManager.combine_code(chunk_results)
                context = ChunkManager.build_review_context(chunk_results, iteration) + get_project_files_summary(task)

        elif status == "fix":
            feedback = result.get("feedback", "")
            if alignment == "deviated":
                emit(q, "gpt_realignment", {"feedback": feedback})
            else:
                emit(q, "fix_needed", {"feedback": feedback})
            code = run_implementer(claude_client, openai_client, session_id, task,
                                 f"Correggi il codice:\n\nCODICE:\n{code}",
                                 feedback, iteration, implementer_model, q)
            context = (f"Codice corretto (iterazione {iteration}):\n```python\n{code}\n```\n"
                       "Verifica di nuovo."
                       + get_project_files_summary(task))

    # Max iterazioni raggiunto
    total = session_costs[session_id]["total"]
    emit(q, "loop_end", {
        "success":    False,
        "summary":    f"Raggiunto limite di {max_iterations} iterazioni.",
        "iterations": iteration,
        "total_cost": total,
        "by_model":   session_costs[session_id]["by_model"],
    })


def continue_agent_loop(session_id: str, followup: str, q: queue.Queue):
    """Riprende il loop: riclassifica il followup, propone modelli, poi esegue."""
    state = session_state.get(session_id, {})
    code = state.get("code", "")
    task = state.get("task", "")
    prev_reasoner = state.get("reasoner", TIER_MODELS["medium"]["reasoner"])
    prev_implementer = state.get("implementer", TIER_MODELS["medium"]["implementer"])
    iteration = state.get("iteration", 0)

    try:
        claude_client = get_anthropic_client()
        openai_client = get_openai_client()
    except ValueError as e:
        emit(q, "error", {"message": str(e)})
        return

    combined_task = f"{task} | {followup}"
    emit(q, "loop_start", {"task": f"[Continuazione] {followup}"})

    # ── FASE 0: riclassifica il followup tenendo conto del codice esistente ──
    classify_input = (
        f"TASK ORIGINALE: {task}\n\n"
        f"CODICE GIÀ PRODOTTO ({len(code)} chars):\n```python\n{code[:800]}{'...' if len(code)>800 else ''}\n```\n\n"
        f"RICHIESTA DI CONTINUAZIONE: {followup}\n\n"
        f"Valuta la difficoltà di questa modifica/aggiunta rispetto al codice esistente."
    )
    classification = classify_task(claude_client, session_id, classify_input, q)

    difficulty            = classification.get("difficulty", "medium")
    suggested_reasoner    = classification.get("suggested_reasoner", prev_reasoner)
    suggested_implementer = classification.get("suggested_implementer", prev_implementer)
    needs_clarification   = classification.get("needs_clarification", False)
    clarification_q       = classification.get("clarification_question")
    est_cost              = classification.get("estimated_cost_usd", 0.0)
    reasoning             = classification.get("reasoning", "")
    model_rationale       = classification.get("model_rationale", "")
    complexity_factors    = classification.get("complexity_factors", [])

    # Chiarimento se necessario
    if needs_clarification and clarification_q:
        emit(q, "waiting_human", {"question": clarification_q, "session_id": session_id, "context": "clarification"})
        clarification = wait_for_human(session_id, timeout=300)
        if clarification is None:
            emit(q, "timeout", {})
            return
        emit(q, "human_response", {"text": clarification})
        combined_task += f" | Chiarimento: {clarification}"

    # ── CONFERMA MODELLI ──────────────────────────────────────────────────────
    override = model_overrides.get(session_id, {})
    reasoner_model    = override.get("reasoner", suggested_reasoner)
    implementer_model = override.get("implementer", suggested_implementer)

    emit(q, "confirm_models", {
        "session_id":         session_id,
        "difficulty":         difficulty,
        "reasoning":          reasoning,
        "model_rationale":    model_rationale,
        "complexity_factors": complexity_factors,
        "reasoner_model":     reasoner_model,
        "reasoner_label":     MODELS[reasoner_model]["label"],
        "implementer_model":  implementer_model,
        "implementer_label":  MODELS[implementer_model]["label"],
        "estimated_cost":     est_cost,
        "available_reasoners": [
            {"id": k, "label": v["label"], "tier": v["tier"], "available": v.get("available", True)}
            for k, v in MODELS.items() if "reasoner" in v["role"]
        ],
        "available_implementers": [
            {"id": k, "label": v["label"], "tier": v["tier"], "provider": v["provider"], "available": v.get("available", True)}
            for k, v in MODELS.items() if "implementer" in v["role"]
        ],
    })

    confirmation = wait_for_human(session_id, timeout=600)
    if confirmation is None:
        emit(q, "timeout", {})
        return

    try:
        conf_data = json.loads(confirmation)
        if conf_data.get("action") == "change":
            reasoner_model    = conf_data.get("reasoner", reasoner_model)
            implementer_model = conf_data.get("implementer", implementer_model)
            emit(q, "models_updated", {
                "reasoner_label":    MODELS[reasoner_model]["label"],
                "implementer_label": MODELS[implementer_model]["label"],
            })
    except Exception:
        pass

    # ── LOOP PRINCIPALE ──────────────────────────────────────────────────────
    context = (
        f"CODICE PRODOTTO FINORA:\n```python\n{code}\n```\n\n"
        f"TASK ORIGINALE: {task}\n\n"
        f"RICHIESTA DI CONTINUAZIONE: {followup}\n\n"
        f"Analizza il codice esistente e produci le specifiche per la modifica richiesta."
    )
    max_iterations = int(os.environ.get("MAX_ITERATIONS", 10))
    start_iter = iteration

    while iteration < start_iter + max_iterations:
        iteration += 1
        emit(q, "iteration_start", {"n": iteration, "max": start_iter + max_iterations})

        # Check if user requested stop
        if stop_flags.get(session_id):
            stop_flags.pop(session_id, None)
            emit(q, "loop_end", {"success": False, "summary": "Interrotto dall'utente.",
                                  "iterations": iteration, "total_cost": session_costs.get(session_id, {}).get("total", 0),
                                  "by_model": session_costs.get(session_id, {}).get("by_model", {})})
            return

        result = claude_reason(claude_client, session_id, combined_task, context,
                               reasoner_model, iteration, q)
        status = result.get("status", "ask")
        alignment = result.get("gpt_alignment", "ok")

        emit(q, "claude_result", {"status": status, "thoughts": result.get("thoughts", ""),
                                  "alignment": alignment, "iteration": iteration})

        if status == "done":
            total = session_costs[session_id]["total"]
            session_state[session_id] = {
                "code": code, "task": combined_task,
                "reasoner": reasoner_model, "implementer": implementer_model,
                "iteration": iteration,
            }
            emit(q, "loop_end", {
                "success": True, "summary": result.get("summary", ""),
                "iterations": iteration, "total_cost": total,
                "by_model": session_costs[session_id]["by_model"],
            })
            return

        elif status == "ask":
            emit(q, "waiting_human", {"question": result.get("question", ""),
                                       "session_id": session_id, "context": "loop"})
            human_resp = wait_for_human(session_id, timeout=int(os.environ.get("HUMAN_TIMEOUT", 300)))
            if human_resp is None:
                emit(q, "timeout", {})
                return
            emit(q, "human_response", {"text": human_resp})
            context = f"Codice attuale:\n{code}\n\nRisposta utente: {human_resp}"

        elif status == "implement":
            spec = result.get("spec", "")
            emit(q, "spec_ready", {"spec": spec})
            code = run_implementer(claude_client, openai_client, session_id, combined_task, spec, "",
                                 iteration, implementer_model, q)
            context = (f"Codice aggiornato (iterazione {iteration}):\n```python\n{code}\n```\n"
                       "Verifica correttezza e completezza rispetto a task + continuazione."
                       + get_project_files_summary(task))

        elif status == "fix":
            feedback = result.get("feedback", "")
            if alignment == "deviated":
                emit(q, "gpt_realignment", {"feedback": feedback})
            else:
                emit(q, "fix_needed", {"feedback": feedback})
            code = run_implementer(claude_client, openai_client, session_id, combined_task,
                                 f"Correggi il codice:\n\nCODICE:\n{code}",
                                 feedback, iteration, implementer_model, q)
            context = (f"Codice corretto (iterazione {iteration}):\n```python\n{code}\n```\n"
                       "Verifica di nuovo."
                       + get_project_files_summary(task))

    total = session_costs[session_id]["total"]
    emit(q, "loop_end", {
        "success": False, "summary": "Raggiunto limite iterazioni.",
        "iterations": iteration, "total_cost": total,
        "by_model": session_costs[session_id]["by_model"],
    })

# ─────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    version = os.environ.get("ETTORINO_VERSION", "dev")
    return render_template("index.html", version=version)

@app.route("/run", methods=["POST"])
def run():
    data    = request.json or {}
    task    = (data.get("task") or "").strip()
    session_id = data.get("session_id") or f"s{int(time.time()*1000)}"
    if not task:
        return jsonify({"error": "task vuoto"}), 400

    q = queue.Queue()
    event_queues[session_id] = q

    thread = threading.Thread(target=run_agent_loop, args=(session_id, task, q), daemon=True)
    thread.start()

    return jsonify({"session_id": session_id})

@app.route("/stream/<session_id>")
def stream(session_id):
    q = event_queues.get(session_id)
    if not q:
        return "Session not found", 404

    def generate():
        while True:
            try:
                event = q.get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
                if event["type"] in ("loop_end", "error", "timeout"):
                    break
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/respond/<session_id>", methods=["POST"])
def respond(session_id):
    data = request.json or {}
    human_responses[session_id] = data.get("response", "")
    return jsonify({"ok": True})

@app.route("/continue", methods=["POST"])
def continue_run():
    data = request.json or {}
    session_id = data.get("session_id", "").strip()
    followup = (data.get("followup") or "").strip()
    if not session_id or not followup:
        return jsonify({"error": "session_id o followup mancante"}), 400
    if session_id not in session_state:
        return jsonify({"error": "sessione non trovata o già scaduta"}), 404

    q = queue.Queue()
    event_queues[session_id] = q

    thread = threading.Thread(target=continue_agent_loop, args=(session_id, followup, q), daemon=True)
    thread.start()

    return jsonify({"session_id": session_id})

@app.route("/stop/<session_id>", methods=["POST"])
def stop(session_id):
    stop_flags[session_id] = True
    # also push a sentinel to unblock any wait_for_human
    human_responses[session_id] = "__stop__"
    return jsonify({"ok": True})

@app.route("/download")
def download():
    """Serve la cartella del progetto come ZIP scaricabile."""
    import zipfile, io
    path_str = request.args.get("path", "").strip()
    if not path_str:
        return "path mancante", 400
    proj_path = Path(path_str)
    if not proj_path.exists() or not proj_path.is_dir():
        # Try as relative to WORKSPACE
        proj_path = WORKSPACE / path_str
    if not proj_path.exists():
        return "path non trovato", 404
    # Security check: must be inside WORKSPACE
    try:
        proj_path.resolve().relative_to(WORKSPACE.resolve())
    except ValueError:
        return "path non autorizzato", 403

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in proj_path.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(proj_path.parent))
    buf.seek(0)
    zip_name = proj_path.name + ".zip"
    from flask import send_file
    return send_file(buf, mimetype="application/zip",
                     as_attachment=True, download_name=zip_name)

@app.route("/file_content")
def file_content():
    """Restituisce il contenuto testuale di un file nel workspace."""
    path_str = request.args.get("path", "").strip()
    if not path_str:
        return jsonify({"error": "path mancante"}), 400
    file_path = Path(path_str)
    # Security: must be inside WORKSPACE
    try:
        file_path.resolve().relative_to(WORKSPACE.resolve())
    except ValueError:
        return jsonify({"error": "path non autorizzato"}), 403
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"error": "file non trovato"}), 404
    try:
        content = file_path.read_text(encoding="utf-8")
        return jsonify({"content": content, "filename": file_path.name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models")
def models():
    return jsonify(MODELS)

if __name__ == "__main__":
    port  = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug, port=port, threaded=True, use_reloader=False)