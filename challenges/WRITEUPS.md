# Writeups — NCTF25

Index des solutions officielles des **38 challenges** (22 servis en conteneur Docker par équipe 🐳, 16 statiques).

Chaque challenge a un dossier `solution/` (à côté de son `challenge.yml`) contenant le **writeup** (`README.md`, parfois `solve.md`) et un **solveur automatisé** (`solve.py` ou `solve.sh`). Les liens ci-dessous sont relatifs à ce fichier.

> ⚠️ Contenu spoiler : ne pas exposer ce dossier aux participants pendant l'épreuve.

## Sommaire

- **🌐 Web** — 5 challenges
- **💥 Pwn** — 6 challenges
- **🔁 Reverse** — 4 challenges
- **🔎 Forensics** — 5 challenges
- **🔐 Crypto** — 5 challenges
- **🤖 ML Security** — 3 challenges
- **🧠 AI / LLM** — 5 challenges
- **🧩 Misc** — 5 challenges

## 🌐 Web

| Challenge                    | Pts | Diff. | Type      | Writeup                                                        | Solveur                                                      |
| ---------------------------- | --- | ----- | --------- | -------------------------------------------------------------- | ------------------------------------------------------------ |
| `jwt-cousin`                 | 150 | —     | 🐳 équipe | [README.md](web/jwt-cousin/solution/README.md)                 | [solve.py](web/jwt-cousin/solution/solve.py)                 |
| `ssrf-metadata-decoy`        | 350 | —     | 🐳 équipe | [README.md](web/ssrf-metadata-decoy/solution/README.md)        | [solve.py](web/ssrf-metadata-decoy/solution/solve.py)        |
| `race-the-coupon`            | 400 | —     | 🐳 équipe | [README.md](web/race-the-coupon/solution/README.md)            | [solve.py](web/race-the-coupon/solution/solve.py)            |
| `graphql-introspection-maze` | 500 | —     | 🐳 équipe | [README.md](web/graphql-introspection-maze/solution/README.md) | [solve.py](web/graphql-introspection-maze/solution/solve.py) |
| `smuggle-gap`                | 500 | hard  | 🐳 équipe | [README.md](web/smuggle-gap/solution/README.md)                | [solve.py](web/smuggle-gap/solution/solve.py)                |

## 💥 Pwn

| Challenge           | Pts | Diff.    | Type      | Writeup                                                                                                 | Solveur                                             |
| ------------------- | --- | -------- | --------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `format-string-101` | 150 | beginner | 🐳 équipe | [README.md](pwn/format-string-101/solution/README.md)                                                   | [solve.py](pwn/format-string-101/solution/solve.py) |
| `heap-note`         | 350 | —        | 🐳 équipe | [README.md](pwn/heap-note/solution/README.md)                                                           | [solve.py](pwn/heap-note/solution/solve.py)         |
| `boot2root-c2`      | 500 | hard     | 🐳 équipe | [README.md](pwn/boot2root-c2/solution/README.md)                                                        | [solve.sh](pwn/boot2root-c2/solution/solve.sh)      |
| `boot2root-linux`   | 500 | hard     | 🐳 équipe | [README.md](pwn/boot2root-linux/solution/README.md) · [solve.md](pwn/boot2root-linux/solution/solve.md) | [solve.sh](pwn/boot2root-linux/solution/solve.sh)   |
| `boot2root-webapp`  | 500 | hard     | 🐳 équipe | [README.md](pwn/boot2root-webapp/solution/README.md)                                                    | [solve.sh](pwn/boot2root-webapp/solution/solve.sh)  |
| `ret2csu-ish`       | 500 | hard     | 🐳 équipe | [README.md](pwn/ret2csu-ish/solution/README.md)                                                         | [solve.py](pwn/ret2csu-ish/solution/solve.py)       |

## 🔁 Reverse

| Challenge        | Pts | Diff.    | Type     | Writeup                                                | Solveur                                              |
| ---------------- | --- | -------- | -------- | ------------------------------------------------------ | ---------------------------------------------------- |
| `strings-lie`    | 150 | beginner | statique | [README.md](reverse/strings-lie/solution/README.md)    | [solve.py](reverse/strings-lie/solution/solve.py)    |
| `packed-vm-lite` | 350 | —        | statique | [README.md](reverse/packed-vm-lite/solution/README.md) | [solve.py](reverse/packed-vm-lite/solution/solve.py) |
| `maze-vm`        | 500 | hard     | statique | [README.md](reverse/maze-vm/solution/README.md)        | [solve.py](reverse/maze-vm/solution/solve.py)        |
| `synthvm`        | 500 | —        | statique | [README.md](reverse/synthvm/solution/README.md)        | [solve.py](reverse/synthvm/solution/solve.py)        |

## 🔎 Forensics

| Challenge          | Pts | Diff.  | Type     | Writeup                                                    | Solveur                                                  |
| ------------------ | --- | ------ | -------- | ---------------------------------------------------------- | -------------------------------------------------------- |
| `USB Keystrokes`   | 150 | easy   | statique | [README.md](forensics/usb-keystrokes/solution/README.md)   | [solve.py](forensics/usb-keystrokes/solution/solve.py)   |
| `DNS Exfil`        | 300 | medium | statique | [README.md](forensics/dns-exfil/solution/README.md)        | [solve.py](forensics/dns-exfil/solution/solve.py)        |
| `SRAM Retention`   | 350 | medium | statique | [README.md](forensics/sram-retention/solution/README.md)   | [solve.py](forensics/sram-retention/solution/solve.py)   |
| `Evasion Timeline` | 400 | medium | statique | [README.md](forensics/evasion-timeline/solution/README.md) | [solve.py](forensics/evasion-timeline/solution/solve.py) |
| `Audio FSK`        | 500 | hard   | statique | [README.md](forensics/audio-fsk/solution/README.md)        | [solve.py](forensics/audio-fsk/solution/solve.py)        |

