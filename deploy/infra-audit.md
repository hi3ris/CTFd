# Audit infra vérifié — `deploy/` (2026-09-11)

Audit adverse de l'infrastructure actuelle (Terraform, cloud-init, compose, nginx,
Makefile, backend d'état distant). 8 dimensions → 12 findings bruts → **9 confirmés
en contradictoire** (chaque finding re-vérifié par un agent chargé de le réfuter).
Remplace le reliquat « 45 findings mineurs non vérifiés » du premier audit.

Convention : ✅ corrigé dans ce commit · 🕓 différé (documenté).

| # | Sévérité | Fichier | Problème | État |
|---|---|---|---|---|
| 1 | **BLOCKER** | `terraform/templates/arena-userdata.sh.tftpl` | `grep -q active` matche `inactive` (sous-chaîne) → `docker swarm init` sauté au 1ᵉʳ boot → overlay `ctfd_challenges` jamais créé → **instancier totalement HS**. | ✅ égalité stricte `!= "active"` ; création overlay conditionnée + échec non masqué |
| 2 | **MAJOR** | `front/docker-compose.prod.yml` | `dockerproxy` (socket Docker arena = root) attaché au réseau `web` → joignable depuis nginx exposé ; une compromission nginx ⇒ root sur l'arena. | ✅ `dockerproxy` sur `internal` seul (ctfd le joint déjà par `internal`) + commentaire Dockerfile corrigé |
| 3 | **MAJOR** | `Makefile` (backup) | Le check table users `zcat \| grep -q` peut recevoir SIGPIPE sous `pipefail` sur un gros dump → code 141 → **suppression d'un dump valide**. | ✅ `grep -c … >/dev/null` (lit tout le flux, pas de SIGPIPE) |
| 4 | minor | `front/docker-compose.prod.yml` + `ai-gateway/app.py` | La passerelle IA (service le plus exposé) recevait le **secret maître** des flags alors qu'elle n'a besoin que de la clé de jeton dérivée. | ✅ app.py préfère `AI_PROXY_TOKEN_KEY` (dérivée) ; à défaut dérive puis **retire le maître** de l'env du process |
| 5 | minor | `terraform/templates/ai-userdata.sh.tftpl` | Pilote NVIDIA installé sans `modprobe` → `nvidia-smi`/Ollama peuvent échouer/tomber en CPU au 1ᵉʳ boot. | ✅ `modprobe nvidia` avec échec explicite avant tout usage GPU |
| 6 | minor | `front/nginx/tls.conf.template` | Le `add_header` de `location /themes/` annule l'héritage des en-têtes de sécurité (nosniff/HSTS/X-Frame-Options) sur les JS/CSS de thème. | ✅ en-têtes redéclarés dans `/themes/` |
| 7 | minor | `Makefile` (check-arena) | `docker image ls -q \| wc -l ≥ 2` compte les images de base → le garde passe même avec **zéro** image de challenge. | ✅ compte les images `ctf-*` uniquement, seuil ≥ 1 |
| 8 | minor | `Makefile` (init) | `backend.tf` présent mais `backend.hcl` absent → `terraform init` nu (prompt interactif), message trompeur « état LOCAL ». | ✅ garde sur `backend.tf` ; erreur claire si `backend.hcl` manque |
| 9 | nit | `terraform/archive.tf` | Pas de règle `abort_incomplete_multipart_upload` → morceaux de gros dumps interrompus facturés indéfiniment. | ✅ règle ajoutée (7 j) |
| 10 | nit | `terraform/variables.tf` | Doc phase `off` mentionne « S3/CloudFront » alors qu'aucun CloudFront n'existe (S3 statique nu). | ✅ formulation corrigée |
| 11 | nit | `Makefile` (state-bootstrap) | Ne propage pas `project_name`/`aws_region` → un override diverge silencieusement du bucket d'état. | ✅ `PROJECT_NAME`/`AWS_REGION` passés au bootstrap |
| 12 | minor | `Makefile` (link) | Jeton frp + mot de passe admin passés sur l'argv de `sudo` → journalisés en clair dans auth.log de l'arène. | 🕓 **différé** : le correctif (secrets via stdin) touche la recette `link` = « Risque #1 » frpc, non testable hors infra live. À appliquer **et tester** à la répétition (Lot 5). Impact réel faible : nécessite déjà root sur l'arène pour lire auth.log. |

**Non confirmés / faux positifs** : le premier passage a aussi soulevé des pistes réfutées à la vérification (réseau/SG jugé conforme : aucun port ouvert à tort, Ollama reste front-only ; IMDSv2 et IAM lecture-seule OK). Zéro finding « incertain » restant.
