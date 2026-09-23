#!/usr/bin/env bash
# Nouveau plan gratuit AWS (comptes crees apres le 15 juillet 2025) : la
# console "Explore AWS > Earn AWS credits" offre 20 USD par activite, 5
# activites, soit 100 USD en plus des 100 USD de bienvenue. Ce script fait
# les cinq depuis la CLI, avec les ressources les moins cheres possibles,
# et detruit tout derriere lui sauf le budget (gratuit, et utile en soi).
#
#   1. EC2      : lance une t3.micro (Amazon Linux 2023), puis la termine.
#   2. Bedrock  : un appel `converse` sur un modele Amazon Nova (us-east-1).
#   3. Budgets  : budget de cout mensuel (BUDGET_USD, defaut 50).
#   4. RDS      : db.t4g.micro MySQL 20 Go, attend "available", puis supprime.
#   5. Lambda   : fonction Python "hello", un invoke, puis supprime (role inclus).
#
# Usage (depuis deploy/) :
#   scripts/aws_free_credits.sh                 # les 5 activites
#   ONLY=budget,lambda scripts/aws_free_credits.sh
#   BUDGET_EMAIL=ops@exemple.com REGION=eu-west-3 scripts/aws_free_credits.sh
#
# Variables : REGION (defaut eu-west-3), BEDROCK_REGION (us-east-1),
#   BUDGET_USD (50), BUDGET_EMAIL (alerte a 80 %, optionnel), ONLY (liste
#   parmi ec2,bedrock,budget,rds,lambda), KEEP=1 pour ne pas detruire (debug).
#
# Idempotent : une ressource laissee par un passage precedent est reutilisee
# ou nettoyee. Le tableau de bord de la console peut mettre plusieurs heures
# a passer une activite en "Completed".
set -euo pipefail

REGION=${REGION:-eu-west-3}
BEDROCK_REGION=${BEDROCK_REGION:-us-east-1}
BUDGET_USD=${BUDGET_USD:-50}
BUDGET_EMAIL=${BUDGET_EMAIL:-}
BUDGET_NAME=${BUDGET_NAME:-ctf-monthly}
ONLY=${ONLY:-ec2,bedrock,budget,rds,lambda}
KEEP=${KEEP:-0}
PREFIX=free-credits

for t in aws jq; do
  command -v "$t" >/dev/null || { echo "ERREUR : $t introuvable" >&2; exit 1; }
done

log()  { printf '\n>> %s\n' "$*"; }
want() { [[ ",$ONLY," == *",$1,"* ]]; }
declare -A RESULT

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
log "Compte $ACCOUNT, region $REGION (Bedrock : $BEDROCK_REGION)"

# --- 1. Budgets --------------------------------------------------------------
act_budget() {
  if aws budgets describe-budget --account-id "$ACCOUNT" --budget-name "$BUDGET_NAME" >/dev/null 2>&1; then
    echo "Budget '$BUDGET_NAME' deja present."
    RESULT[budget]="deja fait"; return
  fi
  local budget notif=()
  budget=$(jq -nc --arg n "$BUDGET_NAME" --arg a "$BUDGET_USD" \
    '{BudgetName:$n, BudgetType:"COST", TimeUnit:"MONTHLY",
      BudgetLimit:{Amount:$a, Unit:"USD"}}')
  if [[ -n $BUDGET_EMAIL ]]; then
    notif=(--notifications-with-subscribers "$(jq -nc --arg e "$BUDGET_EMAIL" \
      '[{Notification:{NotificationType:"ACTUAL", ComparisonOperator:"GREATER_THAN",
                       Threshold:80, ThresholdType:"PERCENTAGE"},
         Subscribers:[{SubscriptionType:"EMAIL", Address:$e}]}]')")
  fi
  aws budgets create-budget --account-id "$ACCOUNT" --budget "$budget" "${notif[@]}"
  echo "Budget '$BUDGET_NAME' cree : $BUDGET_USD USD / mois${BUDGET_EMAIL:+, alerte 80 % -> $BUDGET_EMAIL}."
  RESULT[budget]=OK
}

# --- 2. EC2 ------------------------------------------------------------------
act_ec2() {
  local ami id
  ami=$(aws ssm get-parameter --region "$REGION" \
        --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
        --query Parameter.Value --output text)
  id=$(aws ec2 run-instances --region "$REGION" --image-id "$ami" --instance-type t3.micro \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$PREFIX}]" \
        --query 'Instances[0].InstanceId' --output text)
  echo "Instance $id ($ami) lancee, attente de l'etat running..."
  aws ec2 wait instance-running --region "$REGION" --instance-ids "$id"
  if [[ $KEEP == 1 ]]; then RESULT[ec2]="OK (instance $id CONSERVEE)"; return; fi
  aws ec2 terminate-instances --region "$REGION" --instance-ids "$id" >/dev/null
  echo "Instance $id terminee."
  RESULT[ec2]=OK
}

