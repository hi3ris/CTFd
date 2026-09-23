# CI/CD — NCTF26

Deux workflows GitHub Actions propres au fork, à côté de ceux de CTFd amont
(lint, bases de données, thèmes) :

## `NCTF26 CI` (`.github/workflows/nctf26-ci.yml`)

Se lance sur tout push / PR qui touche `deploy/` ou `challenges/` :

- **Terraform** : `fmt -check` + `validate` (sans backend distant), y compris
  `terraform/bootstrap`.
- **Scripts shell** : `bash -n` + `shellcheck` sur `deploy/*.sh` et
  `deploy/scripts/*.sh`.
- **challenge.yml** : `deploy/scripts/check_challenges.py` — clés requises,
  catégorie = dossier, noms uniques, fichiers obligatoires d'un servi, et la règle
  de publication : **un servi n'est `visible` que s'il porte la marque du Lot-5**
  (`lot5.sh --flip`).
- **Lot-5** : pour chaque servi IMPLEMENTED modifié par le push, build de
  l'image + rejeu du solveur (`deploy/scripts/lot5.sh --only …`). Le Lot-5
  complet (~1 h) se lance à la main : _Actions → NCTF26 CI → Run workflow →
  lot5_all_.

## `NCTF26 deploy (front)` (`.github/workflows/nctf26-deploy.yml`)

Déploiement continu du front à chaque push sur `master` ou la branche de
déploiement, quand le code CTFd, `deploy/front/` ou les scripts du front
changent. Aussi lançable à la main (_Run workflow_).

Chaîne : GitHub OIDC → rôle AWS `ctf-github-deploy`
(`deploy/terraform/github-oidc.tf`, permis uniquement à ce dépôt et aux refs
listées dans `github_deploy_refs`) → **SSM Run Command** sur l'instance taguée
`ctf-front` → `deploy/scripts/front-update.sh <sha>` (fetch, checkout, timer de
sauvegarde, `docker compose up -d --build`, attente de `/healthcheck`).
`make deploy` exécute le même script par SSH : une seule procédure.

- Aucune clé AWS dans GitHub. Le SSH admin reste fermé aux runners.
- Le rôle ne peut **que** lancer `AWS-RunShellScript` sur le front et lire le
  résultat.
- Si le front est éteint (`phase = off`), le job se termine sans rien faire.
- **Gel pendant l'épreuve** : variable de dépôt `DEPLOY_FREEZE=1`
  (_Settings → Secrets and variables → Actions → Variables_). Remettre à `0`
  ou la supprimer pour rouvrir.
- Un déploiement à la fois (`concurrency: nctf26-front-deploy`), environnement
  GitHub `production` (y ajouter des _required reviewers_ pour exiger une
  approbation manuelle).

Variables de dépôt attendues : `AWS_DEPLOY_ROLE_ARN` (sortie Terraform
`github_deploy_role_arn`), `AWS_REGION` (`eu-west-3`).
