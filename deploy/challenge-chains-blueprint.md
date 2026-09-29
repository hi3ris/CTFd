# Blueprint — challenges à chaîne de vulnérabilités & AI-résistants

_Spec de conception. Ce document ne contient pas de code d'exploit : il cadre
**quoi** construire et **pourquoi ça résiste à un agent**, pour qu'une session de
build dédiée les fabrique vite et juste. Chaque challenge ici est **servi**
(`team_instance`, flag par équipe), état serveur, aucun artefact à télécharger._

Voir `deploy/anti-llm-guardrails.md` (le raisonnement), `deploy/ai-resistance-audit.md`
(le constat : 177/204 statiques, à rééquilibrer vers le servi) et
`challenges/cve/README.md` (les règles de la catégorie CVE).

---

## 1. Pourquoi une chaîne résiste mieux qu'un one-shot

Un challenge statique = une transformation, un flag : un agent lit le paquet et
répond. Une **chaîne** exige de :

1. **maintenir un modèle mental** de l'état à travers 2–4 étapes liées ;
2. **pivoter** : la sortie de l'étape N (un credential, une URL interne, un
   comportement observé) est l'entrée de l'étape N+1, et n'existe **que sur
   l'instance de l'équipe** ;
3. **agir sur un service vivant**, pas sur un fichier — donc rien à coller dans
   un chat.

Un agent peut faire tout ça s'il est bien piloté — mais le **coût explose** :
il faut un harnais qui garde l'état entre étapes, et chaque étape est
per-équipe. On convertit un solve d'1 minute en un solve outillé d'1–2 heures.
« Coûteux », pas « impossible » : c'est l'objectif réaliste, et c'est le même que
tout le reste du dispositif.

## 2. Le contrat de conception (chaque chaîne le respecte)

- **Oracle de succès côté serveur.** Le flag n'apparaît qu'après un **effet**
  réel côté serveur (un credential miné, une action admin déclenchée). Jamais un
  fichier, jamais une question reposée à un modèle.
- **Gate inter-étapes serveur.** L'info de l'étape N est émise **uniquement** en
  effet de bord de N−1 (ligne d'audit, jeton généré, endpoint révélé). On ne peut
  pas sauter une étape en devinant.
- **Flag par équipe, en bout de chaîne seulement.** Dérivé (`CHALLENGE_SECRET`),
  posé par le dernier effet. Le plugin anticheat détecte le partage.
- **Canal de lecture auto-contenu.** Le flag revient sans serveur de rappel
  (déposé dans un espace servi, reflété dans une réponse). Un CTF public ne peut
  pas supposer que chaque équipe a un collaborateur.
- **Format inventé pour au moins une étape.** Un protocole/endpoint maison sur
  une étape casse le pattern-matching pur (cf. §4.2 garde-fous).
- **Reset self-service instantané, sans re-tirer le flag** (dérivation
  déterministe), indicateur de santé d'instance visible. Pas de transition
  destructive, pas de cooldown (cf. §4.4 garde-fous).
- **Vérif live au Lot 5** (Docker) : `solution/solve.py` traverse toute la chaîne
  et sort le flag de l'équipe, sinon ça ne part pas.

## 3. Les chaînes à construire (slate)

Chacune : servie, 3 étapes en moyenne, 400–600 pts (scoring dynamique). Le
**mélange de catégories** dans une même épreuve est délibéré — c'est ce qu'un
généraliste humain fait bien et qu'un agent mono-tâche fait mal.

### C1 — `chains/vaultboard` (web → cloud → objets) · 500

Tableau de bord d'entreprise « métriques ».

1. **SSRF** dans le widget « aperçu d'URL » → atteint le mesh interne.
2. Le mesh expose un service d'identité qui **émet un jeton scopé** (effet
   serveur) quand on l'atteint depuis le tier app.
3. Le jeton liste un **magasin d'objets interne** ; un objet mal-ACLé rend le
   flag. Ancrage : classe SSRF→metadata→creds (famille cloud réelle).

_Résistance : 3 tiers réseau, le jeton est per-équipe et éphémère, le pivot exige
de comprendre la topologie, pas de réciter un PoC._

### C2 — `chains/clinic` (auth → IDOR → export → admin) · 450

Portail patient.

1. **Jeton de session prévisible** (LCG/temps — ancrage crypto faible réel) →
   prise de contrôle d'un compte bas-privilège.
