# ctf-pickle-rce:latest
#
# Build:  docker build -t ctf-pickle-rce:latest .
# Run:    docker run --rm -p 9080:9080 \
#             -e TEAM_SECRET="<per-team-secret>" \
#             ctf-pickle-rce:latest
#
# TEAM_SECRET is injected per team at instance-creation time. No secret is baked
# into the image; the flag is derived at runtime by flag.py and written to the
# flag file on the container filesystem (default /flag). It never appears in a
# response unless a solver achieves code execution during unpickling.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=9080 \
    FLAG_PATH=/flag

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app.py         /app/app.py
COPY flag.py        /app/flag.py
COPY entrypoint.sh  /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Unprivileged runtime user. The entrypoint writes the flag file world-readable
# so this same user can read it via the exploit; no privilege boundary is being
# tested here -- the vuln is the deserialization, not file permissions.
RUN useradd --no-create-home --uid 10001 ctf \
    && touch /flag /flag.decoy \
    && chown ctf:ctf /flag /flag.decoy
USER ctf

EXPOSE 9080

ENTRYPOINT ["/app/entrypoint.sh"]
