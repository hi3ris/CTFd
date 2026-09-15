# AI admission gateway. Runs on the front (SG allows it to reach Ollama on the
# GPU node). ONE gunicorn worker with threads so the in-memory admission
# counters are exact; the GPU bottleneck (~1-2 req/s) makes one worker ample.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd -m -u 1001 gw && mkdir -p /var/log/ai-gateway && chown gw /var/log/ai-gateway
USER gw

EXPOSE 8600
# One worker (exact counters), several threads (Ollama calls block), long timeout
# to cover model generation.
CMD ["gunicorn", "-w", "1", "--threads", "8", "-t", "300", "-b", "0.0.0.0:8600", "app:app"]
