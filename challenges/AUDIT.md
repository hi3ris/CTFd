# Audit de pertinence des challenges — NCTF

Audit conduit par des relecteurs indépendants (modèle **fable**) sur **les 205 challenges jeopardy**, selon 5 axes notés 1–5 (pertinence, qualité, originalité, adéquation-difficulté, anti-triche) avec un verdict **keep / revise / cut**. Les collines KotH (`challenges/koth/`) sont hors périmètre (scorées par plugin).

## Synthèse

| verdict   | n       | %    |
| --------- | ------- | ---- |
| ✅ keep   | 180     | 88%  |
| 🛠 revise | 23      | 11%  |
| ❌ cut    | 2       | 1%   |
| **total** | **205** | 100% |

- **Note moyenne globale : 4.13/5.**
- Moyennes par axe : relevance 4.3, quality 4.55, originality 3.77, difficulty_fit 3.89, anti_cheat 4.12.
- Après retrait des **2 cut**, il reste **203 challenges** (> objectif 200). Les **revise** restent jouables mais méritent un correctif avant l'événement (voir plus bas).
- Répartition d'usage conseillée : présélection 106, finale 41, indifférent 58.

## Qualité par catégorie

| catégorie   | n   | note moy. | keep | revise | cut |
| ----------- | --- | --------- | ---- | ------ | --- |
| ai          | 12  | 4.22      | 11   | 1      | 0   |
| blockchain  | 10  | 4.52      | 10   | 0      | 0   |
| cloud       | 9   | 3.69      | 6    | 2      | 1   |
| crypto      | 13  | 4.48      | 12   | 1      | 0   |
| forensics   | 13  | 3.94      | 9    | 4      | 0   |
| hardware    | 8   | 4.4       | 8    | 0      | 0   |
| misc        | 13  | 4.38      | 13   | 0      | 0   |
| ml          | 11  | 4.36      | 11   | 0      | 0   |
| mobile      | 8   | 3.68      | 7    | 1      | 0   |
| networking  | 9   | 3.87      | 9    | 0      | 0   |
| osint       | 8   | 3.55      | 4    | 4      | 0   |
| ppc         | 9   | 4.29      | 9    | 0      | 0   |
| pwn         | 13  | 4.65      | 13   | 0      | 0   |
| reverse     | 12  | 4.57      | 12   | 0      | 0   |
| stego       | 8   | 4.12      | 8    | 0      | 0   |
| supplychain | 11  | 3.78      | 10   | 1      | 0   |
| sysadmin    | 8   | 3.48      | 4    | 4      | 0   |
| warmup      | 16  | 4.23      | 16   | 0      | 0   |
| web         | 14  | 3.63      | 8    | 5      | 1   |

## ❌ À retirer (cut)

- **`challenges/web/xxe-local`** (2.6) — The handout literally ships secret.flag containing the flag in cleartext (listed under files:), so `cat secret.flag` solves it; nothing to salvage offline, rebuild only as a served instance.
- **`challenges/cloud/mounted-chain`** (3.0) — Near-identical duplicate of sysadmin/rbac-reveal (Role/RoleBinding + double-base64 Secret.token, same solver narrative); keep rbac-reveal and cut this one unless it gets a genuinely different twist (e.g. projected SA token JWT, or cross-namespace binding).

## 🛠 À retravailler (revise)

Classés par note croissante (les plus urgents en tête).

