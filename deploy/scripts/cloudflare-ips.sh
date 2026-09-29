#!/usr/bin/env bash
# Plages IP du proxy Cloudflare (source officielle, sans authentification).
#   scripts/cloudflare-ips.sh            # IPv4, une par ligne
#   scripts/cloudflare-ips.sh --tfvars   # au format liste HCL pour web_cidrs
#   scripts/cloudflare-ips.sh --nginx    # bloc set_real_ip_from pour nginx
set -euo pipefail
json=$(curl -fsS https://api.cloudflare.com/client/v4/ips)
v4=$(printf '%s' "$json" | python3 -c 'import sys,json; print("\n".join(json.load(sys.stdin)["result"]["ipv4_cidrs"]))')
case "${1:-}" in
  --tfvars) printf 'web_cidrs = [\n'; printf '%s\n' "$v4" | sed 's/^/  "/; s/$/",/'; printf ']\n' ;;
  --nginx)  printf '%s\n' "$v4" | sed 's/^/set_real_ip_from /; s/$/;/' ;;
  *)        printf '%s\n' "$v4" ;;
esac
