# Handoff NCTF26 — ce qui reste hors du conteneur cloud

Note de passation. Le code, la config et la doc sont finalisés et verts en CI
sur la branche `claude/ctf-platform-free-ptiggj` (PR #1). Ce qui suit **ne peut
pas** être fait depuis l'environnement cloud (pas d'accès SSM/SSH au compte AWS,
Docker indisponible, ni GPU/qemu/EVM/modèles) : ce sont des actions
**opérateur** (🖥️ = machine avec AWS CLI + Docker) ou des **décisions humaines**
(🧑).

Légende : 🖥️ action sur une machine de déploiement · 🧑 décision / action humaine.

## Finalisé (dans le repo, CI verte)

- **Backend IA = Amazon Bedrock par défaut** (`ai_backend = "bedrock"`). Aucun
  nœud GPU ; la passerelle `ai-gateway` du front traduit le dialecte Ollama
  `/api/chat` vers Bedrock Converse (pool de 4 modèles Nova, ~85 req/min,
  cooldown 20 s). GPU/Ollama reste sélectionnable en repli, étiqueté partout.
- Les 8 chantiers transverses (`TODO-ameliorations.md`) : anti-triche,
  `preflight`, loadtest k6, sauvegardes, flakes CI, first bloods, ops, writeups.
- Thème `hibris`, KotH, scoreboard « La Course », board challenges (compteur +
  vue par auteur + super-catégorie « Mise en jambe »), plomberie e-mail SMTP.

## Revue qualité des challenges — état d'application

Détail dans `challenge-review.md` (constats) et `innovative-challenges-todo.md`
(pistes). Résumé :

- **§1 Dédup** ✅ appliqué : 1 skin par primitive, 505 → 350 (2 épreuves
  réellement distinctes préservées).
- **§2 Indices trop généreux** ✅ appliqué : dernier indice rendu directionnel
  sur les 26 familles templatées + `graphql-introspection-maze`, `synthvm`.
- **§3 Résistance LLM des statiques** ✅ volet indices (7 statiques à forte
  valeur) ; 🖥️🧑 **volet structurel parké** (oracle serveur, flag offline non
  récupérable, reverse « écart aux specs ») — voir la section dédiée ci-dessous.
- **§4 Calibration** ✅ appliqué : 155 tags de difficulté ajoutés ; canoniques
  mono-étape sur-cotés recalés (450-500 → 250-300).
- **§5 Descriptions mensongères** ✅ appliqué (commit antérieur).
- **Deep-research** : MCP statique ✅ (`challenges/ai/mcp-manifest-audit/`) ;
  restent 🖥️🧑 au backlog : MCP agentique, LLMail-inject aveugle, ML statique,
  catégorie ICS/OT, reverse durci, composante physique on-site (finale).

## À faire par un opérateur 🖥️ (machine avec AWS + Docker)

1. **Apply AWS** : `cd deploy && make phase-setup` puis, aux dates,
   `make phase-preselection` / `make phase-final`. Renseigner `terraform.tfvars`
   (voir `.example`) et les secrets **hors git** au préalable.
2. **Vérifier Bedrock en vrai** : `make check-bedrock` (chaque modèle du pool
   répond, chat + appel d'outil) et que le rôle IAM du front porte
   `bedrock:InvokeModel` en `eu-west-3`. Activer l'accès aux modèles Nova dans
   la console Bedrock si ce n'est pas déjà fait.
3. **E-mail** : `make mail-test TO=…` doit délivrer avant de passer
   `verify_emails=ON` (voir `PROD-SETUP.md §2bis`), DKIM/SPF/DMARC en DNS-only.
4. **Preflight** : `make preflight` doit être vert avant chaque `make phase-*`.
5. **Playtest arène** : `make local-playtest` sur la stack Docker pour valider
   les ~26 challenges servis historiques (impossible ici, Docker absent).

## Décisions humaines 🧑

- **Règlement anti-triche** : sanction au 1er incident de partage de flag ? au
  2e ? (le plugin signale, ne bannit jamais seul.)
- **Politique IA (A/B)** : IA autorisée en présélection / contrôlée en finale
  (**A**, recommandé) ou partout (**B**).
- **Piste IA** : en présélection ou réservée à la finale.
- **Juridique / RH** : notice de collecte (logs, prompts finale, conservation
  30 j).
- **Domaine / Savings Plan** : à confirmer après le test de charge.

## Durcissement anti-LLM structurel (revue §3) 🖥️🧑

Le volet **indices** de la revue §3 est appliqué (dernier indice directionnel
sur les statiques à forte valeur, cf. `challenge-review.md`). Le volet
**structurel** exige l'arène / une refonte binaire et reste à trancher :

- **pwn à flag récupérable hors-ligne** (`fmt-key-leak`, `shellcode-decoder`,
  etc.) : le flag est XOR-encodé avec une clé de compilation lisible dans le
  binaire → récupérable sans exploitation. Durcir = flag servi par un **oracle**
  côté conteneur (au run), pas embarqué dans l'ELF. Nécessite Docker.
- **reverse à format standard** (`java-cafe`, `pyc-ghost`) : appliquer le
  principe deep-research « **écart délibéré aux specs** + leurres » (ex. runtime
  WASM à opcodes permutés, à la `synthvm`) plutôt que JVM/.pyc décompilables.
- **web statiques à forte valeur** (`reset-token-lcg`) : envisager la bascule
  vers un **oracle serveur** (`type: team_instance`) comme le set servi, sinon
  garder l'indice directionnel (fait) et le prix aligné.

## Challenges restants (~70 stubs) 🖥️

Backlog chiffré : pwn (heap/ROP), blockchain/EVM, ai, ml, os. Leur **authoring**
est possible mais leur **validation logique** exige Docker/GPU/qemu/anvil/modèles
— absents ici. Ils ne sont donc **pas** déversés non vérifiés (contrat qualité
du repo : chaque servi = `type: team_instance`, flag `team_hmac`, writeup +
solveur, validation logique). Idées et priorisation dans
`innovative-challenges-todo.md` et le plan d'extraction (dépôt de write-ups).
