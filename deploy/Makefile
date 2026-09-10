# Pilotage du CTF. Toutes les commandes se lancent depuis deploy/.
#
# Calendrier 2026 :
#   preselection  vendredi 23 - samedi 24 octobre  (~300 joueurs)
#   finale        jeudi 29 - vendredi 30 octobre   (~50 joueurs, 10 equipes)
#
# Hors de ces fenetres la phase est `off` : aucune instance EC2 n'existe.

SHELL       := /usr/bin/env bash
.SHELLFLAGS := -o errexit -o pipefail -c

TF          := terraform -chdir=terraform
SSH_OPTS    := -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10
REPO_URL    ?= https://github.com/hi3ris/CTFd.git
REPO_BRANCH ?= claude/ctf-platform-free-ptiggj

# Les sorties Terraform sont lues paresseusement (=), jamais au chargement du
# Makefile : sinon un `make phase-preselection` capturerait les valeurs
# d'AVANT son propre apply et deploierait vers l'ancienne machine.
tfout      = $(shell $(TF) output -raw $(1) 2>/dev/null)
FRONT_IP    = $(call tfout,front_public_ip)
ARENA_IP    = $(call tfout,arena_public_ip)
AI_IP       = $(call tfout,ai_public_ip)
ARENA_PRIV  = $(call tfout,arena_private_ip)
AI_PRIV     = $(call tfout,ai_private_ip)
BUCKET      = $(call tfout,archive_bucket)
REGION      = $(call tfout,aws_region)
PHASE       = $(call tfout,phase)
WHALE_PORT_START = $(call tfout,whale_port_range_start)
WHALE_PORT_END   = $(call tfout,whale_port_range_end)

FRONT_SSH = ssh $(SSH_OPTS) ubuntu@$(FRONT_IP)
ARENA_SSH = ssh $(SSH_OPTS) ubuntu@$(ARENA_IP)
AI_SSH    = ssh $(SSH_OPTS) ubuntu@$(AI_IP)

COMPOSE = docker compose -f deploy/front/docker-compose.prod.yml --env-file deploy/front/.env

# Attente maximale d'un provisionnement, en secondes. Au-dela, on echoue au
# lieu de boucler : le matin du 23 octobre, une boucle infinie silencieuse est
# pire qu'une erreur.
WAIT_TIMEOUT ?= 1800

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Preparatifs ------------------------------------------------------------

.PHONY: init
init: ## Initialise Terraform (une fois)
	$(TF) init

.PHONY: check-gpu-quota
check-gpu-quota: ## Verifie le quota GPU AWS dans LA BONNE region. A LANCER MAINTENANT.
	@REGION=$$($(TF) output -raw aws_region 2>/dev/null || echo eu-west-3); \
	 echo "Quota 'Running On-Demand G and VT instances' dans $$REGION :"; \
	 V=$$(aws service-quotas get-service-quota --region "$$REGION" \
	      --service-code ec2 --quota-code L-DB2E81BA \
	      --query 'Quota.Value' --output text 2>/dev/null) || \
	   { echo "  (AWS CLI indisponible ou non configuree)"; exit 1; }; \
	 echo "  $$V vCPU"; \
	 echo; \
	 if awk -v v="$$V" 'BEGIN{exit (v>=4)?0:1}'; then \
	   echo "OK : une g4dn.xlarge (4 vCPU) tient dans ce quota."; \
	 else \
	   echo "INSUFFISANT. Une g4dn.xlarge consomme 4 vCPU de ce quota."; \
	   echo "Demandez une augmentation a >= 8 des maintenant :"; \
	   echo "  https://$$REGION.console.aws.amazon.com/servicequotas/home/services/ec2/quotas/L-DB2E81BA"; \
	   echo "Le traitement prend souvent plusieurs jours ouvres."; \
	   exit 1; \
	 fi

# --- Phases -----------------------------------------------------------------

