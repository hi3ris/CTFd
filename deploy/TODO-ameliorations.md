# TODO — améliorations proposées (post-KotH, post-intro)

Suivi détaillé des 8 propositions faites le 15 septembre 2026, pour les appliquer
une par une. Complète `ROADMAP.md` (lots) et `RUNBOOK.md` (jour J) : ici, ce sont
les chantiers **transverses** de fiabilité, d'équité et de spectacle.

- **Légende propriétaire** : 🧑 = vous (décision / action humaine) · 🤖 = moi (build)
- **Convention** : `[ ]` à faire · `[~]` en cours · `[x]` fait · `[!]` bloquant / délai critique
- **Échéances** : présélection ven 23 → dim 25 oct · finale jeu 29 → ven 30 oct (Lomé)

## Ordre recommandé

| #   | Chantier                                 | Priorité | Effort | À livrer avant       | Dépend de |
| --- | ---------------------------------------- | -------- | ------ | -------------------- | --------- |
| 1   | Détecteur de partage de flags ✅         | 🔴 haute | S      | présélection (23/10) | —         |
| 2   | `make preflight` (check-list de prod) ✅ | 🔴 haute | S      | J-7 (16/10)          | —         |
| 5   | Réparer les 2 flakes CI ✅               | 🟠 moy.  | S      | dès maintenant       | —         |
| 3   | Test de charge à 300 (outil k6) ✅ outil | 🔴 haute | M      | Lot 5 (sem. 12/10)   | —         |
| 4   | Sauvegardes automatiques ✅ + répétition | 🟠 moy.  | S      | J-7 (16/10)          | —         |
| 6   | First bloods (notif + ticker) ✅         | 🟡 spect | M      | finale (29/10)       | —         |
| 7   | Tableau de bord ops ✅                   | 🟡 spect | M      | finale (29/10)       | 3, 6      |
| 8   | Page writeups à la clôture               | 🟢 basse | S      | clôture (30/10)      | —         |

Effort : S = ½ à 1 journée · M = 1 à 3 jours. Commencer par **1 + 2** (plus grand
effet pour le moins d'effort, zéro impact sur l'expérience joueur), puis **5**
(une CI qu'on peut enfin croire), puis **3 + 4** quand la date approche.

---

## 1. Détecteur de partage de flags 🔴

**Pourquoi.** Les flags `team_hmac` sont dérivés **par équipe**
(`CTFd/plugins/team_hmac_flag/__init__.py` → `expected_flag(account_id, challenge_id)`).
Si l'équipe B soumet le flag de l'équipe A, CTFd l'enregistre comme un simple
« mauvais flag » (`Fails.provided`)… alors qu'il est **exactement** le flag valide de A.
Aujourd'hui personne ne le voit. C'est la preuve de triche la plus nette qu'un CTF
puisse produire, et elle est déjà en base.

**Périmètre.**

- [x] 🤖 Nouveau plugin `CTFd/plugins/anticheat/` (livré le 15/09) :
  - `find_shared_flags(since=None)` : pour chaque `Fails` sur un challenge dont le flag
    est de type `team_hmac`, comparer `provided` (constant-time, `hmac.compare_digest`)
    au flag attendu de **chaque autre** équipe ; retourner
    `(date, soumetteur, propriétaire du flag, challenge, ip)`.
  - Performance : ~300 équipes × N fails → mettre en cache par
    `(challenge_id, provided)` ; ne recalculer que les fails postérieurs au dernier scan
    (curseur `Fails.id`).
  - Détection **en direct** : la page admin interroge l'API toutes les 10 s (scan
    incrémental, curseur `Fails.id`) et chaque incident est écrit dans
    `logs/submissions.log` (`ANTICHEAT shared flag: …`). **Pas de `Notifications`** :
    dans CTFd elles sont globales (tous les joueurs les voient) — écarté.
- [x] 🤖 Page admin `/plugins/anticheat/admin` (menu **Anti-triche**, même patron que
      `koth/admin.html`) : tableau des incidents, filtre par équipe/challenge, export CSV.
