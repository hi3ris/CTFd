/*
 * challenge-extras.js — NCTF26 hibris add-ons for the challenges board.
 *
 * Standalone, dependency-free enhancement loaded AFTER the theme's challenges
 * bundle (hibris has no build pipeline, so we do not touch the bundle). It:
 *
 *   1. shows a "solved / total" progress counter + bar,
 *   2. adds a view switch: by Category (native), by Author, or a "Warm-up"
 *      super-group of the very-easy challenges (to get newcomers started),
 *
 * by re-parenting the LIVE challenge nodes the bundle rendered (so CTFd's own
 * click handlers, solved marks and hidden-challenge logic keep working). The
 * bundle re-renders the board (category layout) on solve and every 5 min; a
 * MutationObserver re-applies the selected view each time. Author data is not
 * in the challenge API, so it is read from a static name->author map.
 */
(function () {
  "use strict";

  var BOARD_ID = "challenges-board";
  var LS_KEY = "nctf_chal_view";
  var authors = {};
  var currentView = "category";
  try {
    currentView = localStorage.getItem(LS_KEY) || "category";
  } catch (e) {
    /* private mode: fall back to default */
  }

  function t(view) {
    return {
      category: "Catégorie",
      author: "Auteur",
      warmup: "🔰 Mise en jambe",
    }[view];
  }

  function board() {
    return document.getElementById(BOARD_ID);
  }

  // All live challenge wrappers currently in the board (visible or hidden).
  function wrappers() {
    var b = board();
    if (!b) return [];
    return Array.prototype.slice.call(b.querySelectorAll(".challenges-row > div"));
  }

  // Capture metadata onto each wrapper. Called while the board is in its native
  // (category) layout so the row header gives the true category.
  function capture() {
    wrappers().forEach(function (w) {
      var btn = w.querySelector("button.challenge-button");
      if (!btn) return;
      var nameEl = btn.querySelector("p");
      var name = nameEl ? nameEl.textContent.trim() : "";
      var row = w.closest("[id$='-row']");
      var head = row ? row.querySelector(".category-header h3") : null;
      var cat = head ? head.textContent.trim() : "";
      if (name) w.dataset.cname = name;
      if (cat && !w.dataset.locked) w.dataset.ccat = cat;
      w.dataset.cauthor = authors[name] || "Autres";
      var easy =
        w.classList.contains("tag-warmup") ||
        w.classList.contains("tag-beginner") ||
        (cat && cat.toLowerCase() === "warmup");
      w.dataset.ceasy = easy ? "1" : "0";
    });
  }

  function makeRow(title) {
    var row = document.createElement("div");
    row.className = "pt-5 nctf-group";
    var head = document.createElement("div");
    head.className = "category-header col-md-12 mb-3";
    var h3 = document.createElement("h3");
    h3.textContent = title;
    head.appendChild(h3);
    var body = document.createElement("div");
    body.className = "category-challenges col-md-12";
    var inner = document.createElement("div");
    inner.className = "challenges-row col-md-12";
    body.appendChild(inner);
    row.appendChild(head);
    row.appendChild(body);
    row._inner = inner;
    return row;
  }

  // Rebuild the board from a list of groups. Groups are appended in the given
  // order; every wrapper is always re-appended (hidden groups keep their nodes
  // in the DOM so switching views never loses a challenge).
  function rebuild(groups) {
    var b = board();
    if (!b) return;
    b.textContent = "";
    groups.forEach(function (g) {
      if (g.nodes.length === 0 && !g.keepEmpty) return;
      var row = makeRow(g.title + " (" + g.nodes.length + ")");
      if (g.hidden) row.style.display = "none";
      g.nodes.forEach(function (w) {
        w.style.display = "";
        row._inner.appendChild(w);
      });
      b.appendChild(row);
    });
  }

  // Bucket all wrappers by keyFn, preserving first-seen order of keys.
  function groupBy(keyFn) {
    var buckets = {};
    var order = [];
    wrappers().forEach(function (w) {
      var key = keyFn(w);
      if (!buckets[key]) {
        buckets[key] = [];
        order.push(key);
      }
      buckets[key].push(w);
    });
    return order.map(function (k) {
      return { title: k, nodes: buckets[k] };
    });
  }

  function applyView(view) {
    var b = board();
    if (!b || wrappers().length === 0) return;
    if (view === "author") {
      rebuild(groupBy(function (w) {
        return w.dataset.cauthor || "Autres";
      }));
    } else if (view === "warmup") {
      var easy = [];
      var rest = [];
      wrappers().forEach(function (w) {
        (w.dataset.ceasy === "1" ? easy : rest).push(w);
      });
      // Non-easy challenges stay in a hidden group so nothing is lost on switch.
      rebuild([
        { title: "🔰 Mise en jambe", nodes: easy, keepEmpty: true },
        { title: "Autres", nodes: rest, hidden: true },
      ]);
    } else {
      rebuild(groupBy(function (w) {
        return w.dataset.ccat || "Divers";
      }));
    }
  }

  function updateProgress() {
    var ws = wrappers();
    var total = ws.length;
    var solved = ws.filter(function (w) {
      return w.querySelector("button.solved-challenge");
    }).length;
    var pct = total ? Math.round((solved / total) * 100) : 0;
    var label = document.getElementById("nctf-progress-label");
    var bar = document.getElementById("nctf-progress-bar");
    if (label) label.textContent = solved + " / " + total + " résolus (" + pct + "%)";
    if (bar) bar.style.width = pct + "%";
  }

  function buildToolbar() {
    if (document.getElementById("nctf-chal-toolbar")) return;
    var b = board();
    if (!b) return;
    var bar = document.createElement("div");
    bar.id = "nctf-chal-toolbar";
    bar.className = "container mb-2";

    var prog = document.createElement("div");
    prog.className = "nctf-progress-wrap";
    var lbl = document.createElement("div");
    lbl.id = "nctf-progress-label";
    lbl.className = "nctf-progress-label";
    lbl.textContent = "…";
    var track = document.createElement("div");
    track.className = "nctf-progress-track";
    var fill = document.createElement("div");
    fill.id = "nctf-progress-bar";
    fill.className = "nctf-progress-fill";
    track.appendChild(fill);
    prog.appendChild(lbl);
    prog.appendChild(track);

    var group = document.createElement("div");
    group.className = "nctf-view-switch btn-group mt-2";
    ["category", "author", "warmup"].forEach(function (v) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn-sm btn-outline-secondary";
      btn.textContent = t(v);
      btn.dataset.view = v;
      if (v === currentView) btn.classList.add("active");
      btn.addEventListener("click", function () {
        currentView = v;
        try {
          localStorage.setItem(LS_KEY, v);
        } catch (e) {
          /* ignore */
        }
        group.querySelectorAll("button").forEach(function (x) {
          x.classList.toggle("active", x.dataset.view === v);
        });
        run();
      });
      group.appendChild(btn);
    });

    bar.appendChild(prog);
    bar.appendChild(group);
    b.parentNode.insertBefore(bar, b);
  }

  var observer = null;
  function run() {
    var b = board();
    if (!b || wrappers().length === 0) return;
    if (observer) observer.disconnect();
    try {
      capture();
      applyView(currentView);
      updateProgress();
    } catch (e) {
      /* never break the page */
    }
    if (observer) observer.observe(b, { childList: true, subtree: true });
  }

  function start() {
    buildToolbar();
    var b = board();
    if (!b) return;
    observer = new MutationObserver(function () {
      // Only react to the bundle's native re-renders (we disconnect during ours).
      run();
    });
    observer.observe(b, { childList: true, subtree: true });
    // In case the board already rendered before this script ran.
    var tries = 0;
    var iv = setInterval(function () {
      tries++;
      if (wrappers().length > 0 || tries > 40) {
        clearInterval(iv);
        run();
      }
    }, 250);
  }

  function boot() {
    var url =
      window.CHALLENGE_AUTHORS_URL ||
      "/themes/hibris/static/js/pages/challenge-authors.json";
    fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        return r.ok ? r.json() : {};
      })
      .catch(function () {
        return {};
      })
      .then(function (map) {
        authors = map || {};
        if (document.readyState === "loading") {
          document.addEventListener("DOMContentLoaded", start);
        } else {
          start();
        }
      });
  }

  boot();
})();
