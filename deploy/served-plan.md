# Liste nominative des challenges servis — worklist pour tout finir

> Cible : **finir les 328 servis**. Ce fichier est la liste de travail
> exhaustive. Chaque entrée cochée `[x]` est jouable (visible) ou implémentée +
> vérifiée en local (attend seulement la répétition Docker Lot-5). Les `[ ]`
> restent à faire.
>
> Se lit avec `deploy/GOAL.md` (définition de « fini » en 6 points) et
> `deploy/served-status.md` (méthodo + triage). Régénère les writeups avec
> `make writeups-sync`.

## Deux lots

- **LOT LOGIQUE** (162) — services pur-Python,
  implémentés **et vérifiés de bout en bout ici** (app Flask + solveur contre
  localhost, sans Docker). Lot avancé dans les sessions Claude.
- **LOT BUILD** (166) — exploit / binaire / OS
  (pwn, reverse, os, chaînes et cloud/misc/supplychain finissant en RCE/priv-esc).
  Exigent Docker + qemu + compilateur → **session de build dédiée**.

## Avancement

| Statut                                  | Nombre |
| --------------------------------------- | ------ |
| ✅ visibles (déjà jouables)             | 27     |
| ✅ implémentés + vérifiés local (Lot-5) | 6      |
| ⬜ STUB à faire                         | 295    |
| **Total servi**                         | 328    |

Le classement lot (LOGIQUE/BUILD) est heuristique ; à ajuster à la main au cas
par cas.

## LOT LOGIQUE — implémentable + vérifiable ici (162)

### ai (14)

- [ ] **ai/copilotsvc-guard** — 550 pts  
       Contournement de garde-fou -> chaîne d'outils -> action privilégiée.
- [ ] **ai/deskbot-guard** — 550 pts  
       Contournement de garde-fou -> chaîne d'outils -> action privilégiée.
- [ ] **ai/retriever-guard** — 550 pts  
       Contournement de garde-fou -> chaîne d'outils -> action privilégiée.
- [ ] **ai/tool-ladder** — 550 pts  
       Contournement de garde-fou -> chaîne d'outils -> action privilégiée.
- [ ] **ai/triage-guard** — 550 pts  
       Contournement de garde-fou -> chaîne d'outils -> action privilégiée.
- [x] **ai/agent-tool-abuse** — 500 pts ✅ visible  
       **Halcyon Vault Co.** runs a two-agent automation. You chat with **RELAY**,
- [x] **ai/ai3-tool-abuse** — 500 pts ✅ visible  
       **Level 3 of the AI track -- the heaviest.** Meridian Freight runs an internal
- [ ] **ai/copilotsvc-inject** — 500 pts  
       Injection indirecte -> abus d'outil -> exfiltration de données.
- [ ] **ai/deskbot-inject** — 500 pts  
       Injection indirecte -> abus d'outil -> exfiltration de données.
- [ ] **ai/prompt-pivot** — 500 pts  
       Injection indirecte -> abus d'outil -> exfiltration de données internes.
- [ ] **ai/retriever-inject** — 500 pts  
       Injection indirecte -> abus d'outil -> exfiltration de données.
- [ ] **ai/triage-inject** — 500 pts  
       Injection indirecte -> abus d'outil -> exfiltration de données.
