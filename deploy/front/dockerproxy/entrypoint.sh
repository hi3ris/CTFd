#!/bin/sh
# Republie le socket Docker de l'arena en TCP sur le reseau interne.
set -eu

: "${ARENA_HOST:?ARENA_HOST doit etre defini (IP privee de l'arena)}"
ARENA_USER="${ARENA_USER:-ubuntu}"

if [ ! -r /keys/id_ed25519 ]; then
  echo "ERREUR: cle privee absente ou illisible dans /keys/id_ed25519" >&2
  exit 1
fi

# La cle doit etre en 600 : ssh refuse une cle trop permissive. Le montage est
# en lecture seule, on recopie donc avec les bons droits.
install -m 700 -d /root/.ssh
install -m 600 /keys/id_ed25519 /root/.ssh/id_ed25519

if [ -r /keys/known_hosts ]; then
  install -m 644 /keys/known_hosts /root/.ssh/known_hosts
  STRICT=yes
else
  # Sans empreinte connue on accepte a la premiere connexion, mais on le dit :
  # sur ce canal, un homme du milieu obtiendrait root sur l'arena.
  echo "AVERTISSEMENT: pas de known_hosts, verification d'hote desactivee" >&2
  STRICT=accept-new
fi

echo "Tunnel Docker vers ${ARENA_USER}@${ARENA_HOST}"

exec ssh -N \
  -o StrictHostKeyChecking="$STRICT" \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -i /root/.ssh/id_ed25519 \
  -L "0.0.0.0:2375:/var/run/docker.sock" \
  "${ARENA_USER}@${ARENA_HOST}"
