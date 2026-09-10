# Pilotage du CTF. Toutes les commandes se lancent depuis deploy/.
#
# Calendrier 2026 :
#   preselection  23-24 octobre  (~300 joueurs)
#   finale        29-30 octobre  (~50 joueurs, 10 equipes)
#
# Le reste de l'annee la phase est `off` : aucune instance EC2 n'existe.

SHELL       := /usr/bin/env bash
TF          := terraform -chdir=terraform
SSH_OPTS    := -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10
REPO_URL    ?= https://github.com/hi3ris/CTFd.git
REPO_BRANCH ?= claude/ctf-platform-free-ptiggj

tfout    = $(shell $(TF) output -raw $(1) 2>/dev/null)
FRONT_IP  = $(call tfout,front_public_ip)
ARENA_IP  = $(call tfout,arena_public_ip)
AI_IP     = $(call tfout,ai_public_ip)
ARENA_PRIV= $(call tfout,arena_private_ip)
AI_PRIV   = $(call tfout,ai_private_ip)
BUCKET    = $(call tfout,archive_bucket)

FRONT_SSH = ssh $(SSH_OPTS) ubuntu@$(FRONT_IP)
ARENA_SSH = ssh $(SSH_OPTS) ubuntu@$(ARENA_IP)
AI_SSH    = ssh $(SSH_OPTS) ubuntu@$(AI_IP)

COMPOSE = docker compose -f deploy/front/docker-compose.prod.yml --env-file deploy/front/.env

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Preparatifs ------------------------------------------------------------

.PHONY: init
init: ## Initialise Terraform (une fois)
	$(TF) init

.PHONY: check-gpu-quota
check-gpu-quota: ## Verifie le quota GPU AWS. A LANCER DES MAINTENANT.
	@echo "Quota 'Running On-Demand G and VT instances' dans $$($(TF) output -raw 2>/dev/null || echo eu-west-3) :"
	@aws service-quotas get-service-quota \
	  --service-code ec2 --quota-code L-DB2E81BA \
	  --query 'Quota.Value' --output text 2>/dev/null \
	  || echo "(installez/configurez l'AWS CLI pour lire le quota)"
	@echo
	@echo "Une g4dn.xlarge consomme 4 vCPU de ce quota."
	@echo "Si la valeur affichee est 0, demandez une augmentation MAINTENANT :"
	@echo "  https://console.aws.amazon.com/servicequotas/home/services/ec2/quotas/L-DB2E81BA"
	@echo "Le traitement prend souvent plusieurs jours ouvres."

# --- Phases -----------------------------------------------------------------

.PHONY: phase-setup
phase-setup: ## Front seul : preparer les challenges, ouvrir les inscriptions
	$(TF) apply -var 'phase=setup'
	@$(MAKE) --no-print-directory deploy

.PHONY: phase-preselection
phase-preselection: ## 23-24 oct : front + arena + IA, taille ~300 joueurs
	$(TF) apply -var 'phase=preselection'
	@$(MAKE) --no-print-directory deploy wait-nodes link

.PHONY: phase-final
phase-final: ## 29-30 oct : front + arena + IA, taille ~50 joueurs
	$(TF) apply -var 'phase=final'
	@$(MAKE) --no-print-directory deploy wait-nodes link

.PHONY: season-down
season-down: ## Fin d'edition : archive, sauvegarde, puis detruit TOUT l'EC2
	@$(MAKE) --no-print-directory backup archive
	$(TF) apply -var 'phase=off'
	@echo
	@echo "Toutes les instances sont detruites. Seules les archives S3 subsistent."
	@echo "Archives en ligne : $$($(TF) output -raw archive_site_url)"

# --- Deploiement ------------------------------------------------------------

.PHONY: deploy
deploy: ## Deploie/met a jour CTFd sur le front
	$(FRONT_SSH) 'set -e; \
	  if [ ! -d /opt/ctfd/CTFd ]; then \
	    git clone --branch $(REPO_BRANCH) $(REPO_URL) /opt/ctfd/CTFd; \
	  else \
	    cd /opt/ctfd/CTFd && git fetch origin $(REPO_BRANCH) && git checkout $(REPO_BRANCH) && git pull origin $(REPO_BRANCH); \
	  fi; \
	  cd /opt/ctfd/CTFd; \
	  test -f deploy/front/.env || { echo "ERREUR : creez deploy/front/.env (voir .env.example)"; exit 1; }; \
	  $(COMPOSE) up -d --build'

.PHONY: wait-nodes
wait-nodes: ## Attend que l'arena et le noeud IA soient provisionnes
	@echo "Attente de l'arena (Docker, Swarm)..."
	@until $(ARENA_SSH) 'test -f /var/lib/cloud/ctfd-arena-provisioned' 2>/dev/null; do \
	  printf '.'; sleep 15; done; echo " pret."
	@echo "Attente du noeud IA (pilotes NVIDIA, telechargement du modele)..."
	@until $(AI_SSH) 'test -f /var/lib/cloud/ctfd-ai-provisioned' 2>/dev/null; do \
	  printf '.'; sleep 20; done; echo " pret."
	@$(AI_SSH) 'nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv' || true

