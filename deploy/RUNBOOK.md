# Runbook d'exploitation — CTF 2026

Procédure d'exécution de bout en bout : préparation, jours J, incidents, clôture.
Toutes les commandes se lancent **depuis `deploy/`** sauf mention contraire.

- **Présélection** : ven. 23 – sam. 24 octobre (~300 joueurs, par équipe, distant)
- **Finale** : jeu. 29 – ven. 30 octobre (~50 joueurs)
- Légende : 🧑 action humaine · 🤖 automatisable · ⏱ délai incompressible

> Règle d'or : la présélection **filtre**, la finale **décide**. Priorité des risques :
> effondrement infra ≫ compromission plateforme ≫ usage d'un LLM.

---

## 0. Prérequis opérateur (une seule fois)

- [ ] 🧑 AWS CLI configurée (`aws sts get-caller-identity` répond), profil avec droits EC2/S3/IAM/DynamoDB/ServiceQuotas.
- [ ] 🧑 `terraform` ≥ 1.6, `ssh`, `jq` installés sur le poste.
- [ ] 🧑 `deploy/terraform/terraform.tfvars` renseigné (au minimum `admin_cidrs` — **obligatoire, sans défaut**), à partir de `terraform.tfvars.example`.
- [ ] 🧑 Clé SSH d'admin déclarée dans les variables.
- [ ] 🧑 `deploy/front/.env` : `CTF_DOMAIN`, `CERTBOT_EMAIL`, `CTF_TEAM_FLAG_SECRET` (secret maître des flags — **hors git**, généré une fois : `openssl rand -hex 32`).

### État distant Terraform (recommandé avant le jour J)

Pour qu'un `apply` interrompu le matin du 23 soit reprenable et qu'aucun apply concurrent ne corrompe l'état :

```
make state-bootstrap                                              # crée bucket S3 + verrou DynamoDB (état local, une fois)
cp terraform/backend.tf.example terraform/backend.tf
terraform -chdir=terraform/bootstrap output -raw backend_hcl > terraform/backend.hcl
make init                                                        # répondre "yes" pour migrer l'état local -> S3
```

Sans cette étape, l'état reste **local** sur le poste (fonctionne, mais non reprenable ailleurs).

---

## 1. J-30 → J-14 — Délais incompressibles 🧑⏱

Ces points, pas le code, peuvent faire rater le 23 octobre.

- [ ] ⏱ **Quota GPU** : `make check-gpu-quota`. Si < 4 vCPU, **demander ≥ 8 immédiatement** (traitement plusieurs jours ouvrés). Sans GPU → **toute la catégorie IA saute**.
- [ ] ⏱ **Finale sur site ou distante** — deadline **18 septembre** (appro salle/switch/machines). Défaut si non tranché : portables perso sur VLAN contrôlé + téléphones en caisse.
- [ ] **Domaine** acheté/réservé ; décider Route53 (DNS auto) ou manuel.
- [ ] **Usage IA** : (A) mesurer la compétence *sans* assistance → IA autorisée en présélection, finale contrôlée [**recommandé**], ou (B) autorisée partout.
- [ ] **Juridique/RH** : notice de collecte (logs, prompts finale, conservation 30 j).

---

## 2. J-14 → J-7 — Répétition (front `setup`) 🤖🧑

Objectif : tout valider sur une petite infra avant de dimensionner pour 300.

```
make init                # (si pas déjà fait)
make phase-setup         # front seul, ~0,02 USD/h
make wait-front          # attend la fin du cloud-init
```

Puis DNS + TLS :

- [ ] 🧑 Pointer `CTF_DOMAIN` vers l'IP publique du front (`make phase-setup` affiche l'action DNS requise ; automatique si Route53).
- [ ] `make deploy` puis `make tls-init` ; vérifier `https://$CTF_DOMAIN/` répond.

### Import des challenges (ctfcli) 🤖

> ⚠ Pas encore de cible `make import`. Procédure manuelle, sur le front :

```
make ssh-front
cd /opt/ctfd/CTFd
python3 -m pip install --user ctfcli
export CTFCLI_TOKEN=<token admin CTFd>          # Admin > Settings > Access Tokens
export CTF_URL=https://$CTF_DOMAIN
ctf init --url "$CTF_URL" --api-key "$CTFCLI_TOKEN"
for d in challenges/*/*/; do ctf challenge install "$d" || echo "ECHEC: $d"; done
```

- [ ] 🤖 Vérifier l'import des **26** challenges (11 statiques + 15 servis).
- [ ] 🤖 **Chaîne IA de prérequis** : ai0 visible ; ai1/ai2/ai3 verrouillés tant qu'ai0 n'est pas résolu (403 sur `/attempt`). Résoudre ai0 avec un compte test → ai1 se débloque, etc.
- [ ] 🤖 Scoring dynamique : le score d'un challenge baisse quand un compte test le résout.
- [ ] 🤖 `make push-images` : images de challenge disponibles pour l'arena au prochain démarrage.

### Instancier par équipe (Lot 2) — validation live ⚠

