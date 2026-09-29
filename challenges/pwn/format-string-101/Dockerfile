# ctf-format-string-101:latest
#
# Two-stage build: compile the challenge binary, then serve it with socat under
# a non-root user. No flag is baked into the image -- the per-team flag is
# derived at runtime from TEAM_SECRET by entrypoint.sh (see flag.py).

# ---- build stage ----------------------------------------------------------
FROM gcc:13-bookworm AS build
WORKDIR /src
COPY chall.c Makefile ./
RUN make

# ---- runtime stage --------------------------------------------------------
FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends socat python3 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin pwn

WORKDIR /app
COPY --from=build /src/chall /app/chall
COPY flag.py entrypoint.sh /app/
RUN chmod +x /app/chall /app/entrypoint.sh

USER pwn
EXPOSE 9101

# TEAM_SECRET is injected by the instancier at runtime; a dev default lets the
# image run standalone for playtesting (see flag.py).
ENV PORT=9101
ENTRYPOINT ["/app/entrypoint.sh"]