| challenge                                         | note | correctif conseillé                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `challenges/sysadmin/mask-slip`                   | 2.4  | run.log is 13 lines with a base64 flag sitting in it (greppable via TkNURn) and the exact same masking-bypass trick is hint h3 of supplychain/poisoned-pipeline; retier to 100 beginner, pad the log to hundreds of lines and use a different transform (rev/hex/split) than poisoned-pipeline.                                                                                                                                                                     |
| `challenges/sysadmin/rotate-root`                 | 2.8  | The token file is shipped under fs/ and is the only \*.token in the bundle, so find\|cat solves a 450 hard challenge in seconds; do not ship the token, make the hook derive it from rotate.conf values (hash of CYCLE/HOSTID/secret) and retier to 150-200.                                                                                                                                                                                                        |
| `challenges/osint/ct-log-pivot`                   | 2.8  | Tagged hard/450 but the four files total 45 lines and resolver_cache.txt contains only three nctf-b32= TXT records, so base32-decoding all three (30 seconds, no CT-log reasoning) yields the flag; retier to easy/150 or make the CT-log step load-bearing (e.g. many more hosts/TXT decoys, or key the TXT decoding on the shadow hostname).                                                                                                                      |
| `challenges/web/jwt-forge`                        | 2.8  | Tagged hard/450 but the solve is 'read JWT_SECRET from config.env and run the unseal function in app.py' (5 minutes) and it duplicates flask-unsign; retier to easy (100-150) or drop one of the pair.                                                                                                                                                                                                                                                              |
| `challenges/web/mass-assignment`                  | 2.8  | Offline the is_admin gate is meaningless: the flag unseals with a constant key (b'profile-svc-admin-seal-2026') so executing me_flag() from the handout yields it without any mass assignment; needs a live instance to test the actual vuln, and 300/medium is too high.                                                                                                                                                                                           |
| `challenges/web/ssti-jinja`                       | 2.8  | Offline the SSTI is irrelevant: `python3 -c 'import app; print(app.Vault().reveal())'` prints the flag because the vault key is a constant in the handout; make it a served instance so the {{ }} payload is actually required.                                                                                                                                                                                                                                     |
| `challenges/forensics/sqlite-wal`                 | 2.8  | Tagged hard/450 yet `strings app.db \| grep NCTF` solves it (the writeup admits this); great WAL-divergence concept but store the token encoded/encrypted in the page and retier to ~200 medium.                                                                                                                                                                                                                                                                    |
| `challenges/mobile/native-xor`                    | 3.0  | Nothing native is shipped: lib/arm64-v8a/decompiled_native.c is plaintext C with SBOX and KEY, so inverting it is an easy exercise mis-tiered at 450 hard; ship an actual compiled .so (arm64 or x86-64) so Ghidra/objdump is needed, or retier to 150.                                                                                                                                                                                                             |
| `challenges/osint/entity-graph`                   | 3.0  | grep NCTF nodes.csv returns the real flag and a single decoy, so two submissions win without any graph work, and 300 pts for a 16-node/17-edge BFS is overpriced; store the note as something derived (e.g. hash/encoded per-node, or make the flag the person's value assembled from the verified path) and retier to easy/150.                                                                                                                                    |
| `challenges/cloud/imds-ssrf`                      | 3.2  | A 45-line capture where you lift SecretAccessKey and SHA256-XOR the note is a 100-150 pt beginner task, not 300 medium; retier and add noise/decoy credential responses to the log.                                                                                                                                                                                                                                                                                 |
| `challenges/cloud/sub-wildcard`                   | 3.2  | The sealing key is the sub claim sitting verbatim in oidc-token.json, so it is a one-line solve mis-tiered at 300 medium; add several captured tokens (only one satisfying StringLike) and retier to 150.                                                                                                                                                                                                                                                           |
| `challenges/sysadmin/state-secret`                | 3.2  | Great lesson (tfstate plaintext) but the vault.enc format (ENC1 + PBKDF2 + SHA256(key\|\|counter) stream) is documented nowhere in the shipped files, only in paid hint h2, so it is unsolvable from the handout; ship the data.external encrypt script or use a real tool (openssl enc/age).                                                                                                                                                                       |
| `challenges/sysadmin/vault-reuse`                 | 3.2  | Password derivation is trivial (script prints it); the 450 hard rating comes only from a fake $VAULT envelope using the same custom SHA256-counter cipher as state-secret that real ansible-vault cannot decrypt; use genuine ansible-vault AES256 format so `ansible-vault view --vault-password-file bin/get-vault-pass.sh` works, and retier to ~250.                                                                                                            |
| `challenges/supplychain/lockfile-integrity-drift` | 3.2  | Third 'package-lock + tgz, find the odd one, base64 in index.js' sibling after typosquat-lockfile and dependency-confusion, and the flag is zgrep-able in minimist-1.2.8.tgz; merge with typosquat-lockfile into one multi-step lockfile challenge or change the payload encoding and pivot.                                                                                                                                                                        |
| `challenges/crypto/ecb-echo`                      | 3.2  | The log pre-computes each step's target block and full candidate map, so it degrades to a table lookup rather than the byte-at-a-time ECB attack; drop the candidates map and re-tier off 450/hard.                                                                                                                                                                                                                                                                 |
| `challenges/osint/cred-reuse`                     | 3.2  | The admin_portal.enc scheme (XOR with sha256(pass\|\|counter_be32) keystream) is a home-made construction that nothing in the artifacts reveals, so the challenge is unsolvable without buying the 45-pt h3 hint; either state the scheme in the description or switch to a standard container (openssl enc / password-protected zip / GPG), and note it duplicates device-backup-geo's exact keystream trick and is more password-cracking than OSINT.             |
| `challenges/osint/device-backup-geo`              | 3.2  | Good SMS<->GPS correlation idea, but the note cipher (XOR with sha256("{lat:.6f},{lon:.6f}"\|\|counter) keystream) and the exact key string format are stated nowhere in the backup, so only the 60-pt h3 hint makes it solvable; embed the key-format convention in the data (e.g. an app config table or a message saying the note is locked with the RDV coordinates) or use a standard cipher, and drop the duplicated sha256-CTR trick shared with cred-reuse. |
| `challenges/web/flask-unsign`                     | 3.2  | Same recipe as jwt-forge (hardcoded secret -> re-sign -> XOR-unseal with sha256(secret\|tag)); offline the forgery is theatre because anyone can call the unseal code with the shipped key, so either serve it live or merge with jwt-forge and retier to easy.                                                                                                                                                                                                     |
| `challenges/forensics/icmp-beacon`                | 3.2  | Near-duplicate of http-body-exfil and dns-exfil (sort by icmp.seq, take a byte); either lower to 150 easy or add a real twist (e.g. bytes spread over TTL/ID fields or a checksum) so it is not a third copy of the same mechanic.                                                                                                                                                                                                                                  |
| `challenges/web/sqlite-union`                     | 3.4  | 'strings shop.db \| grep NCTF' returns the flag, so no SQL injection is needed; serve it live or seal the secret row (e.g. store it encoded and require the UNION to reach a key column).                                                                                                                                                                                                                                                                           |
| `challenges/forensics/png-magic-fix`              | 3.4  | `strings evidence.png` prints the flag from the uncompressed tEXt chunk, so repairing the signature is never needed; move the flag into a zTXt/iTXt (compressed) chunk or render it in the pixels.                                                                                                                                                                                                                                                                  |
| `challenges/forensics/zip-carve`                  | 3.4  | Hidden member is STORED (uncompressed), so `strings archive.zip` prints the flag with no carving; deflate the orphaned member so the local header must actually be parsed.                                                                                                                                                                                                                                                                                          |
| `challenges/ai/agent-tool-abuse`                  | 4.4  | Near-duplicate of ai3-tool-abuse (confused-deputy indirect prompt injection driving a privileged tool effect); ship only one per event or add a distinguishing twist beyond the two-agent A2A dressing.                                                                                                                                                                                                                                                             |

## Thèmes transversaux (relevés par plusieurs relecteurs)

1. **Sur-cotation de difficulté** — plusieurs épreuves étiquetées `hard/450` se résolvent en une passe (ex. `ecb-echo`, `sqlite-wal`, `rotate-root`, `native-xor`, `dtmf-dial`, `layered-png`, `oracle-multi-turn`). Réaligner `value/decay/minimum` sur l'effort réel.
2. **Flag grepable / anti-triche faible** — certaines épreuves _statiques_ laissent le flag récupérable sans l'exploit voulu (`strings`/`grep -a` dans l'archive ou la clé de scellement en clair) : côté web surtout (`xxe-local` [cut], `sqlite-union`, `ssti-jinja`, `jwt-forge`/`flask-unsign`) et quelques archives (`mask-slip`, `lockfile-integrity-drift`, `sub-wildcard`). → **servir en conteneur** (type `team_instance`) ou re-sceller le secret.
3. **Schéma de chiffrement maison non documenté** — `state-secret`, `vault-reuse`, `cred-reuse`, `device-backup-geo` utilisent un keystream SHA256-XOR décrit nulle part dans le handout → injouable sans l'indice payant. Documenter le format ou utiliser un conteneur standard (openssl/age/zip/gpg).
4. **Réplication de mécanique** (à espacer entre les manches, pas à retirer) — familles LSB stego, VMs bytecode en reverse, boot2root pwn, gabarit « tags triés = flag » en networking, enveloppe « SHA256-keystream XOR » en ppc/cloud/mobile. Ne pas programmer plusieurs quasi-jumeaux dans la même manche.
5. **Doublons quasi-identiques** — `cloud/mounted-chain` ≈ `sysadmin/rbac-reveal` (cut retenu sur le premier) ; `ai/agent-tool-abuse` ≈ `ai3-tool-abuse` (garder un seul par événement).

