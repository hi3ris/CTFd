#!/usr/bin/env bash
# Recompile handout/chall dans un conteneur Ubuntu 20.04 (glibc 2.31), puis le
# patchelf sur le loader + libc livres, exactement comme le fait le Dockerfile.
#
# A lancer UNE FOIS sur une machine avec Docker, quand `make local-build-images`
# echoue sur heap-note avec "requires GLIBC_2.34 > pinned GLIBC_2.31" (binaire
# compile par erreur sur une glibc trop recente).
#
#   cd challenges/pwn/heap-note && ./rebuild-binary.sh
#   # puis, depuis deploy/ :  make local-build-images ONLY=heap-note
#
# Les memes flags que le Makefile (-O0 -fno-stack-protector -no-pie). Le solveur
# resout win()/__free_hook dynamiquement (exe.sym/libc.sym) : aucune adresse a
# re-deriver a la main apres le rebuild.
set -euo pipefail
cd "$(dirname "$0")"

echo ">> compilation de chall dans ubuntu:20.04 (glibc 2.31)"
docker run --rm -v "$PWD:/src" -w /src ubuntu:20.04 bash -c '
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends gcc libc6-dev patchelf binutils >/dev/null
  gcc -O0 -fno-stack-protector -no-pie -Wall -o handout/chall chall.c
  patchelf --set-interpreter handout/ld-2.31.so --set-rpath handout handout/chall
  maxglibc=$(objdump -T handout/chall | grep -oE "GLIBC_[0-9]+\.[0-9]+" | sort -uV | tail -1)
  echo "   chall max GLIBC requirement: ${maxglibc:-none} (attendu <= 2.31)"
  echo "$maxglibc" | awk -F"[_.]" "{ if (\$2>2 || (\$2==2 && \$3>31)) { print \"FATAL: toujours > 2.31\"; exit 1 } }"
'
echo ">> OK. handout/chall recompile pour glibc 2.31."
echo "   Verifie/commit le binaire, puis : (depuis deploy/) make local-build-images ONLY=heap-note"
