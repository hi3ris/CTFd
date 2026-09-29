#!/usr/bin/env bash
# Sauvegarde automatique de CTFd -- tourne SUR LE FRONT, lancee par le timer
# systemd ctfd-backup.timer toutes les 15 minutes (deploy/front/systemd/).
#
#   - dump MariaDB verifie (gzip -t, taille plancher, table users presente),
#     exactement la meme chaine que `make backup` cote operateur ;
#   - cadence decidee ICI, pas par le timer : pendant [start, end] du CTF
#     (lu dans la table config) chaque passage dumpe ; hors epreuve seulement
#     si le dernier dump reussi a plus de 6 h ;
#   - une fois par heure en plus : les uploads (/var/uploads) et l'export
#     natif CTFd (zip importable par Admin > Backup) ;
#   - envoi S3 si BACKUP_BUCKET est renseigne dans deploy/front/.env :
#     backups/auto/  (expire au bout de 14 j, regle de cycle de vie Terraform)
#     backups/daily/ (un fichier par jour, ecrase, garde comme les manuels) ;
#   - etat ecrit dans $BACKUP_DIR/status.json, monte en lecture seule dans le
#     conteneur CTFd (/backups/status.json) et lu par la page admin Ops, qui
#     passe au rouge quand le dernier dump reussi a plus de 30 min pendant
#     l'epreuve. Aucune notification CTFd : elles sont visibles des joueurs.
#
# Usage manuel : sudo -u ubuntu deploy/scripts/backup.sh [--force] [--extras]
set -euo pipefail

REPO=${CTFD_REPO:-/opt/ctfd/CTFd}
BACKUP_DIR=${BACKUP_DIR:-/opt/ctfd/backups}
KEEP_SQL=${BACKUP_KEEP_SQL:-48}      # 12 h de dumps a 15 min
KEEP_EXTRA=${BACKUP_KEEP_EXTRA:-6}   # 6 h d'uploads/exports horaires
OFF_EVENT_INTERVAL=$((6 * 3600))
EXTRA_INTERVAL=$((55 * 60))
ENV_FILE=$REPO/deploy/front/.env
COMPOSE="docker compose -f $REPO/deploy/front/docker-compose.prod.yml --env-file $ENV_FILE"
STATUS=$BACKUP_DIR/status.json
FORCE=0; EXTRAS=0
for a in "$@"; do case "$a" in --force) FORCE=1;; --extras) EXTRAS=1;; esac; done

log() { echo "[ctfd-backup] $*"; logger -t ctfd-backup -- "$*" 2>/dev/null || true; }

