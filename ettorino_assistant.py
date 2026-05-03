import os
import json
import time
import threading
import queue
from pathlib import Path
from flask import Flask, render_template, request, Response, jsonify
import anthropic
import openai

# Carica variabili da .env se presente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv non installato, usa variabili d'ambiente di sistema

app = Flask(__name__)

WORKSPACE = Path("workspace")
WORKSPACE.mkdir(exist_ok=True)

event_queues = {}

# ─────────────────────────────────────────────
# MODEL REGISTRY  (aggiorna prezzi qui se cambiano)
# prezzi in $ per milione di token
# ─────────────────────────────────────────────
MODELS = {
    "claude-haiku-4-5-20251001": {
        "provider": "anthropic", "label": "Claude Haiku 4.5",
        "tier": "easy", "input_cost": 0.80, "output_cost": 4.00,
    },
    "gpt-4o-mini": {
        "provider": "openai", "label": "GPT-4o mini",
        "tier": "easy", "input_cost": 0.15, "output_cost": 0.60,
    },
    "claude-sonnet-4-5-20251001": {
        "provider": "anthropic", "label": "Claude Sonnet 4.5",
        "tier": "medium", "input_cost": 3.00, "output_cost": 15.00,
    },
    "gpt-4o": {
        "provider": "openai", "label": "GPT-4o",
        "tier": "medium", "input_cost": 2.50, "output_cost": 10.00,
    },
    "claude-opus-4-5-20251001": {
        "provider": "anthropic", "label": "Claude Opus 4.5",
        "tier": "hard", "input_cost": 15.00, "output_cost": 75.00,
    },
    "o3": {
        "provider": "openai", "label": "o3",
        "tier": "hard", "input_cost": 10.00, "output_cost": 40.00,
    },
}

TIER_DEFAULTS = {
    "easy":   {"reasoner": "claude-haiku-4-5-20251001",   "implementer": "gpt-4o-mini"},
    "medium": {"reasoner": "claude-sonnet-4-5-20251001",  "implementer": "gpt-4o"},
    "hard":   {"reasoner": "claude-opus-4-5-20251001",    "implementer": "o3"},
}

TIER_LABELS = {
    "easy":   "🟢 FACILE",
    "medium": "🟡 MEDIO",
    "hard":   "🔴 DIFFICILE",
}

session_costs = {}

def calc_cost(model_id, input_tokens, output_tokens):
    m = MODELS.get(model_id, {})
    return (input_tokens / 1_000_000) * m.get("input_cost", 0) + \
           (output_tokens / 1_000_000) * m.get("output_cost", 0)

def add_cost(session_id, model_id, input_tokens, output_tokens):
    cost = calc_cost(model_id, input_tokens, output_tokens)
    if session_id not in session_costs:
        session_costs[session_id] = {"total": 0.0, "calls": []}
    session_costs[session_id]["total"] += cost
    session_costs[session_id]["calls"].append({
        "model": MODELS.get(model_id, {}).get("label", model_id),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost
    })
    return session_costs[session_id]["total"]

