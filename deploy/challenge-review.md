# Revue qualité des challenges NCTF26

Revue éditoriale (ultracode : 9 relecteurs par lots + vérification adverse des
findings sur le disque). **363 challenges implémentés relus.** Ce document
**signale** ; aucune épreuve n'a été modifiée — les correctifs sont des décisions
de conception qui te reviennent.

> Méthode : chaque finding a été re-vérifié par diff/`md5sum` réel avant d'être
> retenu. Les findings non reproduits ont été écartés (voir §7).

> **✅ DÉDUP APPLIQUÉE (§1).** Sur demande, les clones ont été retirés : **153
> épreuves supprimées** (116 octet-pour-octet + 37 variantes reformulées
> auto-déclarées « Variante de la classe X » ou à très faible diff), **1 skin
> canonique conservé par primitive**. Catalogue : **505 → 352**. Deux épreuves
> partageant un suffixe mais réellement distinctes ont été **préservées**
> (`leaky-prefix` — forensic S3 statique ; `oracle-encoding-smuggle` — oracle IA),
> confirmées par un gros diff normalisé (91 / 86 lignes vs ~0-24 pour les clones).
> Références mises à jour (`port_served.py` PROTO → skins survivants, carte
> auteurs régénérée). Les §2-§5 (indices, résistance IA, calibration,
> descriptions) restent des décisions de conception, non appliquées.

## 1. Constat principal — le nombre de challenges est gonflé par du clonage

**~160 épreuves sont des copies octet-pour-octet d'une même primitive, au seul
nom de service près** (`app.py`, description, indices et valeur strictement
identiques ; seul le flag `team_hmac` diffère par équipe). Vérifié :
`diff notarysvc-ecb sealbox-ecb` (app.py) = vide hors nom ; les 9 `*-imds`
partagent un seul `md5` de description.

| Cluster                                             | Copies | Primitive unique                                                                            |
| --------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------- |
| cloud `*-imds`                                      | 9      | SSRF → IMDS → assume-role                                                                   |
| cloud `*-presign`                                   | 9      | abus d'URL pré-signée                                                                       |
| cloud `*-prefix` (+ bucket-pivot)                   | 10     | préfixe public → creds → escalade                                                           |
| cloud `*-oidc` (+ oidc-forge)                       | 9      | OIDC alg=none → jeton forgé                                                                 |
| cloud `*-envexec` (+ func-inject)                   | 9      | injection d'env → exécution                                                                 |
| supplychain `*-artswap`/`*-depconf`/`*-postinstall` | 6/6/5  | provenance / lockfile / hook                                                                |
| crypto `*-ecb`                                      | 6      | ECB cut-and-paste                                                                           |
| crypto `*-kdf`                                      | 6      | KDF faible (brute 10⁴)                                                                      |
| crypto `*-nonce`                                    | 6      | réutilisation de nonce ECDSA                                                                |
| crypto `*-padoracle` (+ padding-oracle-lite)        | 7      | padding oracle CBC                                                                          |
| crypto `*-signext`                                  | 6      | length-extension SHA-256                                                                    |
| sysadmin `*-cap`/`*-cron`/`*-systemd`               | 5/5/6  | capability / cron / systemd env                                                             |
| misc `*-deser`/`*-envreuse`/`*-protoparse`          | 11/5/5 | SSRF-deser / HMAC reuse / parser OOB                                                        |
| web (8 familles)                                    | ~49    | smuggling, JWT-confusion, authbypass, upload-SSRF, SSRF-deser, proto-pollution, SQLi-2, XXE |
| ml pickle-RCE                                       | 6      | désérialisation pickle                                                                      |

Plusieurs clones sont **cachés derrière un nom distinct** (bucket-pivot,
oidc-forge, func-inject, build-hijack, cache-split, proto-desync, jwt-relay,
render-pivot, deserial-chain, rbac-climb, proto-fuzz-live) et certains portent
un tag `cve` sans contenu CVE.

