#!/usr/bin/env python3
"""
gen_assets.py -- AUTHOR TOOL (not shipped to players in the handout).

Builds the fixed challenge assets:
  * app/weights.npz          the SENTRY-6 gate weights
  * app/denied_badge.npy     the reference DENIED badge (32x32 uint8)
  * handout/weights.npz      copy for white-box attack
  * handout/denied_badge.npy + .gatepkt
  * handout/samples/*.gatepkt (+ two decoded .npy) as the format corpus
  * app/_reference_solution.npy   a known-good adversarial badge (for tests)

The convolution stack is a fixed random init. The final linear layer is
OPTIMISED (not searched) so that a provable solution exists: the checkerboard
badge `t`, which lies within L-inf EPS of the shipped DENIED badge, is trained
to be classified GRANTED, while the DENIED badge stays confidently DENIED and a
single-step untargeted attack is captured by the STAFF decoy. Because `t` is a
concrete uint8 image inside the epsilon ball that scores GRANTED, PGD is
guaranteed to find at least as good a point.

Run from the challenge root:  python3 gen_assets.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
import gatepkt  # noqa: E402
from gatemodel import GateModel, SIDE, GRANTED, DENIED  # noqa: E402

EPS = 8              # L-inf budget, in raw 0..255 integer levels
STAFF = 1
CONV_SEED = 7
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")
HANDOUT = os.path.join(HERE, "handout")


def make_convs(rng):
    return {
        "Wc1": rng.normal(0, 0.30, (8, 1, 3, 3)),
        "bc1": rng.normal(0, 0.05, 8),
        "Wc2": rng.normal(0, 0.20, (16, 8, 3, 3)),
        "bc2": rng.normal(0, 0.05, 16),
    }


def make_badge(rng):
    """A smooth-ish structured 32x32 grayscale 'badge scan'."""
    base = rng.integers(40, 90, (8, 8)).astype(np.float64)
    up = np.kron(base, np.ones((4, 4)))
    up += rng.normal(0, 6, (SIDE, SIDE))
    up[6:9, 4:28] += 70
    up[SIDE - 10:SIDE - 7, 4:28] += 55
    return np.clip(up, 0, 255).astype(np.uint8)


def save_npz(convs, Wf, bf, path):
    np.savez(path, Wc1=convs["Wc1"], bc1=convs["bc1"],
             Wc2=convs["Wc2"], bc2=convs["bc2"], Wf=Wf, bf=bf)


def features_of(model, imgs):
    return np.stack([model.features(im) for im in imgs])


def train_fc(F, labels, iters=6000, lr=0.4):
    """Plain softmax-CE gradient descent on the final linear layer only."""
    n, d = F.shape
    Wf = np.zeros((6, d))
    bf = np.zeros(6)
    Y = np.array(labels)
    for _ in range(iters):
        logits = F @ Wf.T + bf                       # (n,6)
        logits -= logits.max(axis=1, keepdims=True)
        p = np.exp(logits)
        p /= p.sum(axis=1, keepdims=True)
        p[np.arange(n), Y] -= 1.0
        gW = p.T @ F / n
        gb = p.mean(axis=0)
        Wf -= lr * gW
        bf -= lr * gb
    return Wf, bf


def min_margin(F, labels, Wf, bf):
    logits = F @ Wf.T + bf
    m = []
    for i, y in enumerate(labels):
        other = np.max(np.delete(logits[i], y))
        m.append(logits[i, y] - other)
    return min(m)


def pgd(model, x0, target, eps, steps=150, step=1.0):
    x0 = x0.astype(np.float64)
    x = x0.copy()
    best, best_margin = None, -1e9
    for _ in range(steps):
        xi = np.clip(np.round(x), 0, 255).astype(np.uint8)
        logits, g = model.logits_and_input_grad(xi, target)
        margin = logits[target] - np.max(np.delete(logits, target))
        if int(np.argmax(logits)) == target and margin > best_margin:
            best, best_margin = xi.copy(), margin
        x = x + step * np.sign(g)
        x = np.clip(x, x0 - eps, x0 + eps)
        x = np.clip(x, 0, 255)
    return best, best_margin


def fgsm_untargeted_point(model, x0, true_label, eps):
    _, g = model.logits_and_input_grad(x0.astype(np.uint8), true_label)
    return np.clip(np.round(x0 - eps * np.sign(g)), 0, 255).astype(np.uint8)


def main():
    rng = np.random.default_rng(CONV_SEED)
    convs = make_convs(rng)
    denied = make_badge(rng)

    tmp = os.path.join(APP, "_tmp_weights.npz")
    save_npz(convs, np.zeros((6, 1024)), np.zeros(6), tmp)
    m0 = GateModel(tmp)

    # anchors: denied -> DENIED, checkerboard t -> GRANTED
    patt = np.where(((np.add.outer(np.arange(SIDE), np.arange(SIDE))) % 2) == 0, 1, -1)
    t = np.clip(denied.astype(np.int32) + EPS * patt, 0, 255).astype(np.uint8)

    anchor_imgs = [denied, t]
    anchor_lbls = [DENIED, GRANTED]

    for attempt in range(6):
        F = features_of(m0, anchor_imgs)
        Wf, bf = train_fc(F, anchor_lbls)
        # scale up so the smallest correct margin is comfortably robust
        mm = min_margin(F, anchor_lbls, Wf, bf)
        if mm <= 0:
            raise SystemExit("FC failed to separate anchors (should not happen)")
        scale = 8.0 / mm
        Wf *= scale
        bf *= scale
        save_npz(convs, Wf, bf, tmp)
        m = GateModel(tmp)

        assert m.predict(denied) == DENIED, "denied not DENIED"
        assert m.predict(t) == GRANTED, "target t not GRANTED"

        # decoy: an untargeted single step must NOT reach GRANTED
        p_fgsm = fgsm_untargeted_point(m, denied.astype(np.float64), DENIED, EPS)
        if m.predict(p_fgsm) == GRANTED:
            # capture that region for STAFF and retrain
            anchor_imgs.append(p_fgsm)
            anchor_lbls.append(STAFF)
            continue
        break

    best, margin = pgd(m, denied, GRANTED, EPS)
    if best is None:
        raise SystemExit("PGD failed to reach GRANTED -- unexpected")
    linf = int(np.max(np.abs(best.astype(int) - denied.astype(int))))
    print(f"[+] conv_seed={CONV_SEED} anchors={len(anchor_imgs)} "
          f"PGD margin={margin:.3f} Linf={linf} (<= {EPS})")
    print(f"[+] fgsm-untargeted lands on class "
          f"{m.predict(fgsm_untargeted_point(m, denied.astype(float), DENIED, EPS))} "
          f"(GRANTED={GRANTED})")

    # ---- write shipped assets ----
    save_npz(convs, Wf, bf, os.path.join(APP, "weights.npz"))
    np.save(os.path.join(APP, "denied_badge.npy"), denied)
    np.save(os.path.join(APP, "_reference_solution.npy"), best)

    os.makedirs(os.path.join(HANDOUT, "samples"), exist_ok=True)
    np.save(os.path.join(HANDOUT, "denied_badge.npy"), denied)
    with open(os.path.join(HANDOUT, "denied_badge.gatepkt"), "wb") as fh:
        fh.write(gatepkt.encode(denied))
    np.savez(os.path.join(HANDOUT, "weights.npz"),
             Wc1=convs["Wc1"], bc1=convs["bc1"], Wc2=convs["Wc2"],
             bc2=convs["bc2"], Wf=Wf, bf=bf)

    srng = np.random.default_rng(9000 + CONV_SEED)
    for i in range(6):
        b = make_badge(srng)
        with open(os.path.join(HANDOUT, "samples", f"badge_{i:02d}.gatepkt"), "wb") as fh:
            fh.write(gatepkt.encode(b))
        if i < 2:
            np.save(os.path.join(HANDOUT, "samples", f"badge_{i:02d}.npy"), b)

    os.remove(tmp)
    print("[+] wrote app/weights.npz, app/denied_badge.npy, handout corpus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
