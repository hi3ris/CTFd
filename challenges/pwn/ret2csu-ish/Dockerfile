# ctf-ret2csu-ish:latest
#
# Serves the challenge binary with socat under a non-root user. No flag is baked
# into the image -- the per-team flag is derived at runtime from TEAM_SECRET by
# entrypoint.sh (see flag.py).
#
# IMPORTANT: we ship the *prebuilt* static `chall` that is committed alongside
# this Dockerfile, rather than recompiling here. The binary is fully static, so
# copying it guarantees the served binary is byte-identical to the handout
# players download -- gadget and buffer offsets can never drift between the two
# because of a different toolchain/glibc. Rebuild it with `make` (see Makefile)
# if you change chall.c, then commit the new artifact.

FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends socat python3 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin pwn

WORKDIR /app
COPY chall /app/chall
COPY flag.py entrypoint.sh /app/
RUN chmod +x /app/chall /app/entrypoint.sh

USER pwn
EXPOSE 9111

# TEAM_SECRET is injected by the instancier at runtime; a dev default lets the
# image run standalone for playtesting (see flag.py). The flag file is written
# to /tmp (a writable tmpfs at runtime); nothing sensitive is baked in.
ENV PORT=9111
ENTRYPOINT ["/app/entrypoint.sh"]
