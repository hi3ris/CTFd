#!/usr/bin/env python3
"""AI-resistance audit for the challenge set.

Answers one question, per challenge: **would a single-shot LLM call, with no
tools, recover the flag from the public packet (statement + attached files)?**
That is the floor an agent clears trivially; a challenge that fails it and sits
in the ranking-deciding point band is where an agent buys placement.

Two modes:

  --heuristic  (default, offline, no model)
      Score each challenge from structural features (served vs static,
      downloadable artifact, category prior, points) and rank by IMPACT =
      risk x points. A fast triage to point the model-based pass at the
      expensive cases first. Never claims to be ground truth.

  --model      (ground truth; needs a model endpoint)
      Assemble the one-shot packet (statement + inlined text of attached files,
      size-capped) and ask the model to output ONLY the flag or UNKNOWN, no
      tools, one turn. Grade against the real flag (static `flags:` list, or the
      team_hmac dev-derivation for served challenges). Prints per-challenge
      SOLVED/RESISTED and a summary. Use the STRONGEST model you have -- a weak
      local model under-reports and will reassure you falsely.

Served (`team_instance`) challenges are structurally resistant (per-team flag,
live state, no downloadable artifact) and are reported as RESISTED without a
model call unless --include-served is given.

Output: a CSV on stdout (or --out FILE), one row per challenge, plus a summary
on stderr. No writes to the challenge tree.

Usage:
    python3 deploy/scripts/ai_resistance_audit.py --heuristic --out audit.csv

    # ground truth against an OpenAI-compatible endpoint:
    AI_AUDIT_API_KEY=... python3 deploy/scripts/ai_resistance_audit.py \\
        --model https://api.example/v1 --model-name gpt-strong --out audit.csv

    # against a local Ollama:
    python3 deploy/scripts/ai_resistance_audit.py \\
        --ollama http://localhost:11434 --model-name llama3.1:70b
"""
import argparse
import csv
import glob
import hashlib
import hmac
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHALLENGES = os.path.join(ROOT, "challenges")

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

# Category prior: how amenable a *static download+transform* in this category is
# to a single no-tool model pass. Coarse, transparent, overridable. Higher =
# more one-shot-soluble. Served challenges ignore this entirely.
CATEGORY_PRIOR = {
    "warmup": 0.98,
    "stego": 0.80,
    "osint": 0.75,
    "crypto": 0.72,
    "misc": 0.70,
    "forensics": 0.68,
    "networking": 0.66,
    "web": 0.64,
    "ppc": 0.62,
    "reverse": 0.60,
    "ml": 0.60,
    "supplychain": 0.58,
    "blockchain": 0.58,
    "mobile": 0.56,
    "sysadmin": 0.55,
    "cloud": 0.55,
    "hardware": 0.52,
    "ai": 0.50,
    "pwn": 0.48,
    "cve": 0.20,
    "koth": 0.10,
}

TEXT_EXT = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".json",
    ".yml",
    ".yaml",
    ".csv",
    ".c",
    ".h",
    ".java",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".sh",
    ".html",
    ".xml",
    ".log",
    ".sql",
    ".pem",
    ".asc",
    ".ini",
    ".conf",
    ".toml",
    ".hex",
    ".s",
    ".asm",
}
PACKET_CAP = 60_000  # chars of attached-file text handed to the one-shot model
FLAG_RE = re.compile(r"NCTF\{[^}]{1,80}\}")


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def challenge_dirs():
    for y in sorted(glob.glob(os.path.join(CHALLENGES, "*/*/challenge.yml"))):
        yield os.path.dirname(y), y


def static_flags(doc):
    """Return the list of literal flag strings for a static challenge."""
    out = []
    for f in doc.get("flags") or []:
        if isinstance(f, str):
            out.append(f)
        elif isinstance(f, dict) and f.get("type") in (None, "static"):
            v = f.get("content") or f.get("flag")
            if v:
                out.append(v)
    return out


