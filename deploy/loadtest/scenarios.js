// Test de charge NCTF -- un VU = une equipe (RUNBOOK §2, TODO chantier 3).
//
//   k6 run -e URL=https://ctf.exemple.tg -e VUS=300 scenarios.js
//   k6 run -e SMOKE=1 -e VUS=5 scenarios.js            # profil court (stack locale)
//
// Comptes : deploy/loadtest/out/accounts.json, ecrit par seed.py (--teams VUS+3).
//
// Boucle d'une equipe (THINK secondes, 20 par defaut) :
//   t+0   scoreboard + etat KotH, liste des challenges, 5 challenges ouverts,
//         1 flag juste PUIS 3 faux sur d'autres challenges ;
//   t+10  etat KotH ;
//   t+12  scoreboard.
// Le flag juste part avant les faux : CTFd refuse TOUTE soumission (429) quand
// un compte a 10 echecs dans la minute glissante ; a 3 faux / 20 s on reste a
// 9 / min, donc les flags justes doivent etre acceptes a 100 %. Le rate-limit
// lui-meme est exerce par le scenario `spammer` (3 VUs qui martelent des faux
// flags et doivent recevoir un 429).
import { check, sleep } from "k6";
import exec from "k6/execution";
import { Counter, Rate, Trend } from "k6/metrics";
import { ACC, apiGet, apiPost, jsonOf, login, report } from "./lib.js";

const VUS = +(__ENV.VUS || 300);
const SMOKE = __ENV.SMOKE === "1";
const RAMP = __ENV.RAMP || (SMOKE ? "20s" : "5m");
const PLATEAU = __ENV.PLATEAU || (SMOKE ? "40s" : "15m");
const DOWN = __ENV.DOWN || (SMOKE ? "10s" : "1m");
const THINK = +(__ENV.THINK || 20);
const SPAMMERS = +(__ENV.SPAMMERS || 3);
const OPEN = 5;
const WRONG = 3;

export const options = {
  scenarios: {
    teams: {
      executor: "ramping-vus",
      exec: "team",
      startVUs: 0,
      stages: [
        { duration: RAMP, target: VUS },
        { duration: PLATEAU, target: VUS },
        { duration: DOWN, target: 0 },
      ],
      gracefulRampDown: "10s",
    },
    spammer: {
      executor: "constant-vus",
      exec: "spammer",
      vus: SPAMMERS,
      duration: SMOKE ? "60s" : "6m",
      startTime: SMOKE ? "5s" : "2m",
    },
  },
  thresholds: {
    lat_challenges: ["p(95)<800"],
    lat_challenge: ["p(95)<800"],
    lat_scoreboard: ["p(95)<800"],
    errors_5xx: ["rate==0"],
    submit_correct_ok: ["rate==1"],
    ratelimit_seen: ["rate>0.9"],
    login_ok: ["rate>0.99"],
    http_req_failed: ["rate<0.01"],
    team_loops: ["count>0"], // no silent green on a run that did nothing
  },
  summaryTrendStats: ["avg", "p(95)", "max", "count"],
};

const lat = {
  login: new Trend("lat_login", true),
  challenges: new Trend("lat_challenges", true),
  challenge: new Trend("lat_challenge", true),
  attempt: new Trend("lat_attempt", true),
  scoreboard: new Trend("lat_scoreboard", true),
  koth: new Trend("lat_koth", true),
};
const loginOk = new Rate("login_ok");
const correctOk = new Rate("submit_correct_ok");
const wrongSeen = new Rate("submit_wrong_refused");
const ratelimitSeen = new Rate("ratelimit_seen");
const loops = new Counter("team_loops");

// VU ids are unique across scenarios but not contiguous per scenario: the
// team VUs share the first accounts, the spammers own the last SPAMMERS ones.
const TEAM_POOL = Math.max(1, ACC.teams.length - SPAMMERS);

// Per-VU state (module scope is per VU in k6).
let session = null;
let solved = 0;
let iter = 0;