- [x] **ai/ai2-output-filter** — 350 pts ✅ visible  
       **LEVEL 2 of the AI track.** Same guard backend as Level 1 (a naive persona
- [x] **ai/ai1-naive-guard** — 300 pts ✅ visible  
       **Level 1 of the AI track.** Nimbus Robotics wired up a quick support

### blockchain (18)

- [ ] **blockchain/bridgepool-reentry** — 550 pts  
       Rejeu de signature -> réentrance -> drain de fonds.
- [ ] **blockchain/escrowd-reentry** — 550 pts  
       Rejeu de signature -> réentrance -> drain de fonds.
- [ ] **blockchain/lender-reentry** — 550 pts  
       Rejeu de signature -> réentrance -> drain de fonds.
- [ ] **blockchain/oraclefeed-reentry** — 550 pts  
       Rejeu de signature -> réentrance -> drain de fonds.
- [ ] **blockchain/reentry-chain** — 550 pts  
       Rejeu de signature -> réentrance -> drain de fonds gardés.
- [ ] **blockchain/vaultdao-reentry** — 550 pts  
       Rejeu de signature -> réentrance -> drain de fonds.
- [ ] **blockchain/bridgepool-allowance** — 500 pts  
       Dérive d'allowance -> approbation -> drain.
- [ ] **blockchain/bridgepool-proxy** — 500 pts  
       Collision de storage proxy -> écrasement d'admin -> action.
- [ ] **blockchain/escrowd-allowance** — 500 pts  
       Dérive d'allowance -> approbation -> drain.
- [ ] **blockchain/escrowd-proxy** — 500 pts  
       Collision de storage proxy -> écrasement d'admin -> action.
- [ ] **blockchain/lender-allowance** — 500 pts  
       Dérive d'allowance -> approbation -> drain.
- [ ] **blockchain/lender-proxy** — 500 pts  
       Collision de storage proxy -> écrasement d'admin -> action.
- [ ] **blockchain/oraclefeed-allowance** — 500 pts  
       Dérive d'allowance -> approbation -> drain.
- [ ] **blockchain/oraclefeed-proxy** — 500 pts  
       Collision de storage proxy -> écrasement d'admin -> action.
- [ ] **blockchain/proxy-climb** — 500 pts  
       Collision de storage proxy -> écrasement d'admin -> action privilégiée.
- [ ] **blockchain/vaultdao-allowance** — 500 pts  
       Dérive d'allowance -> approbation -> drain.
- [ ] **blockchain/vaultdao-proxy** — 500 pts  
       Collision de storage proxy -> écrasement d'admin -> action.
- [x] **blockchain/reentrant-vault** — 450 pts ✅ visible  
       **Reentrant Vault.** _(nouvelle catégorie : blockchain / EVM)_

### chains (3)

- [ ] **chains/tokenforge** — 500 pts  
       Oracle crypto -> cookie admin forgé -> endpoint caché avec SSTI/désérialisation.
- [ ] **chains/vaultboard** — 500 pts  
       SSRF -> jeton scopé interne -> objet mal-ACLé (web -> cloud -> objets).
- [ ] **chains/clinic** — 450 pts  
       Jeton de session prévisible -> IDOR export -> action admin (auth -> IDOR -> admin).

### cloud (21)

- [ ] **cloud/artifacts-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/backup-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/billing-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/cdn-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/gateway-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/identity-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/metrics-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [x] **cloud/oidc-forge** — 500 pts ✅ vérifié-local (attend Lot-5)  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/queue-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/registry-oidc** — 500 pts  
       Mauvaise config OIDC -> jeton forgé -> API privilégiée.
- [ ] **cloud/artifacts-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [ ] **cloud/backup-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [ ] **cloud/billing-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [x] **cloud/breach-chain** — 450 pts ✅ visible  
       **Kékéli Cloud.** Le service de prévisualisation média de Kékéli Cloud tourne
- [ ] **cloud/bucket-pivot** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [ ] **cloud/cdn-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [ ] **cloud/gateway-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [ ] **cloud/identity-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [ ] **cloud/metrics-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [ ] **cloud/queue-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.
- [ ] **cloud/registry-prefix** — 450 pts  
       Préfixe public -> credential fuité -> escalade de rôle.

### crypto (35)

- [x] **crypto/kdf-slip** — 500 pts ✅ vérifié-local (attend Lot-5)  
       Dérivation de clé faible -> prédiction -> reprise de session privilégiée.
- [x] **crypto/lcg-casino** — 500 pts ✅ visible  
       A **"provably fair"** casino deals from a home-grown verifiable shuffle. It
- [ ] **crypto/notarysvc-kdf** — 500 pts  
       Dérivation de clé faible -> prédiction -> reprise de session.
- [ ] **crypto/notarysvc-padoracle** — 500 pts  
       Oracle de padding -> cookie forgé -> endpoint admin atteint.
- [ ] **crypto/notarysvc-signext** — 500 pts  
       Extension de hash -> forge -> API privilégiée.
- [x] **crypto/oracle-cascade** — 500 pts ✅ vérifié-local (attend Lot-5)  
       Oracle de padding -> cookie forgé -> endpoint admin atteint.
- [ ] **crypto/sealbox-kdf** — 500 pts  
       Dérivation de clé faible -> prédiction -> reprise de session.
- [ ] **crypto/sealbox-padoracle** — 500 pts  
       Oracle de padding -> cookie forgé -> endpoint admin atteint.
- [ ] **crypto/sealbox-signext** — 500 pts  
       Extension de hash -> forge -> API privilégiée.
- [ ] **crypto/sessiond-kdf** — 500 pts  
       Dérivation de clé faible -> prédiction -> reprise de session.
- [ ] **crypto/sessiond-padoracle** — 500 pts  
       Oracle de padding -> cookie forgé -> endpoint admin atteint.
- [ ] **crypto/sessiond-signext** — 500 pts  
       Extension de hash -> forge -> API privilégiée.
- [ ] **crypto/signgate-kdf** — 500 pts  
       Dérivation de clé faible -> prédiction -> reprise de session.
- [ ] **crypto/signgate-padoracle** — 500 pts  
       Oracle de padding -> cookie forgé -> endpoint admin atteint.
- [ ] **crypto/signgate-signext** — 500 pts  
       Extension de hash -> forge -> API privilégiée.
- [ ] **crypto/tokenmint-kdf** — 500 pts  
       Dérivation de clé faible -> prédiction -> reprise de session.
- [ ] **crypto/tokenmint-padoracle** — 500 pts  
       Oracle de padding -> cookie forgé -> endpoint admin atteint.
- [ ] **crypto/tokenmint-signext** — 500 pts  
       Extension de hash -> forge -> API privilégiée.
- [ ] **crypto/vaultkey-kdf** — 500 pts  
       Dérivation de clé faible -> prédiction -> reprise de session.
- [ ] **crypto/vaultkey-padoracle** — 500 pts  
       Oracle de padding -> cookie forgé -> endpoint admin atteint.
- [ ] **crypto/vaultkey-signext** — 500 pts  
       Extension de hash -> forge -> API privilégiée.
- [x] **crypto/nonce-climb** — 450 pts ✅ vérifié-local (attend Lot-5)  
       Réutilisation de nonce -> récupération de clé -> forge de jeton signé.
- [ ] **crypto/notarysvc-ecb** — 450 pts  
       ECB cut-and-paste -> contournement d'auth -> action privilégiée.
- [ ] **crypto/notarysvc-nonce** — 450 pts  
       Réutilisation de nonce -> récupération de clé -> forge de jeton.
- [ ] **crypto/sealbox-ecb** — 450 pts  
       ECB cut-and-paste -> contournement d'auth -> action privilégiée.
- [ ] **crypto/sealbox-nonce** — 450 pts  
       Réutilisation de nonce -> récupération de clé -> forge de jeton.
- [ ] **crypto/sessiond-ecb** — 450 pts  
       ECB cut-and-paste -> contournement d'auth -> action privilégiée.
- [ ] **crypto/sessiond-nonce** — 450 pts  
       Réutilisation de nonce -> récupération de clé -> forge de jeton.
- [ ] **crypto/sign-slip** — 450 pts  
       Vérification de signature faible -> forge -> action admin.
- [ ] **crypto/signgate-ecb** — 450 pts  
       ECB cut-and-paste -> contournement d'auth -> action privilégiée.
- [ ] **crypto/signgate-nonce** — 450 pts  
       Réutilisation de nonce -> récupération de clé -> forge de jeton.
- [ ] **crypto/tokenmint-ecb** — 450 pts  
       ECB cut-and-paste -> contournement d'auth -> action privilégiée.
- [ ] **crypto/tokenmint-nonce** — 450 pts  
       Réutilisation de nonce -> récupération de clé -> forge de jeton.
- [ ] **crypto/vaultkey-ecb** — 450 pts  
       ECB cut-and-paste -> contournement d'auth -> action privilégiée.
- [ ] **crypto/vaultkey-nonce** — 450 pts  
       Réutilisation de nonce -> récupération de clé -> forge de jeton.

### cve (1)

- [x] **cve/hookrelay** — 350 pts ✅ visible  
       **Hookrelay** is the CI platform team's internal _mirror healthcheck_. Paste a

### misc (8)

- [ ] **misc/bridged-protoparse** — 450 pts  
       Parser maison -> état corrompu -> lecture hors-borne.
- [ ] **misc/gluesvc-protoparse** — 450 pts  
       Parser maison -> état corrompu -> lecture hors-borne.
- [ ] **misc/ingestd-protoparse** — 450 pts  
       Parser maison -> état corrompu -> lecture hors-borne.
- [ ] **misc/proto-fuzz-live** — 450 pts  
       Parser d'un protocole maison -> état corrompu -> lecture hors-borne.
- [ ] **misc/relaynode-protoparse** — 450 pts  
       Parser maison -> état corrompu -> lecture hors-borne.
- [ ] **misc/transcoder-protoparse** — 450 pts  
       Parser maison -> état corrompu -> lecture hors-borne.
- [x] **misc/esolang-jail** — 400 pts ✅ visible  
       **Marble jail** -- a tiny stack esoteric language, served over TCP as an
- [x] **misc/proto-fuzz** — 350 pts ✅ visible  
       **proto-fuzz** -- a tiny home-grown line protocol, **FZLP/1**, served over

### ml (7)

- [x] **ml/adversarial-gate** — 500 pts ✅ visible  
       **SENTRY-6 badge gate.** An access gate runs a small convolutional
- [x] **ml/model-inversion** — 500 pts ✅ visible  
       **AEGIS-VAULT recall service.** The vault has _memorised_ one sealed record --
- [ ] **ml/feature-inject** — 450 pts  
       Injection dans le pré-traitement -> empoisonnement -> exfiltration.
- [ ] **ml/featurizer-poison** — 450 pts  
       Injection dans le pré-traitement -> empoisonnement -> exfiltration.
- [ ] **ml/modelhub-poison** — 450 pts  
       Injection dans le pré-traitement -> empoisonnement -> exfiltration.
- [ ] **ml/scorer-poison** — 450 pts  
       Injection dans le pré-traitement -> empoisonnement -> exfiltration.
- [ ] **ml/trainer-poison** — 450 pts  
       Injection dans le pré-traitement -> empoisonnement -> exfiltration.

### supplychain (7)

- [ ] **supplychain/build-hijack** — 550 pts  
       Dérive de lockfile -> paquet attaquant -> hook post-install exécuté.
- [ ] **supplychain/buildfarm-depconf** — 550 pts  
       Dérive de lockfile -> confusion de dépendance -> hook de build exécuté.
- [ ] **supplychain/mirror-depconf** — 550 pts  
       Dérive de lockfile -> confusion de dépendance -> hook de build exécuté.
- [ ] **supplychain/pkgproxy-depconf** — 550 pts  
       Dérive de lockfile -> confusion de dépendance -> hook de build exécuté.
- [ ] **supplychain/releaser-depconf** — 550 pts  
       Dérive de lockfile -> confusion de dépendance -> hook de build exécuté.
- [ ] **supplychain/signer-depconf** — 550 pts  
       Dérive de lockfile -> confusion de dépendance -> hook de build exécuté.
- [x] **supplychain/poisoned-pipeline** — 350 pts ✅ visible  
       **MiniCI.** Un runner de build partagé : `http://{host}:{port}`. N'importe qui

### sysadmin (11)

- [ ] **sysadmin/auditd-cap** — 500 pts  
       Capability mal configurée -> escalade -> root.
- [ ] **sysadmin/orchestrator-cap** — 500 pts  
       Capability mal configurée -> escalade -> root.
- [ ] **sysadmin/provisioner-cap** — 500 pts  
       Capability mal configurée -> escalade -> root.
- [ ] **sysadmin/rotatord-cap** — 500 pts  
       Capability mal configurée -> escalade -> root.
- [ ] **sysadmin/schedd-cap** — 500 pts  
       Capability mal configurée -> escalade -> root.
- [ ] **sysadmin/auditd-cron** — 450 pts  
       Injection de chemin -> cron -> root.
- [ ] **sysadmin/orchestrator-cron** — 450 pts  
       Injection de chemin -> cron -> root.
- [ ] **sysadmin/provisioner-cron** — 450 pts  
       Injection de chemin -> cron -> root.
- [ ] **sysadmin/rotatord-cron** — 450 pts  
       Injection de chemin -> cron -> root.
- [ ] **sysadmin/schedd-cron** — 450 pts  
       Injection de chemin -> cron -> root.
- [ ] **sysadmin/secret-slip** — 450 pts  
       Fuite de state -> réutilisation de secret -> rotation détournée.

### web (37)

- [ ] **web/proto-desync** — 550 pts  
       Désync HTTP/2 -> vol de requête -> reprise de session privilégiée.
- [ ] **web/cache-split** — 500 pts  
       Request smuggling -> empoisonnement de cache -> contournement d'auth.
- [ ] **web/cms-smuggle** — 500 pts  
       Request smuggling -> empoisonnement de cache -> contournement d'auth.
- [ ] **web/forum-smuggle** — 500 pts  
       Request smuggling -> empoisonnement de cache -> contournement d'auth.
- [x] **web/graphql-introspection-maze** — 500 pts ✅ visible  
       **Atlas Ops** exposes a single GraphQL endpoint at `POST /graphql`
- [ ] **web/hrportal-smuggle** — 500 pts  
       Request smuggling -> empoisonnement de cache -> contournement d'auth.
- [ ] **web/invoicer-smuggle** — 500 pts  
       Request smuggling -> empoisonnement de cache -> contournement d'auth.
- [ ] **web/ledger-smuggle** — 500 pts  
       Request smuggling -> empoisonnement de cache -> contournement d'auth.
- [ ] **web/shipyard-smuggle** — 500 pts  
       Request smuggling -> empoisonnement de cache -> contournement d'auth.
- [x] **web/smuggle-gap** — 500 pts ✅ visible  
       **Nimbus** runs a tiny job service behind an edge proxy. The edge is the only
- [ ] **web/cms-authbypass** — 450 pts  
       Contournement d'auth -> IDOR -> mass-assignment vers rôle admin.
- [ ] **web/forum-authbypass** — 450 pts  
       Contournement d'auth -> IDOR -> mass-assignment vers rôle admin.
- [ ] **web/forum-sqli2** — 450 pts  
       Injection SQL de second ordre -> contournement d'auth -> action admin.
- [ ] **web/forum-xxe** — 450 pts  
       XXE -> SSRF -> lecture de fichier interne.
- [x] **web/graph-climb** — 450 pts ✅ vérifié-local (attend Lot-5)  
       Introspection GraphQL -> IDOR -> mass-assignment vers rôle admin.
- [ ] **web/hrportal-authbypass** — 450 pts  
       Contournement d'auth -> IDOR -> mass-assignment vers rôle admin.
- [ ] **web/hrportal-sqli2** — 450 pts  
       Injection SQL de second ordre -> contournement d'auth -> action admin.
- [ ] **web/hrportal-xxe** — 450 pts  
       XXE -> SSRF -> lecture de fichier interne.
- [ ] **web/invoicer-authbypass** — 450 pts  
       Contournement d'auth -> IDOR -> mass-assignment vers rôle admin.
- [ ] **web/invoicer-sqli2** — 450 pts  
       Injection SQL de second ordre -> contournement d'auth -> action admin.
- [ ] **web/invoicer-xxe** — 450 pts  
       XXE -> SSRF -> lecture de fichier interne.
- [ ] **web/ledger-authbypass** — 450 pts  
       Contournement d'auth -> IDOR -> mass-assignment vers rôle admin.
- [ ] **web/ledger-sqli2** — 450 pts  
       Injection SQL de second ordre -> contournement d'auth -> action admin.
- [ ] **web/ledger-xxe** — 450 pts  
       XXE -> SSRF -> lecture de fichier interne.
- [ ] **web/shipyard-authbypass** — 450 pts  
       Contournement d'auth -> IDOR -> mass-assignment vers rôle admin.
- [ ] **web/shipyard-sqli2** — 450 pts  
       Injection SQL de second ordre -> contournement d'auth -> action admin.
- [ ] **web/shipyard-xxe** — 450 pts  
       XXE -> SSRF -> lecture de fichier interne.
- [ ] **web/webhook-relay** — 450 pts  
       Validation de webhook contournée -> SSRF -> service interne.
- [ ] **web/cms-jwtconf** — 400 pts  
       Confusion d'algorithme JWT -> forge -> endpoint interne exposé.
- [ ] **web/forum-jwtconf** — 400 pts  
       Confusion d'algorithme JWT -> forge -> endpoint interne exposé.
- [ ] **web/hrportal-jwtconf** — 400 pts  
       Confusion d'algorithme JWT -> forge -> endpoint interne exposé.
- [ ] **web/invoicer-jwtconf** — 400 pts  
       Confusion d'algorithme JWT -> forge -> endpoint interne exposé.
- [x] **web/jwt-relay** — 400 pts ✅ vérifié-local (attend Lot-5)  
       Confusion d'algorithme JWT -> forge -> endpoint interne exposé.
- [ ] **web/ledger-jwtconf** — 400 pts  
       Confusion d'algorithme JWT -> forge -> endpoint interne exposé.
- [x] **web/race-the-coupon** — 400 pts ✅ visible  
       **NimbusPay store wallet** exposes a small JSON API. Every account starts
- [ ] **web/shipyard-jwtconf** — 400 pts  
       Confusion d'algorithme JWT -> forge -> endpoint interne exposé.
- [x] **web/jwt-cousin** — 150 pts ✅ visible  
       "It's basically a JWT," said no one who read the code.

## LOT BUILD — session Docker/qemu dédiée (166)

### chains (3)

- [ ] **chains/citadel** — 600 pts  
       Foothold web -> priv-esc user (credential réutilisé) -> priv-esc root (SUID/sudo).
- [ ] **chains/pipeline** — 550 pts  
       Confusion de dépendance / dérive de lockfile -> hook de build exécuté -> RCE runner.
- [ ] **chains/relay** — 500 pts  
       Reverse d'un protocole binaire maison -> commande cachée -> bug mémoire exploité.

### cloud (30)

- [ ] **cloud/artifacts-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/artifacts-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/artifacts-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.
- [ ] **cloud/backup-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/backup-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/backup-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.
- [ ] **cloud/billing-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/billing-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/billing-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.
- [ ] **cloud/cdn-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/cdn-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/cdn-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.
- [ ] **cloud/func-inject** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret de plateforme.
- [ ] **cloud/gateway-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/gateway-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/gateway-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.
- [ ] **cloud/identity-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/identity-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/identity-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.
- [ ] **cloud/keychain-climb** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/metrics-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/metrics-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/metrics-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.
- [ ] **cloud/queue-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/queue-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/queue-poison** — 500 pts  
       Message empoisonné -> worker -> désérialisation -> exécution.
- [ ] **cloud/queue-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.
- [ ] **cloud/registry-envexec** — 500 pts  
       Injection d'env dans une fonction -> exécution -> vol de secret.
- [ ] **cloud/registry-imds** — 500 pts  
       SSRF -> IMDS -> assume-role -> lecture d'objet privé.
- [ ] **cloud/registry-presign** — 500 pts  
       Abus d'URL pré-signée -> écriture d'objet -> exécution au déploiement.

### crypto (1)

- [x] **crypto/padding-oracle-lite** — 350 pts ✅ visible  
       A decommissioned session service still answers on its own home-grown binary

### misc (11)

- [ ] **misc/bridged-deser** — 500 pts  
       SSRF -> RPC interne -> désérialisation -> exécution.
- [ ] **misc/deserial-chain** — 500 pts  
       SSRF -> RPC interne -> désérialisation non sûre -> exécution.
- [ ] **misc/gluesvc-deser** — 500 pts  
       SSRF -> RPC interne -> désérialisation -> exécution.
- [ ] **misc/ingestd-deser** — 500 pts  
       SSRF -> RPC interne -> désérialisation -> exécution.
- [ ] **misc/relaynode-deser** — 500 pts  
       SSRF -> RPC interne -> désérialisation -> exécution.
- [ ] **misc/transcoder-deser** — 500 pts  
       SSRF -> RPC interne -> désérialisation -> exécution.
- [ ] **misc/bridged-envreuse** — 450 pts  
       Fuite d'env -> réutilisation de secret -> exécution.
- [ ] **misc/gluesvc-envreuse** — 450 pts  
       Fuite d'env -> réutilisation de secret -> exécution.
- [ ] **misc/ingestd-envreuse** — 450 pts  
       Fuite d'env -> réutilisation de secret -> exécution.
- [ ] **misc/relaynode-envreuse** — 450 pts  
       Fuite d'env -> réutilisation de secret -> exécution.
- [ ] **misc/transcoder-envreuse** — 450 pts  
       Fuite d'env -> réutilisation de secret -> exécution.

### ml (6)

- [ ] **ml/featurizer-pickle** — 500 pts  
       Upload de modèle -> pipeline -> désérialisation pickle -> exécution.
- [ ] **ml/model-swap** — 500 pts  
       Upload de modèle -> pipeline -> désérialisation pickle -> exécution.
- [ ] **ml/modelhub-pickle** — 500 pts  
       Upload de modèle -> pipeline -> désérialisation pickle -> exécution.
- [ ] **ml/scorer-pickle** — 500 pts  
       Upload de modèle -> pipeline -> désérialisation pickle -> exécution.
- [ ] **ml/trainer-pickle** — 500 pts  
       Upload de modèle -> pipeline -> désérialisation pickle -> exécution.
- [x] **ml/pickle-rce** — 350 pts ✅ visible  
       **ModelHub** is a model registry. Teams upload a serialized model and the

### os (5)

- [ ] **os/nyx-allocator** — 550 pts  
       Allocateur de tas noyau custom : débordement -> contrôle d'objet -> détournement de flux -> flag.
- [ ] **os/nyx-scheduler** — 550 pts  
       Ordonnanceur custom : course TOCTOU -> confusion de privilège -> exécution en anneau 0 -> flag.
- [ ] **os/nyx-syscall** — 500 pts  
       Table d'appels système custom : borne manquante sur un argument -> lecture/écriture arbitraire noyau -> flag.
- [ ] **os/nyx-vfs** — 500 pts  
       Système de fichiers virtuel custom : bug de permission/chemin -> lecture du flag réservé à root.
- [ ] **os/nyx-bootstrap** — 400 pts  
       Bootloader d'un OS custom : validation d'image défaillante -> détournement du boot -> lecture du flag noyau.

### pwn (57)

- [ ] **pwn/authd-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/brokerd-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/cachesrv-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/keyvault-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/logd-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/meshd-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/parserd-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/relaybox-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/sandbox-break** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/sensorhub-sandbox** — 600 pts  
       Bug logique d'un bac à sable -> évasion -> exécution hôte.
- [ ] **pwn/authd-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/authd-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/brokerd-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/brokerd-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/cachesrv-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/cachesrv-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/heap-relay** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/keyvault-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/keyvault-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/logd-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/logd-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/meshd-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/meshd-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/parserd-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/parserd-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/relaybox-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/relaybox-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/sensorhub-heap** — 550 pts  
       Reverse d'un protocole -> overflow de tas -> shell.
- [ ] **pwn/sensorhub-uaf** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux.
- [ ] **pwn/uaf-ladder** — 550 pts  
       Use-after-free -> primitive d'écriture -> détournement de flux -> exécution.
- [ ] **pwn/authd-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/authd-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [x] **pwn/boot2root-c2** — 500 pts ✅ visible  
       **boot2root-c2** -- _Phantom Wire staging server_. During the HIVE CONSULT
- [x] **pwn/boot2root-linux** — 500 pts ✅ visible  
       **boot2root-linux** -- a full Linux box in a single per-team container. Get a
- [x] **pwn/boot2root-webapp** — 500 pts ✅ visible  
       **boot2root-webapp** -- _SnapNote_, a full Linux box in a single per-team
- [ ] **pwn/brokerd-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/brokerd-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [ ] **pwn/cachesrv-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/cachesrv-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [ ] **pwn/format-pivot** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [ ] **pwn/keyvault-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/keyvault-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [ ] **pwn/logd-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/logd-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [ ] **pwn/meshd-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/meshd-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [ ] **pwn/parserd-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/parserd-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [ ] **pwn/relaybox-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/relaybox-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [x] **pwn/ret2csu-ish** — 500 pts ✅ visible  
       **ret2csu-ish** -- a statically linked, no-PIE x86-64 binary with a stack
- [ ] **pwn/rop-diner** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/sensorhub-canary** — 500 pts  
       Fuite de canari -> overflow -> chaîne ROP -> exécution.
- [ ] **pwn/sensorhub-fmt** — 500 pts  
       Fuite d'info -> format string -> ROP -> lecture du flag.
- [x] **pwn/boot2root-ssh** — 400 pts ✅ visible  
       **boot2root-ssh.** Une box Linux complète, un conteneur par équipe. On te
- [x] **pwn/heap-note** — 350 pts ✅ visible  
       A tiny note-taking service on a **pinned glibc 2.31** (Ubuntu 20.04,
- [x] **pwn/format-string-101** — 150 pts ✅ visible  
       **format-string-101** -- a small networked service, served as

### reverse (17)

- [ ] **reverse/firmwarelet-vmesc** — 550 pts  
       Reverse d'une VM maison -> bug d'instruction -> évasion et exécution.
- [ ] **reverse/licensed-vmesc** — 550 pts  
       Reverse d'une VM maison -> bug d'instruction -> évasion et exécution.
- [ ] **reverse/packedsvc-vmesc** — 550 pts  
       Reverse d'une VM maison -> bug d'instruction -> évasion et exécution.
- [ ] **reverse/protod-vmesc** — 550 pts  
       Reverse d'une VM maison -> bug d'instruction -> évasion et exécution.
- [ ] **reverse/vm-escape** — 550 pts  
       Reverse d'une VM maison -> bug d'instruction -> évasion et exécution.
- [ ] **reverse/vmcore-vmesc** — 550 pts  
       Reverse d'une VM maison -> bug d'instruction -> évasion et exécution.
- [ ] **reverse/firmwarelet-unpack** — 500 pts  
       Dépaquetage -> bug de hook -> exécution.
- [ ] **reverse/licensed-unpack** — 500 pts  
       Dépaquetage -> bug de hook -> exécution.
- [ ] **reverse/packedsvc-unpack** — 500 pts  
       Dépaquetage -> bug de hook -> exécution.
- [ ] **reverse/protod-unpack** — 500 pts  
       Dépaquetage -> bug de hook -> exécution.
- [ ] **reverse/vmcore-unpack** — 500 pts  
       Dépaquetage -> bug de hook -> exécution.
- [ ] **reverse/firmwarelet-license** — 450 pts  
       Reverse d'un contrôle de licence -> forge -> canal admin.
- [ ] **reverse/license-forge** — 450 pts  
       Reverse d'un contrôle de licence -> forge -> déblocage d'un canal admin.
- [ ] **reverse/licensed-license** — 450 pts  
       Reverse d'un contrôle de licence -> forge -> canal admin.
- [ ] **reverse/packedsvc-license** — 450 pts  
       Reverse d'un contrôle de licence -> forge -> canal admin.
- [ ] **reverse/protod-license** — 450 pts  
       Reverse d'un contrôle de licence -> forge -> canal admin.
- [ ] **reverse/vmcore-license** — 450 pts  
       Reverse d'un contrôle de licence -> forge -> canal admin.

### supplychain (11)

- [ ] **supplychain/artifact-swap** — 500 pts  
       Provenance forgée -> substitution d'artefact -> exécution au déploiement.
- [ ] **supplychain/buildfarm-artswap** — 500 pts  
       Provenance forgée -> substitution d'artefact -> exécution au déploiement.
- [ ] **supplychain/buildfarm-postinstall** — 500 pts  
       Hook post-install -> exécution -> vol de secret.
- [ ] **supplychain/mirror-artswap** — 500 pts  
       Provenance forgée -> substitution d'artefact -> exécution au déploiement.
- [ ] **supplychain/mirror-postinstall** — 500 pts  
       Hook post-install -> exécution -> vol de secret.
- [ ] **supplychain/pkgproxy-artswap** — 500 pts  
       Provenance forgée -> substitution d'artefact -> exécution au déploiement.
- [ ] **supplychain/pkgproxy-postinstall** — 500 pts  
       Hook post-install -> exécution -> vol de secret.
- [ ] **supplychain/releaser-artswap** — 500 pts  
       Provenance forgée -> substitution d'artefact -> exécution au déploiement.
- [ ] **supplychain/releaser-postinstall** — 500 pts  
       Hook post-install -> exécution -> vol de secret.
- [ ] **supplychain/signer-artswap** — 500 pts  
       Provenance forgée -> substitution d'artefact -> exécution au déploiement.
- [ ] **supplychain/signer-postinstall** — 500 pts  
       Hook post-install -> exécution -> vol de secret.

### sysadmin (6)

- [ ] **sysadmin/auditd-systemd** — 500 pts  
       Injection d'env -> unit systemd -> sudo mal configuré -> root.
- [ ] **sysadmin/orchestrator-systemd** — 500 pts  
       Injection d'env -> unit systemd -> sudo mal configuré -> root.
- [ ] **sysadmin/provisioner-systemd** — 500 pts  
       Injection d'env -> unit systemd -> sudo mal configuré -> root.
- [ ] **sysadmin/rbac-climb** — 500 pts  
       Injection d'env -> unit systemd -> sudo mal configuré -> root.
- [ ] **sysadmin/rotatord-systemd** — 500 pts  
       Injection d'env -> unit systemd -> sudo mal configuré -> root.
- [ ] **sysadmin/schedd-systemd** — 500 pts  
       Injection d'env -> unit systemd -> sudo mal configuré -> root.

### web (19)

- [ ] **web/cms-ssrf-deser** — 500 pts  
       SSRF -> service RPC interne -> désérialisation non sûre -> exécution.
- [ ] **web/forum-protopoll** — 500 pts  
       Prototype pollution -> gadget -> exécution.
- [ ] **web/forum-ssrf-deser** — 500 pts  
       SSRF -> service RPC interne -> désérialisation non sûre -> exécution.
- [ ] **web/hrportal-protopoll** — 500 pts  
       Prototype pollution -> gadget -> exécution.
- [ ] **web/hrportal-ssrf-deser** — 500 pts  
       SSRF -> service RPC interne -> désérialisation non sûre -> exécution.
- [ ] **web/invoicer-protopoll** — 500 pts  
       Prototype pollution -> gadget -> exécution.
- [ ] **web/invoicer-ssrf-deser** — 500 pts  
       SSRF -> service RPC interne -> désérialisation non sûre -> exécution.
- [ ] **web/ledger-protopoll** — 500 pts  
       Prototype pollution -> gadget -> exécution.
- [ ] **web/ledger-ssrf-deser** — 500 pts  
       SSRF -> service RPC interne -> désérialisation non sûre -> exécution.
- [ ] **web/shipyard-protopoll** — 500 pts  
       Prototype pollution -> gadget -> exécution.
- [ ] **web/shipyard-ssrf-deser** — 500 pts  
       SSRF -> service RPC interne -> désérialisation non sûre -> exécution.
- [ ] **web/cms-uploadssrf** — 450 pts  
       Contournement d'upload -> SSRF via le rendu -> lecture metadata.
- [ ] **web/forum-uploadssrf** — 450 pts  
       Contournement d'upload -> SSRF via le rendu -> lecture metadata.
- [ ] **web/hrportal-uploadssrf** — 450 pts  
       Contournement d'upload -> SSRF via le rendu -> lecture metadata.
- [ ] **web/invoicer-uploadssrf** — 450 pts  
       Contournement d'upload -> SSRF via le rendu -> lecture metadata.
- [ ] **web/ledger-uploadssrf** — 450 pts  
       Contournement d'upload -> SSRF via le rendu -> lecture metadata.
- [ ] **web/render-pivot** — 450 pts  
       Contournement d'upload -> SSRF via le moteur de rendu -> lecture metadata interne.
- [ ] **web/shipyard-uploadssrf** — 450 pts  
       Contournement d'upload -> SSRF via le rendu -> lecture metadata.
- [x] **web/ssrf-metadata-decoy** — 350 pts ✅ visible  
       **imgproxy** is a company image-fetch proxy: give it a URL and it fetches the