- [ ] `make link` (relie front↔arena↔IA et vérifie). Doit passer les deux checks `check-arena` et IA.
- [ ] Un compte test clique « Démarrer » sur un challenge servi → obtient `front_ip:port`, s'y connecte, exploite, soumet son flag propre, scoreboard OK.
- [ ] Vérifier reap : après TTL (1 h) ou `destroy`, l'instance et son port frp disparaissent (`make check-arena`).
- [ ] **Migration MariaDB** : confirmer que les tables `team_instance`/`frp_port` sont créées et que `FOR UPDATE SKIP LOCKED` fonctionne sur la version MariaDB déployée.

### Piste IA (Lot 3) — validation live ⚠

- [ ] Résoudre ai0 → débloquer ai1 → discuter via la console → la passerelle d'admission (`ai-gateway`, front:8600) relaie vers Ollama → `/verify` valide le flag.
- [ ] Vérifier les bornes : rate-limit par équipe, budget tokens, 503 « modèle occupé » normalisé sous charge.
- [ ] `make gpu` montre l'activité ; les tentatives sont loggées (rotation en place).

### Test de charge (300) 🤖

- [ ] Basculer temporairement `make phase-preselection`, lancer un test de charge (login + scoreboard + recalcul scoring) à **300 connexions** → relever le point de rupture, ajuster `WORKERS`/taille d'instance. Puis `make phase-setup` (ou `season-down`) pour ne pas payer.

### Répétition générale 🧑🤖

- [ ] 20-30 personnes internes, 3 h, sur l'infra de prod. **C'est ici qu'on fixe les vraies valeurs** de rate-limit et de quotas IA, pas à l'intuition.
- [ ] Rejouer le pré-test adverse (playtest) sur les challenges du haut de tableau (cf. `anti-llm-guardrails.md` §4.9/§8 ; audit statique de départ dans `challenge-audit.md`).

### Config CTFd + règlement 🧑

- [ ] Mode équipes ; taille max d'équipe ; scoring dynamique ; compteurs de solves masqués ; scoreboard gelable ; fenêtre synchrone ; ToS obligatoire.
- [ ] **Thème** : activer le thème custom **`hibris`** (aligné vitrine CERT.tg, drapeau Togo,
      glitch léger, sans marque CTFd ; pied de page « Organisé par CERT.tg » + « Powered by
      Hibris · ramses.dagban.tg »). Il est présent dans `CTFd/themes/hibris/`. L'activer une
      fois, au choix :
        - UI : *Admin → Config → Theme* → sélectionner `hibris` ;
        - ou API : `curl -H "Authorization: Token <admin>" -H 'Content-Type: application/json' \`
          `-X PATCH https://$CTF_DOMAIN/api/v1/configs -d '{"ctf_theme":"hibris"}'`.
      CTFd 3.7 avertit sur les thèmes custom (SSTI via éditeur admin) : on l'installe par le
      système de fichiers (voie sûre), pas via l'éditeur. Vérifier le rendu (accueil, board,
      scoreboard, login, **pages d'erreur 404/403/429/500/502**) à la phase `setup` — cf. la
      note de compatibilité templates 3.7.7.
- [ ] **Accueil « waou »** : l'accueil de CTFd est une *page CMS*, pas un template du thème —
      par défaut elle trahit CTFd. Coller le bloc `deploy/theme-home-hero.html` dans
      *Admin → Pages → page « / » (route vide/index) → éditeur → bouton `</>` (HTML)*, puis
      *Save*. Bloc autonome (styles préfixés `.nctf-*`, mêmes couleurs/polices que le thème,
      titre `NCTF25` + glitch). Ajuster dates, chiffres et liens si besoin. Objectif : un
      participant ne doit pas deviner que c'est du CTFd.
- [ ] **Règlement** publié AVANT l'ouverture des inscriptions (§6 garde-fous).

---

## 3. J-7 — Bascule présélection 🧑

```
make phase-preselection      # crée arena + nœud IA ; ~1,30 USD/h
make wait-front              # front prêt
make wait-arena             # arena + IA prêts (télécharge le modèle Ollama)
make link                   # relie tout, vérifie arena + IA
make deploy && make tls-init # si le front a été recréé
make check-arena            # images de challenge présentes
```

- [ ] 🧑 Repointer le DNS si l'IP a changé ; vérifier HTTPS.
- [ ] 🧑 Ouvrir les inscriptions.
- [ ] 🧑 Dernier `season`-test : un compte réel résout un challenge de chaque type.

---

## 4. Jours J présélection (23-24 oct) 🧑

Cadence pendant l'épreuve :

| Quand | Commande | Attendu |
|---|---|---|
| toutes les ~30 min | `make backup` | dump **vérifié** (gzip -t + table users) envoyé sur S3 |
| en continu (2ᵉ terminal) | `make logs` | pas d'erreur 5xx en rafale |
| si piste IA active | `make gpu` | file Ollama non saturée en permanence |
| au moindre doute | `make cost` | rappel de ce qui est facturé |

- [ ] 🧑 24 au soir : `make season-down` (**sauvegarde vérifiée + archive S3 + destruction EC2**).
- [ ] 🧑 **Ligne de coupe automatique** à la fermeture : inviter 14-16 équipes (marge + wildcards). Litiges d'intégrité traités **après** la finale.

