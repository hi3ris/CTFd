# TODO — épreuves innovantes candidates (NCTF25)

Backlog d'idées d'épreuves « originales » proposées, **à sélectionner après la
création du King-of-the-Hill** (KotH, en cours). Chaque idée note ce qui la rend
innovante, son adéquation à l'infra existante (instancier Docker par équipe,
gateway LLM Ollama/GPU, mode équipe, univers DFIR Phantom Wire) et l'effort.

Statut légende : `[ ]` à faire · `[~]` en cours · `[x]` fait.

## Fait

- [x] **King-of-the-Hill (KotH)** — finale (10 équipes) + présélection (300 j.).
      Plugin `CTFd/plugins/koth/` (scorer périodique → `Awards`, page joueur, menu) +
      service « colline » partagé `challenges/koth/throne/` (bug XFF → fuite de clé,
      puis tenue du trône par re-signature). Validé au niveau logique ; run arène =
      bring-up. Doc : `deploy/koth-ops.md`.

## Backlog (à trancher après le KotH)

- [ ] **RAG poisoning / agent à outils réels** _(AI + pwn — reco présélection)_
      Chatbot support (gateway Ollama) avec récupération de contexte (RAG) et de
      vrais outils (lecture fichier / requête HTTP) dans un conteneur par équipe.
      Le joueur empoisonne la base de connaissances (ticket / upload) pour
      détourner l'agent et lire un fichier flag hors périmètre.
      OWASP LLM01/LLM06, indirect prompt injection _avec exécution réelle_.
      Innovation ★★★ · effort moyen · infra : GPU déjà là.

- [ ] **Live DFIR — « chasse l'intrusion » Phantom Wire** _(forensics temps réel)_
      Conteneur où un adversaire scripté rejoue l'attaque HIVE/Phantom Wire
      (beacon C2, exfil, wipe). Shell read-only ; questions (heure du beacon,
      host pivot, technique anti-forensics) validées par oracle. Réutilise les
      artefacts de DIGITAL-FORENSICS-CTF-LAB. Innovation ★★★ · effort moyen.

- [x] **Smart-contract / EVM** — fait : `challenges/blockchain/reentrant-vault/`
      (Vault reentrant + anvil/oracle par équipe). _(nouvelle catégorie)_
      Un `anvil` (Foundry) par équipe, bug reentrancy / logique, objectif
      « vider le vault ». Auto-contenu, très prisé, catégorie absente.
      Innovation ★★ · effort moyen.

- [x] **Supply-chain CI/CD** — fait : `challenges/supplychain/poisoned-pipeline/`
      (MiniCI, bypass du masquage de secret). _(nouvelle catégorie)_
      Gitea + runner par équipe : injection d'un workflow malveillant /
      empoisonnement d'un cache de build pour lire un secret. Colle au stack
      Docker/Terraform. Innovation ★★★ · effort élevé.

- [ ] **Stégano multimodale + LLM** _(dépend d'un modèle de vision dispo)_
      Image portant des instructions cachées qu'un modèle de vision exécute
      (prompt-injection par canal image). Innovation ★★★ · effort moyen.

- [x] **Kill-chain réaliste multi-catégories** — fait :
      `challenges/cloud/breach-chain/` (SSRF → IMDS → creds volés). _(scénario)_
      Chaîne `web (SSRF) → cloud (IMDS) → creds → AI (exfil via agent)`, chaque
      étape débloque la suivante via les prérequis CTFd (déjà OK en mode équipe).
      Assemble des briques déjà maîtrisées. Innovation ★★ · effort moyen.

## Notes de sélection

- Présélection (~300 joueurs, équipes) : privilégier accessible→hard, montrer le
  GPU (→ RAG poisoning) + le KotH partagé.
- Finale (10 équipes) : formats spectaculaires (KotH, Live DFIR).
- Toute nouvelle épreuve servie suit le contrat existant : `type: team_instance`,
  flag `team_hmac` par équipe, writeup + solveur, validation logique.
