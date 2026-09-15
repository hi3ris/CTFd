# ctf-koth-boot2root-base:latest -- shared base for the boot2root KotH hills.
#
# A SHARED SSH box (not per-team). Teams log in as `player` and plant their team
# token in one of two king files:
#   /home/player/king.txt   player-writable        -> "user" hold, HALF points
#   /root/king.txt          root-only (in /root 0700) -> "root" hold, FULL points
# A scorer (root) exposes the active hold at /king with its level; the CTFd koth
# plugin halves the points of a user-only hold. The per-hill images below
# (armory / foundry / vault) each add ONE distinct, modest privilege-escalation
# path so most teams reach the holding game, then keep root to score full.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        openssh-server sudo python3 ca-certificates coreutils libcap2-bin \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd

RUN useradd --create-home --shell /bin/bash player

# The two thrones. Root king lives in a root-only /root; the user king is the
# player's own file. entrypoint.sh (re)applies ownership at boot.
RUN : > /root/king.txt && chown root:root /root/king.txt && chmod 0600 /root/king.txt \
 && chmod 0700 /root \
 && : > /home/player/king.txt && chown player:player /home/player/king.txt \
 && chmod 0664 /home/player/king.txt

# A short briefing the player finds on login.
RUN printf '%s\n' \
    'KotH boot2root -- plante ton jeton d equipe (page King of the Hill) :' \
    '  echo <jeton> > /home/player/king.txt   # acces user   -> MOITIE des points' \
    '  echo <jeton> > /root/king.txt          # acces root   -> points PLEINS' \
    'Tiens la colline : reecris ton fichier plus vite que les rivaux.' \
    > /home/player/BRIEFING.txt \
 && chown player:player /home/player/BRIEFING.txt

RUN sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/; s/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

COPY scorer.py /opt/scorer.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/scorer.py

EXPOSE 22 8082
ENTRYPOINT ["/opt/entrypoint.sh"]