2. **IDOR** sur un export → révèle un **second credential** (effet serveur) d'un
   rôle « intégration ».
3. Le rôle intégration atteint une **action admin** qui **mine le flag**.

_Résistance : chaîne auth→accès→escalade, chaque credential per-équipe ; le
pattern « prédire le jeton » est maison, pas une lib connue._

### C3 — `chains/pipeline` (supplychain → build RCE) · 550

Runner CI « vérifie ma config de build ».

1. La config accepte une **source de dépendances** → **confusion de dépendance /
   dérive de lockfile** (ancrage supplychain réel) tire un paquet attaquant.
2. Le build **exécute** le hook du paquet (effet serveur) → RCE dans le runner.
3. La RCE lit le flag déposé par le runner. Aligné avec la catégorie
   `supplychain` existante, mais **vivant** au lieu de statique.

_Résistance : servi, RCE réelle sur instance per-équipe, la chaîne dépendance→
build→exec demande de comprendre le pipeline, pas de deviner un flag._

### C4 — `chains/citadel` (web foothold → user → root, boot2root jeopardy) · 600

Un boot2root **jeopardy** (distinct des 4 collines KotH boot2root : ici en
instance par équipe, pas en colline partagée).

1. **Foothold web** (upload/traversée/désérialisation — format maison) → shell
   www-data.
2. **Priv-esc user** : credential réutilisé / fichier lisible → utilisateur.
3. **Priv-esc root** : SUID/sudo/capability mal configuré (réutilise les
   privescs des collines boot2root) → root → flag.

_Résistance : 3 étapes d'escalade, état de machine à tenir, réutilise l'infra
boot2root déjà écrite._

### C5 — `chains/tokenforge` (crypto → web → RCE) · 500

1. **Oracle crypto** (padding-oracle / LCG — ancrage réel) → forge un cookie de
   session admin.
2. La session admin ouvre un **endpoint caché** (révélé côté serveur).
3. L'endpoint a une **injection de template / désérialisation** → flag.

_Résistance : traverse crypto→web→exec ; une étape au moins en format inventé._

### C6 — `chains/relay` (reverse protocole → pwn) · 500

1. **Reverse** d'un protocole binaire maison (handshake d'auth) — pas une lib
   connue.
2. Le handshake reconstruit atteint une **commande cachée** (effet serveur).
3. La commande a un **bug mémoire** → exploitation → flag.

_Résistance : reverse d'un format hors-distribution + pwn sur service vivant._

## 4. Checklist AI-résistance (à cocher sur CHAQUE nouvelle épreuve)

Distillée des garde-fous + de l'audit. Une épreuve qui coche tout est structurellement dure :

- [ ] **Servie** (per-team flag, état serveur) — pas d'artefact téléchargeable.
- [ ] **Oracle de succès côté serveur** — le flag naît d'un effet, pas d'un fichier.
- [ ] **≥ 1 étape en format inventé** (protocole/endpoint maison).
- [ ] **Jugement > volume** — pas une micro-tâche répétée (ça, un agent adore).
- [ ] **Canal de lecture auto-contenu** (pas de serveur de rappel).
- [ ] **CVE en indice payant** si applicable, jamais dans l'énoncé.
- [ ] **`solution/solve.py`** traverse toute la chaîne (vérif Lot 5).

## 5. Priorité de build (session dédiée)

Ordre par rapport résistance / coût, en réutilisant l'infra existante :

1. **C4 citadel** — réutilise les privescs boot2root déjà écrits (le moins de neuf).
2. **C1 vaultboard** — réutilise le motif SSRF→metadata déjà maîtrisé (2 SSRF existent).
3. **C3 pipeline** — réutilise la catégorie supplychain.
4. **C2 clinic / C5 tokenforge / C6 relay** — plus de neuf, à faire ensuite.

Plus les **3 CVE restantes** (`tarveil`, `invoicing`, `partial` — cf.
`challenges/cve/README.md`). Chaque build : servi, flag par équipe, solveur,
checks statiques, commit immédiat, vérif live au Lot 5.

Coût réaliste : **0,5–1 j-personne par chaîne**, exploit vérifié à chaque fois.
À 4,5 semaines de l'ouverture, viser **3–4 chaînes + les 3 CVE** ; le reste après
la présélection. Ça déplace franchement le poids du tableau vers le servi — la
seule stratégie anti-solve-IA qui tienne à l'échelle.
