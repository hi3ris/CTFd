#!/usr/bin/env python3
"""Réseau Fortune — shared MLM arena that is ALSO a King-of-the-Hill hill.

FICTION / SIMULATION. A deliberately vulnerable marketing-network ("MLM")
economy shared by all teams. No real money, no SMS (the phone is only a string).
Each team joins with its KotH token (from the CTFd "King of the Hill" page),
gets a distributor account seeded with a little capital, and competes to grow
the richest network. The scorer crowns whichever team is richest right now:

    GET /king   (header X-Scorer-Token: SCORER_SECRET)
      -> {"token": <richest team's KotH token>, "ts": <float>}

The KotH plugin polls /king every tick and awards points to the current holder,
so the team that stays richest longest wins. Legitimate play LOSES money (the
house keeps most of every purchase); registering fake members is free but nets
nothing. You must find a business-logic flaw that mints money faster than your
rivals, and keep the crown.

State is in-memory and per-container (ephemeral, shared across teams).
"""
import os
import re
import threading
import time

from flask import Flask, jsonify, request, session

app = Flask(__name__)
app.secret_key = os.urandom(16)

SCORER_SECRET = os.environ.get("SCORER_SECRET", "")
# Shared arena: a light per-IP rate limit on /api/* protects every team from one
# team flooding the box. Generous by default (does not hinder legit exploitation);
# lower RATE_PER_MIN in ops if needed. Also put a rate limit at the front proxy.
RATE_PER_MIN = int(os.environ.get("RATE_PER_MIN", "1200"))
_RATE = {}  # ip -> [window_start_min, count]

# --- economy constants (FCFA, integers) ------------------------------------
SEED = 50_000
PRODUCTS = {"starter": 5_000, "vip": 20_000, "booster": 2_000}
RATES_PERMILLE = [200, 80, 40]
PRIME_ACTIVATION = 3_000
PHONE_RE = re.compile(r"^(\+?228)?[0-9]{8}$")
TOKEN_RE = re.compile(r"^[0-9a-f]{16}$")  # KotH token shape (16 hex)

_LOCK = threading.Lock()
_ACCOUNTS = {}  # code -> account
_BY_PHONE = {}  # phone -> code
_ROOT_BY_TOKEN = {}  # koth token -> root code
_SEQ = [0]


def _new_code(prefix="M"):
    _SEQ[0] += 1
    return f"{prefix}{_SEQ[0]:06d}"


def _mk(code, phone, sponsor, wallet=0, token=None):
    acc = {
        "code": code,
        "phone": phone,
        "sponsor": sponsor,
        "wallet": wallet,
        "activated": False,
        "commissions": 0,
        "orders": {},
        "order_seq": 0,
        "token": token,  # set only on team root accounts
    }
    _ACCOUNTS[code] = acc
    if phone:
        _BY_PHONE[phone] = code
    return acc


def _me():
    code = session.get("code")
    return _ACCOUNTS.get(code) if code else None


def _pay_commissions(buyer, cost):
    sponsor_code = buyer["sponsor"]
    for rate in RATES_PERMILLE:
        if not sponsor_code:
            break
        sp = _ACCOUNTS.get(sponsor_code)
        if not sp:
            break
        amount = cost * rate // 1000
        sp["wallet"] += amount
        sp["commissions"] += amount
        sponsor_code = sp["sponsor"]


def _net_gain(acc):
    return acc["wallet"] - (SEED if acc.get("token") else 0)


def _public(acc):
    return {
        "code": acc["code"],
        "phone": acc["phone"],
        "sponsor": acc["sponsor"],
        "wallet": acc["wallet"],
        "activated": acc["activated"],
        "commissions": acc["commissions"],
        "net_gain": _net_gain(acc),
    }