.PHONY: phase-setup
phase-setup: ## Front seul : preparer les challenges, ouvrir les inscriptions
	$(TF) apply -var 'phase=setup'
	@$(MAKE) --no-print-directory wait-front deploy
	@$(TF) output -raw dns_action_required; echo

.PHONY: phase-preselection
phase-preselection: ## 23-24 oct : front + arena + IA, taille ~300 joueurs
	$(TF) apply -var 'phase=preselection'
	@$(MAKE) --no-print-directory wait-front deploy wait-nodes link
	@$(TF) output -raw dns_action_required; echo

.PHONY: phase-final
phase-final: ## 29-30 oct : front + arena + IA, taille ~50 joueurs
	$(TF) apply -var 'phase=final'
	@$(MAKE) --no-print-directory wait-front deploy wait-nodes link
	@$(TF) output -raw dns_action_required; echo

.PHONY: season-down
season-down: ## Fin de phase : archive, sauvegarde VERIFIEE, puis detruit l'EC2
	@echo ">> Sauvegarde et archivage avant destruction"
	@$(MAKE) --no-print-directory backup archive
	@echo
	@echo ">> Sauvegarde verifiee. Destruction des instances."
	$(TF) apply -var 'phase=off'
	@echo
	@echo "Toutes les instances sont detruites. Seules les archives S3 subsistent."
	@echo "Archives : $$($(TF) output -raw archive_site_url)"

# --- Attentes ---------------------------------------------------------------

.PHONY: wait-front
wait-front: ## Attend la fin du provisionnement du front
	@echo -n "Attente du front ($(FRONT_IP)) "
	@deadline=$$(( $$(date +%s) + $(WAIT_TIMEOUT) )); \
	 until $(FRONT_SSH) 'test -f /var/lib/cloud/ctfd-front-provisioned' 2>/dev/null; do \
	   if [ $$(date +%s) -gt $$deadline ]; then \
	     echo " ECHEC"; \
	     echo "Le front n'est pas provisionne apres $(WAIT_TIMEOUT)s."; \
	     echo "Diagnostiquer : make ssh-front puis 'sudo cat /var/log/cloud-init-output.log'"; \
	     exit 1; \
	   fi; \
	   printf '.'; sleep 10; \
	 done; echo " pret."

.PHONY: wait-nodes
wait-nodes: ## Attend l'arena et le noeud IA (avec delai maximal)
	@echo -n "Attente de l'arena ($(ARENA_IP)) "
	@deadline=$$(( $$(date +%s) + $(WAIT_TIMEOUT) )); \
	 until $(ARENA_SSH) 'test -f /var/lib/cloud/ctfd-arena-provisioned' 2>/dev/null; do \
	   if [ $$(date +%s) -gt $$deadline ]; then \
	     echo " ECHEC"; echo "Diagnostiquer : make ssh-arena puis 'sudo cat /var/log/cloud-init-output.log'"; exit 1; \
	   fi; \
	   printf '.'; sleep 10; \
	 done; echo " pret."
	@$(ARENA_SSH) 'cat /var/log/challenge-images.log' || true
	@echo -n "Attente du noeud IA ($(AI_IP)), telechargement du modele "
	@deadline=$$(( $$(date +%s) + $(WAIT_TIMEOUT) )); \
	 until $(AI_SSH) 'test -f /var/lib/cloud/ctfd-ai-provisioned' 2>/dev/null; do \
	   if [ $$(date +%s) -gt $$deadline ]; then \
	     echo " ECHEC"; \
	     echo "Le noeud IA n'a pas valide ses controles (GPU, bind reseau, modele)."; \
	     echo "Diagnostiquer : make ssh-ai puis 'sudo cat /var/log/cloud-init-output.log'"; \
	     exit 1; \
	   fi; \
	   printf '.'; sleep 15; \
	 done; echo " pret."
	@$(AI_SSH) 'nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv'

