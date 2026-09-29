// Shared helpers for the k6 scenarios: session login, CSRF, metrics, report.
// No remote import (jslib) on purpose: the operator's proxy and CI must not
// need the network to run the test.
import http from "k6/http";
import { check } from "k6";
import { Rate } from "k6/metrics";

export const ACC = JSON.parse(open(__ENV.ACCOUNTS || "./out/accounts.json"));
export const BASE = (__ENV.URL || ACC.url).replace(/\/$/, "");

// 429 (rate-limit) and 403 (locked challenge / outside window) are answers we
// expect and count separately; only network errors and 5xx are "failed".
http.setResponseCallback(
  http.expectedStatuses({ min: 200, max: 399 }, 403, 429),
);

export const err5xx = new Rate("errors_5xx");

export function track(res) {
  err5xx.add(res.status >= 500 || res.status === 0);
  return res;
}

function nonceOf(html) {
  const m =
    /name="nonce" value="([0-9a-f]+)"/.exec(html) ||
    /'csrfNonce':\s*"([0-9a-f]+)"/.exec(html);
  return m ? m[1] : null;
}

// One login per VU; returns {jar, headers} for API calls or null on failure.
export function login(user, password, tags) {
  const jar = http.cookieJar();
  let r = track(http.get(`${BASE}/login`, { jar, tags: { name: "login" } }));
  const nonce = nonceOf(r.body);
  if (!nonce) return null;
  r = track(
    http.post(
      `${BASE}/login`,
      { name: user, password, nonce },
      { jar, tags: { name: "login" }, redirects: 0 },
    ),
  );
  const ok = check(r, { "login redirected": (x) => x.status === 302 });
  if (!ok) return null;
  r = track(http.get(`${BASE}/`, { jar, tags: { name: "home" } }));
  const csrf = nonceOf(r.body);
  if (!csrf) return null;
  return {
    jar,
    headers: { "CSRF-Token": csrf, "Content-Type": "application/json" },
    user,
    tags,
  };
}

export function apiGet(s, path, name) {
  return track(
    http.get(`${BASE}${path}`, {
      jar: s.jar,
      headers: s.headers,
      tags: { name },
    }),
  );
}

export function apiPost(s, path, body, name) {
  return track(
    http.post(`${BASE}${path}`, JSON.stringify(body), {
      jar: s.jar,
      headers: s.headers,
      tags: { name },
    }),
  );
}

export function jsonOf(res) {
  try {
    return res.json();
  } catch (e) {
    return null;
  }
}

// --- report ------------------------------------------------------------------

function fmt(v, digits) {
  return v === undefined || v === null
    ? "-"
    : Number(v).toFixed(digits === undefined ? 0 : digits);
}

function esc(s) {
  return String(s).replace(
    /[&<>]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c],
  );
}

// Text on stdout + summary.json + summary.html (thresholds, then the endpoints
// sorted by p95, the 5 slowest first). `title` names the scenario file.
export function report(data, title) {
  const m = data.metrics;
  const lines = [];
  const rows = [];
  let allOk = true;
  for (const [name, met] of Object.entries(m)) {
    if (met.thresholds) {
      for (const [expr, t] of Object.entries(met.thresholds)) {
        allOk = allOk && t.ok;
        lines.push(`${t.ok ? "OK  " : "FAIL"} ${name} ${expr}`);
        rows.push([t.ok, name, expr]);
      }
    }
  }
  const lat = Object.entries(m)
    .filter(([n, v]) => n.startsWith("lat_") && v.type === "trend")
    .map(([n, v]) => ({
      name: n.slice(4),
      n: v.values.count,
      avg: v.values.avg,
      p95: v.values["p(95)"],
      max: v.values.max,
    }))
    .sort((a, b) => b.p95 - a.p95);
  const reqs = m.http_reqs ? m.http_reqs.values.count : 0;
  const rate = m.http_reqs ? m.http_reqs.values.rate : 0;
  allOk = allOk && reqs > 0;
  const e5 = m.errors_5xx ? m.errors_5xx.values.rate : 0;
  const head =
    `${title} -- ${BASE}\n` +
    `requests ${reqs} (${fmt(rate, 1)}/s)  5xx ${fmt(e5 * 100, 2)} %  ` +
    `max VUs ${m.vus_max ? m.vus_max.values.value : "-"}\n` +
    `VERDICT ${allOk ? "VERT : tous les seuils tiennent" : "ROUGE : au moins un seuil casse"}\n`;
  const table =
    "endpoint            n       avg    p95    max (ms)\n" +
    lat
      .map(
        (l) =>
          `${l.name.padEnd(18)} ${String(l.n).padStart(6)} ${fmt(l.avg).padStart(7)} ${fmt(l.p95).padStart(6)} ${fmt(l.max).padStart(6)}`,
      )
      .join("\n");
  const text = `\n${head}\n${lines.join("\n")}\n\n${table}\n`;

  const html = `<!doctype html><html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} -- test de charge</title>
<style>body{font:15px/1.5 system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem}
table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{padding:.35rem .5rem;border-bottom:1px solid #8884;text-align:left}
td.n{text-align:right;font-variant-numeric:tabular-nums}.ok{color:#188038}.ko{color:#c5221f;font-weight:600}
tr.slow td{background:#fde7e9}h1{font-size:1.3rem}code{font-size:.9em}</style>
<h1>${esc(title)} <small>${esc(BASE)}</small></h1>
<p><b class="${allOk ? "ok" : "ko"}">${allOk ? "VERT : tous les seuils tiennent" : "ROUGE : au moins un seuil casse"}</b>
 · ${reqs} requêtes (${fmt(rate, 1)}/s) · 5xx ${fmt(e5 * 100, 2)} % · VUs max ${m.vus_max ? m.vus_max.values.value : "-"}</p>
<h2>Seuils</h2><table><tr><th></th><th>métrique</th><th>seuil</th></tr>
${rows.map((r) => `<tr><td class="${r[0] ? "ok" : "ko"}">${r[0] ? "OK" : "FAIL"}</td><td><code>${esc(r[1])}</code></td><td><code>${esc(r[2])}</code></td></tr>`).join("")}
</table>
<h2>Endpoints par p95 (les 5 plus lents en rouge)</h2>
<table><tr><th>endpoint</th><th>n</th><th>avg ms</th><th>p95 ms</th><th>max ms</th></tr>
${lat.map((l, i) => `<tr class="${i < 5 ? "slow" : ""}"><td><code>${esc(l.name)}</code></td><td class="n">${l.n}</td><td class="n">${fmt(l.avg)}</td><td class="n">${fmt(l.p95)}</td><td class="n">${fmt(l.max)}</td></tr>`).join("")}
</table>
<p><small>k6 ${esc(__ENV.K6_VERSION || "")} · généré par ${esc(title)} · ${new Date().toISOString()}</small></p>
</html>`;
  const out = (__ENV.OUT || "./out") + "/" + title.replace(/\.js$/, "");
  const files = { stdout: text };
  files[`${out}-summary.json`] = JSON.stringify(data, null, 1);
  files[`${out}-summary.html`] = html;
  return files;
}
