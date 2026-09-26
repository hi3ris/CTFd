#!/usr/bin/env bash
# Quota GPU "Running On-Demand G and VT instances" (L-DB2E81BA) : verifie la
# valeur dans la region, et DEMANDE l'augmentation via Service Quotas si elle
# ne permet pas une g4dn.xlarge (4 vCPU). Le traitement prend souvent plusieurs
# jours ouvres, d'ou `make check-gpu-quota` / `make request-gpu-quota` a lancer
# des maintenant.
#
# Usage (depuis deploy/) :
#   scripts/aws_gpu_quota.sh                # verifie, demande si < 4 vCPU
#   VALUE=16 scripts/aws_gpu_quota.sh       # demande une autre valeur
#   FORCE=1 scripts/aws_gpu_quota.sh        # demande meme si le quota suffit
#   REGION=eu-west-3 (defaut ; ou la sortie Terraform aws_region si presente)
#
# Note plan gratuit : un compte encore sur le plan gratuit AWS n'obtient en
# general pas de quota GPU. Si la demande est refusee, passer le compte en
# plan payant (Billing > Free plan > Upgrade) puis redemander.
set -euo pipefail

REGION=${REGION:-$(terraform -chdir="$(dirname "$0")/../terraform" output -raw aws_region 2>/dev/null)}
REGION=${REGION:-eu-west-3}
VALUE=${VALUE:-8}
FORCE=${FORCE:-0}
QUOTA=L-DB2E81BA
CONSOLE="https://$REGION.console.aws.amazon.com/servicequotas/home/services/ec2/quotas/$QUOTA"

command -v aws >/dev/null || { echo "ERREUR : aws CLI introuvable" >&2; exit 1; }

current=$(aws service-quotas get-service-quota --region "$REGION" \
            --service-code ec2 --quota-code "$QUOTA" --query Quota.Value --output text)
echo "Quota 'Running On-Demand G and VT instances' dans $REGION : $current vCPU"

pending=$(aws service-quotas list-requested-service-quota-change-history-by-quota \
            --region "$REGION" --service-code ec2 --quota-code "$QUOTA" \
            --query "RequestedQuotas[?Status=='PENDING' || Status=='CASE_OPENED'].[Id,DesiredValue,Status,Created]" \
            --output text 2>/dev/null || true)
if [[ -n $pending ]]; then
  echo "Demande deja en cours :"
  echo "$pending" | sed 's/^/  /'
  echo "Suivi : $CONSOLE"
  exit 0
fi

if awk -v v="$current" 'BEGIN{exit (v>=4)?0:1}' && [[ $FORCE != 1 ]]; then
  echo "OK : une g4dn.xlarge (4 vCPU) tient dans ce quota. (FORCE=1 pour demander quand meme.)"
  exit 0
fi

if awk -v v="$current" -v w="$VALUE" 'BEGIN{exit (w>v)?0:1}'; then
  echo "Demande d'augmentation a $VALUE vCPU..."
  aws service-quotas request-service-quota-increase --region "$REGION" \
    --service-code ec2 --quota-code "$QUOTA" --desired-value "$VALUE" \
    --query 'RequestedQuota.[Id,Status]' --output text | sed 's/^/  id, statut : /'
  echo "Suivi : $CONSOLE"
  echo "Compter plusieurs jours ouvres ; AWS envoie la reponse a l'adresse du compte."
else
  echo "VALUE=$VALUE n'est pas superieur au quota actuel ($current) : rien a demander."
  exit 1
fi
