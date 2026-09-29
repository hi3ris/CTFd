#!/usr/bin/env python3
"""Deterministic generator for the 'mask-slip' challenge.

Ships a GitHub Actions workflow and a captured job log. GitHub Actions replaces
any *literal* occurrence of a registered secret with ``***`` in logs. It does
NOT understand transformations of that secret: if you pipe the secret through
``xxd`` / ``base64`` / ``rev`` / ..., the transformed bytes are printed in the
clear because they no longer match the literal secret string.

This run's workflow:
  * echoes the secret directly (correctly masked as ``***`` in the log), then
  * "for debugging" pipes it through ``xxd -p`` (a hex dump) — and that line
    leaks the secret in hex.

The captured ``run.log`` is a realistic, several-hundred-line build log (npm
install noise, webpack output, jest run, ...). Buried in it is the hex dump of
the secret, which decodes straight back to the flag. Nothing is stored in
plaintext, and the leak is NOT base64 (so grepping for a ``TkNURn`` / base64
flag prefix finds nothing).
"""

import os

FLAG = "NCTF{ci_secret_masking_is_only_literal_b64}"

WORKFLOW = """\
name: deploy
on:
  push:
    branches: [main]

jobs:
  ship:
    runs-on: ubuntu-latest
    env:
      DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install deps
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Build
        run: npm run build

      - name: Test
        run: npm test

      - name: Echo token (masked)
        run: |
          echo "using token: $DEPLOY_TOKEN"

      - name: Debug token length
        run: |
          echo -n "$DEPLOY_TOKEN" | wc -c

      # BAD: a hex dump of the secret is NOT masked. GitHub only masks the
      # literal secret string, so any encoding of it (hex here) prints in clear.
      - name: Debug token (hex fingerprint)
        run: |
          echo -n "$DEPLOY_TOKEN" | xxd -p | tr -d '\\n'; echo

      - name: Deploy
        run: ./deploy.sh
"""

# A handful of fake npm package names to synthesise realistic "added" noise.
_PKGS = [
    "lodash",
    "chalk",
    "commander",
    "debug",
    "semver",
    "glob",
    "minimatch",
    "yargs",
    "rimraf",
    "mkdirp",
    "ansi-styles",
    "supports-color",
    "strip-ansi",
    "cross-spawn",
    "which",
    "resolve",
    "is-glob",
    "picomatch",
    "braces",
    "fill-range",
    "to-regex-range",
    "readable-stream",
    "string_decoder",
    "safe-buffer",
    "inherits",
    "once",
    "wrappy",
    "end-of-stream",
    "pump",
    "duplexify",
]


def _clock(step: int, sub: int) -> str:
    """A monotonically increasing fake timestamp prefix."""
    base_s = 3 + step * 7 + sub
    mm = 14 + base_s // 60
    ss = base_s % 60
    return f"2024-05-02T09:{mm:02d}:{ss:02d}.{(sub % 10)}Z"


