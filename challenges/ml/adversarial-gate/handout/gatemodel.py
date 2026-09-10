#!/usr/bin/env python3
"""
gatemodel.py -- the SENTRY-6 badge gate classifier.

A small, fully self-contained CNN implemented in pure NumPy. The SAME file is
shipped in the handout, so the function the player attacks locally is byte-for-
byte the function the server evaluates -- there is no framework mismatch to
worry about, and a white-box adversarial example that works locally will work
against the server.

Architecture (single-channel 32x32 input):

    preprocess:  x_uint8[0..255] -> (x/255 - 0.5) / 0.5     # -> [-1, 1]
    conv1:       1 -> 8   3x3  pad 1  stride 1   + ReLU
    maxpool 2x2
    conv2:       8 -> 16  3x3  pad 1  stride 1   + ReLU
    maxpool 2x2
    flatten  (C,H,W order) -> 1024
    fc:          1024 -> 6 logits

Classes (index -> label):
    0 DENIED      3 CONTRACTOR
    1 STAFF       4 AUDITOR
    2 VISITOR     5 GRANTED       <-- the only class that opens the gate

Weights live in weights.npz (keys: Wc1,bc1,Wc2,bc2,Wf,bf). They are FIXED for
all teams; only the emitted flag is per-team.

The module also exposes `logits_and_input_grad`, an analytic backward pass that
returns d(logit_target)/d(input_uint8_pixels). That is all a PGD/FGSM attack
needs, so no autograd framework is required to solve this challenge.
"""
import os

import numpy as np

CLASSES = ["DENIED", "STAFF", "VISITOR", "CONTRACTOR", "AUDITOR", "GRANTED"]
GRANTED = 5
DENIED = 0
SIDE = 32

_HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# im2col helpers (stride 1, square kernel, symmetric padding)
# ---------------------------------------------------------------------------
def _im2col(x, kh, kw, pad):
    # x: (Cin, H, W) -> cols: (Cin*kh*kw, Ho*Wo)
    Cin, H, W = x.shape
    Ho, Wo = H + 2 * pad - kh + 1, W + 2 * pad - kw + 1
    xp = np.pad(x, ((0, 0), (pad, pad), (pad, pad)), mode="constant")
    cols = np.empty((Cin, kh, kw, Ho, Wo), dtype=x.dtype)
    for i in range(kh):
        for j in range(kw):
            cols[:, i, j, :, :] = xp[:, i:i + Ho, j:j + Wo]
    return cols.reshape(Cin * kh * kw, Ho * Wo), (Ho, Wo)


def _col2im(dcols, x_shape, kh, kw, pad):
    Cin, H, W = x_shape
    Ho, Wo = H + 2 * pad - kh + 1, W + 2 * pad - kw + 1
    dcols = dcols.reshape(Cin, kh, kw, Ho, Wo)
    dxp = np.zeros((Cin, H + 2 * pad, W + 2 * pad), dtype=np.float64)
    for i in range(kh):
        for j in range(kw):
            dxp[:, i:i + Ho, j:j + Wo] += dcols[:, i, j, :, :]
    if pad == 0:
        return dxp
    return dxp[:, pad:-pad, pad:-pad]


def _conv(x, W, b, pad=1):
    Cout = W.shape[0]
    cols, (Ho, Wo) = _im2col(x, W.shape[2], W.shape[3], pad)
    Wr = W.reshape(Cout, -1)
    out = (Wr @ cols + b[:, None]).reshape(Cout, Ho, Wo)
    return out, cols