# --- 3. Bedrock --------------------------------------------------------------
act_bedrock() {
  local m out
  for m in amazon.nova-micro-v1:0 amazon.nova-lite-v1:0 amazon.titan-text-express-v1; do
    if out=$(aws bedrock-runtime converse --region "$BEDROCK_REGION" --model-id "$m" \
              --messages '[{"role":"user","content":[{"text":"Reply with the single word: hello"}]}]' \
              --inference-config '{"maxTokens":8}' \
              --query 'output.message.content[0].text' --output text 2>&1); then
      echo "Modele $m : $out"
      RESULT[bedrock]="OK ($m)"; return
    fi
    echo "  $m : ${out##*: }"
  done
  echo "Aucun modele accessible. Activez l'acces aux modeles Amazon ici :"
  echo "  https://$BEDROCK_REGION.console.aws.amazon.com/bedrock/home?region=$BEDROCK_REGION#/modelaccess"
  RESULT[bedrock]=ECHEC
}

# --- 4. RDS ------------------------------------------------------------------
act_rds() {
  local id=$PREFIX status
  status=$(aws rds describe-db-instances --region "$REGION" --db-instance-identifier "$id" \
             --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || true)
  if [[ -z $status ]]; then
    aws rds create-db-instance --region "$REGION" --db-instance-identifier "$id" \
      --engine mysql --db-instance-class db.t4g.micro --allocated-storage 20 \
      --master-username admin --master-user-password "$(openssl rand -hex 16)" \
      --no-publicly-accessible --backup-retention-period 0 --no-multi-az \
      --no-deletion-protection --tags "Key=Name,Value=$PREFIX" >/dev/null
    echo "Instance RDS $id en cours de creation (5 a 10 min)..."
  elif [[ $status == deleting ]]; then
    echo "Instance RDS $id en cours de suppression (passage precedent)."
    RESULT[rds]="deja fait"; return
  else
    echo "Instance RDS $id deja presente ($status)."
  fi
  aws rds wait db-instance-available --region "$REGION" --db-instance-identifier "$id"
  echo "Instance RDS $id disponible."
  if [[ $KEEP == 1 ]]; then RESULT[rds]="OK (instance $id CONSERVEE)"; return; fi
  aws rds delete-db-instance --region "$REGION" --db-instance-identifier "$id" \
    --skip-final-snapshot --delete-automated-backups >/dev/null
  echo "Suppression de $id lancee (se termine seule en quelques minutes)."
  RESULT[rds]=OK
}

# --- 5. Lambda ---------------------------------------------------------------
act_lambda() {
  local role=$PREFIX-lambda fn=$PREFIX-hello arn tmp i
  tmp=$(mktemp -d)
  # expansion immediate voulue : $tmp est local a la fonction
  # shellcheck disable=SC2064
  trap "rm -rf '$tmp'" RETURN
  arn=$(aws iam get-role --role-name "$role" --query Role.Arn --output text 2>/dev/null) || {
    arn=$(aws iam create-role --role-name "$role" --query Role.Arn --output text \
      --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
        "Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}')
    aws iam attach-role-policy --role-name "$role" \
      --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    echo "Role $role cree, propagation IAM..."
  }
  printf 'def handler(event, context):\n    return {"ok": True, "source": "%s"}\n' "$PREFIX" > "$tmp/hello.py"
  (cd "$tmp" && zip -q hello.zip hello.py)
  aws lambda delete-function --region "$REGION" --function-name "$fn" >/dev/null 2>&1 || true
  for i in 1 2 3 4 5 6; do
    aws lambda create-function --region "$REGION" --function-name "$fn" --runtime python3.12 \
      --handler hello.handler --role "$arn" --zip-file "fileb://$tmp/hello.zip" \
      --tags "Name=$PREFIX" >/dev/null 2>"$tmp/err" && break
    grep -q "cannot be assumed" "$tmp/err" && [[ $i -lt 6 ]] && { sleep 10; continue; }
    cat "$tmp/err" >&2; RESULT[lambda]=ECHEC; return
  done
  aws lambda wait function-active-v2 --region "$REGION" --function-name "$fn"
  aws lambda invoke --region "$REGION" --function-name "$fn" "$tmp/out.json" >/dev/null
  echo "Invoke : $(cat "$tmp/out.json")"
  if [[ $KEEP == 1 ]]; then RESULT[lambda]="OK (fonction $fn CONSERVEE)"; return; fi
  aws lambda delete-function --region "$REGION" --function-name "$fn"
  aws iam detach-role-policy --role-name "$role" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  aws iam delete-role --role-name "$role"
  echo "Fonction $fn et role $role supprimes."
  RESULT[lambda]=OK
}

run() {
  want "$1" || return 0
  log "Activite : $2"
  if ! "act_$1"; then RESULT[$1]=ECHEC; echo "ECHEC de l'activite $1 (on continue)." >&2; fi
}

# RDS d'abord : c'est la plus longue, et son attente ne bloque que la fin.
run budget  "budget de cout (AWS Budgets)"
run ec2     "lancer une instance EC2"
run bedrock "modele de fondation Bedrock"
run lambda  "fonction Lambda"
run rds     "base RDS"

log "Bilan"
fail=0
for a in budget ec2 bedrock lambda rds; do
  want "$a" || continue
  printf '  %-8s %s\n' "$a" "${RESULT[$a]:-non lance}"
  [[ ${RESULT[$a]:-} == OK* || ${RESULT[$a]:-} == "deja fait" ]] || fail=1
done
echo
echo "Suivi : https://console.aws.amazon.com/console/home (widget 'Explore AWS' > 'Earn AWS credits')."
echo "Le statut 'Completed' peut prendre plusieurs heures a apparaitre."
exit $fail
