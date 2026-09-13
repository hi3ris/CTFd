# Audit adverse — vague 2 (10 challenges) + durcissement appliqué (2026-09-13)

10 assesseurs (un par challenge), attaque depuis les **seuls matériaux joueur**.
Rappel doctrine (`anit-llm-guardrails.md`) : présélection **filtre**, finale **décide** ;
« LLM-facile » n'est PAS un ordre de coupe — c'est une donnée de mix de difficulté.

## Corrigé dans ce commit

### Bug de soundness (bypass réel — obligatoire)
- **`pwn/boot2root-linux`** : `entrypoint.sh` ne retirait que `FLAG`, pas
  `CHALLENGE_SECRET`/`TEAM_SECRET`, hérités par le service www. Comme
  `flag == NCTF{CHALLENGE_SECRET[:24]}`, le RCE d'étape 1 (`?target=;env`) donnait
  le flag **sans aucune escalade** → toute la chaîne court-circuitée. **Fix : `unset
  FLAG CHALLENGE_SECRET TEAM_SECRET` avant le drop de privilèges.** (flag.py dérive
  le flag AVANT le scrub — solveur inchangé.)

### Sur-divulgation livrée au joueur (obligatoire)
- **`ml/model-inversion`** : le handout (`README.md` + docstring de `handout/model.py`)
  déroulait toute l'attaque (formule bilinéaire `s(p)`, `M=E^TE`, « closed-form
  inversion », conseil sur le piège). **Réécrit** en scénario + API seulement ; le
  **code white-box reste** (le reverser EST le challenge), la prose de solution part.

### Fuite par les tags (affichés aux joueurs) — génériciseés sur les 10
Retiré les tags qui nomment la technique (`covert-channel`, `polyglot`, `prng`,
`state-recovery`, `bytecode-vm`, `threaded-dispatch`, `suid/sudo/command-injection`,
`desync/parsing`, `model-inversion/model-extraction`, `prompt-injection/tool-registry-
poisoning/confused-deputy/a2a`, `timeline/mitre-attack`…). Gardé catégorie + difficulté.

### Formulations de description trop guidantes
- `misc/timing-channel` : **renommé** « Timing Channel » → « Heartbeat » (le titre
  nommait la technique) ; note « regarder les octets ne sert à rien » neutralisée.
- `crypto/commit-bias` : retiré « les tirages sont bien moins imprévisibles… étudiez
  les rounds ouverts » (spoiler du biais).
- `misc/esolang-jail` : « `SYS` refuse tout **au-dessus** de la plage » (indice de
  borne unilatérale) → « `SYS` n'expose que la bibliothèque standard ».
- `ai/agent-tool-abuse` : retiré la désignation explicite du leurre `art-3`.

## À arbitrer / durcissement plus profond (🧑 — non fait : change la mécanique, re-vérif complète requise)

| Challenge | LLM-facile ? | Reco | Durcissement optionnel (difficulté, pas correctness) |
|---|---|---|---|
| polyglot-onion | oui ~5min | harden/finale | casser l'auto-détection : retirer les sentinelles magiques (Ascii85 `<~ ~>`, en-têtes gzip/bzip2) |
| timing-channel | oui ~5-10min | harden/finale | 2ᵉ couche : bitstream permuté/keyé, ou 2ᵉ flux leurre |
| commit-bias | oui ~5min | harden/warmup | — (biais reste classique ; slot d'échauffement) |
| maze-vm | oui <15min | harden/finale | **casser l'indépendance par octet** (diffusion `st[i]^=st[i-1]`) pour forcer un raisonnement global |
| evasion-timeline | oui <5min | harden/finale | ne pas embarquer le flag en clair dans le base64 (le dériver des artefacts corrélés) ; retirer les signaux faciles (SYSTEM/Tor/autorun) pour que seule la timeline distingue |
| boot2root-linux | moyen (~15min) | keep* | *après le fix bypass ; chaîne live multi-étapes, résiste correctement |
| model-inversion | oui <5min | keep/harden | bruit/quantification sur `/query` ou budget de requêtes réduit |
| smuggle-gap | oui | harden/finale | exiger un cadrage non trivial (dédup `Transfer-Encoding`, chunk-size bare-LF) pour battre le payload canonique |
| esolang-jail | oui <5min | harden/finale | ranger les primitives host dans un dict séparé (pas une liste contiguë) pour que le wrap n'atterrisse pas sur `env`/`read` |
| agent-tool-abuse | non (structurellement dur) | **keep + harden** | **re-rolls gratuits** : `run_turn` re-rend tout le log chaque tour → l'équipe spamme jusqu'à ce que le 8B cède une fois. Ne donner à CUSTODIAN que les worknotes **non traités**. Gate d'effet **SOUND** (vérifié). |

**Synthèse** : 10/10 **sound** (aucun injouable ; le seul bypass, boot2root, est corrigé).
Beaucoup sont LLM-faciles → cohérent avec « présél = filtre ». Pour la **finale**
(où l'anti-LLM compte), choisir dans le tableau ci-dessus les durcissements de mécanique
souhaités ; je les implémente + re-vérifie sur demande. Le re-roll d'`agent-tool-abuse`
mérite le fix quel que soit le choix.
