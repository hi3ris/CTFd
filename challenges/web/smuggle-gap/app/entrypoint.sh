#!/bin/sh
# Start the internal app (loopback-only) and then the edge proxy (exposed).
# The edge runs in the foreground so the container's lifecycle follows it.
set -e

: "${BACKEND_HOST:=127.0.0.1}"
: "${BACKEND_PORT:=9000}"
: "${FRONT_PORT:=8080}"
export BACKEND_HOST BACKEND_PORT FRONT_PORT

python backend.py &
BACKEND_PID=$!

# Give the internal app a moment to bind before the edge starts forwarding.
i=0
while [ "$i" -lt 50 ]; do
    if python - <<PY 2>/dev/null
import socket, os
s = socket.socket()
s.settimeout(0.2)
s.connect((os.environ["BACKEND_HOST"], int(os.environ["BACKEND_PORT"])))
s.close()
PY
    then
        break
    fi
    i=$((i + 1))
    sleep 0.1
done

trap 'kill "$BACKEND_PID" 2>/dev/null || true' INT TERM
exec python front.py
