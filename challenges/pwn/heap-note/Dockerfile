# ctf-heap-note:latest
#
# Build:  docker build -t ctf-heap-note:latest .
# Run:    docker run --rm -p 9022:9022 \
#             -e TEAM_SECRET="<per-team-secret>" \
#             ctf-heap-note:latest
#
# TEAM_SECRET is injected per team at instance-creation time. No secret is baked
# into the image; the flag is derived at runtime by flag.py and only ever lives
# in the served process's environment (win() prints getenv("FLAG")).
#
# The served binary is the SAME artifact players download in handout/, run
# against the SAME pinned glibc 2.31 (2.31-0ubuntu9.18). We patchelf it onto the
# shipped ld/libc so the heap layout and every libc offset are byte-identical to
# the offline copy -- no "works on my libc" surprises.
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat patchelf python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /chall

# Ship the exact pinned libc + loader and the prebuilt challenge binary.
COPY handout/libc.so.6   /chall/libc.so.6
COPY handout/ld-2.31.so  /chall/ld-2.31.so
COPY handout/chall       /chall/chall
COPY flag.py             /chall/flag.py
COPY entrypoint.sh       /chall/entrypoint.sh

# Bind the binary to the shipped loader + libc (exact offset match with handout).
RUN chmod +x /chall/ld-2.31.so /chall/chall /chall/entrypoint.sh \
    && patchelf --set-interpreter /chall/ld-2.31.so --set-rpath /chall /chall/chall

# Unprivileged runtime user.
RUN useradd --no-create-home --uid 10001 ctf
USER ctf

ENV PORT=9022
EXPOSE 9022

ENTRYPOINT ["/chall/entrypoint.sh"]
