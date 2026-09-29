#!/usr/bin/env bash
#
# lot5.sh — répétition Docker (Lot-5) des challenges servis.
#
# Pour chaque servi implémenté : build l'image, lance le conteneur, rejoue le
# solveur de référence contre lui, compare au flag attendu (dérivé du même
# TEAM_SECRET), puis — avec --flip — passe le challenge en `state: visible`.
# C'est la SEULE porte vers le visible (cf. deploy/GOAL.md, définition de fini).
#
# À lancer sur une machine avec Docker (pas dans le conteneur cloud).
#
#   deploy/scripts/lot5.sh                 # tous les servis "IMPLEMENTED", rapport seul
#   deploy/scripts/lot5.sh --flip          # + flip state: visible sur ceux qui passent
#   deploy/scripts/lot5.sh --only web/cms-jwtconf crypto/notarysvc-padoracle
#   deploy/scripts/lot5.sh --all           # tous les servis (même les STUB : échoueront)
#   deploy/scripts/lot5.sh --keep          # ne détruit pas les conteneurs (debug)
#
# Sortie non nulle si au moins un challenge ciblé échoue.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CH="$ROOT/challenges"
PY="${PYTHON:-python3}"
TS="${TEAM_SECRET:-lot5-rehearsal-secret}"   # secret de test, cohérent build<->attendu
BUILD_TIMEOUT="${BUILD_TIMEOUT:-600}"
BOOT_TIMEOUT="${BOOT_TIMEOUT:-40}"
SOLVE_TIMEOUT="${SOLVE_TIMEOUT:-120}"
NO_CACHE="${NO_CACHE:-}"                      # 1 = docker build --no-cache

