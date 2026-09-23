# Déploiement NCTF26 sur AWS — runbook de handoff

> Runbook auto-suffisant pour déployer la plateforme sur AWS. Basé sur
> l'outillage réel du repo : Terraform + une variable `phase` pilotée par les
> cibles `make phase-*`. Se lit avec `deploy/RUNBOOK.md` (procédure jour-J
> détaillée + §5 incidents) et `deploy/GOAL.md`.
>
> **Toutes les commandes se lancent depuis `deploy/`.**

## Contexte

- Repo : `hi3ris/CTFd`, branche `claude/ctf-platform-free-ptiggj`.
- Infra pilotée par `phase` (`off | setup | preselection | final`). Hors
  événement : **0 instance EC2** ; seul un bucket S3 d'archives subsiste
  (~0,50 USD/mois). Estimation de l'édition : ~120 USD (couverts par crédits AWS).
- Calendrier : présélection **23–25 oct** (~300 joueurs, mode équipes, distant),
  finale **29–30 oct** (~50 joueurs).
- Région par défaut : `eu-west-3` (Paris ; GPU g4dn disponibles).

## Authentification AWS (la session d'action fournit ses propres credentials)

La méthode officielle, jamais une clé en clair dans une commande :

```bash
aws configure sso          # ou un profil IAM/role classique
aws sso login
aws sts get-caller-identity # doit répondre : profil avec droits EC2/S3/IAM/DynamoDB/ServiceQuotas
```

## 0. Prérequis poste opérateur

```bash
terraform version   # >= 1.6
# aussi requis : ssh, jq, docker (pour la validation locale §4)
```

## 1. Secrets & config (une fois, HORS git)

```bash
cd deploy
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
cp front/.env.example front/.env
```

Éditer **`terraform/terraform.tfvars`** :

- `admin_cidrs` = IP publique bureau/VPN en `/32` — **obligatoire, sans défaut ;
  jamais `0.0.0.0/0`**.
- `ssh_public_key` = contenu de la clé publique SSH admin.
- `domain_name` (optionnel), `player_cidrs` (défaut `0.0.0.0/0`), `aws_region`,
  `ollama_model` (`llama3.1:8b`).
- Laisser `phase = "off"` (les `make phase-*` passent la valeur voulue).

Éditer **`front/.env`** (renseigner à la main ; générer chaque secret avec
`openssl rand -hex 32`) :

- `SECRET_KEY`, `DB_PASSWORD`, `DB_ROOT_PASSWORD`.
- `CTF_TEAM_FLAG_SECRET` — **secret maître des flags par équipe**. Ne pas le
  changer après le début de l'épreuve : sa rotation invalide les flags
  `team_hmac`.
- `CTF_DOMAIN`, `CERTBOT_EMAIL` (TLS Let's Encrypt, lus par `make tls-init`).
- Ne PAS toucher les blocs marqués « écrits par `make link` » (`ARENA_HOST`,
  `DOCKER_HOST`, `OLLAMA_URL`, `FRPC_*`, `WORKERS`, `INNODB_POOL`…) : le prochain
  `make link` les écrase.

## 2. Délai incompressible — à faire MAINTENANT

```bash
make check-gpu-quota        # lit le quota
make request-gpu-quota      # dépose la demande (≥ 8 vCPU) si le quota est < 4
make free-credits           # plan gratuit : les 5 activités « Earn AWS credits » (+100 USD)
```

Si le quota « Running On-Demand G and VT instances » est < 4 vCPU → **demander
≥ 8 immédiatement** (traitement plusieurs jours ouvrés). Sans GPU, toute la
catégorie IA saute.

## 3. État Terraform distant (recommandé avant le jour J)

```bash
make state-bootstrap                                             # bucket S3 + verrou DynamoDB
cp terraform/backend.tf.example terraform/backend.tf
terraform -chdir=terraform/bootstrap output -raw backend_hcl > terraform/backend.hcl
make init                                                        # "yes" pour migrer l'état -> S3
```

Sans cette étape, l'état reste local sur le poste (fonctionne, mais non
reprenable ailleurs et vulnérable à un apply concurrent).

## 4. Validation locale AVANT tout apply AWS (Docker, 0 coût)

```bash
make local-up && make local-build-images && make local-seed
make local-smoke        # pages, thème, assets, API : tout doit passer
make local-playtest     # spawn -> solveur de référence -> soumission, sans FAIL
```

> **Honnêteté catalogue** : sur les ~328 challenges servis, **10 sont réellement
> implémentés + vérifiés** ; le reste sont des STUBs `state: hidden`.
> `local-playtest` ne passe que sur les servis finis — ne pas rendre les stubs
> visibles. Cf. `deploy/served-plan.md`.

