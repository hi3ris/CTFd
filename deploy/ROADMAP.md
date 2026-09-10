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

## Lot 2 — Instancier par équipe (`ctfd-whale`) 🔴 PROCHAINE ÉTAPE

C'est le maillon bloquant : sans lui, les **15 challenges servis** ne peuvent ni spawner
d'instance par équipe ni recevoir leur `TEAM_SECRET`.

### 2.1 Installation du plugin
- [ ] 🤖 Installer `ctfd-whale` sous `CTFd/plugins/ctfd-whale/` (ou équivalent maintenu),
      épingler une version, ajouter ses `requirements.txt` au build de l'image CTFd.
- [ ] 🤖 Vérifier compat CTFd 3.7.7 (le plugin cible des versions précises — adapter si besoin).

### 2.2 Connexion au Docker de l'arena
- [ ] 🤖 Configurer whale pour piloter le démon Docker de l'arena **via `dockerproxy`**
      (`tcp://dockerproxy:2375` sur le réseau interne), pas un socket exposé.
- [ ] 🤖 Vérifier que `make link` fournit déjà `DOCKER_HOST` à CTFd (fait) et que whale le lit.
- [ ] 🤖 Réseau Swarm : une instance par équipe dans un réseau **isolé** (pas de lien
      équipe A ↔ équipe B). L'overlay `ctfd_challenges` existe déjà côté arena.

### 2.3 Exposition via FRP
- [ ] 🤖 Câbler whale ↔ `frpc` (arena) ↔ `frps` (front) : chaque instance obtient un
      port/sous-domaine unique dans la plage `whale_port_range_start..end` (déjà ouverte).
- [ ] 🤖 Vérifier que l'admin FRP reste sur `127.0.0.1` (déjà durci) et que whale y accède
      par le bon canal.

### 2.4 Injection du secret par équipe (le point clé)
- [ ] 🤖 Adapter whale pour injecter dans chaque conteneur
      `TEAM_SECRET = HMAC(CTF_TEAM_FLAG_SECRET, team_id)` — **exactement** la dérivation du
      plugin `team_hmac` (déjà prouvée byte-à-byte). C'est ce qui fait qu'un flag résolu est
      accepté au scoreboard.
- [ ] 🤖 Test d'intégration : spawn d'une instance de démo → le flag émis par le conteneur
      == `team_hmac.expected_flag(team_id, challenge_id)`. Automatiser en smoke test.

### 2.5 Contrôles d'admission (infra)
- [ ] 🤖 Rate limits **généreux** sur l'instancier (spawn/renew/destroy) par équipe.
- [ ] 🤖 Limites CPU / mémoire / PID par service Swarm (anti fork-bomb / fuzzer).
- [ ] 🤖 TTL + bouton renew/destroy par instance ; nettoyage des instances orphelines.

### 2.6 Validation
- [ ] 🤖 Déployer **1 challenge de démo** (ex. `web/race-the-coupon`) de bout en bout :
      import → spawn par équipe → exploit → flag accepté. `make check-arena` vert.
- [ ] 🧑 Test manuel avec 2 comptes équipe distincts : flags différents, isolation réseau OK.

**Définition de « fait » Lot 2** : une équipe clique « Start », obtient une instance isolée
avec son flag propre, l'exploite, et le scoreboard l'accepte.

---

## Lot 3 — Plugin `ai_challenges` 🔴 À FAIRE (après Lot 2)

Les 4 services IA existent ; il manque l'expérience joueur et le contrôle de charge.

- [ ] 🤖 Route de chat CTFd `POST /api/v1/ai/<challenge_id>/message` qui **rejoue le contrôle
      de prérequis** que CTFd fait sur `/attempt` (sinon un joueur tape le niveau 3 sans avoir
      résolu le 1 — l'hypothèse de capacité s'effondre). Vérif sur `account_id`.
- [ ] 🤖 UI de chat dans le thème (historique par équipe, streaming des réponses).
- [ ] 🤖 **Contrôle d'admission par niveau** : plafond de sessions simultanées (bas au niv. 3),
      budget de tokens par équipe/niveau (fenêtre glissante), rate-limit messages/min.
- [ ] 🤖 Traduire le `503` d'Ollama (file pleine, `OLLAMA_MAX_QUEUE`) en « modèle occupé,
      réessayez » lisible, jamais une erreur brute.
- [ ] 🤖 **Journalisation** de chaque tentative : équipe, niveau, prompt, réponse, tokens,
      verdict. Exporté avant `season-down`.
- [ ] 🤖 Validation du flag par **appel d'outil déterministe**, jamais par le texte du modèle.
- [ ] 🧑 Décider quota exact (ex. 10 req/min/équipe, 500/jour) selon décision Phase 0.

**Définition de « fait » Lot 3** : une équipe résout ai0 (statique) → débloque ai1 → discute
avec le modèle → le flag est validé, la charge GPU reste bornée, tout est loggé.

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
