#!/usr/bin/env python3
"""Hookrelay -- internal Git mirror healthcheck (CVE-2022-24439 reproduction).

Scenario: an internal CI tool that, given a repository URL, runs a lightweight
"mirror check" by cloning it with GitPython. The GitPython version pinned here
(3.1.29) does NOT validate the URL before handing it to `git`, so a URL using
the `ext::` transport is executed as a shell command by git's remote-ext
helper -- exactly CVE-2022-24439. The service surfaces git's stderr back to the
caller, which is the channel the operator uses to read the flag.

The vulnerability, faithfully:
  * GitPython 3.1.29: Repo.clone_from(url, ...) passes `url` straight to git.
    No allow_unsafe_protocols / allow_unsafe_options gate (those were ADDED in
    3.1.30 as the fix).
  * The image sets `git config --global protocol.ext.allow always`, standing in
    for a real-world "internal mirror allows ext transports" misconfiguration,
    so the ext:: helper fires deterministically regardless of the git build.

The fix (3.1.30) is shipped as the paid patch-diff hint; the CVE id is a hint,
never in the description.
"""
import os
import shutil
import tempfile

from flask import Flask, request, send_from_directory

import git  # GitPython 3.1.29 (vulnerable)

app = Flask(__name__)

# A scratch directory the mirror agent uses for build logs. It is world-served
# read-only under /pub/. Nothing sensitive is *placed* here by the app -- but a
# successful CVE-2022-24439 command runs as the agent and can drop a file here,
# which is the read channel the reference solver uses (no attacker callback
# server needed).
PUB_DIR = os.environ.get("PUB_DIR", "/app/pub")

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Hookrelay -- mirror healthcheck</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem}}
 code,pre{{background:#f4f4f4;padding:.15rem .3rem;border-radius:4px}}
 pre{{padding:.8rem;overflow:auto;white-space:pre-wrap}}
 input[type=text]{{width:100%;padding:.5rem;font-family:monospace}}
 .muted{{color:#666}}
</style></head><body>
<h1>Hookrelay</h1>
<p class="muted">Internal Git mirror healthcheck. Paste a repository URL; the
service performs a shallow mirror clone and reports whether the remote is
reachable. Internal mirrors only -- do not point this at production.</p>
<form method="post" action="/check">
  <input type="text" name="repo" placeholder="https://git.internal/team/repo.git"
         value="{repo}" autofocus>
  <p><button type="submit">Run healthcheck</button></p>
</form>
{result}
<hr>
<p class="muted">mirror-agent {version} &middot; operated by the CI platform team</p>
</body></html>
"""


def _render(repo="", result=""):
    return PAGE.format(
        repo=_html_escape(repo),
        result=result,
        version=git.__version__,
    )


def _html_escape(s):
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@app.route("/")
def index():
    return _render()


@app.route("/pub/<path:name>")
def pub(name):
    # Read-only view of the agent's scratch dir. send_from_directory rejects
    # traversal, so this is not itself the vuln -- it is only useful once the
    # CVE has dropped a file here.
    return send_from_directory(PUB_DIR, name)


@app.route("/check", methods=["POST"])
def check():
    repo = (request.form.get("repo") or "").strip()
    if not repo:
        return _render(result="<p>Give a repository URL.</p>"), 400

    tmp = tempfile.mkdtemp(prefix="mirror-")
    try:
        # VULNERABLE SINK (CVE-2022-24439): the operator-supplied URL is handed
        # to git with no scheme validation. GitPython 3.1.29 offers no
        # allow_unsafe_protocols gate, so an ext:: URL runs as a command.
        git.Repo.clone_from(repo, tmp, multi_options=["--depth", "1"])
        reachable = True
        detail = ""
    except git.exc.GitCommandError as exc:
        # The mirror check "failed"; report git's own diagnostics so an operator
        # can see why. git surfaces the remote helper's stderr here.
        reachable = False
        detail = str(exc.stderr or exc)
    except Exception as exc:  # noqa: BLE001 -- operator-facing diagnostic
        reachable = False
        detail = f"{exc.__class__.__name__}: {exc}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if reachable:
        body = "<p><b>OK</b> &mdash; remote reachable, mirror clone succeeded.</p>"
    else:
        body = (
            "<p><b>Unreachable</b> &mdash; mirror clone failed. Git said:</p>"
            f"<pre>{_html_escape(detail)}</pre>"
        )
    return _render(repo=repo, result=body)


if __name__ == "__main__":
    # The flag lives in a file only the exploited command can read; it is never
    # served by any route. entrypoint.sh writes it from get_flag() at boot.
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