## 5. Répétition — phase `setup` (J-14 → J-7)

```bash
make phase-setup        # front seul, ~0,02 USD/h
make wait-front
# DNS : pointer CTF_DOMAIN vers l'IP publique du front (make phase-setup l'affiche)
make deploy && make tls-init
```

## 6. Bascule présélection (J-7 / le 23)

```bash
make phase-preselection        # crée arena + nœud IA ; ~1,30 USD/h
make wait-front && make wait-arena     # wait-arena télécharge le modèle Ollama
make link                      # relie front<->arena<->IA ; écrit les vars auto de front/.env
make deploy && make tls-init   # si le front a été recréé
make check-arena               # images de challenge présentes sur l'arena
make push-images               # si check-arena signale des images manquantes
CTFD_TOKEN=<jeton_admin> make preflight PHASE=preselection   # DOIT être vert : 0 FAIL
```

**Gate** : `preflight` vert (secrets, fenêtre 53 h, challenges/catégories,
collines KotH). Un seul FAIL = on ne bascule pas. Ensuite : repointer le DNS si
l'IP a changé, ouvrir les inscriptions, test réel (un compte résout un challenge
de chaque type).

Fenêtre de présélection (ven 23 19:00 → lun 26 00:00) :

```bash
make presel-window APPLY=1 URL=https://<domaine> CTFD_TOKEN=<jeton>
```

## 7. Pendant l'épreuve (cadence)

```bash
make backup-status     # ~toutes les 2 h : "dernier dump OK < 15 min" (timer auto 15 min)
make logs              # 2e terminal : pas de 5xx en rafale
make gpu               # si piste IA : file Ollama non saturée en continu
make cost              # au moindre doute : ce qui est facturé
make backup            # dump vérifié manuel AVANT toute manipulation
# page admin Ops : https://<domaine>/plugins/ops/admin (DB, Redis, dump, reaper, collines, 5xx)
```

Le 24 au soir → `make season-down`.

## 8. Finale (29–30 oct)

```bash
make phase-final        # taille réduite (~50 joueurs)
make wait-front && make wait-arena && make link
make deploy && make tls-init && make check-arena
CTFD_TOKEN=<jeton> make preflight PHASE=finale
```

Écran salle : ouvrir `https://<domaine>/scoreboard?big=1` (touche `f` = plein
écran).

## 9. Clôture & archives

```bash
make writeups-prepare URL=https://<domaine> TOKEN=<jeton>   # brouillon avant clôture
make writeups-publish URL=https://<domaine> TOKEN=<jeton>   # à la clôture (refusé tant que 'end' pas passé)
make anticheat-report URL=https://<domaine> CTFD_TOKEN=<jeton>   # AVANT season-down (lit la base vivante)
make archive            # scoreboards figés + writeups -> S3 (site statique)
make season-down        # sauvegarde + archive + DÉTRUIT tout l'EC2
```

## Garde-fous (à répéter à la session d'action)

- **Ne jamais** mettre `0.0.0.0/0` dans `admin_cidrs`.
- **Secrets** (`front/.env`, `terraform.tfvars`) restent **hors git**.
- Hors événement, **détruire** (`season-down`) — laisser tourner coûte plus que
  reconstruire.
- Un servi ne se lance que si son image `ctf-<cat>-<slug>:latest` existe sur
  l'arena (`make check-arena` / `push-images`).
- Rien n'existe sur AWS tant qu'un `make phase-*` n'est pas lancé avec
  `terraform.tfvars` renseigné.
- Dépannage complet : `deploy/RUNBOOK.md` §5 (front KO, instancier KO,
  restauration de base, apply Terraform interrompu).

## Carte des commandes

| Commande                                       | Rôle                                           |
| ---------------------------------------------- | ---------------------------------------------- |
| `make init` / `make state-bootstrap`           | init Terraform / état distant S3+DynamoDB      |
| `make check-gpu-quota`                         | quota GPU (à lancer **maintenant**)            |
| `make request-gpu-quota` / `make free-credits` | demande de quota GPU / crédits du plan gratuit |
| `make phase-setup / -preselection / -final`    | leviers de coût / dimensionnement              |
| `make wait-front / wait-arena`                 | attente provisionnement                        |
| `make deploy / tls-init / link`                | déploiement CTFd / HTTPS / liaison             |
| `make check-arena / push-images`               | images de challenge sur l'arena                |
| `make preflight PHASE=...`                     | check-list de mise en prod (gate)              |
| `make backup / restore FILE=... / archive`     | sauvegarde / restauration / archive S3         |
| `make season-down / destroy`                   | destruction de l'EC2 (le bucket survit)        |
| `make logs / gpu / cost`                       | supervision                                    |
| `make ssh-front / ssh-arena / ssh-ai`          | shells                                         |