# status.json : {"last_run","last_ok","last_extra","ok","kind","file","size","s3","error"}
status_get() { python3 -c 'import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: d={}
v=d.get(sys.argv[2], 0); print(v if v is not None else 0)' "$STATUS" "$1" 2>/dev/null || echo 0; }
status_write() { # ok kind file size s3 error [last_ok] [last_extra]
  python3 - "$STATUS" "$@" <<'PY'
import json, os, sys, time
p, ok, kind, file, size, s3, error = sys.argv[1:8]
last_ok = sys.argv[8] if len(sys.argv) > 8 else None
last_extra = sys.argv[9] if len(sys.argv) > 9 else None
try:
    d = json.load(open(p))
except Exception:
    d = {}
now = int(time.time())
d.update(last_run=now, ok=ok == "1", kind=kind, file=file, size=int(size or 0),
         s3=s3 == "1", error=error)
if last_ok: d["last_ok"] = int(last_ok)
if last_extra: d["last_extra"] = int(last_extra)
d.setdefault("last_ok", 0); d.setdefault("last_extra", 0)
tmp = p + ".tmp"
with open(tmp, "w") as fh:
    json.dump(d, fh)
os.replace(tmp, p)
PY
}
fail() { log "ECHEC : $1"; status_write 0 "$KIND" "" 0 0 "$1"; exit 1; }
trap 'fail "erreur inattendue (ligne $LINENO)"' ERR

mkdir -p "$BACKUP_DIR"
test -f "$ENV_FILE" || fail "$ENV_FILE absent"
BUCKET=$(grep -E '^BACKUP_BUCKET=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"' || true)
NOW=$(date +%s)
STAMP=$(date -u +%Y%m%d-%H%M%S)
KIND=sql

# --- cadence ----------------------------------------------------------------
WINDOW=$($COMPOSE exec -T db sh -c 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" -N -s -e "select \`key\`, value from config where \`key\` in (\"start\",\"end\")" ctfd' 2>/dev/null | tr '\t' '=' | tr '\n' ' ' || true)
START=0; END=0
for kv in $WINDOW; do case "$kv" in start=*) START=${kv#start=};; end=*) END=${kv#end=};; esac; done
START=${START:-0}; END=${END:-0}
IN_EVENT=0
if [ "${START:-0}" -gt 0 ] && [ "${END:-0}" -gt 0 ] && [ "$NOW" -ge "$START" ] && [ "$NOW" -le "$END" ]; then IN_EVENT=1; fi
LAST_OK=$(status_get last_ok)
if [ "$FORCE" = 0 ] && [ "$IN_EVENT" = 0 ] && [ $((NOW - LAST_OK)) -lt "$OFF_EVENT_INTERVAL" ]; then
  log "hors epreuve, dernier dump il y a $(( (NOW - LAST_OK) / 60 )) min : rien a faire"
  status_write 1 skipped "" 0 0 ""
  exit 0
fi

# --- dump SQL verifie ---------------------------------------------------------
OUT=$BACKUP_DIR/ctfd-auto-$STAMP.sql.gz
TMP=$OUT.partial
$COMPOSE exec -T db sh -c 'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction --routines ctfd' | gzip > "$TMP"
gzip -t "$TMP" || { rm -f "$TMP"; fail "archive corrompue"; }
SIZE=$(stat -c%s "$TMP")
[ "$SIZE" -gt 10000 ] || { rm -f "$TMP"; fail "dump de $SIZE octets, vide ou tronque"; }
zcat "$TMP" | grep -q 'CREATE TABLE `users`' || { rm -f "$TMP"; fail "table users absente du dump"; }
mv "$TMP" "$OUT"
log "dump $OUT ($SIZE octets)$( [ "$IN_EVENT" = 1 ] && echo ' [epreuve en cours]')"

# --- extras horaires : uploads + export natif ----------------------------------
LAST_EXTRA=$(status_get last_extra)
NEW_EXTRA=""
if [ "$EXTRAS" = 1 ] || [ $((NOW - LAST_EXTRA)) -ge "$EXTRA_INTERVAL" ]; then
  KIND=sql+uploads+export
  UP=$BACKUP_DIR/uploads-auto-$STAMP.tgz
  $COMPOSE exec -T ctfd tar czf - -C /var/uploads . > "$UP.partial" && mv "$UP.partial" "$UP" \
    || { rm -f "$UP.partial"; log "AVERTISSEMENT : archive des uploads impossible"; }
  EX=$BACKUP_DIR/export-auto-$STAMP.zip
  $COMPOSE exec -T ctfd python -c '
import shutil, sys
from CTFd import create_app
from CTFd.utils.exports import export_ctf
app = create_app()
with app.app_context():
    shutil.copyfileobj(export_ctf(), sys.stdout.buffer)
' > "$EX.partial" 2>/dev/null && python3 -c 'import sys,zipfile; zipfile.ZipFile(sys.argv[1]).testzip()' "$EX.partial" \
    && mv "$EX.partial" "$EX" || { rm -f "$EX.partial"; log "AVERTISSEMENT : export natif CTFd impossible"; }
  NEW_EXTRA=$NOW
fi

# --- S3 ------------------------------------------------------------------------
S3=0
if [ -n "$BUCKET" ]; then
  command -v aws >/dev/null || fail "aws CLI absent (deploy/scripts/install-backup-timer.sh)"
  aws s3 cp "$OUT" "s3://$BUCKET/backups/auto/" --only-show-errors || fail "envoi S3 impossible (dump local conserve : $OUT)"
  aws s3 cp "$OUT" "s3://$BUCKET/backups/daily/ctfd-$(date -u +%Y%m%d).sql.gz" --only-show-errors || true
  if [ -n "$NEW_EXTRA" ]; then
    for f in "$BACKUP_DIR/uploads-auto-$STAMP.tgz" "$BACKUP_DIR/export-auto-$STAMP.zip"; do
      [ -f "$f" ] && aws s3 cp "$f" "s3://$BUCKET/backups/auto/" --only-show-errors || true
    done
  fi
  S3=1
else
  log "BACKUP_BUCKET non renseigne : dump local seulement"
fi

# --- rotation locale ----------------------------------------------------------
ls -1t "$BACKUP_DIR"/ctfd-auto-*.sql.gz 2>/dev/null | tail -n +$((KEEP_SQL + 1)) | xargs -r rm -f
ls -1t "$BACKUP_DIR"/uploads-auto-*.tgz 2>/dev/null | tail -n +$((KEEP_EXTRA + 1)) | xargs -r rm -f
ls -1t "$BACKUP_DIR"/export-auto-*.zip 2>/dev/null | tail -n +$((KEEP_EXTRA + 1)) | xargs -r rm -f

status_write 1 "$KIND" "$OUT" "$SIZE" "$S3" "" "$NOW" "$NEW_EXTRA"
log "OK ($KIND, s3=$S3)"
