# ctf-koth-citadel:latest -- SHARED SSH King-of-the-Hill "Citadel" (root-wars).
#
# NOT per-team: one container the whole event attacks over SSH. Teams log in as
# `player`, escalate to root, and write their team token into the root-only
# /koth/king. A scorer (root) exposes that file at /king for the CTFd koth
# plugin. Holding the Citadel = staying root and re-writing faster than rivals.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        openssh-server sudo python3 ca-certificates coreutils \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd

RUN useradd --create-home --shell /bin/bash player

# Privesc puzzle (modest, so most teams reach the holding game): player may run
# `env` as root without a password -> GTFOBins `sudo env <shell>` = root.
RUN echo 'player ALL=(root) NOPASSWD: /usr/bin/env' > /etc/sudoers.d/citadel \
 && chmod 0440 /etc/sudoers.d/citadel \
 && visudo -cf /etc/sudoers.d/citadel

# The throne: root-only. Only root can plant a team token here.
RUN mkdir -p /koth && : > /koth/king \
 && chown -R root:root /koth && chmod 0755 /koth && chmod 0600 /koth/king

RUN sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/; s/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

COPY scorer.py /opt/scorer.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/scorer.py

EXPOSE 22 8081
ENTRYPOINT ["/opt/entrypoint.sh"]