FLIP=0 ALL=0 KEEP=0
ONLY=()
while [ $# -gt 0 ]; do
  case "$1" in
    --flip) FLIP=1 ;;
    --all) ALL=1 ;;
    --keep) KEEP=1 ;;
    --only) shift; while [ $# -gt 0 ] && [[ "$1" != --* ]]; do ONLY+=("$1"); shift; done; continue ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "argument inconnu: $1" >&2; exit 2 ;;
  esac
  shift
done

command -v docker >/dev/null || { echo "docker introuvable — lancer sur la machine Docker" >&2; exit 2; }
docker info >/dev/null 2>&1 || { echo "daemon Docker injoignable (Docker Desktop démarré ?)" >&2; exit 2; }

# --- sélection des cibles ----------------------------------------------------
targets=()
if [ "${#ONLY[@]}" -gt 0 ]; then
  targets=("${ONLY[@]}")
else
  while IFS= read -r y; do
    rel="$(basename "$(dirname "$y")")"; cat="$(basename "$(dirname "$(dirname "$y")")")"
    # servi ? (type team_instance)
    grep -q "type: team_instance" "$y" || continue
    if [ "$ALL" -eq 0 ]; then
      # implementes (hidden) ou deja passes au Lot-5 (visible) : les STUB sont exclus
      grep -qE "IMPLEMENTED \+ locally verified|Lot-5 rehearsal passed" "$y" || continue
    fi
    targets+=("$cat/$rel")
  done < <(find "$CH" -mindepth 3 -maxdepth 3 -name challenge.yml | sort)
fi

[ "${#targets[@]}" -gt 0 ] || { echo "aucune cible."; exit 0; }
echo "Lot-5 : ${#targets[@]} challenge(s) — TEAM_SECRET=${TS} — flip=${FLIP}"
echo

pass=0 fail=0 skip=0
declare -a FAILED

cleanup_cid() { [ "$KEEP" -eq 1 ] || { [ -n "${1:-}" ] && docker rm -f "$1" >/dev/null 2>&1; }; }

for rel in "${targets[@]}"; do
  cdir="$CH/$rel"; y="$cdir/challenge.yml"
  slug="$(basename "$rel")"; cat="$(dirname "$rel")"
  if [ ! -f "$cdir/Dockerfile" ]; then echo "[skip] $rel : pas de Dockerfile"; skip=$((skip+1)); continue; fi

  # image + port interne depuis challenge.yml
  read -r img iport < <("$PY" - "$y" "$cat" "$slug" <<'PY'
import sys, yaml
y, cat, slug = sys.argv[1], sys.argv[2], sys.argv[3]
d = yaml.safe_load(open(y)) or {}
ex = d.get("extra") or {}
img = ex.get("docker_image") or f"ctf-{cat}-{slug}:latest"
print(img, ex.get("internal_port", 8080))
PY
)

  printf '%-34s ' "$rel"

  # 1) build
  # NO_CACHE=1 : rebuild sans cache (couche COPY flag.py empoisonnee vue quand
  # deux builds de freres au Dockerfile identique se chevauchent).
  if ! timeout "$BUILD_TIMEOUT" docker build ${NO_CACHE:+--no-cache} -q -t "$img" "$cdir" >/tmp/lot5-build.log 2>&1; then
    echo "BUILD-FAIL"; fail=$((fail+1)); FAILED+=("$rel (build)"); tail -3 /tmp/lot5-build.log | sed 's/^/    /'; continue
  fi

  # 2) run (host port éphémère lié à 127.0.0.1)
  cid="$(docker run -d -e "TEAM_SECRET=$TS" -p "127.0.0.1::$iport" "$img" 2>/tmp/lot5-run.log)"
  if [ -z "$cid" ]; then echo "RUN-FAIL"; fail=$((fail+1)); FAILED+=("$rel (run)"); tail -3 /tmp/lot5-run.log | sed 's/^/    /'; continue; fi
  # le mapping de port n'est pas toujours publie a la seconde ou `docker run -d`
  # rend la main : on reessaie quelques fois avant de conclure.
  hostport=""
  for _ in $(seq 1 20); do
    hostport="$(docker port "$cid" "$iport"/tcp 2>/dev/null | head -1 | sed 's/.*://')"
    [ -n "$hostport" ] && break
    sleep 0.5
  done
  if [ -z "$hostport" ]; then echo "PORT-FAIL"; fail=$((fail+1)); FAILED+=("$rel (port)"); cleanup_cid "$cid"; continue; fi
  base="http://127.0.0.1:$hostport"

  # 3) attendre la disponibilité
  up=0
  for _ in $(seq 1 "$BOOT_TIMEOUT"); do
    # NB : ne pas faire `|| echo 000` : -w imprime deja 000 quand curl echoue,
    # on obtenait "000000" et la boucle sortait avant que l'appli n'ecoute.
    code="$(curl -s -o /dev/null -w '%{http_code}' "$base/" 2>/dev/null || true)"
    [ -n "$code" ] && [ "$code" != "000" ] && { up=1; break; }
    sleep 1
  done
  if [ "$up" -eq 0 ]; then echo "BOOT-FAIL"; fail=$((fail+1)); FAILED+=("$rel (boot)"); docker logs "$cid" 2>&1 | tail -4 | sed 's/^/    /'; cleanup_cid "$cid"; continue; fi

  # 4) flag attendu (même dérivation que l'entrypoint : get_flag() avec TEAM_SECRET)
  expect="$("$PY" "$cdir/flag.py" "$TS" 2>/dev/null)"

  # 5) rejouer le solveur de référence
  got="$(timeout "$SOLVE_TIMEOUT" "$PY" "$cdir/solution/solve.py" "$base" 2>/tmp/lot5-solve.log | tail -1)"

  cleanup_cid "$cid"

  # 6) verdict. Un SOLVE-FAIL apres un build AVEC cache est rejoue une fois
  # sans cache : BuildKit reutilise parfois la couche `COPY flag.py` du frere
  # construit juste avant (meme Dockerfile, fichier de meme taille et mtime),
  # et le conteneur sert alors le flag du voisin.
  if [ -n "$expect" ] && [ "$got" != "$expect" ] && [ -z "$NO_CACHE" ] && [ "${_retried:-0}" -eq 0 ]; then
    if timeout "$BUILD_TIMEOUT" docker build --no-cache -q -t "$img" "$cdir" >/tmp/lot5-build.log 2>&1; then
      cid="$(docker run -d -e "TEAM_SECRET=$TS" -p "127.0.0.1::$iport" "$img" 2>/dev/null)"
      if [ -n "$cid" ]; then
        hostport=""; for _ in $(seq 1 20); do hostport="$(docker port "$cid" "$iport"/tcp 2>/dev/null | head -1 | sed 's/.*://')"; [ -n "$hostport" ] && break; sleep 0.5; done
        base="http://127.0.0.1:$hostport"
        for _ in $(seq 1 "$BOOT_TIMEOUT"); do
          code="$(curl -s -o /dev/null -w '%{http_code}' "$base/" 2>/dev/null || true)"
          [ -n "$code" ] && [ "$code" != "000" ] && break; sleep 1
        done
        got="$(timeout "$SOLVE_TIMEOUT" "$PY" "$cdir/solution/solve.py" "$base" 2>/tmp/lot5-solve.log | tail -1)"
        cleanup_cid "$cid"
        [ "$got" = "$expect" ] && printf '(rebuild sans cache) '
      fi
    fi
  fi
  if [ -n "$expect" ] && [ "$got" = "$expect" ]; then
    echo "OK"
    pass=$((pass+1))
    if [ "$FLIP" -eq 1 ]; then
      # passe state: hidden -> visible en GARDANT le commentaire (marqueur IMPLEMENTED
      # lu par lot5.sh, port_served.py et check_challenges.py) + date du passage
      if grep -qE '^state:[[:space:]]*hidden' "$y"; then
        sed -i.bak -E "s/^(state:[[:space:]]*)hidden(.*)$/\1visible\2; Lot-5 rehearsal passed $(date -u +%F)/" "$y" && rm -f "$y.bak"
      fi
    fi
  else
    echo "SOLVE-FAIL (got=${got:-<vide>} exp=${expect:-<vide>})"
    fail=$((fail+1)); FAILED+=("$rel (solve)")
    tail -3 /tmp/lot5-solve.log 2>/dev/null | sed 's/^/    /'
  fi
done

echo
echo "=== Lot-5 : pass=$pass fail=$fail skip=$skip ==="
if [ "$fail" -gt 0 ]; then
  printf '  FAIL: %s\n' "${FAILED[@]}"
  echo "  (les FAIL restent state: hidden)"
  exit 1
fi
[ "$FLIP" -eq 1 ] && echo "  challenges vérifiés passés en state: visible — commit + push pour publier."
exit 0
