# Vague 2 de challenges — spec & suivi

Objectif : ~10 nouveaux challenges **compatibles conteneur**, conçus **contre les LLM**
(leçons de `challenge-audit.md`), chacun avec un **solveur de référence vérifié**.
Décisions porteur : pas de VM Windows / AD / drone ; boot2root = **Linux en conteneur** ;
qualité d'abord.

## Règles d'auteur (obligatoires, tirées de l'audit anti-LLM)
1. **Flag** : `NCTF{...}`. Servi (Docker par équipe) → `type: team_instance` + flag `team_hmac`
   (contenu = `<cat>-<nom>`), flag dérivé par `flag.py` (env `FLAG`/`CHALLENGE_SECRET`).
   Pur téléchargement → flag statique.
2. **Ne PAS sur-divulguer** : la description ne nomme pas la technique/l'algorithme/les
   endpoints exacts. Elle pose l'objectif et le contrat de vérification, pas la solution.
3. **Pas de décoy auto-étiqueté** « fake/not the flag ». Un leurre doit coûter un vrai effort à écarter.
4. **Préférer** : format inventé, interaction live/stateful, chaîne multi-étapes, vérification
   d'**effet** côté serveur (pas de shape de payload). Ce sont les propriétés qui résistent aux LLM.
5. `challenge.yml` au format ctfcli du dépôt (voir un exemplaire existant, ex. `challenges/reverse/synthvm`).
   `files:` déclare TOUT handout ; aucun flag/solution dans les fichiers livrés.
6. `solution/solve.py` (+ README) qui **récupère réellement le flag** ; pour les challenges
   offline, l'auteur l'exécute et confirme la sortie. Pas de longueur/flag codés en dur.

## Le lot (≈10)

### Offline (vérifiables ici — solveur exécuté)
- [ ] `misc/polyglot-onion` — fichier polyglotte multi-format ; peler des couches d'encodage
      **non annoncées** (déduire chaque couche). Wow/innovant.
- [ ] `forensics/evasion-timeline` — logs Sysmon **synthétiques** (JSON, inspirés MITRE ATT&CK
      defense-evasion : parent-PID spoof / timestomp / hollowing) noyés dans du bruit ; extraire l'IOC.
- [ ] `crypto/commit-bias` — protocole d'engagement inventé avec un biais subtil → récupérer la clé.
- [ ] `reverse/maze-vm` — nouvelle VM bytecode inventée (≠ synthvm), anti-analyse légère → retrouver l'entrée.
- [ ] `misc/timing-channel` — donnée cachée dans le timing inter-paquets d'une capture fournie.

### Servis (logique + solveur validés statiquement ; run live = Lot 5)
- [ ] `pwn/boot2root-linux` — conteneur : foothold service → user → privesc Linux
      (suid maison / sudo / cron / capabilities) → root → `/root/flag` (effet vérifié).
- [ ] `ml/model-inversion` — API de requêtes d'un modèle ; inversion/extraction → secret → flag (effet).
- [ ] `ai/agent-tool-abuse` — agent outillé à registre de tools empoisonné ; abus de capacité
      → exfiltration → flag (effet). Passe par la gateway d'admission.
- [ ] `web/smuggle-gap` — proxy inventé avec un écart de parsing → atteindre un endpoint interne → flag.
- [ ] `misc/esolang-jail` — interpréteur restreint ; s'en évader pour lire le flag (stateful).

## Définition de « fini » (vague 2)
Chaque challenge : dossier complet (challenge.yml + source + Dockerfile/entrypoint si servi +
handout + solution). Offline : solveur **exécuté et confirmé** ici. Servi : solveur + dérivation
de flag **relus**, run de bout en bout marqué pour la répétition (Lot 5). Puis **audit adverse**
du lot (résolubilité LLM + soundness) et correctifs, comme pour la vague 1.

---

## Résultats — 10/10 écrits, vérifiés, poussés (2026-09-13)

| Challenge | Cat | Type | Vérification |
|---|---|---|---|
| polyglot-onion | misc | statique | solveur exécuté → flag ; aucune fuite dans le handout |
| timing-channel | misc | statique | solveur exécuté (gaps bimodaux décodés) |
| commit-bias | crypto | statique | solveur exécuté (Berlekamp-Massey) ; pas de flag littéral |
| maze-vm | reverse | statique | build gcc + solveur → le binaire imprime le flag |
| evasion-timeline | forensics | statique | solveur exécuté (PPID-spoof T1134.004) ; leurre non trivial |
| boot2root-linux | pwn | servi | contrat OK, flag.py, compile, pas de fuite ; run live = Lot 5 |
| model-inversion | ml | servi | offline : L-inf=0 pour 3 équipes, leurre échoue ; run live = Lot 5 |
| smuggle-gap | web | servi | e2e localhost : direct=403, smuggle→flag ; run live = Lot 5 |
| esolang-jail | misc | servi | escape SYS -1 → flag ; naïf 8 SYS rejeté ; run live = Lot 5 |
| agent-tool-abuse | ai | servi | self-test stub 5/5, gate d'effet SOUND ; run live = Lot 5 |

Total dépôt : **36 challenges**. Audit adverse du lot en cours (résolubilité LLM + soundness).
