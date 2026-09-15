// Instancier sous charge : N equipes demandent une instance servie dans une
// fenetre de SPREAD secondes, attendent qu'elle tourne, la tiennent HOLD s,
// puis la detruisent. Borne realiste pour l'epreuve : 50 equipes en 10 min.
//
//   k6 run -e URL=https://ctf.exemple.tg -e VUS=50 instancer.js
//   k6 run -e SMOKE=1 -e VUS=3 instancer.js
//
// Sur la stack locale sans arena (`make local-up` seul) /spawn repond 503
// "Instancier inactif" : le scenario le constate et s'arrete (seuil
// instancer_active). `make local-koth` / `local-build-images` + INSTANCER_*
// dans le compose local l'activent.
import { check, sleep } from "k6";
import exec from "k6/execution";
import { Rate, Trend } from "k6/metrics";
import { ACC, apiGet, apiPost, jsonOf, login, report } from "./lib.js";

const VUS = +(__ENV.VUS || 50);
const SMOKE = __ENV.SMOKE === "1";
const SPREAD = +(__ENV.SPREAD || (SMOKE ? 15 : 540));
const HOLD = +(__ENV.HOLD || (SMOKE ? 5 : 45));
const WAIT_RUNNING = +(__ENV.WAIT_RUNNING || 90);

export const options = {
  scenarios: {
    instances: {
      executor: "per-vu-iterations",
      exec: "instance",
      vus: VUS,
      iterations: 1,
      maxDuration: SMOKE ? "3m" : "14m",
    },
  },
  thresholds: {
    instancer_active: ["rate==1"],
    spawn_ok: ["rate>0.95"],
    destroy_ok: ["rate>0.95"],
    lat_to_running: ["p(95)<60000"],
    errors_5xx: ["rate==0"],
    login_ok: ["rate>0.99"],
  },
  summaryTrendStats: ["avg", "p(95)", "max", "count"],
};

const latSpawn = new Trend("lat_spawn", true);
const latRunning = new Trend("lat_to_running", true);
const latStatus = new Trend("lat_status", true);
const loginOk = new Rate("login_ok");
const active = new Rate("instancer_active");
const spawnOk = new Rate("spawn_ok");
const destroyOk = new Rate("destroy_ok");

export function instance() {
  const idx = (exec.vu.idInTest - 1) % ACC.teams.length;
  const t = ACC.teams[idx];
  const s = login(t.user, ACC.password);
  loginOk.add(!!s);
  if (!s) return;
  const ids = ACC.instance_challenges;
  if (!ids.length) {
    active.add(false);
    return;
  }
  const cid = ids[idx % ids.length];

  sleep(Math.random() * SPREAD);

  let r = apiPost(
    s,
    "/plugins/team_instancer/spawn",
    { challenge_id: cid },
    "spawn",
  );
  if (r.status === 429) {
    // 6 spawns / 60 s per account: a leftover from a previous run -- wait the window once.
    sleep(62);
    r = apiPost(
      s,
      "/plugins/team_instancer/spawn",
      { challenge_id: cid },
      "spawn",
    );
  }
  latSpawn.add(r.timings.duration);
  if (r.status === 503) {
    active.add(false);
    return;
  }
  active.add(true);
  const j = jsonOf(r) || {};
  const ok = check(r, {
    "spawn accepted": (x) => x.status === 200 && j.success !== false,
  });
  spawnOk.add(ok);
  if (!ok) return;

  const t0 = Date.now();
  let running = false;
  while (Date.now() - t0 < WAIT_RUNNING * 1000) {
    const st = apiGet(
      s,
      `/plugins/team_instancer/status?challenge_id=${cid}`,
      "status",
    );
    latStatus.add(st.timings.duration);
    const sj = jsonOf(st) || {};
    if (sj.status === "running") {
      running = true;
      break;
    }
    if (sj.status === "none" || sj.status === "error") break;
    sleep(5);
  }
  if (running) latRunning.add(Date.now() - t0);
  check(null, { "instance running": () => running });

  sleep(HOLD);
  const d = apiPost(
    s,
    "/plugins/team_instancer/destroy",
    { challenge_id: cid },
    "destroy",
  );
  destroyOk.add(d.status === 200);
}

export function handleSummary(data) {
  return report(data, "instancer.js");
}
