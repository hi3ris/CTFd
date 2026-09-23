#!/usr/bin/env bash
# Met a jour CTFd sur le front, depuis le depot deja clone dans /opt/ctfd/CTFd.
# Idempotent. Lance :
#   - par `make deploy` (SSH admin), avec la branche en argument ;
#   - par le CD GitHub Actions (SSM Run Command), avec le SHA pousse.
#
#   deploy/scripts/front-update.sh [<branche>|<sha>]     (defaut : branche courante)
#
# Env : BACKUP_BUCKET=<bucket> pour (re)poser la destination des sauvegardes
#       dans deploy/front/.env. Le fichier .env lui-meme n'est jamais cree ici.
set -euo pipefail

REPO=${CTFD_REPO:-/opt/ctfd/CTFd}
cd "$REPO"

REF=${1:-$(git rev-parse --abbrev-ref HEAD)}
COMPOSE="docker compose -f deploy/front/docker-compose.prod.yml --env-file deploy/front/.env"

echo ">> git : $REF"
git fetch --prune origin
if git show-ref --verify --quiet "refs/remotes/origin/$REF"; then
  git checkout -q "$REF"
  git reset -q --hard "origin/$REF"
else
  git checkout -q --detach "$REF"
fi
git log -1 --oneline

test -f deploy/front/.env || { echo "ERREUR : deploy/front/.env absent (make deploy l'envoie au premier deploiement)"; exit 1; }
test -f deploy/front/nginx/active.conf || cp deploy/front/nginx/bootstrap.conf deploy/front/nginx/active.conf

if [ -n "${BACKUP_BUCKET:-}" ]; then
  if grep -q '^BACKUP_BUCKET=' deploy/front/.env; then
    sed -i "s|^BACKUP_BUCKET=.*|BACKUP_BUCKET=$BACKUP_BUCKET|" deploy/front/.env
  else
    echo "BACKUP_BUCKET=$BACKUP_BUCKET" >> deploy/front/.env
  fi
fi

echo ">> sauvegarde automatique"
sudo CTFD_REPO="$REPO" deploy/scripts/install-backup-timer.sh

echo ">> conteneurs"
$COMPOSE up -d --build ctfd db cache nginx certbot

echo ">> sante"
ok=0
for _ in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/healthcheck || true)
  [ "$code" = 200 ] && { ok=1; break; }
  # nginx en HTTPS : le port 80 redirige, on interroge alors le 443 en local.
  code=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/healthcheck || true)
  [ "$code" = 200 ] && { ok=1; break; }
  sleep 5
done
$COMPOSE ps --format 'table {{.Name}}\t{{.Status}}'
if [ "$ok" -ne 1 ]; then
  echo "ERREUR : /healthcheck ne repond pas 200 apres 5 min"
  $COMPOSE logs --tail=40 ctfd nginx
  exit 1
fi
echo "OK : CTFd a jour ($(git rev-parse --short HEAD))"
