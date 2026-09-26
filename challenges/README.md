# Challenges du CTF

Set de présélection (par équipe) et finale. Chaque challenge est un dossier
autonome au format ctfcli (`challenge.yml`), important directement dans CTFd.

## Catalogue — 203 challenges, 19 catégories

**177 statiques** (téléchargeables, `type: dynamic`) + **26 servis** (instance
par équipe, `type: team_instance`, image Docker `ctf-*`).

| catégorie   | n   | statiques | servis |
| ----------- | --- | --------- | ------ |
| ai          | 12  | 4         | 8      |
| blockchain  | 10  | 9         | 1      |
| cloud       | 8   | 7         | 1      |
| crypto      | 13  | 11        | 2      |
| forensics   | 13  | 13        | 0      |
| hardware    | 8   | 8         | 0      |
| misc        | 13  | 11        | 2      |
| ml          | 11  | 8         | 3      |
| mobile      | 8   | 8         | 0      |
| networking  | 9   | 9         | 0      |
| osint       | 8   | 8         | 0      |
| ppc         | 9   | 9         | 0      |
| pwn         | 13  | 6         | 7      |
| reverse     | 12  | 12        | 0      |
| stego       | 8   | 8         | 0      |
| supplychain | 11  | 10        | 1      |
| sysadmin    | 8   | 8         | 0      |
| warmup      | 16  | 16        | 0      |
| web         | 13  | 8         | 5      |
| **total**   | 203 | 177       | 26     |

- **Index détaillé** (chaque challenge, points, type, writeup) : [`WRITEUPS.md`](WRITEUPS.md).
- **Audit de pertinence** (5 axes, keep/revise/cut, note moy. 4.13/5) : [`AUDIT.md`](AUDIT.md).
- Les collines **King-of-the-Hill** (`koth/`) sont scorées par le plugin `koth`
  (Awards) et ne figurent pas dans ce décompte jeopardy ; voir `../deploy/koth-ops.md`.

## Conventions

- **Mode équipes** : la présélection est jouée par équipe. Les flags dynamiques
  dérivent du `team_id` (= `account_id` côté CTFd en mode équipes).
- **Oracle côté serveur** pour les challenges à forte valeur : le flag n'est
  émis qu'après vérification serveur d'un _effet_, jamais présent dans un
  artefact téléchargeable. Voir `deploy/anti-llm-guardrails.md` §4.
- **Chaîne de prérequis** pour la catégorie IA : niveau 0 sans inférence, puis
  1→2→3 débloqués via `challenge.yml: requirements`.
- Chaque dossier contient : `challenge.yml`, la source, un `Dockerfile` si le
  challenge est servi, `solution/` (writeup + solveur), et `flag.py` quand le
  flag est dérivé par équipe.

## État

Les 203 challenges sont **écrits, solveur-vérifiés et audités** (voir
[`AUDIT.md`](AUDIT.md) — note moyenne 4.13/5, 2 retraits, 22 corrections
appliquées). Il reste le **playtest adverse en conditions réelles** imposé par
le document garde-fous (2 modèles frontier + 1 harness agentique, budget
30-60 min) avant mise en production : résolu seul en < 15 min → on coupe. Ne pas
mettre en ligne sans cette étape.

## Import

Un challenge isolé :

```bash
pip install ctfcli
ctf challenge install challenges/<cat>/<nom>
```

L'ensemble (setup CTFd + thème + les 203) est installé par le seed, qui
auto-découvre `challenges/*/*/challenge.yml` :

```bash
cd deploy && make local-up && make local-seed   # + make local-build-images pour les 26 servis
```

> Les artefacts téléchargeables (`*.db`, `*.log`, `*.zip`, `*.pyc`, …) sont
> **suivis dans git** (règle `!challenges/**` du `.gitignore`) : un `git clone`
> frais contient tout ce dont `ctf challenge install` a besoin.

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
