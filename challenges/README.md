# Challenges du CTF

Set de présélection (par équipe) et finale. Chaque challenge est un dossier
autonome au format ctfcli (`challenge.yml`), important directement dans CTFd.

## Conventions

- **Mode équipes** : la présélection est jouée par équipe. Les flags dynamiques
  dérivent du `team_id` (= `account_id` côté CTFd en mode équipes).
- **Oracle côté serveur** pour les challenges à forte valeur : le flag n'est
  émis qu'après vérification serveur d'un *effet*, jamais présent dans un
  artefact téléchargeable. Voir `deploy/anti-llm-guardrails.md` §4.
- **Chaîne de prérequis** pour la catégorie IA : niveau 0 sans inférence, puis
  1→2→3 débloqués via `challenge.yml: requirements`.
- Chaque dossier contient : `challenge.yml`, la source, un `Dockerfile` si le
  challenge est servi, `solution/` (writeup + solveur), et `flag.py` quand le
  flag est dérivé par équipe.

## État

Ces challenges sont **écrits mais non playtestés**. Le document garde-fous
impose un pré-test adverse (2 modèles frontier + 1 harness agentique, budget
30-60 min) avant mise en production : résolu seul en < 15 min → on coupe.
Ne pas mettre en ligne sans cette étape.

## Import

```bash
pip install ctfcli
ctf challenge install challenges/<cat>/<nom>
```

## Contrat d'environnement des challenges servis

Les conteneurs par équipe (type `team_instance`) reçoivent de l'instancier :

- `FLAG` — le flag exact à servir/attendre (`NCTF{...}`).
- `CHALLENGE_SECRET` — secret **par challenge** (hex) ; `FLAG == NCTF{CHALLENGE_SECRET[:24]}`.
  Toute valeur secrète auxiliaire (guard-secret, token admin) dérive de `CHALLENGE_SECRET`.

`TEAM_SECRET` (le secret **maître** de l'équipe) n'est **jamais** injecté : un conteneur
compromis ne doit livrer que son propre flag, pas ceux des autres challenges. Chaque
`flag.py` expose `get_flag()` qui lit `FLAG`, sinon dérive de `CHALLENGE_SECRET`, sinon
un repli local marqué pour le dev hors-arène. Le scoreboard valide via la classe de flag
`team_hmac`, qui recalcule la même valeur.