## Conclusion

Le lot est **globalement solide** (moyenne 4.13/5, 88% en keep direct, seulement 2 à retirer). Les correctifs prioritaires avant le J-1 : (a) **servir** les épreuves web dont l'exploit n'a de sens qu'en ligne, (b) **re-tiérer** les épreuves sur-cotées, (c) **documenter/standardiser** les schémas de chiffrement maison. La couverture par catégorie est large (19 catégories) et l'équilibre présélection/finale est exploitable tel quel.

## Corrections appliquées (post-audit)

Toutes les corrections de l'audit ont été appliquées et re-vérifiées (chaque solveur re-testé contre l'artefact livré).

**2 cut (retirés) :**

- `web/xxe-local` — flag livré en clair, à reconstruire en instance servie.
- `cloud/mounted-chain` — doublon de `sysadmin/rbac-reveal`.

**6 re-tiérages (scoring aligné sur l'effort réel) :** `cloud/imds-ssrf`, `forensics/icmp-beacon`, `mobile/native-xor`, `osint/ct-log-pivot`, `web/jwt-forge`, `web/flask-unsign` → easy.

**16 reseals / documentations / régénérations :**

- Anti-triche (flag rendu non-`grep`-able, technique redevenue nécessaire) : `forensics/png-magic-fix` (zTXt compressé), `forensics/zip-carve` (membre DEFLATE), `forensics/sqlite-wal` (token base64+XOR, ->medium), `osint/entity-graph` (flag dérivé par HMAC du chemin BFS, ->easy), `web/sqlite-union` / `web/ssti-jinja` / `web/mass-assignment` (scellés — technique porteuse hors-ligne), `sysadmin/mask-slip` (fuite hex, ->beginner), `sysadmin/rotate-root` (token dérivé, non livré, ->medium), `cloud/sub-wildcard` (5 tokens, politique porteuse, ->easy), `supplychain/lockfile-integrity-drift` (flag XOR après le membre gzip), `crypto/ecb-echo` (map de candidats retirée, vraie attaque byte-à-byte, ->medium).
- Solvabilité / crypto standardisée : `osint/cred-reuse` (conteneur openssl AES-256-CBC), `osint/device-backup-geo` (convention de clé embarquée dans le backup), `sysadmin/state-secret` (script `encrypt.py` documenté livré), `sysadmin/vault-reuse` (vrai `$ANSIBLE_VAULT` AES256).

**1 laissé (choix opérationnel) :** `ai/agent-tool-abuse` — quasi-doublon de `ai3-tool-abuse` ; les deux sont valides (servis), l'organisateur en programme un seul par manche. Pas un défaut de code.

**État final : 203 challenges** (205 − 2 cut), tous solvables et re-vérifiés.
