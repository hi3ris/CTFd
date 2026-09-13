# Build-only image for packed-vm-lite. This challenge is a STATIC download: the
# player receives the compiled ELF 'vmcheck'. Nothing is served at runtime.
#
# This Dockerfile exists to reproduce the artifact deterministically:
#
#   docker build -t ctf-packed-vm-lite:latest .
#   # extract the built binary:
#   id=$(docker create ctf-packed-vm-lite:latest) \
#     && docker cp "$id":/out/vmcheck ./vmcheck \
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
    && mkdir -p /tmp/out && cp vmcheck /tmp/out/vmcheck

# Stage the artifact at a stable path for extraction.
FROM debian:bookworm-slim
COPY --from=build /tmp/out/vmcheck /out/vmcheck
CMD ["/bin/sh", "-c", "echo 'packed-vm-lite is a static download; artifact at /out/vmcheck'"]