def estimate_tokens(text):
    return max(1, len(text) // 4)

def emit(q, event_type, data):
    q.put({"type": event_type, "data": data})

def get_anthropic_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY non trovata")
    return anthropic.Anthropic(api_key=key)

def get_openai_client():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY non trovata")
    return openai.OpenAI(api_key=key)

# ─────────────────────────────────────────────
# STEP 0: CLASSIFIER  (usa sempre Haiku — economico)
# ─────────────────────────────────────────────
def classify_task(client, session_id, task, q):
    emit(q, "classifying", {"message": "Analisi difficoltà del task..."})

    system = """Sei un esperto di architettura software. Analizza il task e rispondi SOLO con JSON valido, nessun testo fuori.

Criteri:
- easy: script semplici, utility, <100 righe, logica lineare
- medium: app con più componenti, API integration, 100-500 righe
- hard: sistemi complessi, algoritmi avanzati, ML/AI, architetture distribuite, >500 righe o alta ambiguità

Risposta JSON:
{
  "difficulty": "easy" | "medium" | "hard",
  "confidence": 0.0-1.0,
  "reasoning": "spiegazione breve",
  "estimated_input_tokens": number,
  "estimated_output_tokens": number,
  "needs_clarification": true | false,
  "clarification_question": "domanda oppure null",
  "complexity_factors": ["fattore1", ...]
}

Stima token: input tipicamente 500-2000, output tipicamente 500-5000 a seconda della complessità."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=system,
        messages=[{"role": "user", "content": f"Classifica:\n\n{task}"}]
    )

    raw = response.content[0].text
    in_tok = response.usage.input_tokens
    out_tok = response.usage.output_tokens
    total = add_cost(session_id, "claude-haiku-4-5-20251001", in_tok, out_tok)

    emit(q, "cost_update", {
        "model_label": "Claude Haiku 4.5",
        "input_tokens": in_tok, "output_tokens": out_tok,
        "call_cost": calc_cost("claude-haiku-4-5-20251001", in_tok, out_tok),
        "total_cost": total, "phase": "classifier"
    })

    try:
        clean = raw.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except Exception:
        return {
            "difficulty": "medium", "confidence": 0.5,
            "reasoning": "Classificazione fallita, uso tier medio",
            "estimated_input_tokens": 1000, "estimated_output_tokens": 2000,
            "needs_clarification": False, "clarification_question": None,
            "complexity_factors": []
        }

# ─────────────────────────────────────────────
# STEP 1: REASONER
# ─────────────────────────────────────────────
def claude_reason(client, session_id, task, context, model_id, q):
    emit(q, "agent_start", {
        "agent": "claude", "phase": "reasoning",
        "model": MODELS[model_id]["label"]
    })

    system = """Sei un architetto software senior. Ragiona e produci specifiche tecniche.

Rispondi SOLO con JSON valido:
{
  "status": "implement" | "fix" | "ask" | "done",
  "thoughts": "ragionamento passo per passo",
  "spec": "specifiche tecniche dettagliate (solo se implement)",
  "feedback": "problemi trovati nel codice (solo se fix)",
  "question": "domanda per l'utente (solo se ask)",
  "summary": "cosa è stato fatto (solo se done)"
}"""

    full_response = ""

    with client.messages.stream(
        model=model_id,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": f"TASK:\n{task}\n\nCONTESTO:\n{context}"}]
    ) as stream:
        for text in stream.text_stream:
            full_response += text
            emit(q, "claude_chunk", {"text": text})
        final = stream.get_final_message()
        in_tok = final.usage.input_tokens
        out_tok = final.usage.output_tokens

    total = add_cost(session_id, model_id, in_tok, out_tok)
    emit(q, "agent_end", {"agent": "claude"})
    emit(q, "cost_update", {
        "model_label": MODELS[model_id]["label"],
        "input_tokens": in_tok, "output_tokens": out_tok,
        "call_cost": calc_cost(model_id, in_tok, out_tok),
        "total_cost": total, "phase": "reasoning"
    })

    try:
        clean = full_response.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except Exception:
        return {"status": "ask", "thoughts": full_response,
                "question": "Errore nel formato. Puoi riformulare il task?"}

# ─────────────────────────────────────────────
# STEP 2: IMPLEMENTER
# ─────────────────────────────────────────────
def implement_code(openai_client, session_id, spec, feedback, iteration, model_id, q):
    emit(q, "agent_start", {
        "agent": "codex", "phase": "implementing",
        "model": MODELS[model_id]["label"]
    })

    system = """Sei un ingegnere software esperto. Scrivi codice pulito, funzionale, ben commentato.
Rispondi con SOLO il codice. Usa commenti per spiegare scelte architetturali importanti.
Codice production-ready: gestione errori, edge cases, leggibilità."""

    user_content = f"SPECIFICHE:\n{spec}"
    if feedback:
        user_content += f"\n\nFEEDBACK DA CORREGGERE:\n{feedback}"
    if iteration > 1:
        user_content += f"\n\n[Iterazione #{iteration}]"

    full_code = ""
    in_tok = estimate_tokens(system + user_content)
    out_tok = 0

    try:
        response = openai_client.chat.completions.create(
            model=model_id,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user_content}],
            stream=True
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_code += delta
                emit(q, "codex_chunk", {"text": delta})
        out_tok = estimate_tokens(full_code)
    except Exception:
        # fallback non-streaming
        response = openai_client.chat.completions.create(
            model=model_id,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user_content}]
        )
        full_code = response.choices[0].message.content or ""
        in_tok = response.usage.prompt_tokens
        out_tok = response.usage.completion_tokens
        emit(q, "codex_chunk", {"text": full_code})

    total = add_cost(session_id, model_id, in_tok, out_tok)
    filename = WORKSPACE / f"iteration_{iteration}.py"
    filename.write_text(full_code, encoding="utf-8")
    emit(q, "file_saved", {"path": str(filename)})
    emit(q, "agent_end", {"agent": "codex"})
    emit(q, "cost_update", {
        "model_label": MODELS[model_id]["label"],
        "input_tokens": in_tok, "output_tokens": out_tok,
        "call_cost": calc_cost(model_id, in_tok, out_tok),
        "total_cost": total, "phase": "implementation"
    })
    return full_code

# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def run_agent_loop(session_id, task, q):
    try:
        claude_client = get_anthropic_client()
        openai_client = get_openai_client()
    except ValueError as e:
        emit(q, "error", {"message": str(e)})
        emit(q, "loop_end", {})
        return

    session_costs[session_id] = {"total": 0.0, "calls": []}
    emit(q, "loop_start", {"task": task})

    # ── FASE 0: classifica ──────────────────────
    cl = classify_task(claude_client, session_id, task, q)
    difficulty      = cl.get("difficulty", "medium")
    confidence      = cl.get("confidence", 0.5)
    reasoning_cl    = cl.get("reasoning", "")
    est_in          = cl.get("estimated_input_tokens", 1000)
    est_out         = cl.get("estimated_output_tokens", 2000)
    needs_q         = cl.get("needs_clarification", False)
    clarification_q = cl.get("clarification_question")
    factors         = cl.get("complexity_factors", [])

    tier             = TIER_DEFAULTS[difficulty]
    reasoner_model   = tier["reasoner"]
    implementer_model= tier["implementer"]

    avg_iters = {"easy": 1, "medium": 2, "hard": 3}[difficulty]
    estimated_cost = (
        calc_cost(reasoner_model, est_in, est_out) +
        calc_cost(implementer_model, est_in, est_out)
    ) * avg_iters

    emit(q, "classification_result", {
        "difficulty": difficulty,
        "confidence": confidence,
        "reasoning": reasoning_cl,
        "complexity_factors": factors,
        "reasoner_model": reasoner_model,
        "reasoner_label": MODELS[reasoner_model]["label"],
        "implementer_model": implementer_model,
        "implementer_label": MODELS[implementer_model]["label"],
        "estimated_input_tokens": est_in,
        "estimated_output_tokens": est_out,
        "estimated_cost": estimated_cost,
        "tier_label": TIER_LABELS[difficulty],
        "avg_iterations": avg_iters
    })

    # ── FASE 0b: chiarimento pre-flight ─────────
    if needs_q and clarification_q:
        emit(q, "waiting_human", {
            "question": f"[Pre-flight] {clarification_q}",
            "session_id": session_id
        })
        answer = wait_for_human(session_id, timeout=int(os.environ.get("HUMAN_TIMEOUT", 300)))
        if answer is None:
            emit(q, "timeout", {})
            return
        emit(q, "human_response", {"text": answer})
        task = f"{task}\n\nCHIARIMENTO: {answer}"

    # ── LOOP PRINCIPALE ─────────────────────────
    context = "Nessun codice ancora prodotto."
    code = ""
    feedback = ""
    iteration = 0
    max_iterations = int(os.environ.get("MAX_ITERATIONS", 10))

    while iteration < max_iterations:
        iteration += 1
        emit(q, "iteration", {"n": iteration})

        result = claude_reason(claude_client, session_id, task, context, reasoner_model, q)
        status = result.get("status", "ask")

        emit(q, "claude_result", {
            "status": status,
            "thoughts": result.get("thoughts", ""),
            "iteration": iteration
        })

        if status == "done":
            total = session_costs[session_id]["total"]
            emit(q, "loop_end", {
                "success": True,
                "summary": result.get("summary", ""),
                "iterations": iteration,
                "total_cost": total,
                "calls": session_costs[session_id]["calls"]
            })
            break

        elif status == "ask":
            emit(q, "waiting_human", {
                "question": result.get("question", ""),
                "session_id": session_id
            })
            answer = wait_for_human(session_id, timeout=int(os.environ.get("HUMAN_TIMEOUT", 300)))
            if answer is None:
                emit(q, "timeout", {})
                break
            emit(q, "human_response", {"text": answer})
            context = f"Codice: {code}\nRisposta: {answer}"

        elif status == "implement":
            spec = result.get("spec", "")
            emit(q, "spec_ready", {"spec": spec})
            code = implement_code(openai_client, session_id, spec, feedback, iteration, implementer_model, q)
            feedback = ""
            context = f"Codice iterazione {iteration}:\n```python\n{code}\n```\nVerifica correttezza."

        elif status == "fix":
            feedback = result.get("feedback", "")
            emit(q, "fix_needed", {"feedback": feedback})
            code = implement_code(openai_client, session_id,
                                  f"Correggi:\n\nCODICE:\n{code}",
                                  feedback, iteration, implementer_model, q)
            context = f"Codice corretto iterazione {iteration}:\n```python\n{code}\n```\nVerifica."

    if iteration >= max_iterations:
        total = session_costs[session_id]["total"]
        emit(q, "loop_end", {
            "success": False,
            "message": f"Limite {max_iterations} iterazioni raggiunto",
            "iterations": iteration,
            "total_cost": total
        })

# ─────────────────────────────────────────────
human_responses = {}
human_events = {}

def wait_for_human(session_id, timeout=300):
    event = threading.Event()
    human_events[session_id] = event
    event.wait(timeout=timeout)
    return human_responses.pop(session_id, None)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    data = request.json
    task = data.get("task", "").strip()
    if not task:
        return jsonify({"error": "Task vuoto"}), 400
    session_id = str(int(time.time() * 1000))
    q = queue.Queue()
    event_queues[session_id] = q
    threading.Thread(target=run_agent_loop, args=(session_id, task, q), daemon=True).start()
    return jsonify({"session_id": session_id})

@app.route("/stream/<session_id>")
def stream(session_id):
    def generate():
        q = event_queues.get(session_id)
        if not q:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Sessione non trovata'}})}\n\n"
            return
        while True:
            try:
                event = q.get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
                if event["type"] in ("loop_end", "error", "timeout"):
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        event_queues.pop(session_id, None)
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/respond/<session_id>", methods=["POST"])
def respond(session_id):
    data = request.json
    human_responses[session_id] = data.get("response", "")
    ev = human_events.pop(session_id, None)
    if ev:
        ev.set()
    return jsonify({"ok": True})

if __name__ == "__main__":
    port  = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug, port=port, threaded=True)
