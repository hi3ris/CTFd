#!/usr/bin/env python3
"""KékéliCash — réseau de distribution (démo). SERVED per-team instance.

FICTION / SIMULATION. This is a deliberately vulnerable marketing-network
("MLM") sandbox. No real money, no SMS is ever sent: the phone number is only a
string. Your distributor account (`ROOT`) starts with a little seed capital.
The platform pays commissions up the sponsor chain when a member activates.

Goal: beat the economy. Grow your account balance past the jackpot threshold
and the platform hands you the flag. Legitimate play LOSES money (the house
keeps most of every purchase), so a naive strategy — even registering a horde
of fake members — nets nothing. You must find a *business-logic* flaw.

State is in-memory and per-container (ephemeral). Single-tenant: this instance
is yours.
"""
import os
import re
import threading

from flask import Flask, jsonify, request, session

app = Flask(__name__)
app.secret_key = os.urandom(16)

# --- economy constants (FCFA, integers) ------------------------------------
SEED = 50_000  # ROOT starting capital
JACKPOT = 1_000_000  # net gain over SEED that unlocks the flag
FLAG_AT = SEED + JACKPOT  # absolute balance that unlocks the flag
PRODUCTS = {"starter": 5_000, "vip": 20_000, "booster": 2_000}
RATES_PERMILLE = [200, 80, 40]  # L1 20% / L2 8% / L3 4% ; house keeps the rest
PRIME_ACTIVATION = 3_000  # sponsor bonus when a filleul activates
PHONE_RE = re.compile(r"^(\+?228)?[0-9]{8}$")  # "looks Togolese" — never verified

_LOCK = threading.Lock()
_ACCOUNTS = {}  # code -> account dict
_BY_PHONE = {}  # phone -> code
_SEQ = [0]


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{local-dev-flag}"


def _new_code(prefix="M"):
    _SEQ[0] += 1
    return f"{prefix}{_SEQ[0]:06d}"


def _mk(code, phone, sponsor, wallet=0):
    acc = {
        "code": code,
        "phone": phone,
        "sponsor": sponsor,  # sponsor code or None
        "wallet": wallet,
        "activated": False,
        "commissions": 0,  # stat only
        "orders": {},  # order_id -> {product, cost, refunded}
        "order_seq": 0,
    }
    _ACCOUNTS[code] = acc
    if phone:
        _BY_PHONE[phone] = code
    return acc


def _seed_root():
    if "ROOT" not in _ACCOUNTS:
        _mk("ROOT", "22890000000", None, wallet=SEED)
        _ACCOUNTS["ROOT"]["activated"] = True


_seed_root()


def _me():
    code = session.get("code")
    return _ACCOUNTS.get(code) if code else None


def _pay_commissions(buyer, cost):
    """Pay the sponsor chain of `buyer`, up to 3 levels."""
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


def _public(acc):
    return {
        "code": acc["code"],
        "phone": acc["phone"],
        "sponsor": acc["sponsor"],
        "wallet": acc["wallet"],
        "activated": acc["activated"],
        "commissions": acc["commissions"],
        "net_gain": acc["wallet"] - (SEED if acc["code"] == "ROOT" else 0),
    }


# --- routes -----------------------------------------------------------------
@app.get("/")
def index():
    return (
        "<!doctype html><html lang=fr><meta charset=utf-8>"
        "<title>KékéliCash — Réseau Fortune</title>"
        "<div style='background:#d21034;color:#fff;padding:.5rem;font-family:sans-serif'>"
        "SIMULATION — argent fictif, aucune valeur, aucun SMS envoyé.</div>"
        "<h1>KékéliCash 💡 — devenez distributeur</h1>"
        "<p>Parrainez, activez, encaissez des commissions. Votre compte "
        "distributeur : <b>ROOT</b> (code de parrainage <b>ROOT</b>).</p>"
        "<p>API : <code>/api/register</code>, <code>/api/login</code>, "
        "<code>/api/me</code>, <code>/api/buy</code>, "
        "<code>/api/bonus/activation</code>, <code>/api/refund</code>, "
        "<code>/api/transfer</code>. Objectif : dépasser le jackpot et "
        "récupérer le drapeau sur <code>/flag</code>.</p>"
        "</html>"
    )


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or request.form
    phone = (data.get("phone") or "").strip()
    parrain = (data.get("parrain_code") or "").strip() or None
    # The number must "look" Togolese — but it is NEVER verified (no OTP/SMS).
    if not PHONE_RE.match(phone):
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
    # Quantity must be a positive integer. (Yes, we check this — no negative
    # quantity tricks here.)
    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        return jsonify(error="quantité invalide"), 400
    if qty <= 0:
        return jsonify(error="quantité invalide"), 400
    price = PRODUCTS[product]
    cost = price * qty
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
        # Prime versée au parrain à l'activation d'un filleul.
        acc["wallet"] += PRIME_ACTIVATION
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
        acc["wallet"] += order["cost"]
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


@app.get("/flag")
def flag():
    acc = _me()
    if not acc:
        return jsonify(error="non connecté"), 401
    if acc["wallet"] >= FLAG_AT:
        return jsonify(ok=True, flag=_flag())
    return (
        jsonify(
            error="fonds insuffisants pour le jackpot",
            wallet=acc["wallet"],
            need=FLAG_AT,
        ),
        403,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
