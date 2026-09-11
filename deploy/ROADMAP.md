# Feuille de route CTF 2026 — suivi lot par lot

Document de suivi vivant. On coche les cases au fur et à mesure.

- **Aujourd'hui** : 10 septembre 2026
- **Présélection** : vendredi 23 – samedi 24 octobre (par équipe, ~300 joueurs, distant)
- **Finale** : jeudi 29 – vendredi 30 octobre (10 équipes, ~50 joueurs)
- **Légende propriétaire** : 🧑 = vous (décision / action humaine) · 🤖 = moi (Claude, build)
- **Convention** : `[ ]` à faire · `[~]` en cours · `[x]` fait · `[!]` bloquant / délai critique

> Règle d'or issue de `anti-llm-guardrails.md` : la présélection **filtre**, la finale
> **décide**. Le risque réel est, dans l'ordre : effondrement de l'infra ≫ compromission
> de la plateforme ≫ quelqu'un utilise un LLM. La feuille de route est priorisée ainsi.

---

## Phase 0 — Décisions & délais incompressibles 🧑 (ne dépendent que de vous)

Ce sont elles qui peuvent faire rater le 23 octobre, pas le code.

- [!] **Demander le quota GPU AWS maintenant.** Compte neuf = quota « Running On-Demand
      G and VT instances » souvent à 0 ; une `g4dn.xlarge` en consomme 4 vCPU. Délai de
      traitement : plusieurs jours ouvrés. Lancer `cd deploy && make check-gpu-quota` ;
      si < 4, demander ≥ 8 immédiatement. **Sans GPU, toute la catégorie IA saute.**
- [!] **Décider : finale sur site ou distante.** Deadline **18 septembre** (appro salle /
      switch / machines a un délai). Défaut si non tranché : portables perso sur VLAN
      contrôlé + téléphones en caisse (moins fort, sans achat).
- [ ] **Trancher (A) ou (B)** sur l'usage de l'IA (cf. §2 du doc garde-fous) :
      (A) mesurer la compétence *sans assistance* → IA autorisée en présélection, finale
      contrôlée. (B) mesurer la compétence *avec* IA → autorisée partout. **Recommandé : A.**
- [ ] **Confirmer : présélection par équipe.** ✅ *Confirmé le 10/09.* Impact déjà intégré
      (mode équipes CTFd, flags par `team_id`).
- [ ] **Trancher : piste IA en présélection ou réservée à la finale.** Un GPU sert ~1-2
      req/s utiles ; à 300 joueurs la piste ne tient qu'avec quota bas + file stricte.
      **Recommandé : réserver à la finale**, ou side-event annoncé à quota bas.
- [ ] **Saisir juridique / RH** sur la notice de collecte de données (logs, prompts finale,
      conservation 30 j). Conditionne la section détection ; hors chemin critique technique.
- [ ] **Acheter / réserver un domaine** pour le CTF, et décider si géré dans Route53
      (DNS automatique) ou manuel.

---

## Lot 0 — Choix de la plateforme ✅ TERMINÉ

- [x] Plateforme retenue : **CTFd 3.7.7** (fork `hi3ris/CTFd`), Apache-2.0, extensible.

---

## Lot 1 — Infrastructure AWS ✅ TERMINÉ (audité + corrigé)

Piloté par une variable `phase` (off / setup / preselection / final). PR #1.

- [x] Terraform : VPC, front (ARM), arena (x86 Swarm), nœud IA (GPU), archives S3
- [x] Modèle de coût par phase (~120 USD/édition), `make cost`
- [x] TLS (`make tls-init`), en-têtes proxy durcis (X-Forwarded-Host)
- [x] Sauvegarde **vérifiée** + `make restore` (le blocker de dump silencieux est corrigé)
- [x] Archives statiques rendues côté serveur, bucket `prevent_destroy`
- [x] IAM arena en lecture seule sur `images/`, IMDSv2 hop-limit 1, Spot one-time
- [x] Audit adverse (5 dimensions, 15 agents) → 6 blockers/majeurs confirmés et corrigés

### Reliquat Lot 1 (à traiter avant mise en prod, non bloquant maintenant)
- [ ] 🤖 Passer en revue les **45 findings mineurs non vérifiés** de l'audit (rapport
      dans le transcript workflow) et trancher un par un.
- [ ] 🤖 État Terraform : aujourd'hui **local**. Mettre un backend S3 + DynamoDB lock
      pour qu'un apply à moitié raté le matin du 23 soit reprenable.
