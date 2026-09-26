#!/usr/bin/env bash
# =============================================================================
# NCTF26 — fenêtre de la FINALE : tu donnes l'HEURE DE DÉBUT (le jour J, après
# la cérémonie), le script calcule le reste. Durée FIXE 24 h, freeze la dernière
# heure. Heure de Lomé = GMT (UTC+0), donc pas de conversion.
#
#   deploy/finale-window.sh '2026-10-29 10:30'            # affiche les exports
#   deploy/finale-window.sh '2026-10-29 10:30' --apply    # + lance le seed (local)
#   deploy/finale-window.sh '2026-10-29 10:30' --apply --url https://ctf.exemple.tg
#
# Réglages optionnels (env) : FINALE_HOURS=24  FREEZE_BEFORE_MIN=60
# =============================================================================
set -euo pipefail

START_HUMAN="${1:-}"
if [ -z "$START_HUMAN" ]; then
  echo "usage: $0 'AAAA-MM-JJ HH:MM' [--apply] [--url URL]" >&2
  echo "  ex : $0 '2026-10-29 10:30'   # début finale (GMT/Lomé), jamais après 12:00" >&2
  exit 2
fi
shift || true

HOURS="${FINALE_HOURS:-24}"
FREEZE_MIN="${FREEZE_BEFORE_MIN:-60}"

# epoch (interprété en UTC = heure de Lomé)
if ! START=$(date -u -d "$START_HUMAN" +%s 2>/dev/null); then
  echo "!! date illisible : '$START_HUMAN' (attendu : 'AAAA-MM-JJ HH:MM')" >&2
  exit 2
fi
END=$((START + HOURS * 3600))
FREEZE=$((END - FREEZE_MIN * 60))

# garde-fous : la finale commence le 29 oct et jamais après midi
day=$(date -u -d "@$START" +%Y-%m-%d)
hour=$(date -u -d "@$START" +%H)
[ "$day" = "2026-10-29" ] || echo "   (info) début le $day — attendu 2026-10-29" >&2
[ "$((10#$hour))" -le 12 ] || echo "   (attention) début après 12:00 GMT — 'on ne dépassera pas midi' ?" >&2

fmt() { date -u -d "@$1" '+%a %d %b %Y %H:%M GMT'; }
echo "Finale — fenêtre calculée (GMT / Lomé) :"
printf "  début  %s   (epoch %s)\n" "$(fmt "$START")"  "$START"
printf "  freeze %s   (epoch %s)   [dernière heure]\n" "$(fmt "$FREEZE")" "$FREEZE"
printf "  fin    %s   (epoch %s)   [+%s h]\n" "$(fmt "$END")" "$END" "$HOURS"
echo
echo "  export CTF_START=$START CTF_END=$END CTF_FREEZE=$FREEZE"

if [ "${1:-}" = "--apply" ] || [ "${2:-}" = "--apply" ]; then
  URL=""
  # récupère --url si fourni
  while [ $# -gt 0 ]; do
    case "$1" in
      --url) URL="${2:-}"; shift 2 ;;
      *) shift ;;
    esac
  done
  echo
  echo ">> application via le seed${URL:+ (--url $URL)} ..."
  export CTF_START="$START" CTF_END="$END" CTF_FREEZE="$FREEZE"
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  if [ -n "$URL" ]; then
    python3 "$ROOT/deploy/local/seed.py" --url "$URL"
  else
    make -C "$ROOT/deploy" local-seed
  fi
fi