def build_log(secret: str) -> str:
    hexed = secret.encode().hex()
    lines = []
    step = 0

    def group(header: str, body_lines):
        nonlocal step
        sub = 0
        lines.append(f"{_clock(step, sub)} ##[group]Run {header}")
        for bl in body_lines:
            sub += 1
            lines.append(f"{_clock(step, sub)} {bl}")
        sub += 1
        lines.append(f"{_clock(step, sub)} ##[endgroup]")
        step += 1

    # --- checkout ---
    group(
        "actions/checkout@v4",
        [
            "Syncing repository: kekeli/webapp",
            "Getting Git version info",
            "Deleting the contents of '/home/runner/work/webapp/webapp'",
            "Initializing the repository",
            "Fetching the repository",
            "remote: Enumerating objects: 1284, done.",
            "remote: Counting objects: 100% (1284/1284), done.",
            "remote: Compressing objects: 100% (612/612), done.",
            "remote: Total 1284 (delta 703), reused 1160 (delta 579)",
            "Receiving objects: 100% (1284/1284), 2.14 MiB | 9.83 MiB/s, done.",
            "Resolving deltas: 100% (703/703), done.",
            "Checking out the ref",
            "HEAD is now at 8f3c1a2 chore: bump release pipeline",
        ],
    )

    # --- setup node ---
    group(
        "actions/setup-node@v4",
        [
            "Attempting to download 20...",
            "Acquiring 20.11.1 - x64 from cached tool",
            "Extracting ...",
            "Adding to the cache ...",
            "Environment details",
            "  node: v20.11.1",
            "  npm: 10.2.4",
            "  yarn: 1.22.22",
        ],
    )

    # --- npm ci (lots of noise) ---
    npm_body = [
        "npm warn deprecated glob@7.2.3: Glob versions prior to v9 are unsupported"
    ]
    for i, pkg in enumerate(_PKGS):
        ver = f"{1 + (i % 6)}.{(i * 3) % 20}.{(i * 7) % 12}"
        npm_body.append(
            f"npm http fetch GET 200 https://registry.npmjs.org/{pkg} {40 + i}ms"
        )
    npm_body.append("")
    for i, pkg in enumerate(_PKGS):
        ver = f"{1 + (i % 6)}.{(i * 3) % 20}.{(i * 7) % 12}"
        npm_body.append(f"added {i + 1} package: {pkg}@{ver}")
    npm_body += [
        "",
        "added 231 packages, and audited 232 packages in 6s",
        "42 packages are looking for funding",
        "  run `npm fund` for details",
        "found 0 vulnerabilities",
    ]
    group("npm ci", npm_body)

    # --- lint ---
    lint_body = ["> webapp@1.4.0 lint", "> eslint 'src/**/*.{js,ts}'", ""]
    for f in [
        "src/index.ts",
        "src/server.ts",
        "src/routes/health.ts",
        "src/routes/deploy.ts",
        "src/lib/config.ts",
        "src/lib/logger.ts",
        "src/lib/queue.ts",
        "src/db/pool.ts",
        "src/db/migrate.ts",
    ]:
        lint_body.append(f"  {f}  ok")
    lint_body += ["", "\u2714 no lint errors"]
    group("npm run lint", lint_body)

    # --- build (webpack) ---
    build_body = [
        "> webapp@1.4.0 build",
        "> webpack --mode production",
        "",
        "asset main.9f8c2a1.js 482 KiB [emitted] [minimized] (name: main)",
        "asset vendors.3b7d90e.js 1.21 MiB [emitted] [minimized] (name: vendors)",
        "asset runtime.0a11c2f.js 3.4 KiB [emitted] [minimized] (name: runtime)",
        "asset index.html 1.9 KiB [emitted]",
    ]
    for i in range(80):
        mod = f"./src/components/Widget{i:02d}.tsx"
        build_body.append(f"orphan modules {mod} 1.{i:02d} KiB [orphan] 1 module")
    for i in range(40):
        build_body.append(
            f"cacheable modules ./node_modules/dep{i:02d}/index.js "
            f"{2 + i}.{i % 9} KiB [built] [code generated]"
        )
    build_body += [
        "",
        "webpack 5.90.3 compiled successfully in 14213 ms",
    ]
    group("npm run build", build_body)

    # --- test (jest) ---
    test_body = [
        "> webapp@1.4.0 test",
        "> jest --ci",
        "",
        "PASS src/lib/config.test.ts",
        "PASS src/lib/logger.test.ts",
        "PASS src/routes/health.test.ts",
        "PASS src/routes/deploy.test.ts",
        "PASS src/db/pool.test.ts",
    ]
    for i in range(50):
        test_body.append(f"PASS src/components/Widget{i:02d}.test.tsx")
    test_body += [
        "",
        "Test Suites: 55 passed, 55 total",
        "Tests:       181 passed, 181 total",
        "Snapshots:   0 total",
        "Time:        11.284 s",
        "Ran all test suites.",
    ]
    group("npm test", test_body)

    # --- echo token (masked) ---
    group('echo "using token: $DEPLOY_TOKEN"', ["using token: ***"])

    # --- token length ---
    group('echo -n "$DEPLOY_TOKEN" | wc -c', [str(len(secret))])

    # --- LEAK: hex dump of the secret (NOT masked, NOT base64) ---
    group(
        "echo -n \"$DEPLOY_TOKEN\" | xxd -p | tr -d '\\n'; echo",
        [hexed],
    )

    # --- deploy ---
    group(
        "./deploy.sh",
        [
            "deploying to staging...",
            "rsync: sent 482 files",
            "restarting service webapp.service",
            "health check: 200 OK",
            "ok",
        ],
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.normpath(os.path.join(here, ".."))
    wf_dir = os.path.join(root, ".github", "workflows")
    os.makedirs(wf_dir, exist_ok=True)
    with open(os.path.join(wf_dir, "deploy.yml"), "w", encoding="utf-8") as fh:
        fh.write(WORKFLOW)
    log = build_log(FLAG)
    with open(os.path.join(root, "run.log"), "w", encoding="utf-8") as fh:
        fh.write(log)
    print("wrote workflow and run.log under", root)
    print("run.log lines:", log.count("\n"))
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
