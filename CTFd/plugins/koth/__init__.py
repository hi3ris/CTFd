"""King-of-the-Hill scoring plugin.

A KotH is a *shared* service (the "hill") that everyone attacks. Whoever has
planted their team's opaque token as the hill's current "king" earns points on
every scoring tick. There is no flag to submit: points accrue as `Awards`, which
`CTFd.utils.scores.get_standings` already sums into the scoreboard, so the kart
scoreboard reflects a held hill automatically.

Three secrets, deliberately separated (see settings.py):

  * HILL_KEY          lives ONLY on the hill container; authorises a claim. It is
                      the thing players must exploit out of the hill. CTFd never
                      sees it.
  * KOTH_SCORER_SECRET  CTFd -> hill trusted read of /king (X-Scorer-Token).
  * KOTH_GLOBAL_SECRET  CTFd-side derivation of each team's opaque hill token.
                      The hill never computes it and cannot map a token to a team;
                      only CTFd can. A player learns only their OWN token.

Flow: a player reads their token from this plugin's page, exploits the hill to
obtain HILL_KEY, then repeatedly signs fresh claims with (token, ts) to keep the
throne. The freshness window (settings.fresh_window) means a single claim decays,
so holding requires continuous re-claiming -- the KotH contest.
"""

import fcntl
import hashlib
import hmac
import json
import threading
import time
import urllib.error
import urllib.request

from flask import Blueprint, Response, jsonify

from CTFd.models import Awards, Teams, Users, db
from CTFd.plugins import register_user_page_menu_bar
from CTFd.utils.config import is_teams_mode
from CTFd.utils.decorators import authed_only, ratelimit
from CTFd.utils.user import get_current_user

from . import settings

bp = Blueprint("koth", __name__, template_folder="templates", static_folder="assets")

_SCORER_LOCK_PATH = "/tmp/ctfd_koth_scorer.lock"  # nosec B108 - lock file, not data


