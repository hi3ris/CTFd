# ctf-boot2root-linux:latest
#
# A single-container Linux boot2root. The only network-facing surface is an
# unprivileged HTTP "node status" service (running as `www`). From a shell as
# `www`, a chain of classic local misconfigurations leads to root, and only
# root can read /root/flag.
#
# The flag is NOT baked into the image. entrypoint.sh derives it at runtime
# from the injected FLAG / CHALLENGE_SECRET (see flag.py) and writes it to
# /root/flag as mode 400, root-owned -- so it is never world-readable and never
# present on disk in the built image.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Runtime deps only. build-essential is kept so logsync can be compiled in this
# same stage; it also just makes the box a more realistic target.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        python3 sudo gcc libc6-dev procps tar gzip coreutils ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---- users ----------------------------------------------------------------
# www : the low-privilege service account the foothold lands you on.
# app : an intermediate account that owns the application logs.
# root: the goal.
RUN useradd --create-home --shell /bin/bash app \
 && useradd --create-home --shell /bin/bash www

# ---- stage 1: the foothold service (runs as www) --------------------------
RUN mkdir -p /opt/web
COPY src/webstatus.py /opt/web/webstatus.py
RUN chown -R root:root /opt/web && chmod 0755 /opt/web/webstatus.py

# ---- stage 2 misconfig: SUID-to-app helper with a PATH-hijack bug ----------
# Compile logsync and install it setuid to `app`. Mode 4755 => any local user
# (i.e. www) may execute it; it runs as app and resolves `ps` via $PATH.
COPY src/logsync.c /tmp/logsync.c
RUN gcc -O2 -o /usr/local/bin/logsync /tmp/logsync.c \
 && rm -f /tmp/logsync.c \
 && chown app:app /usr/local/bin/logsync \
 && chmod 4755 /usr/local/bin/logsync

# ---- stage 3 misconfig: sudo NOPASSWD wildcard for `app` -------------------
# `app` may run tar as root with a wildcard tail => GTFOBins tar --checkpoint
# gives arbitrary root command execution.
RUN echo 'app ALL=(root) NOPASSWD: /usr/bin/tar -czf /var/backups/app-logs.tgz *' \
        > /etc/sudoers.d/app-backup \
 && chmod 0440 /etc/sudoers.d/app-backup \
 && visudo -cf /etc/sudoers.d/app-backup \
 && mkdir -p /var/backups && chown app:app /var/backups

# ---- flag derivation + entrypoint -----------------------------------------
COPY flag.py /opt/flag.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/flag.py

# The container starts as root (entrypoint writes the root-only flag file, then
# drops to `www` to serve the foothold). No USER directive on purpose.
EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/opt/entrypoint.sh"]