def served_dev_flag(cdir, doc):
    """Reproduce a served challenge's LOCAL DEV flag from flag.py's CHALLENGE_ID,
    so the model grader has something to grade against off-arena. This is the dev
    value (TEAM_SECRET=local-dev-secret), never a production flag."""
    fp = os.path.join(cdir, "flag.py")
    cid = None
    if os.path.exists(fp):
        m = re.search(r'CHALLENGE_ID\s*=\s*["\']([^"\']+)["\']', open(fp).read())
        if m:
            cid = m.group(1)
    if not cid:
        return None
    secret = "local-dev-secret"
    digest = hmac.new(secret.encode(), cid.encode(), hashlib.sha256).hexdigest()
    return "NCTF{" + digest[:24] + "}"


def points_of(doc):
    return int(doc.get("value") or (doc.get("extra") or {}).get("initial") or 0)


def is_served(doc):
    return doc.get("type") == "team_instance"


def heuristic_risk(rel, doc):
    """0..1, higher = more likely a single no-tool model pass recovers the flag."""
    cat = rel.split("/")[0]
    if is_served(doc):
        # Live per-team service, no downloadable artifact: structurally hard for
        # a one-shot model. Small residual for a thin wrapper an agent scripts.
        return 0.12
    prior = CATEGORY_PRIOR.get(cat, 0.6)
    files = doc.get("files") or []
    # A single small text-ish artifact is the classic one-shot shape; many files
    # or clearly-binary artifacts push it down slightly (needs tool piloting).
    binary = sum(
        1 for f in files if os.path.splitext(str(f))[1].lower() not in TEXT_EXT
    )
    adj = 1.0
    if binary and not (len(files) - binary):
        adj = 0.82  # all-binary artifact: floor test under-reads it
    if len(files) >= 3:
        adj *= 0.9
    # Progressive hints that give away the vuln reduce the *unaided* difficulty.
    if doc.get("hints"):
        adj *= 1.05
    return max(0.05, min(0.99, prior * adj))


def gather_packet(cdir, doc):
    """Statement + inlined text of attached files (size-capped). Binary files are
    named with size only -- the one-shot no-tool test is a floor, not an agent."""
    parts = [("STATEMENT", (doc.get("description") or "").strip())]
    total = 0
    for f in doc.get("files") or []:
        p = os.path.join(cdir, str(f))
        if not os.path.exists(p):
            # files: entries are often relative to a dist dir; try basename match
            cand = glob.glob(
                os.path.join(cdir, "**", os.path.basename(str(f))), recursive=True
            )
            p = cand[0] if cand else p
        if not os.path.exists(p):
            parts.append((str(f), "<missing at audit time>"))
            continue
        sz = os.path.getsize(p)
        if os.path.splitext(p)[1].lower() in TEXT_EXT and total < PACKET_CAP:
            try:
                txt = open(p, encoding="utf-8", errors="replace").read(
                    PACKET_CAP - total
                )
            except Exception:
                txt = "<unreadable>"
            total += len(txt)
            parts.append((str(f), txt))
        else:
            parts.append(
                (str(f), f"<binary artifact, {sz} bytes -- an agent would parse it>")
            )
    return "\n\n".join(f"=== {name} ===\n{body}" for name, body in parts)


ONESHOT_SYS = (
    "You are auditing a CTF challenge. Given the public packet (statement and "
    "attached file contents), output ONLY the flag, exactly, in the form "
    "NCTF{...}. You have no tools and one turn. If you cannot recover the exact "
    "flag from this packet alone, output exactly UNKNOWN."
)


def call_openai(base, model_name, api_key, packet):
    body = json.dumps(
        {
            "model": model_name,
            "messages": [
                {"role": "system", "content": ONESHOT_SYS},
                {"role": "user", "content": packet[:PACKET_CAP]},
            ],
            "temperature": 0,
        }
    ).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + (api_key or ""),
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


