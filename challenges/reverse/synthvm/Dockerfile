# Build-only image for synthvm. This challenge is a STATIC download: the player
# receives the single compiled ELF 'synthvm'. Nothing is served at runtime.
#
# This Dockerfile exists to reproduce the artifact deterministically:
#
#   docker build -t ctf-synthvm:latest .
#   # extract the built binary:
#   id=$(docker create ctf-synthvm:latest) \
#     && docker cp "$id":/out/synthvm ./synthvm \
#     && docker rm "$id"
#
# There is no long-running service and no per-team secret: the flag is static
# and lives in challenge.yml (allowed for reverse challenges whose artifact
# carries the flag logic locally).
FROM debian:bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libc6-dev python3 make binutils \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m builder
USER builder
WORKDIR /home/builder/chall

COPY --chown=builder:builder src ./src
COPY --chown=builder:builder Makefile ./

RUN make CFLAGS="-O2 -s" \
    && mkdir -p /tmp/out && cp synthvm /tmp/out/synthvm

# Stage the artifact at a stable path for extraction.
FROM debian:bookworm-slim
RUN useradd -m ctf
USER ctf
COPY --from=build /tmp/out/synthvm /out/synthvm
CMD ["/bin/sh", "-c", "echo 'synthvm is a static download; artifact at /out/synthvm'"]