---

## 5. Playbooks d'incident 🚑

Diagnostic d'abord : `make cost` (qu'est-ce qui tourne ?), `make logs`, `make ssh-*` puis `sudo cat /var/log/cloud-init-output.log`.

**Front injoignable (HTTP KO)**
1. `make ssh-front` → `cd /opt/ctfd/CTFd && docker compose ps`.
2. Conteneur ctfd down → `docker compose up -d` ; logs → `docker compose logs ctfd`.
3. cloud-init pas fini → attendre / `make wait-front`.
4. Nginx/TLS cassé → revérifier `make tls-init` (DNS doit résoudre vers l'IP du front).

**CTFd ne joint pas le Docker de l'arena** (instancier KO — **risque #1**)
1. `make link` (réétablit le tunnel ssh dockerproxy + frpc).
2. Échec du check → `make ssh-arena`, vérifier le démon Docker et l'overlay `--attachable`.
3. Vérifier que `-p 127.0.0.1:P` fonctionne côté arena et que la plage frp (28000-28500) n'est pas épuisée (501 instances max).

**Connexion joueur `front_ip:port` échoue**
1. frpc admin joignable via le tunnel ? `PUT /api/config` + reload effectifs ?
2. `allowPorts` frps couvre la plage ; le forward 7400 via dockerproxy est up.

**Piste IA : 503 permanents / GPU saturé**
1. `make gpu` : file pleine → c'est le comportement borné attendu sous pointe. Réduire les quotas d'admission (`AI_*` dans l'env de `ai-gateway`) sans rebuild.
2. Ollama down → `make ssh-ai`, redémarrer le service ; vérifier le modèle téléchargé.
3. Arène→front:8600 injoignable → vérifier la règle SG et l'injection `OLLAMA_URL`/`AI_PROXY_TOKEN`.

**Disque plein (« no space left »)**
- Les logs de tentatives IA sont en rotation bornée (pas la cause). Supprimer artefacts/anciens backups locaux ; sur l'arena, purger images/conteneurs morts. Les deletes réussissent même disque plein.

**Corruption / perte de données** → **restaurer**
```
make backup                                   # d'abord figer l'état courant
make restore FILE=backups/<dump>.sql.gz       # restaure sur le front
```

**Apply Terraform interrompu / à moitié raté**
- Avec état distant : relancer simplement `make phase-<...>` (verrou DynamoDB + état S3 rendent l'apply reprenable). Si un verrou traîne (process tué) : `terraform -chdir=terraform force-unlock <LOCK_ID>` après avoir confirmé qu'aucun apply ne tourne.
- Base branch/infra saine mais ressource bloquée : `terraform -chdir=terraform apply` seul re-converge.

---

## 6. Entre-deux (24 → 29 oct) 🧑

- [ ] Infra **détruite** (`season-down` déjà fait le 24 au soir — 5 jours d'instances inutiles coûtent plus que la reconstruction).
- [ ] Résultats de présélection = dans la sauvegarde S3 + l'archive statique (`make archive`).
- [ ] Logistique finale (convocations, salle/VLAN si sur site).

---

## 7. Finale (29-30 oct) 🧑

```
make phase-final            # taille réduite (~50 joueurs)
make wait-front && make wait-arena && make link
make deploy && make tls-init
make check-arena
```

- [ ] 🧑 Si sur site : réseau contrôlé, egress liste blanche, machines/VLAN, téléphones en caisse.
- [ ] 🧑 **Classement repart de zéro** (présélection à 0 %).
- [ ] 🧑 Défense devant jury (poids additif faible ≤ 10 %, jamais un gate).
- [ ] 🧑 `make backup` régulier ; `make season-down` le 30 au soir.

---

## 8. Clôture & archives 🧑🤖

```
make archive                # scoreboards figés + write-ups sur S3 (site statique)
make season-down            # si pas déjà détruit
```

- [ ] 🤖 Publier les write-ups officiels par challenge (**après** l'événement — jamais avant, ils leakeraient les solutions).
- [ ] 🧑 Rapport de clôture (agrégé, sans accusation nominative depuis la scène).
- [ ] 🤖 Exploiter les logs de charge pour dimensionner l'édition suivante.

---

## Annexe — carte des commandes

| Commande | Rôle |
|---|---|
| `make init` / `make state-bootstrap` | init Terraform / état distant S3+DynamoDB |
| `make check-gpu-quota` | quota GPU (à lancer **maintenant**) |
| `make phase-setup / -preselection / -final / season-down` | leviers de coût |
| `make wait-front / wait-arena` | attente provisionnement |
| `make deploy / tls-init / link` | déploiement CTFd / HTTPS / liaison front↔arena↔IA |
| `make check-arena / push-images` | images de challenge sur l'arena |
| `make backup / restore FILE=... / archive` | sauvegarde vérifiée / restauration / archive S3 |
| `make logs / gpu / cost` | supervision |
| `make ssh-front / ssh-arena / ssh-ai` | shells |
| `make destroy` | détruit l'EC2 (le bucket d'archives survit) |
