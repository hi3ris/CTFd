# ctf-ai1-naive-guard:latest
#
# Build:  docker build -t ctf-ai1-naive-guard:latest .
# Run:    docker run --rm -p 8080:8080 \
#             -e TEAM_SECRET="<per-team-secret>" \
#             -e OLLAMA_URL="http://ollama:11434" \
#             ctf-ai1-naive-guard:latest
#
# TEAM_SECRET (derives the guarded SIGMA secret AND the flag) and OLLAMA_URL
# (the team's Ollama backend serving llama3.1:8b) are injected at
# instance-creation time. No secret is baked into the image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OLLAMA_MODEL=llama3.1:8b

WORKDIR /srv

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/app.py app/prompts.py ./

# non-root
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 8080

# ONE worker: the in-process session store keeps each conversation coherent.
# Chat history is not security-relevant (the oracle is /verify), so this is
# purely a UX choice.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "180", "app:app"]