- [x] 🤖 Endpoint `GET /plugins/anticheat/api/incidents` (`@admins_only`) : `?since_id=`,
      `?rebuild=1` (après rotation du secret / ajout d'un flag `team_hmac` sur un challenge
      qui a déjà des fails), `?format=csv` (cellules protégées contre l'injection de formules).
- [x] 🤖 Tests `tests/test_plugin_anticheat.py` (6 tests, dont le vrai chemin de soumission) : A soumet son flag → rien ; B soumet le
      flag de A → 1 incident (bonnes équipes, bon challenge) ; flag aléatoire → rien ;
      flags `static`/`dynamic` classiques ignorés ; page admin 403 pour un joueur.
- [ ] 🧑 **Décision de politique** (à écrire dans le règlement) : avertissement au
      1ᵉʳ incident, disqualification au 2ᵉ ? Sanction manuelle uniquement — le plugin
      **signale**, il ne bannit jamais seul.
- [x] 🤖 Doc : section « Partage de flags » dans `deploy/anti-llm-guardrails.md` +
      playbook d'incident dans `RUNBOOK.md §5`.

**Définition de « fait ».** En local : deux équipes de test, B soumet le flag de A →
l'incident apparaît sur la page admin avec horodatage et les deux équipes, et une ligne
`ANTICHEAT` dans `logs/submissions.log`. Aucun faux positif sur `make local-playtest`.
_Reste : la décision de politique 🧑 et la vérification sur la stack locale (Docker)._

---

## 2. `make preflight` — check-list de mise en prod 🔴

**Pourquoi.** Les erreurs de configuration se font à 23 h la veille. Un script qui
**refuse** de valider tant qu'un point est faux évite la catégorie d'incident la
plus bête et la plus fréquente.

**Périmètre.** Script `deploy/scripts/preflight.py` (Python, `requests`, lisible par
un humain) + cibles `preflight` (front, `CTFD_TOKEN=… PHASE=…`) et `local-preflight`
dans `deploy/Makefile`. Livré le 15/09 ; tests `tests/test_preflight.py` (évaluateurs purs).

- [x] 🤖 **Secrets** (lus depuis l'env du conteneur CTFd, jamais affichés) :
  - `CTF_TEAM_FLAG_SECRET` posé, ≠ `test-secret`, ≥ 32 hex ;
  - `KOTH_SCORER_SECRET` ≠ `local-dev-koth-scorer` si `KOTH_HILLS` est posé ;
  - `SECRET_KEY` CTFd non vide ; mot de passe DB ≠ `ctfd` ; Redis protégé.
- [x] 🤖 **Fenêtres** (via `/api/v1/configs`) : `start` < `freeze` < `end`, tous posés,
      cohérents avec `event-windows.env.example` (présélection 72 h / finale 24 h),
      `freeze` = dernière heure. Refus si `start` est dans le passé de plus de 1 h sans
      `--allow-running`.
- [x] 🤖 **Identité & inscriptions** : `ctf_name == NCTF26`, `user_mode == teams`,
      `team_size` attendu, visibilité inscriptions/scores/comptes conforme à la phase
      (présélection : inscriptions ouvertes ; finale : fermées), vérification e-mail.
- [x] 🤖 **Contenu** : 203 challenges installés (`/api/v1/challenges` admin), 0 challenge
      en `state: hidden` non voulu, 19 catégories, aucun flag `static` contenant
      `NCTF{test` ; les 26 servis ont leur image `ctf-*` présente sur l'arena
      (`make check-arena`).
- [~] 🤖 **Services** : `/plugins/koth/api/admin` → chaque colline `online` ✅ ;
  passerelle IA et instancier (spawn/kill d'une instance témoin) restent des lignes
  `MANUAL` du rapport (RUNBOOK §2) — un spawn n'est pas « lecture seule ».
- [x] 🤖 **Thème/pages** : page `/` contient `nctf-intro` ; `HTML_SANITIZATION` désactivée
      (sinon l'intro et le bloc `<style>` disparaissent) — **avertissement**, pas refus.
- [x] 🤖 Sortie : tableau `OK / WARN / FAIL` par ligne, code retour ≠ 0 sur tout FAIL.
- [x] 🤖 Brancher dans `RUNBOOK.md §3` (J-7) et `§7` (finale) : « `make preflight`
      doit être vert avant `make phase-*` ».

**Définition de « fait ».** Sur la stack locale seedée, `make local-preflight` sort FAIL
sur les secrets de dev et les fenêtres vides ; après `make local-seed` avec
`event-windows.env.example`, tout passe sauf les WARN attendus.
_Reste : la passe sur la vraie stack locale (Docker) — vérifié ici contre un CTFd de test
(sqlite) : FAIL sur secrets/fenêtres/contenu, puis vert une fois configuré._

---

## 3. Test de charge à 300 (outil) 🔴 — outil construit, run de répétition à faire

**Pourquoi.** `ROADMAP.md` (Lot 5) et `RUNBOOK.md §2` prévoient « test de charge à
300 connexions » mais l'outil n'existe pas. On découvre les limites **avant** le
vendredi 00 h 00, pas pendant.

**Périmètre.** `deploy/loadtest/` (k6, un seul binaire, scripts JS versionnés).

- [x] 🤖 `scenarios.js` — un VU = une équipe : login → liste des challenges → ouverture
      de 5 challenges → 1 flag **juste puis** 3 faux (sur d'autres challenges) → scoreboard
      toutes les 12 s → `/plugins/koth/api/state` toutes les 10 s, boucle de 20 s. Montée
      0 → 300 VU sur 5 min, plateau 15 min, descente 1 min. _Écart assumé_ : le juste part
      avant les faux et la boucle fait 20 s, parce que CTFd refuse **toute** soumission
      (429) dès 10 échecs dans la minute glissante — à « 3 faux / 12 s » les flags justes
      seraient rejetés par construction. Le rate-limit est exercé par un scénario
      `spammer` dédié (3 VU) qui doit recevoir un 429 (seuil `ratelimit_seen`).
- [x] 🤖 `instancer.js` — 50 équipes spawnent/killent une instance servie en 10 min
      (démarrage étalé au hasard, attente `running` ≤ 90 s, tenue 45 s, `destroy`).
- [x] 🤖 Seuils : `p95 < 800 ms` sur challenges/scoreboard, `0 %` d'erreurs 5xx,
      soumissions correctes = 100 % acceptées, + `login_ok`, `ratelimit_seen`, et un run
      sans requête n'est jamais VERT ; instancier : `spawn` ≥ 95 %, `running` en p95 < 60 s.
- [x] 🤖 Cibles Make : `local-loadtest` (stack locale, 100 VU, smoke), `loadtest`
      (`URL=…`, 300 VU, la vraie), `loadtest-instancer`, `loadtest-purge`. Comptes
      `lt-0001…` créés/purgés par `deploy/loadtest/seed.py --teams N` / `--purge`, qui
      **refuse** une URL non locale sans `--allow-remote`, une plateforme portant > 20
      équipes réelles (= l'épreuve) et un `start` dans le futur (403 sur `/attempt`).
      Le purge recalcule les valeurs dynamiques ; le plugin firstblood compare désormais
      les ids de solve, donc un first blood pris par la charge puis purgé est rejoué au
      vrai premier solve. Restaurer le dump d'avant test reste la voie propre (RUNBOOK §2).
- [x] 🤖 Rapport : `out/*-summary.html` + JSON, verdict VERT/ROUGE, endpoints triés par
      p95 (les 5 plus lents en rouge), sans import réseau ; section « Test de charge »
      à remplir dans `deploy/infra-audit.md`.
- [ ] 🧑 **Ce qu'on règle avec les chiffres** : nb de workers gunicorn, pool DB, taille du
      front (cf. ROADMAP « Décider Savings Plan / taille du front »), `POLL_MS` du
      scoreboard si le front souffre.

**Définition de « fait ».** Un run à 300 VU sur le front de répétition avec tous les
seuils verts, rapport archivé, et la taille d'instance du front **figée** à partir de ce
résultat. _Exécuté ici_ : fumée des deux scripts à 5 VU contre un serveur de test
(login, 100 % des flags justes acceptés, 429 reçu par `spammer`, rapport généré, purge
vérifiée) — **pas** un chiffre de capacité ; `instancer.js` n'a pu que constater
l'instancier inactif (ROUGE attendu sans arena). Le run à 300 reste à faire au Lot 5.

---

## 4. Sauvegardes automatiques + répétition de restauration 🟠

**Pourquoi.** `make backup` (dump **vérifié** → S3) et `make restore` existent déjà.
Le trou : pendant 72 h, `RUNBOOK §4` dit « `make backup` régulièrement » — donc
**manuel**, donc oublié à 4 h du matin. Et la restauration n'a jamais été répétée sur
une base **de la taille de l'épreuve**.

**Périmètre.**

- [x] 🤖 Timer systemd sur le front (`deploy/front/systemd/ctfd-backup.timer`, toutes les
      15 min) → `deploy/scripts/backup.sh` : dump vérifié (même chaîne que `make backup`) ;
      la cadence est décidée par le script (fenêtre `[start, end]` lue dans la table
      `config` ; hors épreuve seulement si le dernier dump OK a > 6 h). Installé par
      `make deploy` (`install-backup-timer.sh`, idempotent, installe aussi l'aws CLI).
      Rétention S3 (**écart avec l'idée initiale** : une règle de cycle de vie ne sait pas
      « garder 1/jour ») : `backups/auto/` expire à 14 j, `backups/daily/<jour>.sql.gz`
      (1 fichier/jour, écrasé) et les dumps manuels suivent la règle Glacier existante.
      Terraform : rôle IAM du front **écriture seule** sur `backups/*` (`iam.tf`,
      `front.tf` — mise à jour en place, vérifier `~` et non `-/+` au plan).
- [x] 🤖 Alerte : `status.json` (`/opt/ctfd/backups`, monté en lecture seule dans CTFd
      → `BACKUP_STATUS_FILE`) + ligne `ctfd-backup` dans le journal système ; la page
      **Ops** (chantier 7) passe au rouge si le dernier dump OK a > 30 min pendant l'épreuve.
      **Pas de notification CTFd** (globales, visibles des joueurs — même décision qu'au §1).
      `make backup-status` / `make backup-now` côté opérateur.
- [x] 🤖 Uploads (`tar` de `/var/uploads`) et export natif CTFd (`export_ctf()`, zip
      testé) une fois par heure, en plus du dump SQL.
- [ ] 🧑🤖 **Répétition** (Lot 5) : restaurer un dump de la répétition à 300 VU sur un
      front neuf, chronométrer → RTO mesuré, écrit dans `RUNBOOK §5` ; vérifier que le
      scoreboard, les awards KotH et les instances survivent.
- [x] 🤖 Playbook « perte de base » dans `RUNBOOK §5` (gel, choix du dump, restauration,
      vérifications, annonce) ; RTO à remplir à la répétition.

**Définition de « fait ».** Pendant 2 h de stack locale, 8 dumps apparaissent sans
intervention ; couper un dump à la main déclenche l'alerte ; la restauration
chronométrée est documentée.
_État : script, unités, Terraform et docs livrés (15/09) ; `bash -n` et helpers de
statut testés hors Docker. **Non exécuté ici** : la passe « 8 dumps en 2 h » (Docker),
`terraform plan` (AWS) et la répétition chronométrée 🧑🤖._

---

## 5. Réparer les deux flakes CI 🟠

**Pourquoi.** Theme Verification est rouge sur la plupart des pushs et
`test_challenge_kpm_limit_no_freeze` tombe au hasard. Une CI souvent rouge apprend à
tout le monde à ignorer le rouge — le jour où ce sera un vrai problème, personne ne
regardera.

- [x] 🤖 **Theme Verification** (`.github/workflows/verify-themes.yml`) — deux
      correctifs. (1) Le workflow faisait `yarn install` **sans** `--frozen-lockfile` :
      aligné sur l'amont (CTFd #3073 / #3082) — lockfile figé, cache yarn, `.node-version`
      (20.19), et `verify` qui diffe `static/` en voyant aussi les nouveaux fichiers.
      Utile, mais **pas la cause** : un run rouge et un run vert ont restauré la même clé
      de cache yarn avec le même Node. (2) La vraie cause, lue en reconstruisant le chunk
      depuis le log : le plugin commonjs de vite en mode `auto` décidait d'envelopper
      `codemirror` (importé en ESM par `configs.js` / `editor.js` **et** `require()` par
      ses modes) selon la transformation qui finissait la première — `htmlmixed-*.js`
      changeait de ~50 octets et donc de hash, et `configs`, `editor`, `manifest.json`
      avec lui. Correctif : `strictRequires: true` dans `build.commonjsOptions` de
      `CTFd/themes/admin/vite.config.js` (chemin déterministe du plugin, son défaut depuis
      la v26) + bundles admin reconstruits (5 builds locaux identiques ; pages admin,
      CodeMirror, modales Bootstrap et echarts vérifiés avec Playwright).
      _Reste : constater 3 pushs verts d'affilée._
- [x] 🤖 **`tests/users/test_challenges.py::test_challenge_kpm_limit_no_freeze`** (fait :
      toute la rafale + la soumission finale sous un seul `freeze_time`, 5 runs verts) :
      `assert "…59 seconds" == "…60 seconds"` — course entre l'horloge du rate-limit et
      celle du test. Correctif minimal et honnête : figer l'horloge (`freezegun`, déjà
      utilisé dans ce fichier) autour de la soumission, **pas** une assertion tolérante ;
      garder le test, ne jamais le `skip`.
- [ ] 🤖 Retirer les deux mentions « flake documenté » du commentaire de PR #1 une fois
      3 runs verts d'affilée.

**Définition de « fait ».** 3 pushs consécutifs entièrement verts sur les 8 jobs, sans
re-run manuel.

---

## 6. First bloods — notification + ticker 🟡 (finale)

**Pourquoi.** « 🩸 Kékéli Defenders ouvre _heap-note_ » projeté dans la salle fait
vibrer 10 équipes ; CTFd a déjà les `Notifications` (SSE vers la navbar, badge
hibris déjà en place).

**Périmètre.**

- [x] 🤖 Plugin `CTFd/plugins/firstblood/` (livré le 15/09) : boucle légère (même patron que le scorer
      KotH : verrou `fcntl`, pas de thread sous `TESTING`) qui, toutes les 5 s, cherche
      les challenges dont le **premier** `Solves` (compte ni caché ni banni, challenge
      visible — mêmes règles que le classement) n'a pas encore été annoncé (cache,
      **amorcé sans rien poster** au démarrage à froid pour ne pas rejouer l'historique)
      et poste une `Notifications` publique `🩸 First blood — <équipe> ouvre <challenge> (<catégorie>)`.
- [x] 🤖 Option `FIRSTBLOOD_BONUS` (points, défaut 0) : award `category="firstblood"`
      — **désactivé** par défaut ; à trancher 🧑 avec le règlement.
- [x] 🤖 Ruban HUD (`base.html`, `.hud-bar`) : segment « dernier first blood ».
      **Écart** : il interroge `/plugins/firstblood/api/recent` (mis en cache 10 s) toutes
      les 45 s plutôt que le flux SSE — un second `EventSource` par onglet doublerait les
      connexions tenues par gunicorn à 300 joueurs, et le bundle `events.js` d'hibris est
      pré-construit.
- [x] 🤖 Grand Prix mode projecteur (`scoreboard.html?big=1`) : **ticker** en bas des 5
      derniers first bloods + pastille 🩸 éphémère sur le kart concerné (à côté du badge
      KotH 👑, ne pas chevaucher la couronne du leader).
- [x] 🤖 Respect du **gel** : après `freeze`, plus d'annonce publique (l'admin voit tout).
- [x] 🤖 Tests (`tests/test_plugin_firstblood.py`) : premier solve → 1 notification ; 2ᵉ solve du même challenge → rien ;
      sous gel → rien pour le public.

**Définition de « fait ».** Sur la stack locale, `make local-playtest` déclenche une
notification par challenge résolu pour la première fois ; le ticker défile sur
`/scoreboard?big=1`.
_Vérifié le 15/09 contre un CTFd de test (sqlite) piloté par Playwright : ticker en bas
de `/scoreboard?big=1`, pastille 🩸 sur le kart après une vraie soumission via l'API,
segment HUD sur l'accueil. Reste 🧑 : `FIRSTBLOOD_BONUS` (règlement) et la passe
`make local-playtest` (Docker)._

---

## 7. Tableau de bord ops 🟡 (finale)

**Pourquoi.** Pendant l'épreuve, l'opérateur jongle entre `make logs`, `make gpu`,
la page KotH admin et l'admin CTFd. Une seule page, rafraîchie toutes les 5 s, pour
voir en 3 secondes si quelque chose brûle.

**Périmètre.** Plugin `CTFd/plugins/ops/`, page admin **Ops** (patron `koth/admin.html`).
Livré le 15/09 ; tests `tests/test_plugin_ops.py`.

- [x] 🤖 **Instancier** : instances vivantes / capacité (pool de ports frp), par équipe,
      plus ancienne vs TTL, reaper OK (battement `instancer:last_reap` ajouté dans
      `_reap_once`), instances en erreur.
- [x] 🤖 **Collines** : réutiliser `/plugins/koth/api/admin` (en ligne, tenant, plafond).
- [x] 🤖 **Soumissions** : débit/min sur l'heure (bonnes / mauvaises / limitées), 5 challenges
      les plus tentés. **5xx** : compteur cache alimenté par un `after_request` — donc
      « 5xx Flask » seulement : un timeout gunicorn ou une exception jamais transformée en
      réponse n'est pas vu (les logs gunicorn restent la référence, `make logs`).
- [x] 🤖 **Joueurs** : « actifs 15 min » = ont agi (soumission, connexion, nouvelle IP :
      c'est ce que `Tracking` enregistre, pas chaque GET), équipes ayant ≥ 1 solve.
- [x] 🤖 **Santé** : DB (ping + taille), Redis (ping), dernier backup (chantier 4, rouge si > 30 min pendant l'épreuve), dernier first blood (chantier 6), incidents anti-triche
      (chantier 1, lecture du cache seulement), état `ctftime()/paused/freeze`.
- [x] 🤖 Aucune action destructive sur la page : lecture seule, comme la page KotH.
- [x] 🤖 Endpoint `GET /plugins/ops/api/status` (`@admins_only`) pour un affichage
      sur écran secondaire.

**Définition de « fait ».** Pendant `make local-loadtest`, la page montre le débit monter,
les instances apparaître et rien ne dépasse 1 s de rendu.
_État : page rendue et vérifiée (Playwright, 7 cartes, rendu ~30 ms sur un CTFd de test) ;
le test unitaire borne le rendu à 1 s. La passe sous charge dépend du chantier 3 (k6),
pas encore construit._

---

## 8. Page « writeups » à la clôture 🟢

**Pourquoi.** Les joueurs en redemandent toujours, et ça valorise les 203 épreuves.
`challenges/WRITEUPS.md` + les `solution/README.md` existent déjà.

- [ ] 🤖 `deploy/scripts/publish_writeups.py` : assemble `WRITEUPS.md` + chaque
      `solution/README.md` (sans les scripts de solveur bruts) en une Page CTFd
      `/writeups` (Markdown → CTFd `Pages`, via l'API admin) — créée **cachée**
      (`hidden=True`) à l'avance, publiée d'un `--publish`.
- [ ] 🤖 Garde-fou : refus de publier tant que `ctf_ended()` est faux, sauf `--force`.
- [ ] 🤖 Cible `make writeups-publish` (`URL= TOKEN=`) + ligne dans `RUNBOOK §8`
      (clôture) et dans `render_archive.py` pour l'archive statique S3.
- [ ] 🧑 Décider : writeups **complets** ou seulement les catégories jouées en finale ;
      crédit des auteurs.

**Définition de « fait ».** Après `make writeups-publish` sur la stack locale
(`end` dans le passé), `/writeups` affiche l'index et les 203 solutions, lisibles
sur mobile, sans flag `NCTF{…}` réel en clair (les flags dynamiques sont par équipe
de toute façon).

---

## Ce qui n'est **pas** dans cette liste, et pourquoi

- **Re-design des collines KotH** (Throne XFF, Citadel `sudo env`) — mécanique de jeu
  validée, à ne toucher qu'à la marge après le playtest Lot 5.
- **Élection multi-conteneurs du scorer KotH** — le déploiement est mono-conteneur ;
  le verrou `fcntl` suffit (documenté dans `koth-ops.md`).
- **Consolidation des awards KotH en base** — le gel du scoreboard dépend de la date
  de chaque award ; le regroupement est fait à l'affichage uniquement.