.PHONY: link
link: ## Relie le front a l'arena et au noeud IA
	@echo ">> Cle publique du front deposee sur l'arena"
	@PUBKEY=$$($(FRONT_SSH) 'cat ~/.ssh/id_ed25519_arena.pub'); \
	 $(ARENA_SSH) "grep -qF \"$$PUBKEY\" ~/.ssh/authorized_keys || echo \"$$PUBKEY\" >> ~/.ssh/authorized_keys"
	@echo ">> Jeton frp injecte sur l'arena"
	@TOKEN=$$($(FRONT_SSH) 'sudo cat /etc/frp/token'); \
	 FRPADMIN=$$(openssl rand -hex 16); \
	 $(ARENA_SSH) "sudo sed -i -e \"s|REMPLACE_TOKEN|$$TOKEN|\" -e \"s|REMPLACE_ADMIN_PASSWORD|$$FRPADMIN|\" /etc/frp/frpc.toml && sudo systemctl restart frpc"
	@echo ">> CTFd pointe vers l'arena et le noeud IA"
	@$(FRONT_SSH) "cd /opt/ctfd/CTFd && \
	  sed -i 's|^OLLAMA_URL=.*|OLLAMA_URL=http://$(AI_PRIV):11434|' deploy/front/.env && \
	  sed -i 's|^DOCKER_HOST=.*|DOCKER_HOST=ssh://ubuntu@$(ARENA_PRIV)|' deploy/front/.env && \
	  $(COMPOSE) up -d"
	@echo
	@echo "Pret. $$($(TF) output -raw cost_note)"

# --- Exploitation -----------------------------------------------------------

.PHONY: backup
backup: ## Sauvegarde la base dans S3 et en local
	@mkdir -p backups
	@STAMP=$$(date +%Y%m%d-%H%M%S); \
	 $(FRONT_SSH) 'cd /opt/ctfd/CTFd && $(COMPOSE) exec -T db sh -c \
	   "mariadb-dump -uroot -p\$$MARIADB_ROOT_PASSWORD --single-transaction ctfd" | gzip' \
	   > backups/ctfd-$$STAMP.sql.gz; \
	 aws s3 cp backups/ctfd-$$STAMP.sql.gz s3://$(BUCKET)/backups/ 2>/dev/null \
	   && echo "Sauvegarde envoyee dans s3://$(BUCKET)/backups/ctfd-$$STAMP.sql.gz" \
	   || echo "Sauvegarde locale : backups/ctfd-$$STAMP.sql.gz (envoi S3 impossible)"

.PHONY: archive
archive: ## Fige le scoreboard et les pages publiques dans S3
	@echo ">> Export statique du CTF depuis le front"
	@$(FRONT_SSH) 'cd /tmp && rm -rf ctf-archive && mkdir ctf-archive && cd ctf-archive && \
	  wget --quiet --mirror --page-requisites --adjust-extension \
	       --convert-links --no-parent --no-host-directories \
	       http://localhost/scoreboard http://localhost/challenges 2>/dev/null || true; \
	  tar czf /tmp/ctf-archive.tar.gz -C /tmp ctf-archive'
	@scp $(SSH_OPTS) ubuntu@$(FRONT_IP):/tmp/ctf-archive.tar.gz /tmp/ctf-archive.tar.gz
	@YEAR=$$(date +%Y); \
	 rm -rf /tmp/ctf-archive && tar xzf /tmp/ctf-archive.tar.gz -C /tmp; \
	 aws s3 sync /tmp/ctf-archive s3://$(BUCKET)/site/$$YEAR/ --delete \
	   && echo "Archive $$YEAR publiee sur $$($(TF) output -raw archive_site_url)/$$YEAR/" \
	   || echo "Publication S3 impossible (verifiez l'AWS CLI)"

.PHONY: logs
logs: ## Suit les logs du front
	$(FRONT_SSH) 'cd /opt/ctfd/CTFd && $(COMPOSE) logs -f --tail=100'

.PHONY: gpu
gpu: ## Etat du GPU et des requetes Ollama en cours
	$(AI_SSH) 'nvidia-smi; echo; curl -s http://127.0.0.1:11434/api/ps | jq .'

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
destroy-all: ## DETRUIT TOUT, bucket d'archives compris. Irreversible.
	@echo "Cette commande detruit aussi les archives de toutes les editions."
	@read -p "Taper 'detruire' pour confirmer : " ans; [ "$$ans" = "detruire" ] || exit 1
	$(TF) destroy