.PHONY: check-arena
check-arena: ## Liste les images de challenge reellement presentes sur l'arena
	@$(ARENA_SSH) 'docker image ls --format "{{.Repository}}:{{.Tag}}" | sort'
	@echo
	@n=$$($(ARENA_SSH) 'docker image ls -q | wc -l'); \
	 if [ "$$n" -lt 2 ]; then \
	   echo "AUCUNE image de challenge sur l'arena. L'instancier ne pourra rien lancer."; \
	   echo "Poussez-les avec 'make push-images' puis relancez la phase."; \
	   exit 1; \
	 fi

# --- Deploiement ------------------------------------------------------------

.PHONY: deploy
deploy: ## Deploie/met a jour CTFd sur le front
	$(FRONT_SSH) 'set -euo pipefail; \
	  if [ ! -d /opt/ctfd/CTFd ]; then \
	    git clone --branch $(REPO_BRANCH) $(REPO_URL) /opt/ctfd/CTFd; \
	  else \
	    cd /opt/ctfd/CTFd && git fetch origin $(REPO_BRANCH) && git checkout $(REPO_BRANCH) && git pull origin $(REPO_BRANCH); \
	  fi; \
	  cd /opt/ctfd/CTFd; \
	  test -f deploy/front/.env || { echo "ERREUR : creez deploy/front/.env (voir .env.example)"; exit 1; }; \
	  test -f deploy/front/nginx/active.conf || cp deploy/front/nginx/bootstrap.conf deploy/front/nginx/active.conf; \
	  $(COMPOSE) up -d --build ctfd db cache nginx certbot'

.PHONY: tls-init
tls-init: ## Emet le certificat Let's Encrypt et bascule nginx en HTTPS
	@echo ">> Verification que le domaine pointe bien sur ce front"
	@$(FRONT_SSH) 'set -euo pipefail; cd /opt/ctfd/CTFd; \
	  set -a; . deploy/front/.env; set +a; \
	  test -n "$$CTF_DOMAIN" || { echo "ERREUR : CTF_DOMAIN vide dans .env"; exit 1; }; \
	  test -n "$$CERTBOT_EMAIL" || { echo "ERREUR : CERTBOT_EMAIL vide dans .env"; exit 1; }; \
	  resolved=$$(getent hosts "$$CTF_DOMAIN" | awk "{print \$$1}" | head -1); \
	  echo "  $$CTF_DOMAIN -> $$resolved (attendu : $(FRONT_IP))"; \
	  test "$$resolved" = "$(FRONT_IP)" || { \
	    echo "ERREUR : le domaine ne pointe pas sur ce front. Let'"'"'s Encrypt echouerait"; \
	    echo "et brulerait un essai sur le quota horaire. Corrigez le DNS d'"'"'abord."; exit 1; }'
	@echo ">> Emission du certificat"
	@$(FRONT_SSH) 'set -euo pipefail; cd /opt/ctfd/CTFd; \
	  set -a; . deploy/front/.env; set +a; \
	  $(COMPOSE) run --rm --entrypoint certbot certbot certonly \
	    --webroot -w /var/www/certbot \
	    -d "$$CTF_DOMAIN" --email "$$CERTBOT_EMAIL" \
	    --agree-tos --no-eff-email --non-interactive'
	@echo ">> Bascule de nginx en HTTPS"
	@$(FRONT_SSH) 'set -euo pipefail; cd /opt/ctfd/CTFd; \
	  set -a; . deploy/front/.env; set +a; \
	  sed "s|__CTF_DOMAIN__|$$CTF_DOMAIN|g" deploy/front/nginx/tls.conf.template \
	    > deploy/front/nginx/active.conf; \
	  $(COMPOSE) exec -T nginx nginx -t || { \
	    echo "ERREUR : configuration nginx invalide, retour au HTTP"; \
	    cp deploy/front/nginx/bootstrap.conf deploy/front/nginx/active.conf; \
	    $(COMPOSE) restart nginx; exit 1; }; \
	  $(COMPOSE) restart nginx'
	@echo ">> Verification depuis l'exterieur"
	@curl -fsS -o /dev/null -w "  HTTPS %{http_code}, redirection HTTP -> %{redirect_url}\n" \
	  "https://$$($(FRONT_SSH) 'cd /opt/ctfd/CTFd && . deploy/front/.env && echo $$CTF_DOMAIN')/" \
	  && echo "TLS actif."