**Effet** : le flag `team_hmac` garantit l'unicité **par équipe** mais **pas** la
distinction pédagogique. Un joueur qui résout une instance **rejoue le même
exploit** sur 5–10 skins pour farmer les points. Les épreuves réellement
distinctes et bien conçues sont une minorité (smuggle-gap, jwt-cousin,
race-the-coupon, ssrf-metadata-decoy, graphql-introspection-maze, breach-chain,
poisoned-pipeline, reentrant-vault…).

**Reco** : garder **1 skin visible par primitive**, ou différencier réellement
chaque variante (endpoint / bypass / gadget distinct). Sinon regrouper les copies
en « série » non re-scorable. Déduit, le set implémenté distinct est de l'ordre
de ~24 primitives « matricielles » + ~50 épreuves singulières.

## 2. Indices trop généreux (systémique)

Sur les familles templatées, le **dernier indice payant — parfois le premier
(coût 20)** — imprime le **payload / la requête / la formule exacte**, alors que
la catégorie de vuln est déjà nommée dans le titre. Un challenge à **450–550 pts
devient achetable pour 10–40 pts**, découverte nulle.

- ex. `cms-authbypass` h2 (40) = `X-Account-Role: admin` sur `POST /api/users/<uid>` `{"role":"admin"}` ;
- `graphql-introspection-maze` (par ailleurs excellent) : h3 donne l'octet kind exact (`0x2A`) + le layout complet du scalaire NodeRef ;
- `synthvm` : les indices livrent les graines et la fonction de round anti-analyse.

**Reco** : dernier indice **directionnel** (nommer la classe de bug) et non
exécutable ; retirer la chaîne de vuln explicite des descriptions publiques.

## 3. Faible résistance aux solveurs LLM sur les artefacts statiques

Contredit la posture anti-LLM affichée (`anti-llm-guardrails.md`).

- **pwn** : flag XOR-encodé avec une **clé de compilation** récupérable hors-ligne (`fmt-key-leak` `enc[i]=flag[i]^0x4D`, `bss-admin-flip`, `off-by-one-auth`, `stack-smash-reveal`, `ret2win-keyed`, `shellcode-decoder`).
- **reverse** : formats **ultra-reconnaissables** — `java-cafe` (`javap -c`), `pyc-ghost` (marshal/décompile), `shell-lock`.
- **web statiques** (`type: dynamic`) : source complète + flag scellé (bonne parade au grep) **mais** le dernier indice épelle le descellement → purement mécanique pour un LLM. Pire ratio : `reset-token-lcg` (450 pts, tag hard, LCG seedé par un timestamp du log fourni).
- **networking (9)**, **hardware (8)**, **mobile (7)**, **warmup (16)** : décodage statique mono/bi-étape, résistance IA ≈ nulle (attendu pour warmup ; à ne pas compter comme « résistant »).

**Reco** : pour les statiques à forte valeur, passer à un **oracle serveur**
(comme le set servi) ou retirer la formule finale de l'indice, sinon aligner les
points sur la vraie résistance.

> **✅ PARTIELLEMENT APPLIQUÉ (§3, volet indices).** La branche « retirer la
> formule finale de l'indice » a été appliquée aux statiques à forte valeur :
> `reverse/java-cafe`, `reverse/pyc-ghost`, `reverse/shell-lock`,
> `web/reset-token-lcg` (le pire ratio, 450 pts), `pwn/fmt-key-leak`,
> `pwn/ret2win-keyed` — le dernier indice ne livre plus la formule close /
> l'offset / la graine, seulement la technique et la forme. Les statiques
> bon-marché (`bss-admin-flip`/`off-by-one-auth`/`stack-smash-reveal` 100-150,
> beginner/easy ; warmup/networking/hardware/mobile) sont **laissées
> explicites** : leur résistance ≈ nulle est cohérente avec leur prix bas, elles
> ne sont **pas** comptées comme « résistantes ». Le **volet structurel**
> (oracle serveur, flag offline non récupérable statiquement, reverse « écart
> aux specs ») nécessite l'arène et est **parké** (`HANDOFF-NCTF26.md`).

## 4. Calibration & étiquetage

