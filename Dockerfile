FROM cgr.dev/chainguard/python:latest-dev AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# crea venv E workspace qui — il runtime Chainguard non ha /bin/sh
RUN python -m venv /app/venv && mkdir -p /app/workspace
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y pip setuptools wheel && \
    find /app/venv -name "pip*" -type d -exec rm -rf {} + 2>/dev/null || true && \
    find /app/venv -name "pip*" -type f -delete 2>/dev/null || true

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM cgr.dev/chainguard/python:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/venv /app/venv
# workspace vuota dal builder — sovrascritta dal volume mount in produzione
COPY --from=builder /app/workspace /app/workspace

COPY ettorino_assistant.py .
COPY templates/ templates/

EXPOSE 5000

# workers=1 obbligatorio: stato sessioni in-memory (event_queues, session_costs…)
# timeout=600: il loop Claude×GPT può girare per minuti
ENTRYPOINT ["gunicorn", "ettorino_assistant:app", \
            "--bind=0.0.0.0:5000", \
            "--workers=1", \
            "--worker-class=gthread", \
            "--threads=16", \
            "--timeout=600", \
            "--graceful-timeout=30", \
            "--keep-alive=5", \
            "--access-logfile=-", \
            "--error-logfile=-", \
            "--log-level=info"]