.PHONY: link
link: ## Relie le front a l'arena et au noeud IA, et verifie que ca marche
	@echo ">> Cle de service deposee sur l'arena"
	@PUBKEY=$$($(FRONT_SSH) 'cat ~/.ssh/id_ed25519_arena.pub'); \
	 test -n "$$PUBKEY" || { echo "ERREUR : cle publique introuvable sur le front"; exit 1; }; \
	 $(ARENA_SSH) "grep -qF \"$$PUBKEY\" ~/.ssh/authorized_keys || echo \"$$PUBKEY\" >> ~/.ssh/authorized_keys"
	@echo ">> Cle privee et empreinte d'hote installees pour le tunnel Docker"
	@$(FRONT_SSH) 'set -euo pipefail; cd /opt/ctfd/CTFd; \
	  install -d -m 700 deploy/front/ssh; \
	  install -m 600 ~/.ssh/id_ed25519_arena deploy/front/ssh/id_ed25519; \
	  ssh-keyscan -H $(ARENA_PRIV) > deploy/front/ssh/known_hosts 2>/dev/null; \
	  test -s deploy/front/ssh/known_hosts || { echo "ERREUR : ssh-keyscan n'"'"'a rien renvoye"; exit 1; }'
	@echo ">> Jeton frp injecte sur l'arena et instancier configure sur le front"
	@TOKEN=$$($(FRONT_SSH) 'sudo cat /etc/frp/token'); \
	 test -n "$$TOKEN" || { echo "ERREUR : jeton frp vide cote front"; exit 1; }; \
	 FRPADMIN=$$(openssl rand -hex 16); \
	 $(ARENA_SSH) "sudo sed -i -e \"s|REMPLACE_TOKEN|$$TOKEN|\" -e \"s|REMPLACE_ADMIN_PASSWORD|$$FRPADMIN|\" /etc/frp/frpc.toml && sudo systemctl restart frpc"; \
	 sleep 2; \
	 $(ARENA_SSH) 'systemctl is-active --quiet frpc' \
	   || { echo "ERREUR : frpc n'a pas demarre. 'make ssh-arena' puis 'journalctl -u frpc'"; exit 1; }; \
	 case "$(PHASE)" in \
	   preselection) W=4; POOL=1G ;; \
	   *)            W=2; POOL=256M ;; \
	 esac; \
	 $(FRONT_SSH) "cd /opt/ctfd/CTFd && \
	   set -e; \
	   upsert() { grep -q \"^\$$1=\" deploy/front/.env && sed -i \"s|^\$$1=.*|\$$1=\$$2|\" deploy/front/.env || echo \"\$$1=\$$2\" >> deploy/front/.env; }; \
	   upsert OLLAMA_URL http://$(AI_PRIV):11434; \
	   upsert ARENA_HOST $(ARENA_PRIV); \
	   upsert DOCKER_HOST tcp://dockerproxy:2375; \
	   upsert WORKERS $$W; \
	   upsert INNODB_POOL $$POOL; \
	   upsert FRONT_PUBLIC_IP $(FRONT_IP); \
	   upsert FRPC_ADMIN_ADDR dockerproxy:7400; \
	   upsert FRPC_ADMIN_PASSWORD $$FRPADMIN; \
	   upsert WHALE_PORT_RANGE_START $(WHALE_PORT_START); \
	   upsert WHALE_PORT_RANGE_END $(WHALE_PORT_END); \
	   $(COMPOSE) --profile arena up -d --build"
	@echo ">> Verification du canal Docker vers l'arena"
	@$(FRONT_SSH) 'cd /opt/ctfd/CTFd && $(COMPOSE) exec -T ctfd python -c "\
import os, urllib.request, json; \
u = os.environ[\"DOCKER_HOST\"].replace(\"tcp://\", \"http://\") + \"/version\"; \
print(\"  Docker arena :\", json.load(urllib.request.urlopen(u, timeout=10))[\"Version\"])"' \
	  || { echo "ECHEC : CTFd ne joint pas le Docker de l'arena. L'instancier ne marchera pas."; exit 1; }
	@echo ">> Verification du canal Ollama"
	@$(FRONT_SSH) 'cd /opt/ctfd/CTFd && $(COMPOSE) exec -T ctfd python -c "\
import os, urllib.request, json; \
r = json.load(urllib.request.urlopen(os.environ[\"OLLAMA_URL\"] + \"/api/tags\", timeout=15)); \
print(\"  Modeles :\", [m[\"name\"] for m in r[\"models\"]])"' \
	  || { echo "ECHEC : CTFd ne joint pas Ollama. Les challenges IA ne marcheront pas."; exit 1; }
	@echo
	@$(TF) output -raw cost_note; echo

