# ctf-lcg-casino:latest
#
# Build:  docker build -t ctf-lcg-casino:latest .
# Run:    docker run --rm -p 9021:9021 \
#             -e CHALLENGE_SECRET="<per-challenge-hex>" \
#             ctf-lcg-casino:latest
#         (or -e FLAG="NCTF{...}"; with neither set the service uses a local-dev
#          fallback derived from TEAM_SECRET for off-arena smoke tests.)
#
# FLAG / CHALLENGE_SECRET are injected at instance-creation time; the service
# resolves the per-challenge flag via flag.get_flag(). The LCG seed is generated
# fresh inside the process on every connection. No secret is baked into the
# image; the service uses only the Python stdlib.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BIND_HOST=0.0.0.0 \
    BIND_PORT=9021

WORKDIR /srv

COPY app/casino_core.py app/server.py flag.py ./

# non-root
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 9021

CMD ["python3", "server.py"]
