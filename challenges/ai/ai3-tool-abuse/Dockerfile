# ctf-ai3-tool-abuse:latest
#
# Build:  docker build -t ctf-ai3-tool-abuse:latest .
# Run:    docker run --rm -p 8080:8080 \
#             -e TEAM_SECRET="<per-team-secret>" \
#             -e OLLAMA_URL="http://ollama:11434" \
#             ctf-ai3-tool-abuse:latest
#
# TEAM_SECRET (derives the flag) and OLLAMA_URL (the team's tool-capable Ollama
# backend, default model llama3.1:8b) are injected at instance-creation time.
# No secret is baked into the image. The model must support tool calling.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OLLAMA_MODEL=llama3.1:8b \
    MODEL_BACKEND=ollama

WORKDIR /srv

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/app.py app/prompts.py app/tools.py app/model_backends.py ./
# flag.py (challenge root) provides get_flag(); tools.py imports it at runtime.
COPY flag.py ./

# non-root
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 8080

# ONE worker: the in-process session store holds each conversation's tool state.
# Losing it only resets a conversation; the oracle is the per-session server
# state, so a single worker keeps a player's approve->deploy chain coherent.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "300", "app:app"]
