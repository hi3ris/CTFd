# Playtest anti-LLM (statique) + prior-art — 26 challenges (2026-09-11)

Audit adverse **statique** : par challenge, un agent estime la résolubilité par
un LLM/agent frontier **à partir des seuls matériaux joueur** (description +
handout), cherche le prior art public, et traque les bugs de soundness ; puis un
second agent **contradictoire** tente de réfuter chaque verdict en produisant le
chemin de solution. 52 agents.

> ⚠ **Statique, pas un vrai playtest live.** On n'a pas lancé les modèles ni les
> services. Le playtest live obligatoire (2 modèles frontier + 1 harness agentique
> sur le front `setup`) reste à faire — cet audit le pré-cadre.

## Comment lire ce rapport (IMPORTANT)

La règle appliquée par l'audit — « résolu par un LLM en < 15 min → couper » — est
**volontairement stricte** et donne **22/26 challenges « LLM-trivial »**. Mais la
doctrine du projet (`anti-llm-guardrails.md`) est explicite : **la présélection
FILTRE, la finale DÉCIDE**, et « quelqu'un utilise un LLM » est le risque le **plus
faible** (loin derrière effondrement infra et compromission). Beaucoup d'excellents
challenges CTF *sont* résolubles par un LLM ; c'est **attendu et acceptable** en
présélection.

