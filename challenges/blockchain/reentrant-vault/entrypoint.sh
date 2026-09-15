#!/bin/sh
# Start a local anvil node (internal only), then the launcher/oracle which
# deploys+seeds the Vault, funds a player, proxies JSON-RPC, and gates the flag.
set -eu
anvil --host 127.0.0.1 --port 8545 --silent &
# wait for the RPC to answer before deploying
i=0
while ! python3 -c "import urllib.request,json;urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8545',data=b'{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"web3_clientVersion\",\"params\":[]}',headers={'Content-Type':'application/json'}),timeout=2)" 2>/dev/null; do
    i=$((i+1)); [ "$i" -gt 60 ] && { echo "anvil did not come up" >&2; exit 1; }
    sleep 0.5
done
echo "[entrypoint] anvil up; launching oracle" >&2
exec python3 /opt/chall/src/oracle.py