def _maxpool2(x):
    C, H, Wd = x.shape
    xr = x.reshape(C, H // 2, 2, Wd // 2, 2)
    out = xr.max(axis=(2, 4))
    # argmax mask for backward
    flat = xr.transpose(0, 1, 3, 2, 4).reshape(C, H // 2, Wd // 2, 4)
    idx = flat.argmax(axis=3)
    return out, idx


def _maxpool2_backward(dout, idx, in_shape):
    C, H, Wd = in_shape
    dflat = np.zeros((C, H // 2, Wd // 2, 4), dtype=np.float64)
    ii, jj, kk = np.indices((C, H // 2, Wd // 2))
    dflat[ii, jj, kk, idx] = dout
    dflat = dflat.reshape(C, H // 2, Wd // 2, 2, 2).transpose(0, 1, 3, 2, 4)
    return dflat.reshape(C, H, Wd)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class GateModel:
    def __init__(self, weights_path=None):
        if weights_path is None:
            weights_path = os.path.join(_HERE, "weights.npz")
        with np.load(weights_path) as z:
            self.Wc1 = z["Wc1"].astype(np.float64)
            self.bc1 = z["bc1"].astype(np.float64)
            self.Wc2 = z["Wc2"].astype(np.float64)
            self.bc2 = z["bc2"].astype(np.float64)
            self.Wf = z["Wf"].astype(np.float64)
            self.bf = z["bf"].astype(np.float64)

    @staticmethod
    def preprocess(img_uint8):
        x = np.asarray(img_uint8, dtype=np.float64).reshape(1, SIDE, SIDE)
        return (x / 255.0 - 0.5) / 0.5

    def logits(self, img_uint8):
        x = self.preprocess(img_uint8)
        a1, _ = _conv(x, self.Wc1, self.bc1, pad=1)
        r1 = np.maximum(a1, 0.0)
        p1, _ = _maxpool2(r1)
        a2, _ = _conv(p1, self.Wc2, self.bc2, pad=1)
        r2 = np.maximum(a2, 0.0)
        p2, _ = _maxpool2(r2)
        flat = p2.reshape(-1)
        return self.Wf @ flat + self.bf

    def features(self, img_uint8):
        """Flattened penultimate activation (1024-d). Used only by the
        weight-construction tooling, never by the gate at runtime."""
        x = self.preprocess(img_uint8)
        a1, _ = _conv(x, self.Wc1, self.bc1, pad=1)
        r1 = np.maximum(a1, 0.0)
        p1, _ = _maxpool2(r1)
        a2, _ = _conv(p1, self.Wc2, self.bc2, pad=1)
        r2 = np.maximum(a2, 0.0)
        p2, _ = _maxpool2(r2)
        return p2.reshape(-1)

    def predict(self, img_uint8):
        return int(np.argmax(self.logits(img_uint8)))

    # --- analytic gradient of a chosen logit wrt the raw uint8 pixels -------
    def logits_and_input_grad(self, img_uint8, target):
        x = self.preprocess(img_uint8)
        # forward, caching what backward needs
        a1, _ = _conv(x, self.Wc1, self.bc1, pad=1)
        r1 = np.maximum(a1, 0.0)
        p1, idx1 = _maxpool2(r1)
        a2, _ = _conv(p1, self.Wc2, self.bc2, pad=1)
        r2 = np.maximum(a2, 0.0)
        p2, idx2 = _maxpool2(r2)
        flat = p2.reshape(-1)
        logits = self.Wf @ flat + self.bf

        # backward from logits[target]
        dflat = self.Wf[target]                       # (1024,)
        dp2 = dflat.reshape(p2.shape)
        dr2 = _maxpool2_backward(dp2, idx2, r2.shape)
        da2 = dr2 * (a2 > 0)
        # conv2 backward -> dp1
        dp1 = _col2im((self.Wc2.reshape(self.Wc2.shape[0], -1).T
                       @ da2.reshape(da2.shape[0], -1)),
                      p1.shape, 3, 3, 1)
        dr1 = _maxpool2_backward(dp1, idx1, r1.shape)
        da1 = dr1 * (a1 > 0)
        # conv1 backward -> dx  (input is single channel)
        dx = _col2im((self.Wc1.reshape(self.Wc1.shape[0], -1).T
                      @ da1.reshape(da1.shape[0], -1)),
                     x.shape, 3, 3, 1)
        # through preprocess: d/d(uint8) = dx * (1/255)/0.5
        dpix = (dx / (255.0 * 0.5)).reshape(SIDE, SIDE)
        return logits, dpix
