"""Token lockdown — restrict API access-token creation to admins.

By default any authenticated player can mint a personal API token
(``POST /api/v1/tokens``) from *Settings → Access Tokens*. During NCTF26 that
token is a ready-made automation key: a player could script challenge
submissions, instance spins, or scoreboard scraping straight against the API,
around every UI-level rate limit and CTF-time guard.

This plugin closes that off:

  * ``POST /api/v1/tokens`` is gated to admins only. Players get ``403``; the
    admin's own deploy token — the one ctfcli / ``make preflight`` /
    ``make reglement-publish`` rely on — still works, because the admin is
    ``is_admin()`` and passes straight through.
  * In the hibris theme the *Access Tokens* tab and its pane are hidden from
    non-admins (``themes/hibris/templates/settings.html`` wraps them in
    ``{% if is_admin() %}``).

The API gate is the real control; hiding the tab is cosmetic. Other themes
still render the tab, but the gate applies to every theme because it wraps the
request, not the page.

Scope is deliberately narrow: only *creation* is restricted. ``GET`` and
``DELETE`` on existing tokens are untouched, so a token minted before this was
loaded (or by an admin) keeps working and can still be listed / revoked by its
owner. No new tables, no config, no migration.

The gate is an app-scoped ``before_request`` rather than a monkeypatch of the
endpoint class: it is registered per-app during ``load(app)`` (so it runs after
CTFd's own token-auth ``before_request`` populated the current user), and it
leaves no global state behind — the test suite loads and tears down many apps.
"""

from flask import abort, request

from CTFd.utils.user import is_admin

# Path (relative to the app's script root) of the token collection endpoint.
_TOKENS_PATH = "/api/v1/tokens"


def load(app):
    @app.before_request
    def _gate_token_creation():
        if request.method != "POST":
            return
        if request.path.rstrip("/") != _TOKENS_PATH:
            return
        # Admins (including the deploy-token owner, whether authenticated by
        # session or by an existing admin token) pass through; anyone else —
        # players and unauthenticated callers alike — is refused.
        if not is_admin():
            abort(403)
