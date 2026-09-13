#!/usr/bin/env bash
# Construit les images des challenges SERVIS (type team_instance) sous le nom
# attendu par l'instancier et par `make push-images` : ctf-<nom>:latest.
#
#   deploy/local/build-images.sh              # tous
#   deploy/local/build-images.sh jwt-cousin   # un seul (nom du dossier)
#   NO_CACHE=1 deploy/local/build-images.sh   # rebuild complet
#
# Ne s'arrete pas au premier echec : construit tout, puis liste ce qui a rate
# et sort en erreur si au moins une image manque.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ONLY="${1:-}"
CACHE_FLAG=""; [ "${NO_CACHE:-0}" = "1" ] && CACHE_FLAG="--no-cache"

ok=(); ko=(); skipped=()
for yml in "$ROOT"/challenges/*/*/challenge.yml; do
  dir="$(dirname "$yml")"; name="$(basename "$dir")"
  [ -n "$ONLY" ] && [ "$name" != "$ONLY" ] && continue
  grep -qE '^type:\s*"?team_instance"?' "$yml" || continue
  if [ ! -f "$dir/Dockerfile" ]; then
    echo "!! $name : type team_instance mais pas de Dockerfile"; ko+=("$name"); continue
  fi
  # docker_image declare dans challenge.yml (extra:), sinon convention.
  image="$(sed -nE 's/^[[:space:]]+docker_image:[[:space:]]*"?([^"[:space:]]+)"?.*/\1/p' "$yml" | head -1)"
  image="${image:-ctf-$name:latest}"
  echo ">> $name  ->  $image"
  if docker build $CACHE_FLAG -t "$image" "$dir" >"$dir/.build.log" 2>&1; then
    ok+=("$image"); rm -f "$dir/.build.log"
  else
    ko+=("$name"); echo "   ECHEC (voir $dir/.build.log)"; tail -5 "$dir/.build.log" | sed 's/^/   | /'
  fi
done

echo
echo "Construites : ${#ok[@]}"; printf '  %s\n' "${ok[@]}"
if [ ${#ko[@]} -gt 0 ]; then
  echo "EN ECHEC    : ${#ko[@]}"; printf '  %s\n' "${ko[@]}"
  exit 1
fi
