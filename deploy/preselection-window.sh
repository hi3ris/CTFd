#!/usr/bin/env bash
# =============================================================================
# NCTF26 — fenêtre de la PRÉSÉLECTION. Fenêtre décidée par défaut :
#   ven 23 oct 2026 19:00  ->  lun 26 oct 2026 00:00  (53 h, GMT/Lomé),
#   gel du scoreboard la dernière heure (dim 25 oct 23:00).
# Heure de Lomé = GMT (UTC+0), donc aucune conversion.
#
#   deploy/preselection-window.sh                       # affiche les exports
#   deploy/preselection-window.sh --apply               # + applique (stack locale)
#   deploy/preselection-window.sh --apply --url https://ctf.exemple.tg
#   deploy/preselection-window.sh '2026-10-23 19:00'    # début personnalisé
#
# Réglages (env) : PRESEL_HOURS=53  FREEZE_BEFORE_MIN=60
# Sans argument de date, reprend deploy/event-windows.env s'il existe.
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# valeurs décidées par défaut (epoch, GMT)
DEF_START=1792782000   # ven 23 oct 2026 19:00 GMT
DEF_END=1792972800     # lun 26 oct 2026 00:00 GMT
DEF_FREEZE=1792969200  # dim 25 oct 2026 23:00 GMT

HOURS="${PRESEL_HOURS:-53}"
FREEZE_MIN="${FREEZE_BEFORE_MIN:-60}"

APPLY=0; URL=""; START_HUMAN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --url) URL="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) START_HUMAN="$1"; shift ;;
  esac
done

if [ -n "$START_HUMAN" ]; then
  # début fourni -> calcule end/freeze depuis la durée
  if ! START=$(date -u -d "$START_HUMAN" +%s 2>/dev/null); then
    echo "!! date illisible : '$START_HUMAN' (attendu : 'AAAA-MM-JJ HH:MM')" >&2; exit 2
  fi
  END=$((START + HOURS * 3600)); FREEZE=$((END - FREEZE_MIN * 60))
elif [ -f "$ROOT/deploy/event-windows.env" ] \
     && grep -q '^CTF_START=' "$ROOT/deploy/event-windows.env"; then
  # reprend le fichier décidé
  # shellcheck disable=SC1090
  set -a; . <(grep -E '^CTF_(START|END|FREEZE)=' "$ROOT/deploy/event-windows.env" | sed 's/#.*//'); set +a
  START="$CTF_START"; END="$CTF_END"; FREEZE="$CTF_FREEZE"
else
  START="$DEF_START"; END="$DEF_END"; FREEZE="$DEF_FREEZE"
fi

fmt() { date -u -d "@$1" '+%a %d %b %Y %H:%M GMT'; }
echo "Présélection — fenêtre (GMT / Lomé) :"
printf "  début  %s   (epoch %s)\n" "$(fmt "$START")"  "$START"
printf "  freeze %s   (epoch %s)   [dernière heure]\n" "$(fmt "$FREEZE")" "$FREEZE"
printf "  fin    %s   (epoch %s)   [+%s h]\n" "$(fmt "$END")" "$END" "$(( (END-START)/3600 ))"
echo
echo "  export CTF_START=$START CTF_END=$END CTF_FREEZE=$FREEZE"

if [ "$APPLY" = "1" ]; then
  echo
  echo ">> application via le seed${URL:+ (--url $URL)} ..."
  export CTF_START="$START" CTF_END="$END" CTF_FREEZE="$FREEZE"
  if [ -n "$URL" ]; then
    python3 "$ROOT/deploy/local/seed.py" --url "$URL" --no-challenges
  else
    make -C "$ROOT/deploy" local-seed
  fi
  echo ">> fenêtre appliquée. Vérifier : make preflight PHASE=preselection CTFD_TOKEN=... (prod)"
fi
