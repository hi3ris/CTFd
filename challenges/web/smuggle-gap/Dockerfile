# ctf-smuggle-gap:latest
#
# Two-tier setup in one container:
#   * backend.py -- internal application, binds 127.0.0.1:9000 (never exposed)
#   * front.py   -- edge proxy, binds 0.0.0.0:8080 (the only exposed port)
#
# Build:  docker build -t ctf-smuggle-gap:latest .
# Run:    docker run --rm -p 8080:8080 \
#             -e CHALLENGE_SECRET="$(openssl rand -hex 32)" \
#             ctf-smuggle-gap:latest
#
# The flag is injected per team via FLAG / CHALLENGE_SECRET (see flag.py); no
# secret is baked into the image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# flag.py lives at the challenge root; the app imports it as a top-level module.
COPY flag.py .
COPY app/framing.py app/backend.py app/front.py app/entrypoint.sh ./
RUN chmod +x entrypoint.sh

# non-root
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 8080

CMD ["./entrypoint.sh"]
