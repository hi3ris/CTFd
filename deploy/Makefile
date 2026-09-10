# Pilotage du CTF. Toutes les commandes se lancent depuis deploy/.
#
#   make front-up      installe le front (une fois par an, ou apres un changement)
#   make event-up      allume l'arena pour l'evenement
#   make event-down    detruit l'arena  -> retour au cout minimal
#   make cost          rappelle ce qui est facture en ce moment

SHELL       := /usr/bin/env bash
TF          := terraform -chdir=terraform
SSH_OPTS    := -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10
REPO_URL    ?= https://github.com/hi3ris/CTFd.git
REPO_BRANCH ?= claude/ctf-platform-free-ptiggj

FRONT_IP     = $(shell $(TF) output -raw front_public_ip 2>/dev/null)
ARENA_IP     = $(shell $(TF) output -raw arena_public_ip 2>/dev/null)
ARENA_PRIV   = $(shell $(TF) output -raw arena_private_ip 2>/dev/null)
FRONT_SSH    = ssh $(SSH_OPTS) ubuntu@$(FRONT_IP)
ARENA_SSH    = ssh $(SSH_OPTS) ubuntu@$(ARENA_IP)

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- Infrastructure ---------------------------------------------------------

.PHONY: init
init: ## Initialise Terraform (a lancer une fois)
	$(TF) init

.PHONY: plan
plan: ## Montre ce que Terraform changerait
	$(TF) plan

.PHONY: front-up
front-up: ## Cree/met a jour le front (allume toute l'annee)
	$(TF) apply -var 'arena_enabled=false'
	@echo
	@echo "Front joignable sur : $$($(TF) output -raw ctf_url)"
	@echo "Pointez votre DNS sur : $$($(TF) output -raw front_public_ip)"

.PHONY: deploy
deploy: ## Deploie/met a jour CTFd sur le front
	$(FRONT_SSH) 'set -e; \
	  if [ ! -d /opt/ctfd/CTFd ]; then \
	    git clone --branch $(REPO_BRANCH) $(REPO_URL) /opt/ctfd/CTFd; \
	  else \
	    cd /opt/ctfd/CTFd && git fetch origin $(REPO_BRANCH) && git checkout $(REPO_BRANCH) && git pull origin $(REPO_BRANCH); \
	  fi; \
	  cd /opt/ctfd/CTFd; \
	  test -f deploy/front/.env || { echo "ERREUR : creez deploy/front/.env sur le front (voir .env.example)"; exit 1; }; \
	  docker compose -f deploy/front/docker-compose.prod.yml --env-file deploy/front/.env up -d --build'

.PHONY: logs
logs: ## Suit les logs du front
	$(FRONT_SSH) 'cd /opt/ctfd/CTFd && docker compose -f deploy/front/docker-compose.prod.yml logs -f --tail=100'

# --- Evenement --------------------------------------------------------------

.PHONY: event-up
event-up: ## Allume l'arena (Swarm + Ollama) et la relie au front
	$(TF) apply -var 'arena_enabled=true'
	@echo "Attente du provisionnement de l'arena (Docker, Swarm, Ollama)..."
	@until $(ARENA_SSH) 'test -f /var/lib/cloud/ctfd-arena-provisioned' 2>/dev/null; do \
	  printf '.'; sleep 15; \
	done; echo " pret."
	@$(MAKE) --no-print-directory link

.PHONY: link
link: ## Relie front et arena (cle SSH, jeton frp, variables CTFd)
	@echo ">> Depot de la cle publique du front sur l'arena"
	@PUBKEY=$$($(FRONT_SSH) 'cat ~/.ssh/id_ed25519_arena.pub'); \
	 $(ARENA_SSH) "grep -qF \"$$PUBKEY\" ~/.ssh/authorized_keys || echo \"$$PUBKEY\" >> ~/.ssh/authorized_keys"
	@echo ">> Injection du jeton frp sur l'arena"
	@TOKEN=$$($(FRONT_SSH) 'sudo cat /etc/frp/token'); \
	 FRPADMIN=$$(openssl rand -hex 16); \
	 $(ARENA_SSH) "sudo sed -i -e \"s|REMPLACE_TOKEN|$$TOKEN|\" -e \"s|REMPLACE_ADMIN_PASSWORD|$$FRPADMIN|\" /etc/frp/frpc.toml && sudo systemctl restart frpc"
	@echo ">> Pointage de CTFd vers l'arena"
	@$(FRONT_SSH) "cd /opt/ctfd/CTFd && \
	  sed -i 's|^OLLAMA_URL=.*|OLLAMA_URL=http://$(ARENA_PRIV):11434|' deploy/front/.env && \
	  sed -i 's|^DOCKER_HOST=.*|DOCKER_HOST=ssh://ubuntu@$(ARENA_PRIV)|' deploy/front/.env && \
	  docker compose -f deploy/front/docker-compose.prod.yml --env-file deploy/front/.env up -d"
	@echo
	@echo "Arena reliee. Challenges Docker et IA disponibles."

.PHONY: event-down
event-down: ## Detruit l'arena. Le front reste en ligne. Retour au cout minimal.
	@echo ">> Sauvegarde de la base avant extinction"
	@$(MAKE) --no-print-directory backup
	@echo ">> Coupure des references a l'arena dans CTFd"
	@$(FRONT_SSH) "cd /opt/ctfd/CTFd && \
	  sed -i 's|^OLLAMA_URL=.*|OLLAMA_URL=|' deploy/front/.env && \
	  sed -i 's|^DOCKER_HOST=.*|DOCKER_HOST=|' deploy/front/.env && \
	  docker compose -f deploy/front/docker-compose.prod.yml --env-file deploy/front/.env up -d" || true
	$(TF) apply -var 'arena_enabled=false'
	@echo
	@echo "Arena detruite. Seul le front est encore facture."

# --- Exploitation -----------------------------------------------------------

.PHONY: backup
backup: ## Sauvegarde la base et les uploads en local (dossier backups/)
	@mkdir -p backups
	@STAMP=$$(date +%Y%m%d-%H%M%S); \
	 $(FRONT_SSH) 'cd /opt/ctfd/CTFd && \
	   docker compose -f deploy/front/docker-compose.prod.yml --env-file deploy/front/.env \
	     exec -T db sh -c "mariadb-dump -uroot -p\$$MARIADB_ROOT_PASSWORD --single-transaction ctfd" | gzip' \
	   > backups/ctfd-$$STAMP.sql.gz; \
	 echo "Base sauvegardee dans backups/ctfd-$$STAMP.sql.gz"

.PHONY: cost
cost: ## Rappelle ce qui est facture en ce moment
	@$(TF) output -raw cost_note; echo

.PHONY: ssh-front
ssh-front: ## Ouvre un shell sur le front
	$(FRONT_SSH)

.PHONY: ssh-arena
ssh-arena: ## Ouvre un shell sur l'arena
	$(ARENA_SSH)

.PHONY: destroy-all
destroy-all: ## DETRUIT TOUT, front compris. Faites `make backup` avant.
	@echo "Cette commande detruit le front ET sa base de donnees."
	@read -p "Taper 'detruire' pour confirmer : " ans; [ "$$ans" = "detruire" ] || exit 1
	$(TF) destroy
