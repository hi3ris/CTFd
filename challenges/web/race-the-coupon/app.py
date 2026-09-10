#!/usr/bin/env python3
"""race-the-coupon -- a deliberately vulnerable shop wallet API.

Story
-----
"NimbusPay" store credit. Every account starts with 100 credits. There is a
single-use cash-out coupon (CASHOUT60) that moves 60 credits from your store
wallet back to your bank card. The coupon is meant to be redeemable exactly
once, and only when your wallet can cover the 60-credit withdrawal.

The withdrawal is implemented as a check-then-act sequence with no atomicity
between the check and the decrement (a classic TOCTOU / double-spend race):

    1. read `redeemed` flag and `balance`
    2. if already redeemed or balance < 60 -> reject
    3. ... a small amount of "processing" happens here ...
    4. balance -= 60 ; redeemed = True

A single honest client can only ever reach balance == 40 (one legitimate
withdrawal). But many concurrent clients can all pass step 2 while balance is
still 100, then each execute step 4, pushing the authoritative wallet balance
negative -- withdrawing more money than the account ever held.

Server-side oracle
------------------
The flag is NOT present in any downloadable artifact. It is derived per-team
from TEAM_SECRET (see flag.py) and is emitted ONLY after the server observes
the *effect*: a persisted wallet balance strictly less than 0. There is no
"expected payload" -- any sequence of requests that actually overdraws the
wallet wins. Reset is instant and self-service and does NOT re-derive the flag.
"""
import threading
import time

from flask import Flask, jsonify, request

from flag import get_flag

app = Flask(__name__)

FLAG = get_flag()

START_BALANCE = 100
COUPON_CODE = "CASHOUT60"
COUPON_AMOUNT = 60

# Artificial widening of the check->act window. Real-world races have windows of
# microseconds; here we make the bug reliably exploitable (and demonstrable
# under load) without making it trivially win on a single request. This models
# the latency of a real "contact the payment processor" step.
PROCESSING_DELAY_S = 0.10

# Per-instance mutable state. NOTE: intentionally NOT guarded by a lock around
# the check-then-decrement critical section -- that missing lock IS the bug.
# `_state_lock` below only protects assignment atomicity of individual fields on
# CPython, it does NOT make the read-modify-write sequence atomic.
state = {
    "balance": START_BALANCE,
    "redeemed": False,
    "withdrawals": 0,
}
_state_lock = threading.Lock()  # deliberately unused across the race window


def _wallet_view():
    view = {
        "wallet": "store-credit",
        "balance": state["balance"],
        "coupon_redeemed": state["redeemed"],
        "withdrawals": state["withdrawals"],
        "currency": "NBX",
    }
    if state["balance"] < 0:
        # The effect the challenge verifies: an overdrawn wallet. This is the
        # server-side success oracle. It fires no matter HOW you got here.
        view["overdraft"] = True
        view["flag"] = FLAG
        view["message"] = (
            "Wallet overdrawn -- you withdrew more than the account held. "
            "That should have been impossible. Nice race."
        )
    return view


@app.get("/")
def index():
    return jsonify({
        "service": "NimbusPay store wallet API",
        "start_balance": START_BALANCE,
        "coupon": {
            "code": COUPON_CODE,
            "amount": COUPON_AMOUNT,
            "policy": "single-use; wallet must cover the withdrawal",
        },
        "endpoints": {
            "GET  /api/wallet": "current authoritative wallet state",
            "POST /api/coupon/redeem": "body {\"code\": \"...\"} -- withdraw via coupon",
            "POST /api/reset": "instant self-service reset of this instance",
            "POST /api/promo/apply": "body {\"code\": \"...\"} -- legacy promo endpoint",
        },
        "goal": "Make the authoritative wallet balance go strictly negative.",
        "flag_format": "CTF{...}",
    })


@app.get("/api/wallet")
def wallet():
    return jsonify(_wallet_view())


@app.post("/api/coupon/redeem")
def redeem():
    body = request.get_json(silent=True) or {}
    code = (body.get("code") or request.form.get("code") or "").strip()

    if code != COUPON_CODE:
        return jsonify({"error": "unknown coupon code"}), 400

    # ---- CHECK (step 1-2) -------------------------------------------------
    # Read state and validate. No lock is held across to the write below.
    if state["redeemed"]:
        return jsonify({"error": "coupon already redeemed"}), 409
    if state["balance"] < COUPON_AMOUNT:
        return jsonify({"error": "insufficient balance for withdrawal"}), 402

    # ---- processing window (step 3) --------------------------------------
    # Simulates contacting the payment processor. During this window other
    # concurrent requests can also pass the CHECK above before any of them
    # reach the ACT below. This is the TOCTOU race.
    time.sleep(PROCESSING_DELAY_S)

    # ---- ACT (step 4) -----------------------------------------------------
    state["balance"] -= COUPON_AMOUNT
    state["redeemed"] = True
    state["withdrawals"] += 1

    resp = {
        "ok": True,
        "withdrawn": COUPON_AMOUNT,
        "balance": state["balance"],
    }
    if state["balance"] < 0:
        resp["overdraft"] = True
        resp["flag"] = FLAG
    return jsonify(resp)


@app.post("/api/reset")
def reset():
    # Instant, self-service, no cooldown. Restores the instance to its initial
    # state. Does NOT re-derive the flag (flag is a deterministic per-team
    # value), so resetting is always safe and never costs progress.
    state["balance"] = START_BALANCE
    state["redeemed"] = False
    state["withdrawals"] = 0
    return jsonify({"ok": True, "balance": state["balance"]})


# ---------------------------------------------------------------------------
# DECOY (exactly one). This "legacy promo" endpoint looks injectable and looks
# like it stacks arbitrary credit / balances. It is a honeypot: it echoes a
# fabricated inflated balance in ITS OWN response but never touches the
# authoritative wallet and never emits the flag. Refutable in seconds: apply
# any payload here, then GET /api/wallet and observe the real balance is
# unchanged and still non-negative. Following this path leads nowhere.
# ---------------------------------------------------------------------------
@app.post("/api/promo/apply")
def promo_apply():
    body = request.get_json(silent=True) or {}
    code = (body.get("code") or request.form.get("code") or "")
    # Deliberately "vulnerable"-looking: reflects the code and pretends to apply
    # stacked discounts. All fabricated; the real wallet is not read or written.
    fabricated = START_BALANCE + 900
    if "'" in code or "--" in code.lower() or " or " in code.lower():
        fabricated = 999999
    return jsonify({
        "ok": True,
        "applied_code": code,
        "note": "legacy promo engine (v1) -- deprecated",
        "display_balance": fabricated,
        # No flag here. This does not change /api/wallet. It never will.
    })


if __name__ == "__main__":
    # threaded=True is required for the race to be reachable: each request runs
    # in its own thread, and the GIL is released across the time.sleep window.
    app.run(host="0.0.0.0", port=8080, threaded=True)
