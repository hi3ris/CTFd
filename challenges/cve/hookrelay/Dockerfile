# ctf-cve-hookrelay:latest
FROM python:3.12-alpine

# git provides the vulnerable clone path + the remote-ext helper; su-exec drops
# privilege after the root-only boot steps in entrypoint.sh.
RUN apk add --no-cache git su-exec

WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/
# Flag source of truth lives at the challenge root; ship it so entrypoint.sh can
# import get_flag() at boot.
COPY flag.py /app/flag.py
RUN chmod +x /app/entrypoint.sh

# Unprivileged app user. Only entrypoint.sh (flag write + git config) runs as
# root; the HTTP service and every clone run as appuser.
RUN adduser -D -H appuser

# Only the public HTTP port is published; the flag file and the clone worker are
# reachable only through the CVE.
EXPOSE 8080

# Dev default only: feeds flag.py's LOCAL DEV fallback so the image runs
# off-arena. In production the instancier injects FLAG / CHALLENGE_SECRET.
ENV TEAM_SECRET=devsecret

ENTRYPOINT ["/app/entrypoint.sh"]