- [ ] 🧑 Décider Savings Plan / taille du front après le test de charge (Lot 5).

---

## Lot 1.5 — Garde-fous anti-LLM ✅ TERMINÉ

- [x] `deploy/anti-llm-guardrails.md` : doc de décision (55 mesures → red team → synthèse)
- [x] Principe présélection 0 % / finale décide ; liste de ce qu'on **ne** construit **pas**

---

## Lot 4 — Challenges (écrits, à câbler + playtester) 🟡 PARTIEL

26 challenges sous `challenges/`. **15 servis** (flag `team_hmac`, dépendent du Lot 2),
**11 statiques** (jouables tels quels une fois importés).

- [x] 🤖 Écriture des 26 challenges (workflow 52 agents + vérif adverse)
- [x] 🤖 Plugin `team_hmac` (`CTFd/plugins/team_hmac_flag/`) — validation flag par équipe
- [x] 🤖 Les 15 challenges servis convertis en `type: team_hmac` (contenu = leur CHALLENGE_ID)
- [x] 🤖 Correctifs : dns-exfil (pcap régénéré), ai2 (image/state + flag), adversarial-gate
- [ ] 🤖 **Ajouter les clés `files:` manquantes** là où un handout doit être livré au joueur
      (plusieurs verdicts l'ont noté ; sinon les aides de recon ne parviennent pas aux équipes).
- [ ] 🤖 **Câbler la chaîne de prérequis IA** dans CTFd à l'import : ai0 → ai1 → ai2 → ai3
      (via `requirements` par challenge ID). Idem toute autre dépendance voulue.
- [ ] 🧑🤖 **Playtest adverse OBLIGATOIRE** (cf. §4.9 & §8 garde-fous) : 2 modèles frontier
      + 1 harness agentique, budget 30-60 min/challenge, transcript conservé. Résolu seul
      en < 15 min → **on coupe**. À faire sur le front `setup` avant la présélection.
- [ ] 🧑🤖 **Recherche de prior art** publique ET interne (éditions passées, dépôts, images).
- [ ] 🧑 Relecture à froid par un second auteur des challenges à format inventé (tlv-vault…).
- [ ] 🤖 Vérifier que `pwn/*` (heap libc-pinné, ROP) buildent et que les solveurs passent
      dans un vrai environnement (non vérifiable dans la session actuelle — signalé).

> Détail des 26 : voir `challenges/README.md`. Chaîne IA à 4 niveaux (ai0 sans inférence
> gate le reste). ML : pickle-rce, adversarial-gate.

---

## Lot 2 — Instancier par équipe (`team_instancer`) 🟢 CODE COMPLET (validation live au Lot 5)

> Revue adverse (12 agents) → 8 défauts corrigés, dont **2 blockers** : injection du secret
> **maître** dans les conteneurs (un pwn compromis livrait tous les flags) → n'injecte plus
> qu'un `CHALLENGE_SECRET` par challenge + le `FLAG` concret ; et `start_time` NULL en prod
> (jamais reap) → défaut Python-side. Les **15 challenges servis** adaptés au contrat
> `FLAG`/`CHALLENGE_SECRET` (valeur de flag inchangée, vérifiée 15/15).

**Décision : build-maison** (`CTFd/plugins/team_instancer/`), pas `ctfd-whale` — celui-ci
casse chez nous sur 5 points (clé sur `user_id`, flag en boucle fermée conflictuel avec
`team_hmac`, services Swarm qui tenteraient un pull, admin frpc injoignable). On réutilise
les patrons, on importe `team_hmac_flag.team_secret_for()` pour ne jamais redériver le secret.

### 2.1 Squelette plugin & type de challenge
- [x] 🤖 Type `team_instance` (hérite du scoring dynamique + `docker_image`/`internal_port`),
      enregistré dans `CHALLENGE_CLASSES`, assets create/update/view. Charge même si inactif.
- [x] 🤖 Les 15 challenges servis convertis `type: dynamic → team_instance` (+ `extra`), flag `team_hmac`.

### 2.2 Modèle & migration
- [x] 🤖 Tables `team_instance` (clé équipe, unicité `(account_id, challenge_id)`) + `frp_port`.
      Révision Alembic ; `create_all` sur SQLite dev.
- [ ] 🧑🤖 Exécuter réellement la migration sur **MariaDB** prod (vérifier `SKIP LOCKED` / version).

### 2.3 Client Docker & création
- [x] 🤖 `containers.run` sur `DOCKER_HOST` (image locale, pas de pull), env **`TEAM_SECRET` seul**,
      réseau overlay par équipe, limites mem/cpu/**pids**, labels.
- [ ] ⚠🧑🤖 **Répétition** : que le socket tunnelé porte `containers.run` sur image locale ;
      que `-p 127.0.0.1:P` marche sur l'arena ; création overlay `--attachable`.

### 2.4 Câblage FRP
- [x] 🤖 Allocation de port atomique (`FOR UPDATE SKIP LOCKED`), génération/parsing du bloc TOML
      (idempotent, testé en unitaire), reload frpc. **Voie B retenue** : forward du 7400 via
      `dockerproxy` (+ `allowPorts` durci sur frps). dockerproxy/compose/Makefile/.env câblés.
- [ ] ⚠🧑🤖 **Répétition** : joignabilité réelle de frpc admin via le tunnel ; `PUT /api/config`
      + reload effectifs ; connexion joueur `front_ip:port` de bout en bout. **Risque #1.**

### 2.5 Routes & admission
- [x] 🤖 Blueprint spawn/renew/destroy/status, `@authed_only`+`during_ctf_time`, **garde de
      prérequis** (rejeu de `challenges.py`), caps (`MAX_PER_TEAM`, global, unicité), rate-limit.
- [ ] 🧑 Tenue sous ~300 équipes concurrentes sur le canal ssh unique (test de charge Lot 5).

### 2.6 TTL, reaper, réconciliation
- [x] 🤖 Reaper thread dépendance-zéro (verrou `fcntl`, un seul worker), teardown idempotent,
      réconciliation DB↔Docker, purge au reboot arena.
- [ ] ⚠🧑🤖 **Répétition** : réconciliation contre l'état arena réel.

**⚠ Décision capacité à figer avant Lot 5** : la plage 28000-28500 = **501 instances
concurrentes** max. TTL 1 h + reaping le tiennent, mais élargir la plage si besoin de marge.

**Définition de « fait » Lot 2** : validé à la répétition (Lot 5) — une équipe clique
« Démarrer », obtient une instance isolée avec son flag propre, l'exploite, scoreboard OK.

---

## Lot 3 — Piste IA : passerelle d'admission + correctifs 🟡 EN COURS

**Déviation actée du ROADMAP** (conception dans `deploy/ai-track-design.md`) : la route
`/message`, l'UI de chat et l'oracle de flag **existent déjà dans les conteneurs** (chaque
app IA sert sa console + un `/verify` déterministe). On **ne les reconstruit pas**. Le vrai
Lot 3 = **une passerelle d'admission Ollama** sur le front + petits correctifs.

### Correctifs (faits)
- [x] 🤖 **Chaîne de prérequis câblée** (elle n'était qu'en commentaire) : ai0→ai1→ai2→ai3
      via `requirements` (noms nus) dans les YAML.
- [x] 🤖 **Accessibilité** : les conteneurs IA (sur l'arène) ne pouvaient pas joindre Ollama
      (SG ouvert au seul front) et n'avaient pas `OLLAMA_URL`. Corrigé : règle SG arène→front:8600,
      l'instancier injecte `OLLAMA_URL`=passerelle + `AI_PROXY_TOKEN` signé pour les challenges
      `category: ai` ; `make link` écrit `AI_PROXY_URL`. Ollama reste fermé à l'arène.

### Passerelle d'admission (à construire)
- [ ] 🤖 Service front `ai-gateway` : `POST /api/chat` (vérif jeton signé → équipe/niveau),
      concurrence globale + par-niveau, budget tokens + rate-limit par équipe (fenêtre glissante),
      file bornée, **normalisation du 503** Ollama en « modèle occupé, réessayez ».
- [ ] 🤖 Les apps ai1/ai2/ai3 envoient `AI_PROXY_TOKEN` en en-tête à `OLLAMA_URL`.
- [ ] 🤖 **Journalisation** des tentatives (équipe, niveau, tokens, verdict ; contenu
      **finale-seulement**) exportée par `make backup` avant `season-down`.
- [ ] 🧑 **Décision** : piste IA en présélection ou **réservée à la finale** ? Un T4 ne tient
      pas 300 équipes simultanées ; la passerelle borne, elle n'ajoute pas de capacité.
- [ ] 🧑 Quotas exacts par phase — fixés à la répétition (Lot 5), pas à l'intuition.
- [ ] ⚠🧑🤖 **Répétition** : joignabilité arène→8600→Ollama, latence, comportement 503/429 réels.

**Définition de « fait » Lot 3** : une équipe résout ai0 → débloque ai1 → discute via la
passerelle → flag validé par `/verify` → scoreboard OK, GPU borné, tentatives loggées.

---

## Lot 5 — Intégration & répétition générale 🔴 (semaine du 12 octobre)

- [ ] 🤖 Import de **tous** les challenges via ctfcli sur le front `setup`.
- [ ] 🤖 Vérifier la chaîne de prérequis IA de bout en bout, et les scores dynamiques.
- [ ] 🤖 **Test de charge à 300 connexions** (login + scoreboard + recalcul scoring) sur le
      front `preselection` → relever le vrai point de rupture, ajuster WORKERS/instance.
- [ ] 🧑🤖 **Répétition générale** : 20-30 personnes internes, 3 h, sur l'infra de prod.
      C'est là qu'on fixe les vraies valeurs de rate-limit, pas à l'intuition.
- [ ] 🤖 Rejouer le pré-test adverse sur les challenges du haut de tableau.
- [ ] 🧑 Rédiger et publier le **règlement** (§6 garde-fous) AVANT l'ouverture des inscriptions.
- [ ] 🧑 Config CTFd : mode équipes, taille max d'équipe, scoring dynamique, compteurs de
      solves masqués, scoreboard gelé, fenêtre synchrone, ToS obligatoire.

---

## Lot 6 — Jour J présélection (23-24 octobre) 🔴

- [ ] 🧑 J-7 : `make phase-preselection` (crée arena + IA, télécharge le modèle, câble tout).
- [ ] 🧑 Repointer le DNS (ou automatique si Route53) ; `make tls-init` ; vérifier HTTPS.
- [ ] 🧑 Ouvrir les inscriptions ; vérifier `make check-arena` et la piste IA.
- [ ] 🧑 Pendant l'épreuve : `make logs`, `make gpu`, `make backup` **régulièrement**.
- [ ] 🧑 24 au soir : `make season-down` (sauvegarde vérifiée + archive S3 + destruction EC2).
- [ ] 🧑 Ligne de coupe **automatique** à la fermeture : inviter 14-16 équipes (marge +
      wildcards). Litiges d'intégrité traités **après** la finale.

---

## Lot 7 — Entre-deux (24 → 29 octobre) 🔴

- [ ] 🧑 Infra détruite (5 jours d'instances inutiles coûtent plus que la reconstruction).
- [ ] 🧑 Résultats de présélection = dans la sauvegarde S3 + l'archive statique.
- [ ] 🧑 Préparer la logistique finale (convocations, salle/VLAN si sur site).

---

## Lot 8 — Jour J finale (29-30 octobre) 🔴

- [ ] 🧑 `make phase-final` (taille réduite ~50 joueurs), DNS, TLS, check-arena.
- [ ] 🧑 Si sur site : réseau contrôlé, egress liste blanche, machines/VLAN, téléphones en caisse.
- [ ] 🧑 Classement **repart de zéro** (présélection à 0 %).
- [ ] 🧑 Défense devant jury (poids additif faible ≤ 10 %, jamais un gate).
- [ ] 🧑 `make backup` régulier ; `make season-down` le 30 au soir.

---

## Lot 9 — Clôture & archives 🔴

- [ ] 🧑 `make archive` : scoreboards figés + write-ups publiés sur S3 (site statique).
- [ ] 🤖 Publier les write-ups officiels par challenge.
- [ ] 🧑 Rapport de clôture (agrégé, sans accusation nominative depuis la scène).
- [ ] 🤖 Exploiter les logs de charge pour dimensionner l'édition suivante.

---

## Ordre recommandé d'exécution

1. **En parallèle maintenant** : 🧑 Phase 0 (quota GPU + décisions) · 🤖 **Lot 2 (instancier)**
2. 🤖 Lot 3 (plugin IA) + reliquat Lot 4 (prérequis, files:)
3. 🧑🤖 Lot 5 (intégration + test de charge + répétition + playtest)
4. Lots 6 → 9 (jours J et clôture)

**Prochaine action de ma part : Lot 2.1 (installation de `ctfd-whale`).**