## 🔐 Crypto

| Challenge             | Pts | Diff.  | Type      | Writeup                                                    | Solveur                                                  |
| --------------------- | --- | ------ | --------- | ---------------------------------------------------------- | -------------------------------------------------------- |
| `nonce-sense`         | 150 | —      | statique  | [README.md](crypto/nonce-sense/solution/README.md)         | [solve.py](crypto/nonce-sense/solution/solve.py)         |
| `commit-bias`         | 300 | medium | statique  | [README.md](crypto/commit-bias/solution/README.md)         | [solve.py](crypto/commit-bias/solution/solve.py)         |
| `padding-oracle-lite` | 350 | —      | 🐳 équipe | [README.md](crypto/padding-oracle-lite/solution/README.md) | [solve.py](crypto/padding-oracle-lite/solution/solve.py) |
| `tlv-vault`           | 350 | —      | statique  | [README.md](crypto/tlv-vault/solution/README.md)           | [solve.py](crypto/tlv-vault/solution/solve.py)           |
| `lcg-casino`          | 500 | —      | 🐳 équipe | [README.md](crypto/lcg-casino/solution/README.md)          | [solve.py](crypto/lcg-casino/solution/solve.py)          |

## 🤖 ML Security

| Challenge          | Pts | Diff. | Type      | Writeup                                             | Solveur                                           |
| ------------------ | --- | ----- | --------- | --------------------------------------------------- | ------------------------------------------------- |
| `pickle-rce`       | 350 | —     | 🐳 équipe | [README.md](ml/pickle-rce/solution/README.md)       | [solve.py](ml/pickle-rce/solution/solve.py)       |
| `adversarial-gate` | 500 | hard  | 🐳 équipe | [README.md](ml/adversarial-gate/solution/README.md) | [solve.py](ml/adversarial-gate/solution/solve.py) |
| `model-inversion`  | 500 | hard  | 🐳 équipe | [README.md](ml/model-inversion/solution/README.md)  | [solve.py](ml/model-inversion/solution/solve.py)  |

## 🧠 AI / LLM

| Challenge               | Pts | Diff.    | Type      | Writeup                                                  | Solveur                                                |
| ----------------------- | --- | -------- | --------- | -------------------------------------------------------- | ------------------------------------------------------ |
| `ai0-leaked-transcript` | 100 | beginner | statique  | [README.md](ai/ai0-leaked-transcript/solution/README.md) | [solve.py](ai/ai0-leaked-transcript/solution/solve.py) |
| `ai1-naive-guard`       | 300 | medium   | 🐳 équipe | [README.md](ai/ai1-naive-guard/solution/README.md)       | [solve.py](ai/ai1-naive-guard/solution/solve.py)       |
| `ai2-output-filter`     | 350 | —        | 🐳 équipe | [README.md](ai/ai2-output-filter/solution/README.md)     | [solve.py](ai/ai2-output-filter/solution/solve.py)     |
| `agent-tool-abuse`      | 500 | hard     | 🐳 équipe | [solve.md](ai/agent-tool-abuse/solution/solve.md)        | [solve.py](ai/agent-tool-abuse/solution/solve.py)      |
| `ai3-tool-abuse`        | 500 | hard     | 🐳 équipe | [README.md](ai/ai3-tool-abuse/solution/README.md)        | [solve.py](ai/ai3-tool-abuse/solution/solve.py)        |

## 👑 Formats spéciaux

| Format                          | Pts               | Type       | Writeup / doc                                                                                     |
| ------------------------------- | ----------------- | ---------- | ------------------------------------------------------------------------------------------------- |
| King of the Hill — `The Throne` | par tick (Awards) | 🐳 partagé | [README.md](koth/throne/solution/README.md) · ops : [`deploy/koth-ops.md`](../deploy/koth-ops.md) |

## 🧩 Misc

| Challenge         | Pts | Diff.  | Type      | Writeup                                              | Solveur                                            |
| ----------------- | --- | ------ | --------- | ---------------------------------------------------- | -------------------------------------------------- |
| `git-archaeology` | 100 | easy   | statique  | [README.md](misc/git-archaeology/solution/README.md) | [solve.sh](misc/git-archaeology/solution/solve.sh) |
| `polyglot-onion`  | 250 | medium | statique  | [README.md](misc/polyglot-onion/solution/README.md)  | [solve.py](misc/polyglot-onion/solution/solve.py)  |
| `Heartbeat`       | 300 | medium | statique  | [README.md](misc/timing-channel/solution/README.md)  | [solve.py](misc/timing-channel/solution/solve.py)  |
| `proto-fuzz`      | 350 | —      | 🐳 équipe | [README.md](misc/proto-fuzz/solution/README.md)      | [solve.py](misc/proto-fuzz/solution/solve.py)      |
| `esolang-jail`    | 400 | medium | 🐳 équipe | [README.md](misc/esolang-jail/solution/README.md)    | [solve.py](misc/esolang-jail/solution/solve.py)    |