@app.before_request
def _rate_limit():
    # Only throttle player API calls; leave "/", "/king" and static alone.
    if not request.path.startswith("/api/"):
        return None
    ip = (
        (request.headers.get("X-Forwarded-For", request.remote_addr or "?"))
        .split(",")[0]
        .strip()
    )
    window = int(time.time() // 60)
    with _LOCK:
        slot = _RATE.get(ip)
        if not slot or slot[0] != window:
            _RATE[ip] = [window, 0]
            slot = _RATE[ip]
        slot[1] += 1
        over = slot[1] > RATE_PER_MIN
    if over:
        return jsonify(error="trop de requêtes, réessaie dans une minute"), 429
    return None


# --- routes -----------------------------------------------------------------
@app.get("/")
def index():
    return (
        "<!doctype html><html lang=fr><meta charset=utf-8>"
        "<title>Réseau Fortune — arène</title>"
        "<div style='background:#d21034;color:#fff;padding:.5rem;font-family:sans-serif'>"
        "SIMULATION — argent fictif, aucune valeur, aucun SMS envoyé.</div>"
        "<h1>Réseau Fortune 💡 — l'arène du plus riche</h1>"
        "<p>Rejoignez avec votre <b>jeton KotH</b> (page « King of the Hill »), "
        "bâtissez le réseau le plus riche, gardez la couronne.</p>"
        "<p>API : <code>/api/join {token}</code>, <code>/api/register</code>, "
        "<code>/api/login</code>, <code>/api/me</code>, <code>/api/buy</code>, "
        "<code>/api/bonus/activation</code>, <code>/api/refund</code>, "
        "<code>/api/transfer</code>, <code>/api/leaderboard</code>.</p>"
        "</html>"
    )


@app.post("/api/join")
def join():
    data = request.get_json(silent=True) or request.form
    token = (data.get("token") or "").strip().lower()
    if not TOKEN_RE.match(token):
        return jsonify(error="jeton KotH invalide (16 hex)"), 400
    with _LOCK:
        code = _ROOT_BY_TOKEN.get(token)
        if not code:
            code = _new_code("T")
            acc = _mk(code, None, None, wallet=SEED, token=token)
            acc["activated"] = True
            _ROOT_BY_TOKEN[token] = code
    session["code"] = code
    return jsonify(ok=True, code=code, referral_code=code)


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or request.form
    phone = (data.get("phone") or "").strip()
    parrain = (data.get("parrain_code") or "").strip() or None
    if not PHONE_RE.match(phone):  # never verified: no OTP, no SMS
        return jsonify(error="numéro invalide (format +228XXXXXXXX)"), 400
    with _LOCK:
        if phone in _BY_PHONE:
            return jsonify(error="numéro déjà inscrit"), 409
        if parrain and parrain not in _ACCOUNTS:
            return jsonify(error="code de parrainage inconnu"), 400
        acc = _mk(_new_code(), phone, parrain)
    return jsonify(ok=True, code=acc["code"], parrain=parrain)


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or request.form
    phone = (data.get("phone") or "").strip()
    code = _BY_PHONE.get(phone)
    if not code:
        return jsonify(error="numéro inconnu"), 404
    session["code"] = code
    return jsonify(ok=True, code=code)


@app.get("/api/me")
def me():
    acc = _me()
    if not acc:
        return jsonify(error="non connecté"), 401
    return jsonify(_public(acc))


@app.post("/api/buy")
def buy():
    acc = _me()
    if not acc:
        return jsonify(error="non connecté"), 401
    data = request.get_json(silent=True) or request.form
    product = (data.get("product") or "").strip()
    if product not in PRODUCTS:
        return jsonify(error="produit inconnu"), 400
    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        return jsonify(error="quantité invalide"), 400
    if qty <= 0:
        return jsonify(error="quantité invalide"), 400
    cost = PRODUCTS[product] * qty
    with _LOCK:
        if acc["wallet"] < cost:
            return jsonify(error="solde insuffisant"), 402
        acc["wallet"] -= cost
        acc["order_seq"] += 1
        oid = acc["order_seq"]
        acc["orders"][oid] = {"product": product, "cost": cost, "refunded": False}
        if product == "starter":
            acc["activated"] = True
        _pay_commissions(acc, cost)
    return jsonify(ok=True, order_id=oid, spent=cost, wallet=acc["wallet"])


@app.post("/api/bonus/activation")
def bonus_activation():
    acc = _me()
    if not acc:
        return jsonify(error="non connecté"), 401
    data = request.get_json(silent=True) or request.form
    filleul_code = (data.get("filleul_code") or "").strip()
    with _LOCK:
        f = _ACCOUNTS.get(filleul_code)
        if not f or f["sponsor"] != acc["code"]:
            return jsonify(error="ce n'est pas votre filleul"), 403
        if not f["activated"]:
            return jsonify(error="filleul non activé"), 400
        acc["wallet"] += PRIME_ACTIVATION  # BUG A: not idempotent
        acc["commissions"] += PRIME_ACTIVATION
    return jsonify(ok=True, prime=PRIME_ACTIVATION, wallet=acc["wallet"])


@app.post("/api/refund")
def refund():
    acc = _me()
    if not acc:
        return jsonify(error="non connecté"), 401
    data = request.get_json(silent=True) or request.form
    try:
        oid = int(data.get("order_id"))
    except (TypeError, ValueError):
        return jsonify(error="commande invalide"), 400
    with _LOCK:
        order = acc["orders"].get(oid)
        if not order:
            return jsonify(error="commande introuvable"), 404
        if order["refunded"]:
            return jsonify(error="déjà remboursée"), 400
        order["refunded"] = True
        acc["wallet"] += order["cost"]  # BUG B: commission never clawed back
    return jsonify(ok=True, refunded=order["cost"], wallet=acc["wallet"])


@app.post("/api/transfer")
def transfer():
    acc = _me()
    if not acc:
        return jsonify(error="non connecté"), 401
    data = request.get_json(silent=True) or request.form
    to_code = (data.get("to_code") or "").strip()
    try:
        montant = int(data.get("montant"))
    except (TypeError, ValueError):
        return jsonify(error="montant invalide"), 400
    if montant <= 0:
        return jsonify(error="montant invalide"), 400
    with _LOCK:
        dest = _ACCOUNTS.get(to_code)
        if not dest:
            return jsonify(error="destinataire inconnu"), 404
        if acc["wallet"] < montant:
            return jsonify(error="solde insuffisant"), 402
        acc["wallet"] -= montant
        dest["wallet"] += montant
    return jsonify(ok=True, wallet=acc["wallet"])


@app.get("/api/leaderboard")
def leaderboard():
    with _LOCK:
        rows = sorted(
            (
                {"team": _ACCOUNTS[c]["code"], "net_gain": _net_gain(_ACCOUNTS[c])}
                for c in _ROOT_BY_TOKEN.values()
            ),
            key=lambda r: r["net_gain"],
            reverse=True,
        )
    return jsonify(rows)


@app.get("/king")
def king():
    # Scorer-only. Returns the KotH token of the currently richest network.
    if not SCORER_SECRET or request.headers.get("X-Scorer-Token") != SCORER_SECRET:
        return jsonify(error="forbidden"), 403
    best_token, best_gain = "", None
    with _LOCK:
        for token, code in _ROOT_BY_TOKEN.items():
            g = _net_gain(_ACCOUNTS[code])
            if best_gain is None or g > best_gain:
                best_gain, best_token = g, token
    # Only crown a team that is actually ahead (positive net gain).
    if best_gain is None or best_gain <= 0:
        return jsonify(token="", ts=time.time())
    return jsonify(token=best_token, ts=time.time())


if __name__ == "__main__":
    if not SCORER_SECRET:
        raise SystemExit("SCORER_SECRET is required")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
