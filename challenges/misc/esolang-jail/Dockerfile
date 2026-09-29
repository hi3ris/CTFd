# ctf-esolang-jail:latest
#
# Serves the Marble interpreter jail with socat under a non-root user. No flag is
# baked into the image -- the per-team flag is derived at runtime from the
# injected FLAG/CHALLENGE_SECRET by entrypoint.sh (see flag.py), placed only in
# the served process's environment and a tmpfs file.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends socat \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin jail

WORKDIR /app
COPY app/interp.py /app/interp.py
COPY flag.py entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Writable tmpfs mount point for the runtime flag file (see entrypoint.sh /
# docker-compose.yml). Created here so it exists even before the tmpfs mounts.
RUN mkdir -p /flag && chown jail:jail /flag

USER jail
EXPOSE 9301

ENV PORT=9301
ENTRYPOINT ["/app/entrypoint.sh"]
