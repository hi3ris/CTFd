/*
 * nctf-fx.js — « Fonds vivants » du thème hibris (NCTF26).
 *
 * Standalone, sans dépendance, chargé en defer par base.html (hibris n'a pas
 * de pipeline de build : .dev.js et .min.js sont le même fichier, comme
 * challenge-extras). Un seul fond animé par écran, choisi par la page :
 *
 *   /challenges         orage   — un éclair frappe la tuile d'un first blood
 *                                 (rémanence rouge) ou d'un solve de ton
 *                                 équipe (vert) ; un éclair lointain de temps
 *                                 en temps.
 *   /scoreboard         radar   — un écho vert par score qui monte, un écho
 *                                 rouge avec onde par first blood ; l'éclair
 *                                 frappe le kart de l'équipe (calque avant,
 *                                 effet ponctuel) et le vainqueur à la
 *                                 révélation finale (nctf:kartstrike).
 *   login / register /  circuit — impulsions tricolores sur des pistes de
 *   reset / confirm               circuit ; accélèrent à l'envoi du formulaire.
 *   pages d'erreur      pluie de chiffrement (glyphes hex, « NCTF26{ »).
 *   pages statiques     aurore tricolore (CSS pur).
 *
 * Événements écoutés (émis par base.html et scoreboard.html) :
 *   nctf:firstblood  {challenge_id, challenge, name, solve_id}
 *   nctf:score       {account_id, delta}
 *
 * Garde-fous : tout se coupe sous prefers-reduced-motion (image figée ou rien),
 * les boucles s'arrêtent quand l'onglet est caché, 400 ms au minimum entre deux
 * éclairs (≤ 3 flashs/s, WCAG 2.3.1), voile lumineux ≤ 12 %, calques en
 * z-index -1 et pointer-events: none — le contenu reste au-dessus, cliquable.
 */