function ensureLogin(teamIndex) {
  if (session) return session;
  const t = ACC.teams[teamIndex];
  const t0 = Date.now();
  session = login(t.user, ACC.password);
  lat.login.add(Date.now() - t0);
  loginOk.add(!!session);
  return session;
}

function poll(s, what) {
  if (what === "scoreboard") {
    const r = apiGet(s, "/api/v1/scoreboard", "scoreboard");
    lat.scoreboard.add(r.timings.duration);
    check(r, { "scoreboard 200": (x) => x.status === 200 });
  } else {
    const r = apiGet(s, "/plugins/koth/api/state", "koth");
    lat.koth.add(r.timings.duration);
  }
}

function submit(s, challengeId, flag) {
  const r = apiPost(
    s,
    "/api/v1/challenges/attempt",
    { challenge_id: challengeId, submission: flag },
    "attempt",
  );
  lat.attempt.add(r.timings.duration);
  const j = jsonOf(r);
  return (j && j.data && j.data.status) || `http ${r.status}`;
}

export function team() {
  const idx = (exec.vu.idInTest - 1) % TEAM_POOL;
  const s = ensureLogin(idx);
  if (!s) {
    sleep(THINK);
    return;
  }
  iter += 1;
  loops.add(1);
  const started = Date.now();

  poll(s, "scoreboard");
  poll(s, "koth");

  const list = apiGet(s, "/api/v1/challenges", "challenges");
  lat.challenges.add(list.timings.duration);
  const chals = ((jsonOf(list) || {}).data || []).filter(
    (c) => !c.solved_by_me,
  );
  check(list, { "challenges 200": (x) => x.status === 200 });
  for (let i = 0; i < OPEN && chals.length; i++) {
    const c = chals[(idx * 13 + iter * OPEN + i) % chals.length];
    const r = apiGet(s, `/api/v1/challenges/${c.id}`, "challenge");
    lat.challenge.add(r.timings.duration);
  }

  // 1 correct flag first (its own slice of the list per team, no two teams
  // solving the same challenge at the same moment), then 3 wrong ones aimed
  // at OTHER challenges (the kpm key is per account+challenge).
  const F = ACC.flags;
  if (F.length) {
    const good = F[(idx * 7 + solved) % F.length];
    const st = submit(s, good.challenge_id, good.flag);
    const ok = st === "correct" || st === "already_solved";
    correctOk.add(ok);
    if (ok) solved += 1;
    for (let w = 1; w <= WRONG; w++) {
      const c = F[(idx * 7 + solved + w * 31) % F.length];
      const stw = submit(s, c.challenge_id, `NCTF{wrong-${idx}-${iter}-${w}}`);
      wrongSeen.add(stw === "incorrect" || stw === "ratelimited");
      sleep(0.5 + Math.random());
    }
  }

  // Remaining ticks of the loop.
  const el = () => (Date.now() - started) / 1000;
  if (el() < 10) sleep(10 - el());
  poll(s, "koth");
  if (el() < 12) sleep(12 - el());
  poll(s, "scoreboard");
  if (el() < THINK) sleep(THINK - el());
}

export function spammer() {
  // Last accounts of the file: seed.py creates VUS + SPAMMERS teams.
  const idx = ACC.teams.length - 1 - ((exec.vu.idInTest - 1) % SPAMMERS);
  const s = ensureLogin(idx);
  if (!s || !ACC.flags.length) {
    sleep(30);
    return;
  }
  const target = ACC.flags[idx % ACC.flags.length].challenge_id;
  let limited = false;
  for (let i = 0; i < 12 && !limited; i++) {
    const st = submit(s, target, `NCTF{spam-${idx}-${i}}`);
    limited = st === "ratelimited";
  }
  ratelimitSeen.add(limited);
  sleep(65); // the window slides, next burst starts clean
}

export function handleSummary(data) {
  return report(data, "scenarios.js");
}