def call_ollama(base, model_name, packet):
    body = json.dumps(
        {
            "model": model_name,
            "messages": [
                {"role": "system", "content": ONESHOT_SYS},
                {"role": "user", "content": packet[:PACKET_CAP]},
            ],
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    return (data.get("message") or {}).get("content", "")


def grade(answer, flags):
    got = set(FLAG_RE.findall(answer or ""))
    if not got:
        # exact-match fallback for non-NCTF flag formats in static flags
        got = {(answer or "").strip()}
    return any(f in got or f == (answer or "").strip() for f in flags)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--heuristic",
        action="store_true",
        help="offline feature scoring (default if no model)",
    )
    ap.add_argument(
        "--model",
        metavar="BASE_URL",
        help="OpenAI-compatible /v1 base URL for the ground-truth pass",
    )
    ap.add_argument(
        "--ollama", metavar="BASE_URL", help="Ollama base URL for the ground-truth pass"
    )
    ap.add_argument("--model-name", default=os.environ.get("AI_AUDIT_MODEL", "gpt-4o"))
    ap.add_argument(
        "--include-served",
        action="store_true",
        help="also one-shot-test served challenges",
    )
    ap.add_argument("--out", help="write CSV here instead of stdout")
    a = ap.parse_args(argv)

    use_model = bool(a.model or a.ollama)
    api_key = os.environ.get("AI_AUDIT_API_KEY", "")

    rows = []
    solved = resisted = errors = 0
    for cdir, y in challenge_dirs():
        rel = os.path.relpath(cdir, CHALLENGES)
        try:
            doc = load_yaml(y)
        except Exception as e:
            rows.append(
                {
                    "challenge": rel,
                    "category": rel.split("/")[0],
                    "points": 0,
                    "kind": "ERR",
                    "risk": "",
                    "impact": "",
                    "verdict": "yaml:" + str(e)[:40],
                }
            )
            errors += 1
            continue
        cat = rel.split("/")[0]
        pts = points_of(doc)
        served = is_served(doc)
        risk = heuristic_risk(rel, doc)
        impact = round(risk * pts, 1)
        row = {
            "challenge": rel,
            "category": cat,
            "points": pts,
            "kind": "served" if served else "static",
            "risk": round(risk, 2),
            "impact": impact,
            "verdict": "",
        }
        if use_model and (not served or a.include_served):
            flags = (
                static_flags(doc)
                if not served
                else [f for f in [served_dev_flag(cdir, doc)] if f]
            )
            if not flags:
                row["verdict"] = "no-gradeable-flag"
            else:
                packet = gather_packet(cdir, doc)
                try:
                    ans = (
                        call_ollama(a.ollama, a.model_name, packet)
                        if a.ollama
                        else call_openai(a.model, a.model_name, api_key, packet)
                    )
                    ok = grade(ans, flags)
                    row["verdict"] = "SOLVED" if ok else "RESISTED"
                    solved += ok
                    resisted += not ok
                except Exception as e:
                    row["verdict"] = "model-err:" + str(e)[:30]
                    errors += 1
        elif use_model and served:
            row["verdict"] = "RESISTED(served,not-tested)"
            resisted += 1
        rows.append(row)

    rows.sort(
        key=lambda r: (r["impact"] if isinstance(r["impact"], (int, float)) else 0),
        reverse=True,
    )

    fh = open(a.out, "w", newline="", encoding="utf-8") if a.out else sys.stdout
    w = csv.DictWriter(
        fh,
        fieldnames=[
            "challenge",
            "category",
            "points",
            "kind",
            "risk",
            "impact",
            "verdict",
        ],
    )
    w.writeheader()
    for r in rows:
        w.writerow(r)
    if a.out:
        fh.close()

    n = len(rows)
    served_n = sum(1 for r in rows if r["kind"] == "served")
    danger = [r for r in rows if r["kind"] == "static" and 150 <= r["points"] <= 350]
    print(
        f"\n[audit] {n} challenges: {served_n} served, {n - served_n} static",
        file=sys.stderr,
    )
    print(
        f"[audit] static in the 150-350 ranking band (one-shot exposure): {len(danger)}",
        file=sys.stderr,
    )
    if use_model:
        print(
            f"[audit] model={a.model_name}  SOLVED={solved}  RESISTED={resisted}  ERR={errors}",
            file=sys.stderr,
        )
        print(
            "[audit] act on: kind=static + verdict=SOLVED + high points. Convert to served, add a step, retier, or retire.",
            file=sys.stderr,
        )
    else:
        print(
            "[audit] heuristic only. Run with --model/--ollama and your STRONGEST model for ground truth.",
            file=sys.stderr,
        )
        print("[audit] top exposure (risk x points):", file=sys.stderr)
        for r in rows[:12]:
            print(
                f"        {r['impact']:>6}  {r['points']:>4}pt  {r['kind']:<6} {r['challenge']}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
