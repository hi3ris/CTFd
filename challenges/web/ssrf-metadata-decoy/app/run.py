"""
Supervisor: start all three services in one non-root process.

  * public proxy        -> 0.0.0.0:8080     (published)
  * decoy metadata      -> 169.254.169.254:80  (link-local; unpublished)
  * internal registry   -> 0.0.0.0:9137     (loopback mesh; unpublished)

The link-local alias 169.254.169.254 is added to `lo` by entrypoint.sh (which
runs as root before dropping to appuser). If that alias is unavailable (no
NET_ADMIN), we fall back to 127.0.0.254 so the decoy still answers -- but the
canonical solve path uses the link-local IP as advertised in robots.txt.

Binding port 80 as a non-root user is permitted via a file capability
(cap_net_bind_service) set on the interpreter in the Dockerfile.
"""
import socket
import threading
import time

from werkzeug.serving import make_server

import proxy
import metadata
import internal


class ServerThread(threading.Thread):
    def __init__(self, app, host, port, label):
        super().__init__(daemon=True)
        self.label = label
        self.host = host
        self.port = port
        self._srv = make_server(host, port, app, threaded=True)
        self._ctx = app.app_context()
        self._ctx.push()

    def run(self):
        print(f"[run] {self.label} listening on {self.host}:{self.port}", flush=True)
        self._srv.serve_forever()


def _try_bind(app, candidates, label):
    for host, port in candidates:
        # Probe the bind first: werkzeug's make_server turns a bind OSError into
        # a bare SystemExit, so we check with a raw socket to fail gracefully.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.bind((host, port))
        except OSError as exc:
            print(f"[run] could not bind {label} on {host}:{port}: {exc}", flush=True)
            probe.close()
            continue
        probe.close()
        try:
            t = ServerThread(app, host, port, label)
            t.start()
            return t
        except (OSError, SystemExit) as exc:
            print(f"[run] could not start {label} on {host}:{port}: {exc}", flush=True)
    print(f"[run] WARNING: {label} did not start on any candidate address", flush=True)
    return None


def main():
    # Internal registry / admin (loopback mesh, unpublished).
    _try_bind(internal.app, [("0.0.0.0", 9137)], "internal-registry")

    # Decoy metadata mirror. Prefer the canonical link-local IP; fall back.
    _try_bind(
        metadata.app,
        [("169.254.169.254", 80), ("127.0.0.254", 80)],
        "metadata-decoy",
    )

    # Give the background servers a moment to bind before the proxy answers.
    time.sleep(0.3)

    # Public proxy in the foreground so the container stays attached to it.
    srv = make_server("0.0.0.0", 8080, proxy.app, threaded=True)
    print("[run] proxy listening on 0.0.0.0:8080", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
