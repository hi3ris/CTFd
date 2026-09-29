# ctf-boot2root-webapp:latest  (SnapNote)
#
# A single-container Linux boot2root. The only network-facing surface is the
# unprivileged SnapNote preview service (running as `www`). From a shell as
# `www`, a chain of local misconfigurations leads to root, and only root can
# read /root/flag.
#
# The flag is NOT baked into the image. entrypoint.sh derives it at runtime from
# the injected FLAG / CHALLENGE_SECRET (see flag.py) and writes it to /root/flag
# as mode 400, root-owned -- never world-readable, never on disk in the image.
#
# Intended chain (three distinct techniques):
#   1. www  : Jinja2 SSTI in SnapNote  -> code execution as www
#   2. svc  : SUID `notebackup` shell argument-injection -> shell as svc
#   3. root : `/opt/maint/python3` has cap_setuid+ep, executable only by group
#             svc -> os.setuid(0) -> root -> cat /root/flag
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Runtime deps only. gcc/libc6-dev compile notebackup in this stage; libcap2-bin
# provides setcap/getcap; python3-jinja2 backs the (vulnerable) SnapNote render.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        python3 python3-jinja2 gcc libc6-dev libcap2-bin util-linux \
        procps tar gzip coreutils ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---- users ----------------------------------------------------------------
# www : the low-privilege service account the foothold lands you on.
# svc : an intermediate account that owns the notes bundle.
# root: the goal.
RUN useradd --create-home --shell /bin/bash svc \
 && useradd --create-home --shell /bin/bash www

# ---- stage 1: the foothold service (runs as www) --------------------------
RUN mkdir -p /opt/web
COPY src/snapnote.py /opt/web/snapnote.py
RUN chown -R root:root /opt/web && chmod 0755 /opt/web/snapnote.py

# ---- stage 2 misconfig: SUID-to-svc helper with shell arg-injection --------
# notebackup is setuid `svc` (owner svc:svc, mode 4755) => any local user (www)
# may run it; it concatenates its <bundle> argument into a /bin/sh command.
RUN mkdir -p /srv/notes \
 && printf 'welcome to snapnote\n' > /srv/notes/hello.txt \
 && chown -R svc:svc /srv/notes \
 && mkdir -p /var/backups && chown svc:svc /var/backups
COPY src/notebackup.c /tmp/notebackup.c
RUN gcc -O2 -o /usr/local/bin/notebackup /tmp/notebackup.c \
 && rm -f /tmp/notebackup.c \
 && chown svc:svc /usr/local/bin/notebackup \
 && chmod 4755 /usr/local/bin/notebackup

# ---- stage 3 misconfig: cap_setuid python runnable only by group svc --------
# A stray "maintenance" python carries cap_setuid+ep. It is root:svc mode 0750,
# so `www` cannot run it (must first become svc via stage 2); once svc runs it,
# os.setuid(0) succeeds and root can read the flag. A world-executable copy
# would collapse the chain, so the group restriction is deliberate.
RUN mkdir -p /opt/maint \
 && cp /usr/bin/python3 /opt/maint/python3 \
 && setcap cap_setuid+ep /opt/maint/python3 \
 && chown root:svc /opt/maint/python3 \
 && chmod 0750 /opt/maint/python3

# ---- flag derivation + entrypoint -----------------------------------------
COPY flag.py /opt/flag.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/flag.py

# The container starts as root (entrypoint writes the root-only flag file, then
# drops to `www` to serve the foothold). No USER directive on purpose.
EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/opt/entrypoint.sh"]