(function () {
  "use strict";

  var body = document.body;
  if (!body || window.NCTF_FX) return;

  var RM = !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
  var css = getComputedStyle(document.documentElement);
  function tk(name, fallback) {
    var v = css.getPropertyValue("--" + name).trim();
    return v || fallback;
  }
  function rnd(a, b) {
    return a + Math.random() * (b - a);
  }

  // ------------------------------------------------------------------ layers
  function layer(tag, cls) {
    var el = document.createElement(tag);
    el.className = "nctf-fx " + cls;
    el.setAttribute("aria-hidden", "true");
    body.insertBefore(el, body.firstChild);
    return el;
  }

  function Canvas(cls) {
    var cv = layer("canvas", cls);
    var self = { el: cv, c: cv.getContext("2d"), w: 0, h: 0 };
    self.fit = function () {
      var d = Math.min(window.devicePixelRatio || 1, 2); // 300 joueurs : pas de 3x
      self.w = window.innerWidth;
      self.h = window.innerHeight;
      cv.width = Math.round(self.w * d);
      cv.height = Math.round(self.h * d);
      self.c.setTransform(d, 0, 0, d, 0, 0);
    };
    self.fit();
    return self;
  }

  // Un seul point d'entrée pour pause/reprise quand l'onglet change.
  var visHandlers = [];
  document.addEventListener("visibilitychange", function () {
    visHandlers.forEach(function (fn) {
      fn(!document.hidden);
    });
  });
  var resizeHandlers = [];
  var resizeT = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizeT);
    resizeT = setTimeout(function () {
      resizeHandlers.forEach(function (fn) {
        fn();
      });
    }, 150);
  });

  // ======================================================== MOTEUR D'ÉCLAIRS
  // Partagé par l'orage du plateau (calque de fond) et par la course (calque
  // AU-DESSUS du contenu, pour frapper un kart : effet ponctuel de 420 ms, pas
  // un fond). File d'attente : jamais deux frappes à moins de 400 ms.
  function Lightning(cls, veil) {
    var S = Canvas(cls);
    var Y = tk("yellow", "#ffce00"),
      CORE = tk("bolt-core", "#fff7cc"),
      RED = tk("red", "#d21034"),
      GB = tk("green-b", "#17b06b");
    var bolts = [],
      running = false,
      lastStrike = 0,
      queue = [];
    resizeHandlers.push(S.fit);

    function seg(x0, y0, x1, y1, d, out) {
      if (d < 2) {
        out.push([x1, y1]);
        return;
      }
      var mx = (x0 + x1) / 2 + (Math.random() - 0.5) * d,
        my = (y0 + y1) / 2 + (Math.random() - 0.5) * d * 0.35;
      seg(x0, y0, mx, my, d / 2, out);
      seg(mx, my, x1, y1, d / 2, out);
    }
    function make(x, y1, spread) {
      var main = [[x + rnd(-spread, spread) * 0.3, -12]];
      seg(main[0][0], -12, x, y1, spread, main);
      var br = [];
      for (var i = 0; i < 3; i++) {
        var k = main[Math.floor(main.length * rnd(0.25, 0.7))],
          q = [[k[0], k[1]]];
        seg(k[0], k[1], k[0] + (Math.random() < 0.5 ? -1 : 1) * rnd(40, 110), k[1] + rnd(50, 130), 50, q);
        br.push(q);
      }
      return { main: main, br: br };
    }
    function path(c, p) {
      c.beginPath();
      c.moveTo(p[0][0], p[0][1]);
      for (var i = 1; i < p.length; i++) c.lineTo(p[i][0], p[i][1]);
      c.stroke();
    }
    function draw(b, a) {
      var c = S.c,
        glow = b.kind === "solve" ? GB : Y,
        s = b.kind === "ambient" ? 0.45 : 1;
      c.save();
      c.globalCompositeOperation = "lighter";
      c.lineJoin = "round";
      c.shadowColor = glow;
      c.shadowBlur = 18;
      c.strokeStyle = glow;
      c.globalAlpha = a * 0.55 * s;
      c.lineWidth = 3.2;
      path(c, b.main);
      c.lineWidth = 1.6;
      b.br.forEach(function (q) {
        c.globalAlpha = a * 0.35 * s;
        path(c, q);
      });
      if (b.kind === "fb" && b.t > 160) {
        // rémanence rouge du first blood
        c.shadowColor = RED;
        c.shadowBlur = 24;
        c.strokeStyle = RED;
        c.globalAlpha = a * 0.7;
        c.lineWidth = 4;
        path(c, b.main);
      }
      c.shadowBlur = 6;
      c.strokeStyle = CORE;
      c.globalAlpha = a * s;
      c.lineWidth = 1.5;
      path(c, b.main);
      c.lineWidth = 0.8;
      b.br.forEach(function (q) {
        c.globalAlpha = a * 0.6 * s;
        path(c, q);
      });
      c.restore();
    }
    function frame(now) {
      S.c.clearRect(0, 0, S.w, S.h);
      bolts = bolts.filter(function (b) {
        b.t = now - b.t0;
        if (b.t > 420) return false;
        // impact 60 ms, creux, re-frappe, fondu : 420 ms en tout
        var a = b.t < 60 ? 1 : b.t < 90 ? 0.25 : b.t < 150 ? 0.9 : 1 - (b.t - 150) / 270;
        draw(b, Math.max(0, a));
        return true;
      });
      if (bolts.length) requestAnimationFrame(frame);
      else running = false;
    }
    function fire(x, y1, kind) {
      lastStrike = performance.now();
      var b = make(x, y1, Math.max(60, S.w * 0.08));
      b.kind = kind;
      b.t0 = lastStrike;
      b.t = 0;
      bolts.push(b);
      if (veil && kind !== "solve") {
        veil.style.setProperty("--fx", ((x / S.w) * 100).toFixed(1) + "%");
        veil.style.opacity = kind === "fb" ? "1" : "0.5";
        setTimeout(function () {
          veil.style.opacity = "0";
        }, 120);
      }
      if (!running) {
        running = true;
        requestAnimationFrame(frame);
      }
    }
    // File d'attente : jamais deux frappes à moins de 400 ms.
    function strike(x, y1, kind) {
      if (RM || document.hidden) return;
      queue.push([x, y1, kind]);
      pump();
    }
    var pumping = false;
    function pump() {
      if (pumping || !queue.length) return;
      var wait = Math.max(0, 400 - (performance.now() - lastStrike));
      pumping = true;
      setTimeout(function () {
        pumping = false;
        var q = queue.shift();
        if (q) fire(q[0], q[1], q[2]);
        pump();
      }, wait);
    }
    return { S: S, strike: strike };
  }

  // Dédoublonnage des first bloods : le ruban HUD et la course peuvent annoncer
  // le même (même solve_id) à quelques secondes d'écart.
  var fbDone = {};
  function freshFb(d) {
    if (!d || d.solve_id == null) return true;
    if (fbDone[d.solve_id]) return false;
    fbDone[d.solve_id] = 1;
    return true;
  }

  // ================================================================== ORAGE
  function storm(board) {
    var veil = layer("div", "nctf-veil");
    var E = Lightning("nctf-storm", veil),
      S = E.S,
      strike = E.strike;

    function tile(cid) {
      return board.querySelector('button.challenge-button[value="' + String(cid).replace(/[^0-9]/g, "") + '"]');
    }
    function mark(btn, kind) {
      var cls = kind === "fb" ? "nctf-struck-fb" : "nctf-struck-solve";
      btn.classList.remove(cls);
      void btn.offsetWidth;
      btn.classList.add(cls);
      setTimeout(function () {
        btn.classList.remove(cls);
      }, 1700);
    }
    function hit(btn, kind) {
      if (!btn) {
        strike(rnd(0.2, 0.8) * S.w, S.h * rnd(0.35, 0.6), kind);
        return;
      }
      var r = btn.getBoundingClientRect();
      var y = Math.min(Math.max(r.top + 4, 90), S.h * 0.85);
      strike(r.left + r.width / 2, y, kind);
      mark(btn, kind);
    }

    // First blood : l'événement porte le challenge_id → la tuile.
    window.addEventListener("nctf:firstblood", function (e) {
      var d = e.detail || {};
      if (!freshFb(d)) return;
      hit(d.challenge_id != null ? tile(d.challenge_id) : null, "fb");
    });

    // Solve de ton équipe : une tuile passe à .solved-challenge. Le bundle
    // re-rend tout le plateau après un solve ; on compare par id.
    var solved = null;
    function scan() {
      var now = {};
      var list = board.querySelectorAll("button.challenge-button");
      if (!list.length) return;
      Array.prototype.forEach.call(list, function (b) {
        if (b.classList.contains("solved-challenge")) now[b.value] = true;
      });
      if (solved === null) {
        solved = now; // premier rendu : état de référence, aucun éclair
        return;
      }
      Object.keys(now).forEach(function (id) {
        if (!solved[id]) hit(tile(id), "solve");
      });
      solved = now;
    }
    var scanT = null;
    new MutationObserver(function () {
      clearTimeout(scanT);
      scanT = setTimeout(scan, 120);
    }).observe(board, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });

    // Ambiance : un éclair lointain toutes les 20 à 40 s.
    (function ambient() {
      setTimeout(function () {
        if (!document.hidden) strike(rnd(0.08, 0.92) * S.w, S.h * rnd(0.25, 0.5), "ambient");
        ambient();
      }, rnd(20000, 40000));
    })();

    return { strike: hit, tile: tile };
  }

  // ================================================================== RADAR
  function radar() {
    var S = Canvas("nctf-radar");
    var LINE = tk("line", "#1c2431"),
      GB = tk("green-b", "#17b06b"),
      RED = tk("red", "#d21034");
    var a = 0,
      blips = [],
      raf = 0,
      lastT = 0;
    function geo() {
      return { cx: S.w * 0.8, cy: S.h * 0.32, R: Math.min(S.w, S.h) * 0.62 };
    }
    function grid(c, g) {
      c.strokeStyle = LINE;
      c.lineWidth = 1;
      c.globalAlpha = 0.9;
      for (var r = g.R / 4; r <= g.R + 1; r += g.R / 4) {
        c.beginPath();
        c.arc(g.cx, g.cy, r, 0, 7);
        c.stroke();
      }
      c.beginPath();
      c.moveTo(g.cx - g.R, g.cy);
      c.lineTo(g.cx + g.R, g.cy);
      c.moveTo(g.cx, g.cy - g.R);
      c.lineTo(g.cx, g.cy + g.R);
      c.stroke();
      c.globalAlpha = 1;
    }
    function paint(dt) {
      var c = S.c,
        g = geo();
      c.clearRect(0, 0, S.w, S.h);
      grid(c, g);
      if (!RM && c.createConicGradient) {
        var cg = c.createConicGradient(a - 0.9, g.cx, g.cy);
        cg.addColorStop(0, "rgba(23,176,107,0)");
        cg.addColorStop(0.14, "rgba(23,176,107,.16)");
        cg.addColorStop(0.1432, "rgba(23,176,107,0)");
        c.fillStyle = cg;
        c.beginPath();
        c.arc(g.cx, g.cy, g.R, 0, 7);
        c.fill();
        c.strokeStyle = GB;
        c.globalAlpha = 0.5;
        c.beginPath();
        c.moveTo(g.cx, g.cy);
        c.lineTo(g.cx + Math.cos(a) * g.R, g.cy + Math.sin(a) * g.R);
        c.stroke();
        c.globalAlpha = 1;
      }
      blips = blips.filter(function (b) {
        var x = g.cx + Math.cos(b.ang) * b.d * g.R,
          y = g.cy + Math.sin(b.ang) * b.d * g.R;
        c.fillStyle = b.fb ? RED : GB;
        c.globalAlpha = Math.max(0, b.t);
        c.shadowColor = c.fillStyle;
        c.shadowBlur = 10;
        c.beginPath();
        c.arc(x, y, b.fb ? 4 : 2.8, 0, 7);
        c.fill();
        if (b.fb && !RM) {
          c.strokeStyle = RED;
          c.beginPath();
          c.arc(x, y, 4 + (1 - b.t) * 22, 0, 7);
          c.stroke();
        }
        c.shadowBlur = 0;
        c.globalAlpha = 1;
        b.t -= dt / 3000; // un écho s'éteint en 3 s
        return b.t > 0;
      });
    }
    function loop(now) {
      var dt = lastT ? Math.min(100, now - lastT) : 16;
      if (now - lastT >= 32) {
        // ~30 fps suffisent pour une texture de fond
        a += dt * 0.0007; // un tour en ~9 s
        paint(dt);
        lastT = now;
      }
      raf = requestAnimationFrame(loop);
    }
    function start() {
      if (RM) {
        paint(0);
        return;
      }
      if (!raf) {
        lastT = 0;
        raf = requestAnimationFrame(loop);
      }
    }
    function stop() {
      cancelAnimationFrame(raf);
      raf = 0;
    }
    function blip(fb) {
      // l'écho apparaît juste derrière le faisceau, comme « détecté »
      blips.push({ ang: a - 0.08, d: rnd(0.2, 0.95), t: 1, fb: fb });
      if (RM) {
        paint(0);
        setTimeout(function () {
          blips = [];
          paint(0);
        }, 3000);
      }
    }
    window.addEventListener("nctf:score", function () {
      blip(false);
    });
    // Éclair sur le kart : calque au-dessus du contenu, sans voile d'écran.
    var E = Lightning("nctf-front", null);
    resizeHandlers.push(E.S.fit);
    function strikeKart(accountId) {
      var lane = document.querySelector('.car-lane[data-account="' + String(accountId).replace(/[^0-9]/g, "") + '"]');
      if (!lane) return false;
      var w = lane.querySelector(".car-wrap .car") || lane;
      var r = w.getBoundingClientRect();
      if (r.bottom < 0 || r.top > E.S.h) return false;
      E.strike(r.left + r.width / 2, r.top + r.height / 2, "fb");
      lane.classList.remove("nctf-struck-fb");
      void lane.offsetWidth;
      lane.classList.add("nctf-struck-fb");
      setTimeout(function () {
        lane.classList.remove("nctf-struck-fb");
      }, 1700);
      return true;
    }
    window.addEventListener("nctf:firstblood", function (e) {
      var d = e.detail || {};
      if (!freshFb(d)) return;
      blip(true);
      if (d.account_id != null) strikeKart(d.account_id);
    });
    // la révélation finale fait frapper le vainqueur
    window.addEventListener("nctf:kartstrike", function (e) {
      var d = e.detail || {};
      if (d.account_id != null) strikeKart(d.account_id);
    });
    visHandlers.push(function (visible) {
      if (visible) start();
      else stop();
    });
    resizeHandlers.push(function () {
      S.fit();
      if (RM) paint(0);
    });
    start();
  }

  // ================================================================ CIRCUIT
  function circuit(form) {
    var NS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "nctf-fx nctf-circuit");
    svg.setAttribute("aria-hidden", "true");
    body.insertBefore(svg, body.firstChild);
    var cols = [tk("green", "#006a4e"), tk("yellow", "#ffce00"), tk("red", "#d21034")],
      P = 24,
      anims = [];
    function el(n, attrs) {
      var e = document.createElementNS(NS, n);
      for (var k in attrs) e.setAttribute(k, attrs[k]);
      svg.appendChild(e);
      return e;
    }
    function build() {
      anims.forEach(function (x) {
        x.cancel();
      });
      anims = [];
      while (svg.firstChild) svg.removeChild(svg.firstChild);
      var W = window.innerWidth,
        H = window.innerHeight,
        n = Math.round(Math.min(34, (W * H) / 42000));
      svg.setAttribute("viewBox", "0 0 " + W + " " + H);
      for (var i = 0; i < n; i++) {
        var x = Math.round(rnd(0, W) / P) * P,
          y = Math.round(rnd(0, H) / P) * P,
          d = "M" + x + " " + y,
          len = 0;
        for (var s = 0; s < 5; s++) {
          var step = Math.floor(rnd(2, 7)) * P * (Math.random() < 0.5 ? -1 : 1);
          if (s % 2 === 0) x += step;
          else y += step;
          len += Math.abs(step);
          d += " L" + x + " " + y;
        }
        el("path", { d: d, fill: "none", stroke: tk("line", "#1c2431"), "stroke-width": 1.5 });
        el("circle", { cx: x, cy: y, r: 3, fill: tk("line-strong", "#2b3a4d") });
        if (RM || !Element.prototype.animate) continue;
        var col = cols[i % 3];
        var p = el("path", {
          d: d,
          fill: "none",
          stroke: col,
          "stroke-width": 2,
          "stroke-linecap": "round",
          "stroke-dasharray": "18 " + (len + 40),
          "stroke-dashoffset": len + 18,
          style: "filter:drop-shadow(0 0 4px " + col + ")",
        });
        anims.push(
          p.animate([{ strokeDashoffset: len + 18 }, { strokeDashoffset: -40 }], {
            duration: rnd(2200, 4800),
            delay: rnd(0, 3000),
            iterations: Infinity,
            easing: "ease-in",
          }),
        );
      }
    }
    build();
    resizeHandlers.push(build);
    visHandlers.push(function (visible) {
      anims.forEach(function (x) {
        if (visible) x.play();
        else x.pause();
      });
    });
    // Envoi du formulaire : le réseau s'emballe 600 ms.
    if (form)
      form.addEventListener("submit", function () {
        anims.forEach(function (x) {
          x.playbackRate = 3;
        });
        setTimeout(function () {
          anims.forEach(function (x) {
            x.playbackRate = 1;
          });
        }, 600);
      });
  }

  // ========================================================= PLUIE CHIFFRÉE
  function cipher() {
    var S = Canvas("nctf-cipher");
    var F = 14,
      G = "0123456789abcdef{}_$#",
      WORD = "NCTF26{",
      MUT = tk("cipher", "rgba(154,164,178,.22)"),
      HEAD = tk("nav-text", "#c7cfda"),
      Y = tk("yellow", "#ffce00"),
      drops = [],
      timer = 0;
    function reset() {
      S.fit();
      drops = [];
      for (var i = 0; i < Math.floor(S.w / F); i++) drops.push({ y: rnd(-40, 0), v: rnd(0.25, 0.75), w: -1 });
      S.c.clearRect(0, 0, S.w, S.h);
    }
    function tick() {
      var c = S.c;
      c.globalCompositeOperation = "destination-out"; // traînée qui s'efface, fond transparent
      c.fillStyle = "rgba(0,0,0,.16)";
      c.fillRect(0, 0, S.w, S.h);
      c.globalCompositeOperation = "source-over";
      c.font = "500 " + (F - 2) + 'px "JetBrains Mono", monospace';
      drops.forEach(function (d, i) {
        var x = i * F,
          y = d.y * F,
          ch;
        if (d.w >= 0) {
          ch = WORD[d.w];
          c.fillStyle = Y;
          d.w = d.w + 1 >= WORD.length ? -1 : d.w + 1;
        } else {
          ch = G[Math.floor(Math.random() * G.length)];
          c.fillStyle = HEAD;
          c.globalAlpha = 0.55;
        }
        c.fillText(ch, x, y);
        c.globalAlpha = 1;
        c.fillStyle = MUT;
        c.fillText(G[Math.floor(Math.random() * G.length)], x, y - F);
        d.y += d.v;
        if (y > S.h + F * 4) {
          d.y = rnd(-20, 0);
          d.v = rnd(0.25, 0.75);
          if (Math.random() < 0.06) d.w = 0; // une colonne se « déchiffre »
        }
      });
    }
    function start() {
      if (!timer) timer = setInterval(tick, 50); // ~20 images/s
    }
    function stop() {
      clearInterval(timer);
      timer = 0;
    }
    reset();
    resizeHandlers.push(reset);
    if (RM) {
      for (var k = 0; k < 40; k++) tick();
      return;
    }
    visHandlers.push(function (visible) {
      if (visible) start();
      else stop();
    });
    start();
  }

  // ================================================================ AURORE
  function aurora() {
    var el = layer("div", "nctf-aurora");
    el.innerHTML = '<i class="a1"></i><i class="a2"></i><i class="a3"></i>';
  }

  // ============================================================= AIGUILLAGE
  // Un seul fond animé par écran (en plus de la grille ConsoleDepth).
  var api = {};
  var board = document.getElementById("challenges-board");
  var cls = body.className || "";
  if (board) {
    api.storm = storm(board);
  } else if (/\bep-scoreboard-listing\b/.test(cls)) {
    radar();
  } else if (/\bep-auth-(login|register|reset_password|confirm)\b/.test(cls)) {
    circuit(document.querySelector("main form"));
  } else if (document.querySelector(".term-window")) {
    cipher();
  } else if (/\bep-views-static_html\b/.test(cls)) {
    aurora();
  }

  // Petite API pour tester depuis la console : NCTF_FX.firstBlood(12)
  api.firstBlood = function (challengeId) {
    window.dispatchEvent(new CustomEvent("nctf:firstblood", { detail: { challenge_id: challengeId } }));
  };
  api.score = function () {
    window.dispatchEvent(new CustomEvent("nctf:score", { detail: {} }));
  };
  window.NCTF_FX = api;
})();
