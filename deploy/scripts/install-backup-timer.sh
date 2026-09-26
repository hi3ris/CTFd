#!/usr/bin/env bash
# Installe (ou met a jour) la sauvegarde automatique sur le front. Idempotent ;
# lance par `make deploy` via sudo. Le cloud-init ne rejoue jamais sur un front
# deja vivant (user_data_replace_on_change = false), donc l'aws CLI est aussi
# installe ici.
set -euo pipefail
REPO=${CTFD_REPO:-/opt/ctfd/CTFd}
BACKUP_DIR=${BACKUP_DIR:-/opt/ctfd/backups}

if ! command -v aws >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends awscli
fi

install -d -m 750 -o ubuntu -g ubuntu "$BACKUP_DIR"
chmod +x "$REPO/deploy/scripts/backup.sh"
install -m 0644 "$REPO/deploy/front/systemd/ctfd-backup.service" /etc/systemd/system/ctfd-backup.service
install -m 0644 "$REPO/deploy/front/systemd/ctfd-backup.timer" /etc/systemd/system/ctfd-backup.timer
systemctl daemon-reload
systemctl enable --now ctfd-backup.timer
systemctl list-timers ctfd-backup.timer --no-pager | head -3
