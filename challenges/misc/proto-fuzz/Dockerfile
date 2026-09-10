# ctf-proto-fuzz:latest
#
# Small, single-stage image serving the FZLP/1 text protocol. No flag is baked
# into the image -- the per-team flag is derived at runtime from TEAM_SECRET
# (see flag.py), computed inside the service, and emitted only after the service
# observes the required effect (maintenance channel armed). Runs as non-root.
FROM python:3.12-alpine

RUN adduser -D -u 10001 fzlp
WORKDIR /app

# Only the two files the service needs. Handout/solution/spec stay out of the
# image so nothing extra is reachable from inside the container.
COPY server.py flag.py /app/

USER fzlp
ENV PORT=9109
EXPOSE 9109

# TEAM_SECRET is injected by the instancier at runtime; a dev default in flag.py
# lets the image run standalone for playtesting. Nothing sensitive is baked in.
CMD ["python3", "-u", "server.py"]
