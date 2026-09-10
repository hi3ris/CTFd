# ctf-lcg-casino:latest
#
# Build:  docker build -t ctf-lcg-casino:latest .
# Run:    docker run --rm -p 9021:9021 \
#             -e TEAM_SECRET="<per-team-secret>" \
#             ctf-lcg-casino:latest
#
# TEAM_SECRET is injected at instance-creation time and derives the per-team
# flag. The LCG seed is generated fresh inside the process on every connection.
# No secret is baked into the image; the service uses only the Python stdlib.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BIND_HOST=0.0.0.0 \
    BIND_PORT=9021

WORKDIR /srv

COPY app/casino_core.py app/server.py ./

# non-root
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 9021

CMD ["python3", "server.py"]