**Donc ce tableau n'est PAS un ordre de couper 16 challenges.** C'est :
1. **une donnée de mix de difficulté** pour l'organisateur (🧑) — quels challenges
   réserver/durcir pour la **finale** (là où l'anti-LLM compte), lesquels laisser
   filtrer en présélection ;
2. **un levier de durcissement pas cher** : le motif dominant est la **sur-divulgation**
   (la description donne l'algo/technique/endpoints) et les **décoys inertes**
   (auto-étiquetés « fake »). Retirer ces cadeaux dans les descriptions **sans changer
   la mécanique** relève la barre à coût quasi nul — c'est une relecture éditoriale (🧑).

## Défauts techniques réels (🤖 traités dans ce commit)

- **heap-note — BLOCKER (challenge injouable) — corrigé/gardé.** Le binaire livré
  `handout/chall` requiert `GLIBC_2.34` (`__libc_start_main@GLIBC_2.34`) alors que
  la libc épinglée livrée est **2.31** → le loader échoue (`GLIBC_2.34 not found`),
  le process ne démarre jamais, **aucune connexion n'atteint la mécanique**. Vérifié
  (`objdump -T` : max requis = GLIBC_2.34). Le binaire a été compilé sur glibc 2.34+
  (Ubuntu 22.04/24.04), contredisant le Makefile/Dockerfile (« glibc 2.31 »).
  → **Action 🧑 requise : recompiler `chall` sur Ubuntu 20.04 (glibc 2.31).** J'ai
  ajouté un **garde de build** dans le Dockerfile qui **fait échouer la construction
  de l'image** tant que `chall` exige un symbole > GLIBC_2.31 — impossible de livrer
  ce challenge cassé désormais.
- **strings-lie — solveur officiel cassé — corrigé.** `solution/solve.py` codait en
  dur `FLEN=30` alors que le flag fait 31 octets → `make verify` échouait
  (« no solution found »). Réécrit **sans longueur en dur** (ancre sur `NCTF{`,
  étend jusqu'à `}`) ; vérifié : récupère `NCTF{str1ngs_l1e_read_the_c0de}` depuis
  le binaire livré. N'affectait pas les joueurs (ils ne reçoivent pas `solution/`).

## Aléas de packaging à surveiller (🧑, non bloquants si ctfcli honore `files:`)

`git-archaeology` (`build_repo.sh` contient le flag), `packed-vm-lite`
(`program.h`/`gen.py` contiennent serial/flag en clair) : le `files:` correct ne
livre que l'artefact prévu, mais un upload « tout le dossier » fuiterait la solution.
Ne jamais déployer par zip-du-répertoire ; s'en tenir à `ctf challenge install`.

## Verdicts par challenge (triés par recommandation puis points)

| Challenge | Cat | Pts | Reco audit | LLM-trivial (vérif) | Note (synthèse contradictoire) |
|---|---|---|---|---|---|
|`graphql-introspection-maze`|web|500|cut|confirmed|llm_trivial verdict CONFIRMED; auditor's 12-min estimate is if anything generous (a fluent agent scripts this in well under 10). All five listed soundness observations substantiated against app.py;...|
|`ret2csu-ish`|pwn|500|cut|confirmed|llm_trivial CONFIRMED. From player materials alone a strong agent reaches a complete two-stage static-ROP-to-execve chain in well under 15 minutes: the not-stripped binary exports the intended gadg...|
|`ai2-output-filter`|ai|350|cut|confirmed|Verified all four prior soundness claims against app.py/filter.py and they hold: (a) flag is unrecoverable offline — it is FLAG env or NCTF{CHALLENGE_SECRET[:24]}, released only by POST /verify aft...|
|`heap-note`|pwn|350|cut|confirmed|Two independent reasons to cut. (1) Design: even when built correctly, this is the single most training-data-saturated heap pattern (glibc 2.31 UAF -> unsorted leak -> tcache poison, no safe-linkin...|
|`packed-vm-lite`|reverse|350|cut|overturned|The intended solve is technically sound (flag is not stored, only reconstructed from a uniquely-determined serial; decoy_key is genuinely unreferenced). But for a preselection whose stated #1 goal ...|
|`pickle-rce`|ml|350|cut|confirmed|Verified independently by executing the payload against the shipped app.py RestrictedUnpickler: both `operator.methodcaller('read')` chained with `codecs.open('/flag')` and with `io.open('/flag')` ...|
|`tlv-vault`|crypto|350|cut|confirmed|Independently reproduced the solve from player-facing files only (challenge.yml, SPEC.md, vault_0*.vlt); did not rely on solution/ or server source except that the recovered flag matches challenge....|
|`ai1-naive-guard`|ai|300|cut|confirmed|The auditor's engineering praise holds and I confirm it: flag = get_flag()/NCTF{CHALLENGE_SECRET[:24]} is emitted ONLY on a hmac.compare_digest match of the 64-bit CANON_SECRET; /verify makes no mo...|
|`dns-exfil`|forensics|300|cut|confirmed|All three prior soundness bugs substantiated and verified against the actual artifact. No correctness/unsolvability bug: challenge is fully solvable and the recovered flag matches the checker exact...|
|`format-string-101`|pwn|150|cut|confirmed|Independently verified the prior auditor's soundness claims and found no real bugs to substantiate: debug_dump() decoy is __attribute__((used)) but never called (unreachable) and prints only a clea...|
|`jwt-cousin`|web|150|cut|confirmed|Adversarial solve attempt SUCCEEDS trivially, so llm_trivial=true stands. The primitive is the textbook 'signature does not cover the authorization field' / partial-claim-signing class, heavily rep...|
|`strings-lie`|reverse|150|cut|confirmed|The prior auditor's llm_trivial verdict holds under adversarial attempt: I produced a complete, working solution path from player materials only, in a couple of minutes, matching the ~4 min estimat...|
|`usb-keystrokes`|forensics|150|cut|confirmed|Refutation attempt failed: I could not overturn llm_trivial. A single generic scapy script decoded NCTF{Bl4ck_H4t_USB_2026} from the pcap alone on the first working run, matching the prior auditor'...|
|`ai0-leaked-transcript`|ai|100|cut|confirmed|llm_trivial CONFIRMED. The description explicitly discloses the obfuscation scheme ("the flag, reversed and then base64-encoded") and the encoded token sits verbatim in the only handout, so the cha...|
|`git-archaeology`|misc|100|cut|confirmed|Prior auditor's verdict fully upheld. I reproduced the solve from player-facing materials alone (tarball + description), never relying on solution/ or server source except to confirm correctness. T...|
|`sram-retention`|forensics|None|cut|confirmed|Attempted refutation failed. The datasheet is a complete, self-contained specification: every field, the EOF-relative offset trick, the checksum coverage caveat, and the round-robin interleave rule...|
|`adversarial-gate`|ml|500|harden|confirmed|llm_trivial confirmed and solidly under 15 min — I went from handout files to a verified GRANTED packet with only a few short scripts; the ML step converged in 2 iterations. The challenge is sound ...|
|`ai3-tool-abuse`|ai|500|harden|overturned|Cannot execute the live model here, so the <15min claim is not empirically confirmed against the running 8B; it is inferred. But under the task's operational definition (a concrete complete path ca...|
|`lcg-casino`|crypto|500|harden|confirmed|llm_trivial is firmly confirmed. I reproduced the offline analysis in one shot: high_card==shuffle[0] is visible at a glance; L=16 falls out of a trivial 2^16 brute over the sample transcript (no l...|
|`race-the-coupon`|web|400|harden|confirmed|llm_trivial claim survives adversarial scrutiny and is confirmed: my independent player-materials-only solution path is identical to the shipped reference solver, and the description is a near-comp...|
|`padding-oracle-lite`|crypto|350|harden|confirmed|llm_trivial CONFIRMED. The prior auditor was correct on every point. The single strongest tell is that SPEC.md itself names both AES-128-CBC and PKCS#7 ('strip the PKCS#7 padding') and hands over t...|
|`proto-fuzz`|misc|350|harden|confirmed|Mechanically sound and correct: server.py's range(n+1) over-read writes channels[3] safely (store size 4), DUMP gates on channels[3], and flag derivation (FLAG or CHALLENGE_SECRET[:24], legacy HMAC...|
|`ssrf-metadata-decoy`|web|350|harden|confirmed|Independent verification of the three claimed soundness bugs: (1) "description spells out the full solution path" — CONFIRMED verbatim; the description names every step including the substring-bypa...|
|`nonce-sense`|crypto|150|harden|overturned|Verified correctness end-to-end: recovered d matches flag.py's baked-in D and the flag matches challenge.yml. The single repeated-r decoy provably fails against Q (candidate d=0x6ef7...dfd1 does no...|
|`audio-fsk`|forensics|500|finale-only|overturned|Prior auditor's llm_trivial=false is overturned: I recovered the flag one-shot from player-facing files only, in far under 15 minutes, writing a standard Goertzel demod + brute-force over the exact...|
|`synthvm`|reverse|500|keep|confirmed|Independently confirmed all soundness claims: no plaintext flag; strings/grep for ctf|flag|granted|denied|NCTF yields nothing (I/O strings are emitted via OUT from bytecode); solution/solve.py reco...|

**Bilan audit (règle stricte)** : cut 16 · harden 8 · finale-only 1 · keep 1 ·
LLM-trivial confirmé 22 / réfuté 4 (`packed-vm-lite`, `ai3-tool-abuse`,
`nonce-sense`, `audio-fsk` — jugés non trivialement one-shot).
**Rappel** : « reco audit » = sortie de la règle < 15 min, **à arbitrer** par
l'organisateur selon présélection (filtre) vs finale (décide), pas un ordre de coupe.
