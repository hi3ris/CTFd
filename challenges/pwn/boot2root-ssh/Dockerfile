# ctf-boot2root-ssh:latest -- SSH-entry boot2root (per-team instance).
#
# The player receives low-priv SSH access (user `ctf`) and must escalate to root
# to read /root/flag. Root login is disabled; the only way up is the intended
# local privesc. The flag is planted at runtime, never baked into the image.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        openssh-server sudo gcc libc6-dev python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd

RUN useradd --create-home --shell /bin/bash ctf

# healthcheck: a normal DYNAMICALLY-LINKED, NON-suid binary. Nothing exploitable
# in it -- the hole is the sudoers policy below.
COPY src/healthcheck.c /tmp/healthcheck.c
RUN gcc -O2 -o /usr/local/bin/healthcheck /tmp/healthcheck.c \
 && rm -f /tmp/healthcheck.c \
 && chown root:root /usr/local/bin/healthcheck && chmod 0755 /usr/local/bin/healthcheck

# MISCONFIG: ctf may run healthcheck as root KEEPING its environment (SETENV) =>
# LD_PRELOAD passes through to a non-suid binary executed as root, so a preloaded
# library's constructor runs as root.
RUN echo 'ctf ALL=(root) NOPASSWD: SETENV: /usr/local/bin/healthcheck' \
        > /etc/sudoers.d/health \
 && chmod 0440 /etc/sudoers.d/health \
 && visudo -cf /etc/sudoers.d/health

# sshd: password auth for ctf, root login disabled.
RUN sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/; s/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

COPY flag.py /opt/flag.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/flag.py

EXPOSE 22
ENTRYPOINT ["/opt/entrypoint.sh"]
