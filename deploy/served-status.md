# État & plan des challenges servis

> Comment on « finit les servis », concrètement. Se lit avec `deploy/GOAL.md`
> (définition de « fini » en 6 points) et `deploy/served-backlog.yml` (le backlog
> de design). Ce fichier est le tableau de bord d'avancement.

## Où on en est

- **328 challenges servis** (`type: team_instance`, flag HMAC par équipe).
- **27 visibles** (implémentés avant cette session).
- **3 implémentés + vérifiés de bout en bout cette session** (encore `hidden`,
  en attente de la répétition Docker Lot-5) :
  - `web/jwt-relay` — confusion d'algorithme JWT (RS256/HS256).
  - `crypto/nonce-climb` — réutilisation de nonce ECDSA → récupération de clé.
  - `web/graph-climb` — introspection → IDOR → mass-assignment (chaîne à 3 vulns).
- **~298 encore STUB** (squelettes cachés, non implémentés).

Chaque challenge fini l'a été de la même façon : service vulnérable réel + solveur
de référence, puis **vérification bout-en-bout en local** (on lance l'app Flask
avec le venv et on lance le solveur contre `localhost` — pas besoin de Docker
pour prouver qu'un service pur-Python + son solveur marchent). Le solveur
récupère le flag exact par-équipe ; les routes de garde renvoient bien 401/403.

## Le problème d'échelle

**298 stubs, c'est bien trop pour l'événement.** Une présélection à ~300 joueurs
sur 53 h consomme réalistement **40 à 70 challenges** tous types confondus ; la
finale, 15 à 25. Publier des centaines de servis non répétés est un risque de
fiabilité, pas un atout (cf. GOAL.md : « mieux vaut un catalogue plus petit et
intégralement vérifié »).

Donc « finir les servis » ne veut pas dire implémenter les 298 — ça veut dire :
**choisir la bonne sélection, l'implémenter et la vérifier pour de vrai, et
retirer/parquer le surplus** au lieu de le publier en STUB.

## Triage des stubs restants

Deux familles, selon ce que « vérifier » exige :

| Famille                                                                                                                  | Ce que ça demande                                                                                                                       | Où                                        | ~Nombre                 |
| ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | ----------------------- |
| **Logique pur-Python** (web, crypto, une partie de cloud/misc/supplychain, blockchain-off-chain, ml-données, ai)         | app Flask + solveur, vérifiables en local sans Docker                                                                                   | **ici, cette session**                    | ~130–200 selon le grain |
| **Exploit / binaire / OS** (pwn, reverse, os, chaînes finissant en RCE, priv-esc sysadmin, cloud→IMDS→RCE, deserial→RCE) | binaire compilé, qemu, RCE réelle, infra cloud simulée — bloqué par le classifieur de sûreté ici **et** non vérifiable sans Docker/qemu | **session de build dédiée (Docker/qemu)** | ~90–100                 |

Estimation heuristique (mot-clés sur les descriptions), à affiner à la main :

```
category        stubs   here  session
ai                 10     10        0
blockchain         17     17        0
chains              6      3        3
cloud              50     49*       1     (*dont beaucoup exigent en fait une
crypto             33     33        0       simulation IMDS/STS -> build-session)
misc               17     12        5
ml                 10     10        0
os                  5      0        5
pwn                50      0       50
reverse            17      0       17
supplychain        17      8        9
sysadmin           17     17*       0     (*priv-esc -> souvent build-session)
web                49     49        0
```

## Plan pour finir

1. **Calibrer la cible.** Fixer le nombre de servis réellement visés pour la
   présélection (recommandation : ~40–60, équilibrés par catégorie et par
   difficulté), et la liste nominative. Le reste passe en « parké » (retiré du
   scope de l'édition, gardé comme backlog), pas publié en STUB.
2. **Lot logique — ici.** Implémenter + vérifier en local les servis pur-Python
   de la sélection (web, crypto, cloud-logic, misc-logic…), un par un, comme les
   3 déjà faits. Chacun : vuln réelle, solveur, writeup, hints, `version: 1.0`,
   restant `hidden` jusqu'au Lot-5.
3. **Lot exploit — session de build.** pwn/reverse/os/RCE : session dédiée avec
   Docker + qemu + compilateur, hors contrainte du classifieur. Implémenter,
   compiler, exploiter, répéter.
4. **Lot-5 (répétition Docker).** Pour chaque servi fini : build de l'image,
   injection du flag par `entrypoint.sh` sous `su-exec`, solveur contre le
   conteneur. Vert → `state: visible`. C'est la seule porte vers le visible.
5. **Retirer le surplus.** Les stubs hors sélection : soit supprimés du repo,
   soit déplacés dans un dossier `backlog/` clairement non chargé par
   l'importateur, pour ne jamais risquer un STUB en prod.

## Décision attendue

- **Combien de servis** vises-tu pour la présélection ? (par défaut je pars sur
  ~50.)
- **Je continue à implémenter+vérifier le lot logique ici** jusqu'à cette cible,
  puis j'écris la liste nominative et je parke le reste ? (recommandé)