# --- Exploitation -----------------------------------------------------------

.PHONY: backup
backup: ## Sauvegarde la base, VERIFIE le dump, puis l'envoie dans S3
	@mkdir -p backups
	@STAMP=$$(date +%Y%m%d-%H%M%S); \
	 OUT=backups/ctfd-$(PHASE)-$$STAMP.sql.gz; \
	 TMP=$$OUT.partial; \
	 echo ">> Dump de la base"; \
	 $(FRONT_SSH) 'set -euo pipefail; cd /opt/ctfd/CTFd && $(COMPOSE) exec -T db sh -c \
	   "mariadb-dump -uroot -p\$$MARIADB_ROOT_PASSWORD --single-transaction --routines ctfd" | gzip' \
	   > $$TMP; \
	 echo ">> Verification de l'archive"; \
	 gzip -t $$TMP || { echo "ECHEC : archive corrompue"; rm -f $$TMP; exit 1; }; \
	 SIZE=$$(stat -c%s $$TMP); \
	 test "$$SIZE" -gt 10000 \
	   || { echo "ECHEC : dump de $$SIZE octets, manifestement vide ou tronque"; rm -f $$TMP; exit 1; }; \
	 zcat $$TMP | grep -q 'CREATE TABLE `users`' \
	   || { echo "ECHEC : la table users est absente du dump"; rm -f $$TMP; exit 1; }; \
	 ROWS=$$(zcat $$TMP | grep -c 'INSERT INTO' || true); \
	 mv $$TMP $$OUT; \
	 echo "  $$OUT : $$SIZE octets, $$ROWS instructions INSERT"; \
	 echo ">> Envoi dans S3"; \
	 aws s3 cp $$OUT s3://$(BUCKET)/backups/ --only-show-errors \
	   || { echo "ECHEC : envoi S3 impossible. La sauvegarde locale est dans $$OUT."; exit 1; }; \
	 echo "  s3://$(BUCKET)/backups/$$(basename $$OUT)"

