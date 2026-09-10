#!/usr/bin/env python3
"""
gen_assets.py -- AUTHOR TOOL (not shipped to players in the handout).

Builds the fixed challenge assets:
  * app/weights.npz          the SENTRY-6 gate weights
  * app/denied_badge.npy     the reference DENIED badge (32x32 uint8)
  * handout/denied_badge.gatepkt + decoded .npy
  * handout/samples/*.gatepkt (+ a few decoded .npy) as the format corpus

The weights are CONSTRUCTED (not trained) so that a provable solution exists:
from the shipped DENIED badge there is a uint8 image within L-inf EPS that the
gate classifies as GRANTED, yet:
  * the DENIED badge itself is confidently DENIED,
  * a single-step / untargeted attack lands on the STAFF decoy, not GRANTED,
    so real targeted PGD is required.

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
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")
HANDOUT = os.path.join(HERE, "handout")


def make_convs(rng):
    return {
        "Wc1": rng.normal(0, 0.25, (8, 1, 3, 3)),
        "bc1": np.zeros(8),
        "Wc2": rng.normal(0, 0.15, (16, 8, 3, 3)),
        "bc2": np.zeros(16),
    }


def make_badge(rng):
    """A smooth-ish structured 32x32 grayscale 'badge scan'."""
    base = rng.integers(40, 90, (8, 8)).astype(np.float64)
    up = np.kron(base, np.ones((4, 4)))              # 32x32 blocky
    up += rng.normal(0, 6, (SIDE, SIDE))
    # a couple of bright strokes so it looks like a scanned badge
    up[6:9, 4:28] += 70
    up[SIDE - 10:SIDE - 7, 4:28] += 55
    return np.clip(up, 0, 255).astype(np.uint8)


def save_npz(convs, Wf, bf, path):
    np.savez(path, Wc1=convs["Wc1"], bc1=convs["bc1"],
             Wc2=convs["Wc2"], bc2=convs["bc2"], Wf=Wf, bf=bf)


def _norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def pgd(model, x0, target, eps, steps=120, step=1.0):
    """Integer-projected PGD toward `target`. Returns best uint8 image found."""
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


def fgsm_untargeted(model, x0, true_label, eps):
    xi = x0.astype(np.uint8)
    _, g = model.logits_and_input_grad(xi, true_label)
    # ascend the loss => move AGAINST the true-class logit gradient
    x = np.clip(np.round(x0 - eps * np.sign(g)), 0, 255).astype(np.uint8)
    return model.predict(x)


def try_seed(seed):
    rng = np.random.default_rng(seed)
    convs = make_convs(rng)
    denied = make_badge(rng)

    # temporary model to read features under these conv weights
    tmp = os.path.join(APP, "_tmp_weights.npz")
    save_npz(convs, np.zeros((6, 1024)), np.zeros(6), tmp)
    m = GateModel(tmp)

    f_d = m.features(denied)
    # a target perturbation that uses the full budget in a fixed pattern
    patt = np.where(((np.add.outer(np.arange(SIDE), np.arange(SIDE))) % 2) == 0, 1, -1)
    t = np.clip(denied.astype(np.int32) + EPS * patt, 0, 255).astype(np.uint8)
    f_t = m.features(t)
    # a second, different perturbation to seed the STAFF decoy direction
    patt2 = rng.choice([-1, 1], size=(SIDE, SIDE))
    t2 = np.clip(denied.astype(np.int32) + EPS * patt2, 0, 255).astype(np.uint8)
    f_t2 = m.features(t2)

    Wf = rng.normal(0, 0.02, (6, 1024))
    bf = np.zeros(6)
    Wf[DENIED] = 6.0 * _norm(f_d)
    Wf[GRANTED] = 5.0 * _norm(f_t - f_d) + 1.0 * _norm(f_t)
    Wf[STAFF] = 4.5 * _norm(f_t2 - f_d) + 1.0 * _norm(f_t2)
    bf[DENIED] = 1.0

    save_npz(convs, Wf, bf, tmp)
    m = GateModel(tmp)

    if m.predict(denied) != DENIED:
        os.remove(tmp)
        return None
    # untargeted single step must miss GRANTED (the decoy path)
    if fgsm_untargeted(m, denied, DENIED, EPS) == GRANTED:
        os.remove(tmp)
        return None
    # targeted PGD must succeed with a comfortable, quantization-robust margin
    best, margin = pgd(m, denied, GRANTED, EPS)
    os.remove(tmp)
    if best is None or margin < 1.5:
        return None
    # sanity: solution is strictly within the eps ball
    if np.max(np.abs(best.astype(int) - denied.astype(int))) > EPS:
        return None
    return convs, Wf, bf, denied, best, margin


def main():
    for seed in range(1, 4000):
        res = try_seed(seed)
        if res is None:
            continue
        convs, Wf, bf, denied, sol, margin = res
        print(f"[+] seed {seed}: solvable, PGD margin {margin:.3f}")
        save_npz(convs, Wf, bf, os.path.join(APP, "weights.npz"))
        np.save(os.path.join(APP, "denied_badge.npy"), denied)

        # handout copies
        os.makedirs(os.path.join(HANDOUT, "samples"), exist_ok=True)
        np.save(os.path.join(HANDOUT, "denied_badge.npy"), denied)
        with open(os.path.join(HANDOUT, "denied_badge.gatepkt"), "wb") as fh:
            fh.write(gatepkt.encode(denied))
        # weights ship to the player too (white-box)
        np.savez(os.path.join(HANDOUT, "weights.npz"),
                 Wc1=convs["Wc1"], bc1=convs["bc1"], Wc2=convs["Wc2"],
                 bc2=convs["bc2"], Wf=Wf, bf=bf)

        # sample corpus: a handful of other badges as .gatepkt, with two
        # decoded .npy so the container semantics can be inferred from evidence
        rng = np.random.default_rng(9000 + seed)
        for i in range(6):
            b = make_badge(rng)
            with open(os.path.join(HANDOUT, "samples", f"badge_{i:02d}.gatepkt"), "wb") as fh:
                fh.write(gatepkt.encode(b))
            if i < 2:
                np.save(os.path.join(HANDOUT, "samples", f"badge_{i:02d}.npy"), b)

        # emit the constructed solution so ship-time tests can confirm it
        np.save(os.path.join(APP, "_reference_solution.npy"), sol)
        print("[+] wrote weights.npz, denied_badge.npy, handout corpus")
        return 0
    print("[-] no solvable seed found; widen the search")
    return 1


if __name__ == "__main__":
    sys.exit(main())