- **~67/69 servis cloud/supplychain sans tag de difficulté** ; ~310/505 au total sans tag `easy/medium/hard`.
- Matrice cloud à **450–550 pts** pour des solves **mono-étape entièrement pré-décrits** par les indices.
- Incohérences ponctuelles : `notarysvc-kdf` 500 pts pour un brute-force 10⁴ ; `padding-oracle-lite` vs `*-padoracle` (même primitive, points différents) ; `proto-desync` **550 pts** (valeur la plus haute du lot) pour un mécanisme facturé 500 ailleurs.

## 5. Descriptions qui annoncent une autre vulnérabilité que celle servie

- `proto-desync` : annonce « Desync HTTP/2 » ; l'app est le splitter naïf `/ingest` de `cms-smuggle` (le writeup l'admet). Le joueur part sur une technique absente.
- `rbac-climb` : le nom annonce une escalade **Kubernetes RBAC** ; c'est en réalité une injection d'env **systemd** (clone de `schedd-systemd`).
- `build-hijack` : décrit un hook post-install ; mécanisme = clone `buildfarm-depconf`.

**Reco** : aligner la description sur le vrai bug, **ou** implémenter la vuln
annoncée.

> **✅ RÉSOLU (§5).** Les trois épreuves étaient des **clones** au nom/à la
> description mensongers (proto-desync = clone `cms-smuggle` ; rbac-climb =
> clone `auditd-systemd` ; build-hijack = clone `buildfarm-depconf`). Elles ont
> été **supprimées à la dédup** (§1, commit `43af35b`) : la description
> mensongère disparaît avec le clone. Les skins canoniques conservés
> (`web/cms-smuggle`, `sysadmin/auditd-systemd`, `supplychain/buildfarm-depconf`)
> **annoncent le vrai bug** (vérifié : smuggling→cache→auth ; injection d'env
> →systemd→sudo→root ; dérive de lockfile→confusion de dépendance→hook). Aucune
> description mensongère ne subsiste dans le set dédupliqué.

## 6. Flags statiques partageables (offline)

Beaucoup d'épreuves **offline** (`type: dynamic`, non servies) utilisent un
**flag statique** défini dans `challenge.yml` (ex. blockchain `calldata-cache`
= `NCTF{abi_...}`, value 100). C'est **normal** pour de l'offline, mais un flag
statique est **partageable** tel quel entre équipes (le détecteur d'anti-triche
ne repère que le partage des flags `team_hmac`). À garder en tête pour les
épreuves offline à forte valeur ; les épreuves **servies** utilisent bien
`team_hmac` (unique/équipe, non partageable) — vérifié.

## 7. Corrections à mes conclusions mécaniques précédentes

Par honnêteté :

- J'avais annoncé « hygiène de flag excellente ». Précision : **aucune fuite ni
  doublon dans les _entrées_ `flags:` des `challenge.yml`** (toujours vrai), mais
  de nombreuses épreuves offline reposent sur un **flag statique partageable**
  (§6) et les writeups auteur contiennent le flag en clair (non expédié aux
  joueurs ; le pipeline de publication caviarde — vérifié).
- Un finding d'agent (« `strings calldata.txt | grep NCTF` donne le flag » sur
  la blockchain) **ne se reproduit pas** : le handout `calldata.txt` ne contient
  pas le flag littéral. **Écarté.**

## 8. Priorités recommandées (décisions à toi — rien appliqué)

1. 🔴 **Dédupliquer** : 1 skin visible par primitive (les ~160 clones tombent ; le catalogue « réel » monte en qualité). Le plus gros levier, seul.
2. 🔴 **Indices** : rendre le dernier indice directionnel sur toutes les familles templatées.
3. 🟠 **Résistance IA** : oracle serveur (ou re-tag points) pour les statiques à forte valeur (pwn XOR compile-time, reverse formats standard, web statiques).
4. 🟠 **Descriptions mensongères** : corriger `proto-desync`, `rbac-climb`, `build-hijack`.
5. 🟡 **Calibration** : ajouter les tags de difficulté manquants ; recaler la matrice cloud (450-550 → medium bas) ; corriger les points incohérents.

Aucune de ces actions n'est un correctif « sûr » applicable seul (couper des
épreuves, réécrire des indices/énoncés = choix de conception), d'où le
signalement plutôt que l'application automatique.
