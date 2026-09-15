# Index des writeups — NCTF

**205 challenges** répartis sur **19 catégories**. Chaque challenge servi/statique a son writeup dans son dossier `solution/`.

> Les collines King-of-the-Hill (`challenges/koth/`) sont scorées par le plugin `koth` (Awards) et ne figurent pas dans ce tableau jeopardy ; voir `deploy/koth-ops.md`.

## ai (12)

| challenge                 | pts | type          | writeup                                         | résumé                                                                     |
| ------------------------- | --- | ------------- | ----------------------------------------------- | -------------------------------------------------------------------------- |
| `agent-tool-abuse`        | 500 | team_instance | [writeup](ai/agent-tool-abuse/solution/)        | Halcyon Vault Co. runs a two-agent automation. You chat with RELAY,        |
| `ai0-leaked-transcript`   | 100 | dynamic       | [writeup](ai/ai0-leaked-transcript/solution/)   | HelixDesk is Nimbus Robotics' internal support assistant. Someone          |
| `ai1-naive-guard`         | 300 | team_instance | [writeup](ai/ai1-naive-guard/solution/)         | Level 1 of the AI track. Nimbus Robotics wired up a quick support          |
| `ai2-output-filter`       | 350 | team_instance | [writeup](ai/ai2-output-filter/solution/)       | LEVEL 2 of the AI track. Same guard backend as Level 1 (a naive persona    |
| `ai3-tool-abuse`          | 500 | team_instance | [writeup](ai/ai3-tool-abuse/solution/)          | Level 3 of the AI track -- the heaviest. Meridian Freight runs an internal |
| `oracle-canary-decoy`     | 300 | dynamic       | [writeup](ai/oracle-canary-decoy/solution/)     | ChannelBot ships as oracle.py (respond(prompt)). Ask it for the flag       |
| `oracle-doc-injection`    | 300 | dynamic       | [writeup](ai/oracle-doc-injection/solution/)    | SummarizerBot ships as oracle.py (respond(prompt)). It summarises a        |
| `oracle-encoding-smuggle` | 100 | dynamic       | [writeup](ai/oracle-encoding-smuggle/solution/) | SentinelBot is an offline support assistant shipped as a single Python     |
| `oracle-fake-system`      | 150 | dynamic       | [writeup](ai/oracle-fake-system/solution/)      | PolicyBot guards a vault token and ships as oracle.py with a               |
| `oracle-multi-turn`       | 450 | dynamic       | [writeup](ai/oracle-multi-turn/solution/)       | WardenBot ships as oracle.py with a Session class (and a respond           |
| `oracle-reverse-emit`     | 150 | dynamic       | [writeup](ai/oracle-reverse-emit/solution/)     | RedactBot ships as oracle.py with a respond(prompt) entry point. It        |
| `oracle-tool-args`        | 300 | dynamic       | [writeup](ai/oracle-tool-args/solution/)        | ToolBot ships as oracle.py (respond(prompt)) and exposes a                 |

## blockchain (10)

| challenge         | pts | type          | writeup                                         | résumé                                                               |
| ----------------- | --- | ------------- | ----------------------------------------------- | -------------------------------------------------------------------- |
| `airdrop-forge`   | 300 | dynamic       | [writeup](blockchain/airdrop-forge/solution/)   | You get a Merkle-root airdrop contract (MerkleAirdrop.sol) and       |
| `allowance-drift` | 150 | dynamic       | [writeup](blockchain/allowance-drift/solution/) | You get a hand-rolled ERC20 (DriftToken.sol) and token_state.json    |
| `block-oracle`    | 150 | dynamic       | [writeup](blockchain/block-oracle/solution/)    | A lottery seals its pot for whoever guesses the winning ticket. You  |
| `calldata-cache`  | 100 | dynamic       | [writeup](blockchain/calldata-cache/solution/)  | You captured one transaction's raw calldata (calldata.txt) and the   |
| `origin-story`    | 300 | dynamic       | [writeup](blockchain/origin-story/solution/)    | You get Vault.sol and vault.json (a sealed note cipher_hex plus      |
| `overflow-mint`   | 300 | dynamic       | [writeup](blockchain/overflow-mint/solution/)   | You get the Solidity source of a token pre-sale (MintSale.sol) and   |
| `private-ledger`  | 150 | dynamic       | [writeup](blockchain/private-ledger/solution/)  | You are handed the Solidity source of an on-chain ledger and a raw   |
| `proxy-collision` | 300 | dynamic       | [writeup](blockchain/proxy-collision/solution/) | You get an upgradeable Proxy.sol, its Logic.sol implementation, and  |
| `reentrant-vault` | 450 | team_instance | [writeup](blockchain/reentrant-vault/solution/) | Reentrant Vault. (nouvelle catégorie : blockchain / EVM)             |
| `replay-signer`   | 450 | dynamic       | [writeup](blockchain/replay-signer/solution/)   | You captured two withdrawal requests signed by the same treasury key |

## cloud (9)

| challenge         | pts | type          | writeup                                    | résumé                                                                      |
| ----------------- | --- | ------------- | ------------------------------------------ | --------------------------------------------------------------------------- |
| `breach-chain`    | 450 | team_instance | [writeup](cloud/breach-chain/solution/)    | Kékéli Cloud. Le service de prévisualisation média de Kékéli Cloud tourne   |
| `gcp-token-scope` | 300 | dynamic       | [writeup](cloud/gcp-token-scope/solution/) | A leaked GCP service-account key (sa-key.json) for a CI helper, the project |
| `imds-ssrf`       | 300 | dynamic       | [writeup](cloud/imds-ssrf/solution/)       | A proxy capture of an SSRF exploit against an EC2-hosted preview service    |
| `leaky-prefix`    | 100 | dynamic       | [writeup](cloud/leaky-prefix/solution/)    | A snapshot of the kekeli-media-prod S3 bucket: its live bucket policy       |
| `mounted-chain`   | 150 | dynamic       | [writeup](cloud/mounted-chain/solution/)   | A dump of the kekeli Kubernetes namespace: a ServiceAccount, a Role, a      |
| `passrole-ladder` | 450 | dynamic       | [writeup](cloud/passrole-ladder/solution/) | An IAM dump from an AWS account: users (iam-users.json), roles              |
| `sas-forge`       | 450 | dynamic       | [writeup](cloud/sas-forge/solution/)       | An Azure Storage account key leaked into a backup (leaked-account-key.txt), |
| `sub-wildcard`    | 300 | dynamic       | [writeup](cloud/sub-wildcard/solution/)    | The ci-deployer IAM role trusts GitHub Actions via OIDC. You have its trust |
| `trail-of-keys`   | 300 | dynamic       | [writeup](cloud/trail-of-keys/solution/)   | A CloudTrail export (cloudtrail.json) from one busy hour on the             |

## crypto (13)

| challenge             | pts | type          | writeup                                         | résumé                                                                        |
| --------------------- | --- | ------------- | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| `affine-relay`        | 100 | dynamic       | [writeup](crypto/affine-relay/solution/)        | We intercepted a single scrambled memo, cipher.txt. The courier ran every     |
| `commit-bias`         | 300 | dynamic       | [writeup](crypto/commit-bias/solution/)         | The CoinVault table runs a "provably fair" coin-flip game. Every round the    |
| `ecb-echo`            | 450 | dynamic       | [writeup](crypto/ecb-echo/solution/)            | We tapped a device that encrypts data for us on request and logged everything |
| `fermat-twins`        | 150 | dynamic       | [writeup](crypto/fermat-twins/solution/)        | A 1024-bit RSA public key pubkey.pem and a hex ciphertext ciphertext.txt.     |
| `glue-and-extend`     | 450 | dynamic       | [writeup](crypto/glue-and-extend/solution/)     | A gateway seals payloads under a key derived from a shared secret and the     |
| `keystream-reuse`     | 300 | dynamic       | [writeup](crypto/keystream-reuse/solution/)     | messages.txt holds 25 intercepted ciphertexts, one hex string per line. They  |
| `lcg-casino`          | 500 | team_instance | [writeup](crypto/lcg-casino/solution/)          | A "provably fair" casino deals from a home-grown verifiable shuffle. It       |
| `modulus-siblings`    | 300 | dynamic       | [writeup](crypto/modulus-siblings/solution/)    | Two departments encrypted the very same memo for the same recipient, and we   |
| `nonce-sense`         | 150 | dynamic       | [writeup](crypto/nonce-sense/solution/)         | A hardware signing device produced a batch of ECDSA signatures over           |
| `padding-oracle-lite` | 350 | team_instance | [writeup](crypto/padding-oracle-lite/solution/) | A decommissioned session service still answers on its own home-grown binary   |
| `tlv-vault`           | 350 | dynamic       | [writeup](crypto/tlv-vault/solution/)           | We recovered eight .vlt archives from a decommissioned "vault" service,       |
| `twister-tell`        | 300 | dynamic       | [writeup](crypto/twister-tell/solution/)        | A token service leaked a run of its random number generator's raw 32-bit      |
| `vigenere-drift`      | 150 | dynamic       | [writeup](crypto/vigenere-drift/solution/)      | cipher.txt is an intercepted English memorandum enciphered with a repeating   |

## forensics (13)

| challenge          | pts | type    | writeup                                         | résumé                                                                         |
| ------------------ | --- | ------- | ----------------------------------------------- | ------------------------------------------------------------------------------ |
| `Audio FSK`        | 500 | dynamic | [writeup](forensics/audio-fsk/solution/)        | Nous avons intercepté une courte liaison descendante RF et enregistré la bande |
| `DNS Exfil`        | 300 | dynamic | [writeup](forensics/dns-exfil/solution/)        | Notre EDR a signalé un « agent de synchronisation » sur le poste d'un          |
| `Evasion Timeline` | 400 | dynamic | [writeup](forensics/evasion-timeline/solution/) | L'EDR d'un poste de la finance est resté silencieux pendant une tempête        |
| `SRAM Retention`   | 350 | dynamic | [writeup](forensics/sram-retention/solution/)   | Nous avons extrait un vidage mémoire d'un microcontrôleur Aetheris AE-32       |
| `USB Keystrokes`   | 150 | dynamic | [writeup](forensics/usb-keystrokes/solution/)   | Nous avons mis sur écoute le bus USB pendant qu'un collègue se connectait au   |
| `auth-timeline`    | 150 | dynamic | [writeup](forensics/auth-timeline/solution/)    | A public-facing server was compromised overnight. All we salvaged before the   |
| `gzip-tar-nest`    | 150 | dynamic | [writeup](forensics/gzip-tar-nest/solution/)    | A "parcel" (parcel.tar.gz) was intercepted leaving the network. It looks       |
| `http-body-exfil`  | 300 | dynamic | [writeup](forensics/http-body-exfil/solution/)  | A workstation kept "phoning home" to a metrics endpoint that our asset         |
| `icmp-beacon`      | 300 | dynamic | [writeup](forensics/icmp-beacon/solution/)      | During an incident, an analyst noticed a host on the network that "just would  |
| `mem-struct`       | 300 | dynamic | [writeup](forensics/mem-struct/solution/)       | We captured a raw memory dump (memdump.bin) from a process that was holding a  |
| `png-magic-fix`    | 100 | dynamic | [writeup](forensics/png-magic-fix/solution/)    | A screenshot was pulled from a suspect's machine, but the file (evidence.png)  |
| `sqlite-wal`       | 450 | dynamic | [writeup](forensics/sqlite-wal/solution/)       | We seized an application's SQLite database (app.db) plus its sidecar file      |
| `zip-carve`        | 150 | dynamic | [writeup](forensics/zip-carve/solution/)        | We recovered a ZIP archive (archive.zip) from a departing employee's USB       |

## hardware (8)

| challenge        | pts | type    | writeup                                      | résumé                                                                       |
| ---------------- | --- | ------- | -------------------------------------------- | ---------------------------------------------------------------------------- |
| `boot-rom`       | 450 | dynamic | [writeup](hardware/boot-rom/solution/)       | rom.bin is the boot ROM of a tiny custom 8-bit processor. ISA.md documents   |
| `firmware-blob`  | 150 | dynamic | [writeup](hardware/firmware-blob/solution/)  | We pulled firmware.bin off a device's flash chip. It starts with a small     |
| `i2c-sniff`      | 300 | dynamic | [writeup](hardware/i2c-sniff/solution/)      | We clipped a two-wire probe onto an I2C bus and captured SCL and SDA while   |
| `intel-hex`      | 100 | dynamic | [writeup](hardware/intel-hex/solution/)      | image.hex is a dump of a microcontroller's memory in a common text hex       |
| `manchester-ook` | 300 | dynamic | [writeup](hardware/manchester-ook/solution/) | We recorded the demodulated envelope of a short 433 MHz on-off-keyed burst.  |
| `spi-eeprom`     | 150 | dynamic | [writeup](hardware/spi-eeprom/solution/)     | A logic analyzer captured the four SPI lines (CS, CLK, MOSI, MISO)           |
| `uart-capture`   | 100 | dynamic | [writeup](hardware/uart-capture/solution/)   | We tapped a serial line with a logic analyzer and dumped the samples to      |
| `vcd-fsm`        | 300 | dynamic | [writeup](hardware/vcd-fsm/solution/)        | trace.vcd is a Value Change Dump exported from a simulation of a small state |

## misc (13)

| challenge           | pts | type          | writeup                                     | résumé                                                                       |
| ------------------- | --- | ------------- | ------------------------------------------- | ---------------------------------------------------------------------------- |
| `Heartbeat`         | 300 | dynamic       | [writeup](misc/timing-channel/solution/)    | A status agent on an isolated segment "phones home" to a collector with a    |
| `brainfuck-cascade` | 300 | dynamic       | [writeup](misc/brainfuck-cascade/solution/) | All we recovered is one line of dense ASCII (cipher.txt). It decodes to      |
| `chunk-hunt`        | 150 | dynamic       | [writeup](misc/chunk-hunt/solution/)        | Someone exported a company badge as a PNG (badge.png). The picture itself is |
| `dfa-oracle`        | 300 | dynamic       | [writeup](misc/dfa-oracle/solution/)        | automaton.json describes a deterministic finite automaton: an alphabet, a    |
| `esolang-jail`      | 400 | team_instance | [writeup](misc/esolang-jail/solution/)      | Marble jail -- a tiny stack esoteric language, served over TCP as an         |
| `gf2-cipher`        | 450 | dynamic       | [writeup](misc/gf2-cipher/solution/)        | system.json gives you a square binary matrix A and a bit vector b. There     |
| `git-archaeology`   | 100 | dynamic       | [writeup](misc/git-archaeology/solution/)   | Our intern force-pushed away a mistake. "It's gone," they said.              |
| `json-sift`         | 100 | dynamic       | [writeup](misc/json-sift/solution/)         | We dumped 5000 telemetry events into a single JSON array (telemetry.json).   |
| `pbkdf2-crack`      | 150 | dynamic       | [writeup](misc/pbkdf2-crack/solution/)      | We pulled one account's password record out of a leaked database             |
| `polyglot-onion`    | 250 | dynamic       | [writeup](misc/polyglot-onion/solution/)    | A courier dropped off a single file and nothing else. It opens as an         |
| `proto-fuzz`        | 350 | team_instance | [writeup](misc/proto-fuzz/solution/)        | proto-fuzz -- a tiny home-grown line protocol, FZLP/1, served over           |
| `spreadsheet-audit` | 150 | dynamic       | [writeup](misc/spreadsheet-audit/solution/) | A finance intern swears the quarterly ledger (ledger.xlsx) is "just sales    |
| `wire-tap`          | 300 | dynamic       | [writeup](misc/wire-tap/solution/)          | We captured a single serialized message off the wire (message.bin) but the   |

## ml (11)

| challenge          | pts | type          | writeup                                  | résumé                                                                         |
| ------------------ | --- | ------------- | ---------------------------------------- | ------------------------------------------------------------------------------ |
| `adv-flip`         | 450 | dynamic       | [writeup](ml/adv-flip/solution/)         | gate.npz ships a linear gate: weights w, bias b, and one base input            |
| `adversarial-gate` | 500 | team_instance | [writeup](ml/adversarial-gate/solution/) | SENTRY-6 badge gate. An access gate runs a small convolutional                 |
| `embedding-nn`     | 150 | dynamic       | [writeup](ml/embedding-nn/solution/)     | embed_table.npz holds a token embedding table and a batch of query vectors.    |
| `grad-leak`        | 300 | dynamic       | [writeup](ml/grad-leak/solution/)        | During distributed training a worker leaked the gradients from a single step.  |
| `member-ids`       | 150 | dynamic       | [writeup](ml/member-ids/solution/)       | shadow_eval.npz is an evaluation table for a model: for each record it lists   |
| `model-inversion`  | 500 | team_instance | [writeup](ml/model-inversion/solution/)  | AEGIS-VAULT recall service. The vault has memorised one sealed record --       |
| `pickle-rce`       | 350 | team_instance | [writeup](ml/pickle-rce/solution/)       | ModelHub is a model registry. Teams upload a serialized model and the          |
| `poison-shift`     | 300 | dynamic       | [writeup](ml/poison-shift/solution/)     | poisoned_train.npz is a regression training set: features X, targets y,        |
| `surrogate-fit`    | 300 | dynamic       | [writeup](ml/surrogate-fit/solution/)    | A hidden model is a black box: you feed it a vector, it returns a number.      |
| `tree-path`        | 100 | dynamic       | [writeup](ml/tree-path/solution/)        | We recovered a trained binary decision tree from a classifier and dumped it to |
| `trojan-trigger`   | 450 | dynamic       | [writeup](ml/trojan-trigger/solution/)   | detector.npz ships a hidden "detector" unit that scores an input with          |

## mobile (8)

| challenge            | pts | type    | writeup                                        | résumé                                                                       |
| -------------------- | --- | ------- | ---------------------------------------------- | ---------------------------------------------------------------------------- |
| `deeplink-guard`     | 300 | dynamic | [writeup](mobile/deeplink-guard/solution/)     | VaultApp.ipa registers a custom URL scheme and unlocks a "grant" screen only |
| `keystore-alias`     | 450 | dynamic | [writeup](mobile/keystore-alias/solution/)     | entvault.apk ships a custom keystore blob (assets/vault.keystore) holding    |
| `native-xor`         | 450 | dynamic | [writeup](mobile/native-xor/solution/)         | nativegame.apk validates its flag in a bundled native library. We recovered  |
| `obfuscated-strings` | 150 | dynamic | [writeup](mobile/obfuscated-strings/solution/) | app.apk from the StashBox app builds a license string at runtime instead of  |
| `prefs-vault`        | 300 | dynamic | [writeup](mobile/prefs-vault/solution/)        | A backup of the QuickNotes app includes its SharedPreferences and the        |
| `root-gate`          | 150 | dynamic | [writeup](mobile/root-gate/solution/)          | securebank.apk refuses to show its unlock code on rooted devices. We do not  |
| `strings-goldmine`   | 100 | dynamic | [writeup](mobile/strings-goldmine/solution/)   | We pulled app-release.apk off a payments handset. Unzip it like any APK and  |
| `webview-bridge`     | 300 | dynamic | [writeup](mobile/webview-bridge/solution/)     | hybridshop.apk is a hybrid app: a WebView front-end talks to a native        |

## networking (9)

| challenge         | pts | type    | writeup                                         | résumé                                                                        |
| ----------------- | --- | ------- | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| `acl-firewall`    | 150 | dynamic | [writeup](networking/acl-firewall/solution/)    | You are handed a firewall's access-control list and a batch of candidate      |
| `bgp-bestpath`    | 150 | dynamic | [writeup](networking/bgp-bestpath/solution/)    | A router's incoming BGP table (bgp_rib.json) lists several candidate routes   |
| `dns-chain`       | 300 | dynamic | [writeup](networking/dns-chain/solution/)       | A single DNS response was captured as raw bytes (message.bin, with            |
| `eui64-slaac`     | 100 | dynamic | [writeup](networking/eui64-slaac/solution/)     | A stateless address-autoconfig (SLAAC) inventory (hosts.json) lists 29        |
| `framed-protocol` | 300 | dynamic | [writeup](networking/framed-protocol/solution/) | We captured the raw byte stream of an in-house application protocol           |
| `netflow-talker`  | 300 | dynamic | [writeup](networking/netflow-talker/solution/)  | A NetFlow collector exported a batch of flow records (flows.csv): one row per |
| `subnet-reach`    | 300 | dynamic | [writeup](networking/subnet-reach/solution/)    | You have a router's forwarding table and a batch of probe packets             |
| `tcp-reassembly`  | 450 | dynamic | [writeup](networking/tcp-reassembly/solution/)  | We logged one direction of a TCP conversation as a list of segments           |
| `tls-sni`         | 300 | dynamic | [writeup](networking/tls-sni/solution/)         | A single TLS ClientHello was captured as raw bytes (clienthello.bin, with     |

## osint (8)

| challenge            | pts | type    | writeup                                       | résumé                                                                        |
| -------------------- | --- | ------- | --------------------------------------------- | ----------------------------------------------------------------------------- |
| `cred-reuse`         | 300 | dynamic | [writeup](osint/cred-reuse/solution/)         | Un forum communautaire togolais a été piraté et sa base de comptes            |
| `ct-log-pivot`       | 450 | dynamic | [writeup](osint/ct-log-pivot/solution/)       | Reconnaissance sur le domaine cert.tg. On vous remet la zone DNS publique     |
| `device-backup-geo`  | 450 | dynamic | [writeup](osint/device-backup-geo/solution/)  | Saisie d'un téléphone : la sauvegarde exportée contient plusieurs bases       |
| `doc-metadata`       | 150 | dynamic | [writeup](osint/doc-metadata/solution/)       | Six communiqués « officiels » (.docx) ont fuité. Ils sont tous signés         |
| `entity-graph`       | 300 | dynamic | [writeup](osint/entity-graph/solution/)       | Le CERT.tg a exporté son graphe d'enquête sur la fuite de données de la       |
| `exif-triangulation` | 300 | dynamic | [writeup](osint/exif-triangulation/solution/) | Quatre guetteurs ont photographié la même cible depuis des points différents. |
| `social-export`      | 150 | dynamic | [writeup](osint/social-export/solution/)      | Deux exports de comptes ont été saisis chez un suspect : un export Telegram   |
| `wayback-diff`       | 300 | dynamic | [writeup](osint/wayback-diff/solution/)       | Voici cinq captures archivées de la page d'accueil d'un portail, prises à des |

## ppc (9)

| challenge          | pts | type    | writeup                                   | résumé                                                                     |
| ------------------ | --- | ------- | ----------------------------------------- | -------------------------------------------------------------------------- |
| `congruence-vault` | 450 | dynamic | [writeup](ppc/congruence-vault/solution/) | system.txt starts with a CIPHER blob, then lists 160 lines of three        |
| `dijkstra-relay`   | 300 | dynamic | [writeup](ppc/dijkstra-relay/solution/)   | graph.txt describes a directed weighted graph: a header with node/edge     |
| `hull-cipher`      | 150 | dynamic | [writeup](ppc/hull-cipher/solution/)      | points.txt lists a few hundred 2-D points, each tagged with a single       |
| `knapsack-locker`  | 300 | dynamic | [writeup](ppc/knapsack-locker/solution/)  | items.txt gives a capacity, a list of items (each with a weight and a      |
| `life-decode`      | 450 | dynamic | [writeup](ppc/life-decode/solution/)      | grid.txt gives a board size and a step count, a CIPHER blob, and an        |
| `semiprime-sweep`  | 300 | dynamic | [writeup](ppc/semiprime-sweep/solution/)  | semiprimes.txt starts with a CIPHER blob and then lists several dozen      |
| `stack-vm`         | 300 | dynamic | [writeup](ppc/stack-vm/solution/)         | program.txt is source code for a tiny made-up machine: one instruction per |
| `sudoku-vault`     | 450 | dynamic | [writeup](ppc/sudoku-vault/solution/)     | puzzle.txt holds a CIPHER blob and a 9x9 Sudoku grid (0 marks an empty     |
| `z-locator`        | 150 | dynamic | [writeup](ppc/z-locator/solution/)        | data.txt has a short pattern on line 1 and a large blob of text on line 2. |

## pwn (13)

| challenge            | pts | type          | writeup                                     | résumé                                                                       |
| -------------------- | --- | ------------- | ------------------------------------------- | ---------------------------------------------------------------------------- |
| `boot2root-c2`       | 500 | team_instance | [writeup](pwn/boot2root-c2/solution/)       | boot2root-c2 -- Phantom Wire staging server. During the HIVE CONSULT         |
| `boot2root-linux`    | 500 | team_instance | [writeup](pwn/boot2root-linux/solution/)    | boot2root-linux -- a full Linux box in a single per-team container. Get a    |
| `boot2root-ssh`      | 400 | team_instance | [writeup](pwn/boot2root-ssh/solution/)      | boot2root-ssh. Une box Linux complète, un conteneur par équipe. On te        |
| `boot2root-webapp`   | 500 | team_instance | [writeup](pwn/boot2root-webapp/solution/)   | boot2root-webapp -- SnapNote, a full Linux box in a single per-team          |
| `bss-admin-flip`     | 150 | dynamic       | [writeup](pwn/bss-admin-flip/solution/)     | You are given a single x86-64 Linux binary, chall. It asks you to register a |
| `fmt-key-leak`       | 300 | dynamic       | [writeup](pwn/fmt-key-leak/solution/)       | You are given a single x86-64 Linux binary, chall. It echoes a line you type |
| `format-string-101`  | 150 | team_instance | [writeup](pwn/format-string-101/solution/)  | format-string-101 -- a small networked service, served as                    |
| `heap-note`          | 350 | team_instance | [writeup](pwn/heap-note/solution/)          | A tiny note-taking service on a pinned glibc 2.31 (Ubuntu 20.04,             |
| `off-by-one-auth`    | 150 | dynamic       | [writeup](pwn/off-by-one-auth/solution/)    | You are given a single x86-64 Linux binary, chall. It asks how many bytes    |
| `ret2csu-ish`        | 500 | team_instance | [writeup](pwn/ret2csu-ish/solution/)        | ret2csu-ish -- a statically linked, no-PIE x86-64 binary with a stack        |
| `ret2win-keyed`      | 300 | dynamic       | [writeup](pwn/ret2win-keyed/solution/)      | You are given a single x86-64 Linux binary, chall. It prints a token that    |
| `shellcode-decoder`  | 300 | dynamic       | [writeup](pwn/shellcode-decoder/solution/)  | You are given a single x86-64 Linux binary, chall. It prints a couple of     |
| `stack-smash-reveal` | 100 | dynamic       | [writeup](pwn/stack-smash-reveal/solution/) | You are given a single x86-64 Linux binary, chall. It reads some input and   |

## reverse (12)

| challenge        | pts | type    | writeup                                     | résumé                                                                       |
| ---------------- | --- | ------- | ------------------------------------------- | ---------------------------------------------------------------------------- |
| `byte-drift`     | 100 | dynamic | [writeup](reverse/byte-drift/solution/)     | We recovered a small lock program, chall. It asks for a passphrase and       |
| `crc-forge`      | 300 | dynamic | [writeup](reverse/crc-forge/solution/)      | chall is a stripped x86-64 ELF. It reads a flag and answers "checksums       |
| `java-cafe`      | 300 | dynamic | [writeup](reverse/java-cafe/solution/)      | We recovered Vault.class, a compiled Java class. Run it with java Vault      |
| `keygen-me`      | 450 | dynamic | [writeup](reverse/keygen-me/solution/)      | chall is a stripped x86-64 "ACME license validator". Give it a license key   |
| `maze-vm`        | 500 | dynamic | [writeup](reverse/maze-vm/solution/)        | We recovered a small self-contained "gate" binary, chall. It refuses to      |
| `packed-vm-lite` | 350 | dynamic | [writeup](reverse/packed-vm-lite/solution/) | We pulled a small license checker, vmcheck, off an embedded device. When you |
| `pyc-ghost`      | 300 | dynamic | [writeup](reverse/pyc-ghost/solution/)      | We recovered vault.pyc, a compiled Python module. Run it and it asks for the |
| `shell-lock`     | 150 | dynamic | [writeup](reverse/shell-lock/solution/)     | lock.sh is a small self-decrypting shell script. Run it with the right       |
| `stack-vm`       | 300 | dynamic | [writeup](reverse/stack-vm/solution/)       | chall is a stripped x86-64 ELF. It asks for a key and either rejects it or   |
| `strings-lie`    | 150 | dynamic | [writeup](reverse/strings-lie/solution/)    | We recovered a tiny "secret vault" binary, chall. Run it and it happily      |
| `synthvm`        | 500 | dynamic | [writeup](reverse/synthvm/solution/)        | We pulled a "license core", synthvm, off a device. Enter the key it accepts  |
| `triple-wrap`    | 150 | dynamic | [writeup](reverse/triple-wrap/solution/)    | chall is a stripped x86-64 ELF that checks a flag. Run it and it prints a    |

## stego (8)

| challenge         | pts | type    | writeup                                    | résumé                                                                        |
| ----------------- | --- | ------- | ------------------------------------------ | ----------------------------------------------------------------------------- |
| `dtmf-dial`       | 450 | dynamic | [writeup](stego/dtmf-dial/solution/)       | We recorded someone dialling a phone and saved it as dial.wav. It is just a   |
| `layered-png`     | 450 | dynamic | [writeup](stego/layered-png/solution/)     | layers.png is a plain RGB gradient — or so it appears. The name is a hint     |
| `lsb-bmp`         | 100 | dynamic | [writeup](stego/lsb-bmp/solution/)         | A friend mailed us this bitmap postcard and swears there is more to it than a |
| `png-text-chunk`  | 150 | dynamic | [writeup](stego/png-text-chunk/solution/)  | Someone shared this sunset.png with a suspiciously chatty set of properties.  |
| `trailing-zip`    | 100 | dynamic | [writeup](stego/trailing-zip/solution/)    | This banner.bmp opens fine in any image viewer, but its file size seems far   |
| `twin-palette`    | 300 | dynamic | [writeup](stego/twin-palette/solution/)    | mosaic.png is a small blocky picture built from a colour palette. It looks    |
| `wav-lsb`         | 300 | dynamic | [writeup](stego/wav-lsb/solution/)         | A short audio clip, tone.wav, just plays a dull two-note hum. Our analyst     |
| `zero-width-note` | 150 | dynamic | [writeup](stego/zero-width-note/solution/) | We intercepted this bland internal memo.txt. It reads like nothing, yet the   |

## supplychain (11)

| challenge                  | pts | type          | writeup                                                   | résumé                                                                      |
| -------------------------- | --- | ------------- | --------------------------------------------------------- | --------------------------------------------------------------------------- |
| `build-cache-poison`       | 150 | dynamic       | [writeup](supplychain/build-cache-poison/solution/)       | On vous donne le Makefile qui alimente le cache de build d'un projet, sa    |
| `dependency-confusion`     | 300 | dynamic       | [writeup](supplychain/dependency-confusion/solution/)     | Notre chaîne de build a récupéré le paquet interne acme-telemetry — mais    |
| `git-repo-backdoor`        | 450 | dynamic       | [writeup](supplychain/git-repo-backdoor/solution/)        | On a exfiltré un dépôt Git interne, livré ici sous forme d'archive tar du   |
| `layered-image-leak`       | 450 | dynamic       | [writeup](supplychain/layered-image-leak/solution/)       | On vous donne une image conteneur exportée avec docker save (image.tar).    |
| `lockfile-integrity-drift` | 300 | dynamic       | [writeup](supplychain/lockfile-integrity-drift/solution/) | On vous fournit un package-lock.json et les archives .tgz qu'il verrouille. |
| `pip-postinstall-hook`     | 300 | dynamic       | [writeup](supplychain/pip-postinstall-hook/solution/)     | On vous remet une archive source Python (acme-license-check-1.0.0.tar.gz)   |
| `poisoned-pipeline`        | 350 | team_instance | [writeup](supplychain/poisoned-pipeline/solution/)        | MiniCI. Un runner de build partagé : http://{host}:{port}. N'importe qui    |
| `provenance-forgery`       | 300 | dynamic       | [writeup](supplychain/provenance-forgery/solution/)       | Chaque release de acme-app est accompagnée d'une attestation de provenance  |
| `sbom-component-swap`      | 150 | dynamic       | [writeup](supplychain/sbom-component-swap/solution/)      | On vous donne le SBOM CycloneDX d'une release (bom.json), les binaires de   |
| `tuf-rollback`             | 300 | dynamic       | [writeup](supplychain/tuf-rollback/solution/)             | On vous donne les métadonnées d'un dépôt de mises à jour façon TUF          |
| `typosquat-lockfile`       | 150 | dynamic       | [writeup](supplychain/typosquat-lockfile/solution/)       | On vous donne le package-lock.json d'un projet front-end et toutes les      |

## sysadmin (8)

| challenge      | pts | type    | writeup                                    | résumé                                                                      |
| -------------- | --- | ------- | ------------------------------------------ | --------------------------------------------------------------------------- |
| `alias-slip`   | 150 | dynamic | [writeup](sysadmin/alias-slip/solution/)   | A snapshot of a small nginx-served site: the site config nginx.conf and the |
| `env-forge`    | 300 | dynamic | [writeup](sysadmin/env-forge/solution/)    | A developer pushed a deploy bundle for an internal API to a public repo:    |
| `mask-slip`    | 300 | dynamic | [writeup](sysadmin/mask-slip/solution/)    | A CI pipeline (.github/workflows/deploy.yml) and one of its job logs        |
| `rbac-reveal`  | 100 | dynamic | [writeup](sysadmin/rbac-reveal/solution/)  | A Kubernetes manifest bundle: an RBAC Role/RoleBinding (rbac.yaml), a       |
| `rotate-root`  | 450 | dynamic | [writeup](sysadmin/rotate-root/solution/)  | An ops bundle from a host (mirrored under fs/): a cron job, a logrotate     |
| `state-secret` | 450 | dynamic | [writeup](sysadmin/state-secret/solution/) | A committed Terraform bundle: the config (main.tf), its state file          |
| `unit-eval`    | 300 | dynamic | [writeup](sysadmin/unit-eval/solution/)    | A snapshot of a systemd-driven report job: a template unit                  |
| `vault-reuse`  | 450 | dynamic | [writeup](sysadmin/vault-reuse/solution/)  | An Ansible project snapshot: ansible.cfg, inventory.ini, group_vars/        |

## warmup (16)

| challenge            | pts | type    | writeup                                        | résumé                                                                |
| -------------------- | --- | ------- | ---------------------------------------------- | --------------------------------------------------------------------- |
| `atbash-cipher`      | 50  | dynamic | [writeup](warmup/atbash-cipher/solution/)      | secret.txt was made by mirroring the alphabet: A swaps with Z,        |
| `base32-decode`      | 50  | dynamic | [writeup](warmup/base32-decode/solution/)      | secret.txt holds only UPPERCASE letters A-Z and the digits 2-7,       |
| `base64-decode`      | 50  | dynamic | [writeup](warmup/base64-decode/solution/)      | A friend swears this text is 'encrypted'. It only contains letters,   |
| `base85-decode`      | 50  | dynamic | [writeup](warmup/base85-decode/solution/)      | secret.txt looks like line noise: a dense mix of letters, digits and  |
| `binary-ascii`       | 50  | dynamic | [writeup](warmup/binary-ascii/solution/)       | bits.txt is nothing but groups of eight 0s and 1s separated by        |
| `csv-cell`           | 50  | dynamic | [writeup](warmup/csv-cell/solution/)           | roster.csv is a small spreadsheet of players. One cell, among all the |
| `hex-decode`         | 50  | dynamic | [writeup](warmup/hex-decode/solution/)         | secret.txt is one long string of the characters 0-9 and a-f.          |
| `html-entities`      | 50  | dynamic | [writeup](warmup/html-entities/solution/)      | page_snippet.txt is a run of &#NNN; codes -- the kind a web page      |
| `morse-code`         | 50  | dynamic | [writeup](warmup/morse-code/solution/)         | signal.txt is a line of dots (.) and dashes (-). Letters are          |
| `reverse-string`     | 50  | dynamic | [writeup](warmup/reverse-string/solution/)     | backwards.txt contains the flag written from right to left. Read it   |
| `rot13-decode`       | 50  | dynamic | [writeup](warmup/rot13-decode/solution/)       | secret.txt reads almost like the flag, but every letter has been      |
| `rot47-decode`       | 50  | dynamic | [writeup](warmup/rot47-decode/solution/)       | secret.txt is a jumble of visible punctuation and characters. It is   |
| `tap-code`           | 50  | dynamic | [writeup](warmup/tap-code/solution/)           | taps.txt is a list of two-digit numbers. Each number is a row then a  |
| `url-encoding`       | 50  | dynamic | [writeup](warmup/url-encoding/solution/)       | encoded.txt is a string full of % signs followed by two hex           |
| `vigenere-known-key` | 50  | dynamic | [writeup](warmup/vigenere-known-key/solution/) | cipher.txt was enciphered with a Vigenere cipher. The key is not a    |
| `zip-comment`        | 50  | dynamic | [writeup](warmup/zip-comment/solution/)        | archive.zip unzips to a single, unhelpful text file. The flag is not  |

## web (14)

| challenge                    | pts | type          | writeup                                             | résumé                                                                        |
| ---------------------------- | --- | ------------- | --------------------------------------------------- | ----------------------------------------------------------------------------- |
| `flask-unsign`               | 300 | dynamic       | [writeup](web/flask-unsign/solution/)               | A small Members Panel ships as source, along with a session cookie            |
| `graphql-introspection-maze` | 500 | team_instance | [writeup](web/graphql-introspection-maze/solution/) | Atlas Ops exposes a single GraphQL endpoint at POST /graphql                  |
| `jwt-cousin`                 | 150 | team_instance | [writeup](web/jwt-cousin/solution/)                 | "It's basically a JWT," said no one who read the code.                        |
| `jwt-forge`                  | 450 | dynamic       | [writeup](web/jwt-forge/solution/)                  | You have the full source of an internal Ops Console plus a leaked config      |
| `mass-assignment`            | 300 | dynamic       | [writeup](web/mass-assignment/solution/)            | A profile service ships as source, plus the user store and a captured request |
| `path-traversal-archive`     | 150 | dynamic       | [writeup](web/path-traversal-archive/solution/)     | An "Asset CDN" serves files from its public web root. You get the handler     |
| `php-unserialize`            | 300 | dynamic       | [writeup](web/php-unserialize/solution/)            | A legacy PHP portal ships as source, along with a session cookie captured     |
| `race-the-coupon`            | 400 | team_instance | [writeup](web/race-the-coupon/solution/)            | NimbusPay store wallet exposes a small JSON API. Every account starts         |
| `reset-token-lcg`            | 450 | dynamic       | [writeup](web/reset-token-lcg/solution/)            | A password-reset service ships as source, plus the server's reset log. Each   |
| `smuggle-gap`                | 500 | team_instance | [writeup](web/smuggle-gap/solution/)                | Nimbus runs a tiny job service behind an edge proxy. The edge is the only     |
| `sqlite-union`               | 150 | dynamic       | [writeup](web/sqlite-union/solution/)               | A souvenir shop exposes a product search API. You get the handler source and  |
| `ssrf-metadata-decoy`        | 350 | team_instance | [writeup](web/ssrf-metadata-decoy/solution/)        | imgproxy is a company image-fetch proxy: give it a URL and it fetches the     |
| `ssti-jinja`                 | 300 | dynamic       | [writeup](web/ssti-jinja/solution/)                 | A greeting-card service ships as source, with a captured normal request. It   |
| `xxe-local`                  | 300 | dynamic       | [writeup](web/xxe-local/solution/)                  | An invoice-ingest endpoint parses uploaded XML. You get the parser source, a  |