.PHONY: restore
restore: ## Restaure une sauvegarde sur le front (FILE=backups/...sql.gz)
	@test -n "$(FILE)" || { echo "Usage : make restore FILE=backups/ctfd-....sql.gz"; \
	  echo; echo "Sauvegardes disponibles dans S3 :"; \
	  aws s3 ls s3://$(BUCKET)/backups/ || true; exit 1; }
	@test -f "$(FILE)" || { echo "Fichier introuvable : $(FILE)"; exit 1; }
	@gzip -t "$(FILE)" || { echo "Archive corrompue"; exit 1; }
	@echo "Cette commande ECRASE la base actuelle du front."
	@read -p "Taper 'restaurer' pour confirmer : " ans; [ "$$ans" = "restaurer" ] || exit 1
	@gzip -dc "$(FILE)" | $(FRONT_SSH) 'set -euo pipefail; cd /opt/ctfd/CTFd && \
	  $(COMPOSE) exec -T db sh -c "mariadb -uroot -p\$$MARIADB_ROOT_PASSWORD ctfd"'
	@$(FRONT_SSH) 'cd /opt/ctfd/CTFd && $(COMPOSE) restart ctfd'
	@echo "Restauration terminee."

.PHONY: archive
archive: ## Fige le scoreboard de la phase dans S3, en page autonome
	@echo ">> Recuperation des donnees du scoreboard"
	@PREFIX=$(PHASE)-$$(date +%Y%m%d); \
	 mkdir -p /tmp/ctf-archive; \
	 $(FRONT_SSH) 'curl -sf http://localhost/api/v1/scoreboard' > /tmp/ctf-archive/scoreboard.json \
	   || { echo "ECHEC : l'API scoreboard ne repond pas"; exit 1; }; \
	 test -s /tmp/ctf-archive/scoreboard.json \
	   || { echo "ECHEC : scoreboard vide"; exit 1; }; \
	 $(FRONT_SSH) 'curl -sf http://localhost/api/v1/challenges' > /tmp/ctf-archive/challenges.json || true; \
	 python3 scripts/render_archive.py /tmp/ctf-archive "$$PREFIX" \
	   || { echo "ECHEC du rendu de l'archive"; exit 1; }; \
	 echo ">> Publication"; \
	 aws s3 sync /tmp/ctf-archive s3://$(BUCKET)/site/$$PREFIX/ --only-show-errors \
	   || { echo "ECHEC : publication S3 impossible"; exit 1; }; \
	 python3 scripts/render_index.py $(BUCKET) \
	   && aws s3 cp /tmp/ctf-site-index.html s3://$(BUCKET)/site/index.html --only-show-errors; \
	 echo "  $$($(TF) output -raw archive_site_url)/$$PREFIX/"

.PHONY: push-images
push-images: ## Envoie les images de challenge dans S3 (lues depuis l'arena au prochain demarrage)
	@test -d challenges || { echo "Aucun dossier challenges/"; exit 1; }
	@mkdir -p /tmp/ctf-images
	@for img in $$(docker image ls --format '{{.Repository}}:{{.Tag}}' | grep '^ctf-' || true); do \
	   name=$$(echo "$$img" | tr '/:' '__'); \
	   echo "  $$img -> $$name.tar"; \
	   docker save "$$img" -o /tmp/ctf-images/$$name.tar; \
	 done
	@ls /tmp/ctf-images/*.tar >/dev/null 2>&1 \
	  || { echo "Aucune image nommee ctf-* trouvee localement"; exit 1; }
	@aws s3 sync /tmp/ctf-images s3://$(BUCKET)/images/ --only-show-errors
	@echo "Images publiees. Elles seront chargees au prochain demarrage de l'arena."

.PHONY: logs
logs: ## Suit les logs du front
	$(FRONT_SSH) 'cd /opt/ctfd/CTFd && $(COMPOSE) logs -f --tail=100'

.PHONY: gpu
gpu: ## Etat du GPU et des requetes Ollama en cours
	$(AI_SSH) 'nvidia-smi; echo; curl -s http://127.0.0.1:11434/api/ps'

.PHONY: cost
cost: ## Rappelle ce qui est facture en ce moment
	@$(TF) output -raw cost_note; echo

.PHONY: ssh-front
ssh-front: ## Shell sur le front
	$(FRONT_SSH)

.PHONY: ssh-arena
ssh-arena: ## Shell sur l'arena
	$(ARENA_SSH)

.PHONY: ssh-ai
ssh-ai: ## Shell sur le noeud IA
	$(AI_SSH)

.PHONY: destroy-all
destroy-all: ## Detruit l'EC2 et le reseau. Le bucket d'archives SURVIT.
	@echo "Detruit toutes les instances et le VPC."
	@echo "Le bucket d'archives est protege par prevent_destroy et n'est PAS detruit :"
	@echo "pour le supprimer, il faut retirer ce garde-fou dans archive.tf, a la main."
	@read -p "Taper 'detruire' pour confirmer : " ans; [ "$$ans" = "detruire" ] || exit 1
	$(TF) apply -var 'phase=off'