# --------------------------------------------------------------------------
# Per-team token derivation
# --------------------------------------------------------------------------
def koth_token_for(account_id, koth_id: str) -> str:
    """The opaque token a team plants on the hill to claim the throne.

    Derived from KOTH_GLOBAL_SECRET so it is unguessable and unique per team AND
    per hill. 16 hex (64 bits) is short enough to paste yet infeasible to guess.
    The hill treats it as an opaque string; only CTFd can map it back to a team.
    """
    return hmac.new(
        settings.global_secret().encode("utf-8"),
        f"koth:{koth_id}:{account_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]


def _accounts():
    """(account_id, name) for every scoring account, honouring the CTF mode.

    Hidden/banned accounts are excluded so they can neither hold nor appear."""
    model = Teams if is_teams_mode() else Users
    rows = []
    for a in model.query.all():
        if getattr(a, "hidden", False) or getattr(a, "banned", False):
            continue
        rows.append((a.id, a.name))
    return rows


def _resolve(token: str, koth_id: str):
    """Map a planted token back to (account_id, name), or None. Constant-time
    per candidate so a timing side-channel cannot enumerate tokens."""
    if not token:
        return None
    for aid, name in _accounts():
        if hmac.compare_digest(koth_token_for(aid, koth_id), token):
            return (aid, name)
    return None


# --------------------------------------------------------------------------
# Talking to a hill
# --------------------------------------------------------------------------
def _poll_king(hill: dict) -> dict:
    """Read a hill's current king. Raises on any transport/parse error."""
    url = hill["url"] + "/king"
    if not url.startswith(("http://", "https://")):
        raise ValueError("hill url must be http(s)")
    req = urllib.request.Request(
        url, headers={"X-Scorer-Token": settings.scorer_secret()}
    )
    with urllib.request.urlopen(  # nosec B310 - internal arena hill, scheme checked
        req, timeout=settings.http_timeout()
    ) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


# --------------------------------------------------------------------------
# Scorer
# --------------------------------------------------------------------------
def _score_once(app):
    with app.app_context():
        now = time.time()
        teams_mode = is_teams_mode()
        for hill in settings.hills():
            try:
                king = _poll_king(hill)
            except Exception:  # nosec B112 - one unreachable hill must not stop others
                continue
            token = str(king.get("token") or "").strip()
            try:
                ts = float(king.get("ts") or 0)
            except (TypeError, ValueError):
                ts = 0
            # No fresh claim -> nobody scores this tick.
            if not token or (now - ts) > settings.fresh_window():
                continue
            holder = _resolve(token, hill["id"])
            if holder is None:
                continue
            aid, _name = holder
            award = Awards(
                type="koth",
                name="{} — hill tick".format(hill["name"]),
                category="koth:{}".format(hill["id"]),
                value=hill["points"],
                icon="crown",
            )
            if teams_mode:
                award.team_id = aid
            else:
                award.user_id = aid
            db.session.add(award)
        db.session.commit()


def _scorer_loop(app):
    # Only one worker scores. Hold an exclusive fcntl lock for the process
    # lifetime; workers that fail to acquire it simply exit the loop.
    lock_file = open(_SCORER_LOCK_PATH, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return  # another worker owns the scorer
    while True:
        try:
            _score_once(app)
        except Exception:  # nosec B110 - scorer loop must survive a single bad pass
            pass
        time.sleep(settings.tick_seconds())


# --------------------------------------------------------------------------
# Player-facing state
# --------------------------------------------------------------------------
def _leaderboard(koth_id: str, name_by_id: dict, limit: int = 5):
    col = Awards.team_id if is_teams_mode() else Awards.user_id
    rows = (
        db.session.query(col.label("aid"), db.func.sum(Awards.value).label("score"))
        .filter(Awards.category == "koth:{}".format(koth_id))
        .group_by(col)
        .order_by(db.func.sum(Awards.value).desc())
        .limit(limit)
        .all()
    )
    return [
        {"name": name_by_id.get(aid, "?"), "score": int(score or 0)}
        for aid, score in rows
        if aid is not None
    ]


@bp.route("/api/state")
@authed_only
@ratelimit(method="GET", limit=60, interval=60)
def api_state():
    user = get_current_user()
    aid = user.account_id
    now = time.time()
    name_by_id = dict(_accounts())
    fresh = settings.fresh_window()
    out = []
    for hill in settings.hills():
        king = None
        try:
            k = _poll_king(hill)
            ktok = str(k.get("token") or "")
            try:
                kts = float(k.get("ts") or 0)
            except (TypeError, ValueError):
                kts = 0
            holder = _resolve(ktok, hill["id"]) if ktok else None
            king = {
                "token_preview": (ktok[:8] + "…") if ktok else None,
                "holder": holder[1] if holder else None,
                "held_seconds": int(max(0, now - kts)) if ktok else None,
                "fresh": bool(ktok and (now - kts) <= fresh),
                "is_you": bool(holder and holder[0] == aid),
            }
        except Exception:  # nosec B110 - hill down: show it as offline, not an error
            king = None
        out.append(
            {
                "id": hill["id"],
                "name": hill["name"],
                "player_url": hill["player_url"],
                "points": hill["points"],
                "your_token": koth_token_for(aid, hill["id"]),
                "king": king,
                "top": _leaderboard(hill["id"], name_by_id),
            }
        )
    return jsonify(
        {"active": settings.is_active(), "tick": settings.tick_seconds(), "hills": out}
    )


@bp.route("/")
@authed_only
def page():
    return Response(_PAGE_HTML, mimetype="text/html")


def load(app):
    app.register_blueprint(bp, url_prefix="/plugins/koth")
    register_user_page_menu_bar("King of the Hill", "/plugins/koth/")

    if settings.is_active():
        t = threading.Thread(target=_scorer_loop, args=(app,), daemon=True)
        t.start()


# --------------------------------------------------------------------------
# Player page (self-contained; polls /plugins/koth/api/state)
# --------------------------------------------------------------------------
_PAGE_HTML = r"""<!doctype html>
<html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>King of the Hill</title>
<style>
  :root{ --red:#d21034; --yellow:#ffce00; --green-b:#17b06b; --bg:#00040d;
    --panel:#0b0f18; --line:#1c2431; --fg:#fff; --muted:#9aa4b2; --gold:#f9d77e; }
  body{ margin:0; background:var(--bg); color:var(--fg);
    font-family:'Lato',system-ui,sans-serif; padding:24px 16px 48px; }
  .wrap{ max-width:900px; margin:0 auto; }
  h1{ font-family:'Tourney',system-ui,sans-serif; text-transform:uppercase;
    letter-spacing:2px; margin:.2rem 0; }
  .sub{ color:var(--muted); font-family:'JetBrains Mono',monospace; font-size:.8rem;
    letter-spacing:2px; text-transform:uppercase; margin-bottom:1.2rem; }
  .card{ background:var(--panel); border:1px solid var(--line); border-radius:14px;
    padding:18px 20px; margin:16px 0; }
  .card h2{ margin:.1rem 0 .2rem; font-size:1.2rem; }
  .row{ display:flex; flex-wrap:wrap; gap:12px 28px; align-items:baseline; }
  .k{ color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:1px; }
  code,.mono{ font-family:'JetBrains Mono',monospace; }
  .tok{ background:#05070d; border:1px solid var(--line); border-radius:8px;
    padding:.4rem .7rem; color:var(--gold); font-weight:700; user-select:all; }
  .crown{ color:var(--yellow); }
  .held{ display:inline-flex; align-items:center; gap:.5rem; font-weight:700; }
  .dot{ width:9px; height:9px; border-radius:50%; background:var(--muted); }
  .dot.on{ background:var(--green-b); box-shadow:0 0 8px var(--green-b); }
  .you{ color:var(--green-b); }
  table{ width:100%; border-collapse:collapse; margin-top:.6rem; }
  td,th{ text-align:left; padding:.35rem .2rem; border-bottom:1px solid rgba(255,255,255,.05); }
  th{ color:var(--muted); font-size:.68rem; text-transform:uppercase; letter-spacing:1px; }
  .score{ text-align:right; color:var(--gold); font-family:'JetBrains Mono',monospace; }
  .muted{ color:var(--muted); }
  .warn{ color:var(--red); }
  a{ color:var(--yellow); }
  details{ margin-top:.7rem; } summary{ cursor:pointer; color:var(--muted); }
  pre{ background:#05070d; border:1px solid var(--line); border-radius:8px;
    padding:.7rem; overflow:auto; font-size:.8rem; }
</style></head>
<body><div class="wrap">
  <h1>👑 King of the Hill</h1>
  <div class="sub">Tenez la colline &middot; NCTF26</div>
  <div id="hills"><p class="muted">Chargement…</p></div>
  <p class="muted" style="font-size:.78rem">
    Le classement se met à jour tout seul. Les points de KotH s'ajoutent à votre
    score sur le scoreboard principal, tick après tick, tant que vous tenez la
    colline.</p>
</div>
<script>
function esc(s){var d=document.createElement("div");d.textContent=s==null?"":String(s);return d.innerHTML;}
function fmtDur(s){ if(s==null)return "—"; s=Math.max(0,s|0); var m=(s/60)|0; return m?(m+"m "+(s%60)+"s"):(s+"s"); }
function render(state){
  var el=document.getElementById("hills");
  if(!state.active){ el.innerHTML='<div class="card"><p class="warn">Le King of the Hill n\'est pas encore actif.</p><p class="muted">Il ouvrira au démarrage de l\'épreuve.</p></div>'; return; }
  if(!state.hills.length){ el.innerHTML='<div class="card"><p class="muted">Aucune colline configurée.</p></div>'; return; }
  el.innerHTML = state.hills.map(function(h){
    var k=h.king;
    var held = k && k.token_preview
      ? '<span class="held"><span class="dot '+(k.fresh?'on':'')+'"></span>'
        + (k.is_you? '<span class="you">VOUS tenez la colline</span>'
                   : ('<span class="crown">'+esc(k.holder||k.token_preview)+'</span>'))
        + ' <span class="muted">· depuis '+fmtDur(k.held_seconds)+(k.fresh?'':' (expiré)')+'</span></span>'
      : '<span class="muted">colline libre (personne ne tient le trône)</span>';
    var rows = (h.top||[]).map(function(t,i){
      return '<tr><td>'+(i+1)+'</td><td>'+esc(t.name)+'</td><td class="score">'+t.score+'</td></tr>';
    }).join('') || '<tr><td colspan="3" class="muted">pas encore de points</td></tr>';
    return '<div class="card">'
      + '<h2>'+esc(h.name)+' <span class="muted mono" style="font-size:.7rem">'+esc(h.id)+'</span></h2>'
      + '<div class="row">'
      +   '<div><div class="k">Trône</div>'+held+'</div>'
      +   '<div><div class="k">Points / tick</div><b>'+h.points+'</b></div>'
      +   '<div><div class="k">Connexion</div><code>'+esc(h.player_url)+'</code></div>'
      + '</div>'
      + '<div class="row" style="margin-top:.8rem"><div style="flex:1 1 100%">'
      +   '<div class="k">Votre jeton d\'équipe (à planter sur la colline)</div>'
      +   '<span class="tok">'+esc(h.your_token)+'</span></div></div>'
      + '<details><summary>Comment marquer</summary>'
      +   '<pre>1. Récupérez la clé de la colline en exploitant le service ('+esc(h.player_url)+').\n'
      +   '2. Signez une revendication fraîche pour VOTRE jeton et postez-la sur le trône.\n'
      +   '3. Rejouez-la en boucle : une revendication expire, il faut re-tenir la colline.\n'
      +   'Le scorer vous attribue '+h.points+' pts à chaque tick ('+state.tick+'s) où vous tenez le trône.</pre>'
      + '</details>'
      + '<table><thead><tr><th>#</th><th>Équipe</th><th class="score">Points KotH</th></tr></thead>'
      +   '<tbody>'+rows+'</tbody></table>'
      + '</div>';
  }).join('');
}
function tick(){
  fetch("api/state",{headers:{"Accept":"application/json"},credentials:"same-origin"})
    .then(function(r){return r.ok?r.json():null;})
    .then(function(s){ if(s) render(s); })
    .catch(function(){});
}
tick(); setInterval(tick, 10000);
</script>
</body></html>
"""
