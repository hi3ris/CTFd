# ctf-ssrf-metadata-decoy:latest
FROM python:3.12-alpine

# su-exec for privilege drop; libcap for setcap; iproute2 for the lo alias.
RUN apk add --no-cache su-exec libcap iproute2

WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/
RUN chmod +x /app/entrypoint.sh

# Allow the (non-root) app to bind port 80 for the decoy metadata mirror,
# without running the application as root.
RUN PYBIN="$(readlink -f "$(command -v python3)")" && \
    setcap 'cap_net_bind_service=+ep' "$PYBIN"

# Unprivileged application user. Only entrypoint.sh (network setup) runs as root.
RUN adduser -D -H appuser

# Published: only the public proxy. 80 and 9137 are internal-only (SSRF reach).
EXPOSE 8080

# TEAM_SECRET is injected per team at deploy time; default here is for local dev.
ENV TEAM_SECRET=devsecret

ENTRYPOINT ["/app/entrypoint.sh"]
