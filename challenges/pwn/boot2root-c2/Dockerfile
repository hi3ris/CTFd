# ctf-boot2root-c2:latest  (Phantom Wire staging server)
#
# A single-container Linux boot2root themed as the PHANTOM WIRE crew's exposed
# C2 staging server. The only network-facing surface is the operator "task
# queue" panel (running as `www`). From a shell as `www`, a chain of local
# misconfigurations leads to root, and only root can read /root/flag.
#
# The flag is NOT baked into the image. entrypoint.sh derives it at runtime from
# the injected FLAG / CHALLENGE_SECRET (see flag.py) and writes it to /root/flag
# as mode 400, root-owned -- never world-readable, never on disk in the image.
#
# Intended chain (three distinct techniques, none shared with the other boxes):
#   1. www    : unsafe YAML deserialization in the panel -> code exec as www
#   2. deploy : SUID `queuectl` executes a runner path read from a WORLD-WRITABLE
#               config (/etc/phantom/queue.conf) -> shell as deploy
#   3. root   : sudo NOPASSWD `python3 /opt/phantom/report.py`; /opt/phantom is
#               group-writable by deploy, so a planted phantomlib.py is imported
#               as root -> cat /root/flag
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        python3 python3-yaml sudo gcc libc6-dev util-linux \
        procps coreutils ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---- users ----------------------------------------------------------------
# www    : the low-privilege worker the foothold lands you on.
# deploy : the operator account that owns the job spool.
# root   : the goal.
RUN useradd --create-home --shell /bin/bash deploy \
 && useradd --create-home --shell /bin/bash www

# ---- stage 1: the foothold panel (runs as www) ----------------------------
RUN mkdir -p /opt/web
COPY src/panel.py /opt/web/panel.py
RUN chown -R root:root /opt/web && chmod 0755 /opt/web/panel.py

# ---- stage 2 misconfig: SUID-to-deploy runner + world-writable config ------
# queuectl is setuid `deploy` (4755); it execs the path named by `runner=` in
# /etc/phantom/queue.conf, and that config is world-writable (0666) by mistake.
RUN mkdir -p /etc/phantom /opt/phantom \
 && printf 'runner=/opt/phantom/run-jobs.sh\n' > /etc/phantom/queue.conf \
 && chmod 0666 /etc/phantom/queue.conf \
 && printf '#!/bin/sh\necho "[run-jobs] no pending jobs" >&2\n' \
        > /opt/phantom/run-jobs.sh \
 && chown deploy:deploy /opt/phantom/run-jobs.sh \
 && chmod 0755 /opt/phantom/run-jobs.sh
COPY src/queuectl.c /tmp/queuectl.c
RUN gcc -O2 -o /usr/local/bin/queuectl /tmp/queuectl.c \
 && rm -f /tmp/queuectl.c \
 && chown deploy:deploy /usr/local/bin/queuectl \
 && chmod 4755 /usr/local/bin/queuectl

# ---- stage 3 misconfig: sudo python + group-writable script directory ------
# `deploy` may run report.py as root without a password. The script imports
# `phantomlib`, resolved from its own directory /opt/phantom, which is
# group-writable by deploy => deploy plants phantomlib.py and it runs as root.
# report.py itself is root-owned and NOT writable by deploy (the hole is the
# writable *directory*, not the file). phantomlib.py is deliberately absent.
COPY src/report.py /opt/phantom/report.py
RUN chown root:root /opt/phantom/report.py && chmod 0644 /opt/phantom/report.py \
 && chown root:deploy /opt/phantom && chmod 2775 /opt/phantom
RUN echo 'deploy ALL=(root) NOPASSWD: /usr/bin/python3 /opt/phantom/report.py' \
        > /etc/sudoers.d/phantom-report \
 && chmod 0440 /etc/sudoers.d/phantom-report \
 && visudo -cf /etc/sudoers.d/phantom-report

# ---- flag derivation + entrypoint -----------------------------------------
COPY flag.py /opt/flag.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/flag.py

# The container starts as root (entrypoint writes the root-only flag file, then
# drops to `www` to serve the foothold). No USER directive on purpose.
EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/opt/entrypoint.sh"]
