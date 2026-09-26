# TODO — épreuves innovantes candidates (NCTF26)

Backlog d'idées d'épreuves « originales » proposées, **à sélectionner après la
création du King-of-the-Hill** (KotH, en cours). Chaque idée note ce qui la rend
innovante, son adéquation à l'infra existante (instancier Docker par équipe,
passerelle LLM — Bedrock par défaut, Ollama/GPU en repli historique —, mode
équipe, univers DFIR Phantom Wire) et l'effort.

Statut légende : `[ ]` à faire · `[~]` en cours · `[x]` fait.

## Fait

- [x] **King-of-the-Hill (KotH)** — finale (10 équipes) + présélection (300 j.).
      Plugin `CTFd/plugins/koth/` (scorer périodique → `Awards`, page joueur, menu) +
      service « colline » partagé `challenges/koth/throne/` (bug XFF → fuite de clé,
      puis tenue du trône par re-signature). Validé au niveau logique ; run arène =
      bring-up. Doc : `deploy/koth-ops.md`.

## Backlog (à trancher après le KotH)

- [ ] **RAG poisoning / agent à outils réels** _(AI + pwn — reco présélection)_
      Chatbot support (passerelle au dialecte Ollama `/api/chat`) avec récupération
      de contexte (RAG) et de vrais outils (lecture fichier / requête HTTP) dans un
      conteneur par équipe. Le joueur empoisonne la base de connaissances
      (ticket / upload) pour détourner l'agent et lire un fichier flag hors périmètre.
      OWASP LLM01/LLM06, indirect prompt injection _avec exécution réelle_.
      Innovation ★★★ · effort moyen · infra : IA via la passerelle Bedrock du front
      (repli historique GPU si le quota est un jour accordé).

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

- [ ] **Stégano multimodale + LLM** _(dépend d'un modèle de vision Bedrock disponible)_
      Image portant des instructions cachées qu'un modèle de vision exécute
      (prompt-injection par canal image). Innovation ★★★ · effort moyen.

- [x] **Kill-chain réaliste multi-catégories** — fait :
      `challenges/cloud/breach-chain/` (SSRF → IMDS → creds volés). _(scénario)_
      Chaîne `web (SSRF) → cloud (IMDS) → creds → AI (exfil via agent)`, chaque
      étape débloque la suivante via les prérequis CTFd (déjà OK en mode équipe).
      Assemble des briques déjà maîtrisées. Innovation ★★ · effort moyen.

## Notes de sélection

- Présélection (~300 joueurs, équipes) : privilégier accessible→hard, montrer la
  piste IA (Bedrock) (→ RAG poisoning) + le KotH partagé.
- Finale (10 équipes) : formats spectaculaires (KotH, Live DFIR).
- Toute nouvelle épreuve servie suit le contrat existant : `type: team_instance`,
  flag `team_hmac` par équipe, writeup + solveur, validation logique.

## Propositions 2025-2026 (recherche sourcée + vérifiée)

Issues d'une recherche multi-sources (deep-research, findings re-vérifiés en
contradictoire, votes 3-0 sauf indication). Chaque piste note ce qui la rend
neuve **par rapport à ce qui existe déjà** dans `challenges/`, sa faisabilité
sous Bedrock-sans-GPU / instance-par-équipe, le niveau et l'effort.

- [~] **Empoisonnement d'outils MCP** _(AI — la piste la plus nettement neuve)_ ★★★
  **Version statique FAITE** : `challenges/ai/mcp-manifest-audit/` (host MCP
  offline déterministe, sans modèle ni réseau ; name-squatting + tool
  shadowing + description poisoning ; flag révélé uniquement via l'appel
  subverti, non grep-able). La **version agentique (finale, Bedrock/Nova)**
  reste au backlog ci-dessous.
  Classe distincte de l'injection de prompt : les instructions malveillantes
  vivent dans les **descriptions / schémas / métadonnées d'outils** MCP, lues
  et suivies par le LLM. Variantes non couvertes par notre chaîne 4-niveaux :
  full-schema poisoning, tool shadowing, name squatting, description
  poisoning, rug-pull (définitions modifiées en session), denial-of-wallet. - **Version statique (présélection, sans Bedrock)** : auditer un lot de
  manifestes MCP, trouver le serveur piégé et forger l'appel — pas d'appel
  LLM, tient à 300 joueurs. - **Version agentique (finale)** : agent organisateur sur Nova + serveur
  MCP « légitime » détenant le flag ; l'équipe déclare/modifie un serveur
  que l'agent consomme. Coûte plusieurs appels Bedrock → finale (10 éq.). - Réf. à **dépasser** (changer cibles/formats, ne pas recopier) :
  DVMCP (`harishsg993010/damn-vulnerable-MCP-server`), `canack/bad-mcp`. - Effort moyen · risque : fiabilité du tool-calling Nova, non-déterminisme.

- [ ] **Injection indirecte « aveugle » (modèle LLMail-Inject)** _(AI — finale)_ ★★★
      Format à retour **par drapeaux** : l'attaquant envoie **un** e-mail, ne voit
      **jamais** la sortie du LLM, et ne gagne que si l'agent de la victime émet
      un `send_email` non demandé avec les **bons arguments** ; en scénario RAG,
      il faut d'abord **empoisonner le retriever pour entrer dans le top-10**. La
      nouveauté pour nous est ce format aveugle multi-drapeaux (récupéré / détecté
      par défense / outil appelé / args conformes), pas l'injection indirecte
      elle-même (déjà présente). Dépend de Bedrock → **finale**. - Réf. : `microsoft/llmail-inject-challenge` (IEEE SaTML 2025, MIT). - Effort moyen-élevé · risque : orchestration retriever + coût Bedrock.

- [ ] **ML statique : le fichier de modèle comme surface d'attaque** _(ML — présélection)_ ★★
      **Aucune inférence côté orga → ni Bedrock ni GPU**, jouable à 300. On couvre
      déjà le pickle ; restent neufs : **couche Lambda Keras** (RCE à la
      désérialisation du modèle), **charge cachée dans les bits de poids faible**
      des tenseurs (stégano de poids), **contournement d'une détection de
      falsification** de modèle. Catégorie établie (5 épreuves ML à HTB Cyber
      Apocalypse 2025, 2-4★). - Réf. : `hackthebox/cyber-apocalypse-2025` (dossier ML). - Effort moyen · résistance LLM correcte (artefact binaire + logique).

- [ ] **Catégorie ICS / OT** _(nouvelle catégorie — manque au dépôt)_ ★★
      Standard désormais dans un grand CTF de masse (HTB Cyber Apocalypse 2026 :
      catégorie ICS dédiée). On a 8 épreuves hardware mais **zéro ICS**. Pistes
      faisables sans matériel : analyse PCAP **Modbus/S7comm**, reverse de
      **logique ladder** d'un PLC, altération d'un **HMI**, oracle sur un
      simulateur de process. Statique (présélection) ou servi (instance/équipe). - Effort moyen · fort ancrage « cyberdéfense nationale » (SCADA/énergie).

- [ ] **Reverse réellement résistant aux LLM** _(principe de conception — corrige la revue qualité)_ ★★★
      La recherche (déc. 2025) montre que les agents LLM résolvent **58-88 %** des
      crackme ; ni l'anti-décompilation, ni les VM maison, ni les puzzles connus
      ne protègent. **Ce qui résiste** : l'**écart délibéré aux spécifications**
      (ex. runtime WebAssembly à **opcodes permutés**), l'anti-debug + la
      **dissimulation**, et les **leurres**. → À appliquer directement aux reverse
      / pwn / statiques signalés faibles dans `challenge-review.md` §3 (formats
      JVM/.pyc standard, flag XOR à clé de compilation). - Réf. : NDSS 2026 (auto-draft-657) · votes 3-0.

- [ ] **Finale sur site : composante physique / sociale** _(format finale)_ ★★
      La frontière la plus nette contre les solveurs LLM autonomes : à
      Insomni'hack 2026, la tête de course aurait résolu 27/30 épreuves avec l'IA,
      les 3 restantes exigeant **manipulation physique, jeu manuel ou ingénierie
      sociale en personne**. Favorise directement la **finale de Lomé** (badge à
      manipuler, épreuve radio/hardware au stand, défi social encadré). Confiance
      medium (2-1) · effort variable.

- [ ] **Attaque-défense** _(format finale — à trancher, faible priorité)_ ★
      Un preprint isolé et intéressé (Alias Robotics, déc. 2025) plaide pour
      l'attaque-défense contre l'automatisation. Position **non consensuelle** ;
      format distinct du KotH déjà réalisé mais **coûteux**. À ne considérer que
      si le KotH ne suffit pas au spectacle de la finale. Confiance low (2-1).

### Angle togolais — non couvert par la recherche

La recherche **n'a trouvé aucune source vérifiable** sur les CTF africains /
francophones ni sur **mobile money / USSD / e-gouvernement**. Ce ne sont donc
**pas** des propositions sourcées, mais une **direction originale** (et de fait
résistante aux LLM, car domaine peu représenté dans les corpus) : un challenge
**USSD/mobile-money** (protocole de session, manipulation de montants, rejeu)
serait à la fois local, spectaculaire et neuf — à concevoir avec la connaissance
métier de l'équipe CERT.tg, sans référence externe à recopier.

- [x] **Réseau pyramidal / MLM (fraude anti-vérification)** — FAIT, angle
      togolais réalisé. Plateforme MLM fictive « KékéliCash » : inscription par
      numéro togolais **non vérifié** (sybil), commissions multi-niveaux,
      l'économie est conservée (la maison prélève) donc le jeu honnête perd —
      seuls des **bugs de logique métier** (prime non idempotente, remboursement
      sans reprise de commission) rendent le gain positif. Deux formes : - Présélection : `challenges/web/reseau-pyramide/` — jeopardy servi isolé
      (`team_instance`), flag team_hmac au franchissement du jackpot ; validé
      hors-ligne (Flask + solveur), 2 chemins d'exploit. - Finale : `challenges/koth/reseau-fortune/` — colline KotH partagée, le
      `/king` couronne le **réseau le plus riche** (scorer existant, zéro
      modif plugin) ; validé hors-ligne. Doc : `deploy/koth-ops.md`.
      Portée défensive directe (les arnaques pyramidales sont un fléau régional)
      et résistant aux LLM (domaine métier peu représenté).

### Priorité de sélection (synthèse)

- **Présélection (300, sans coût Bedrock)** : MCP statique (audit de manifestes),
  ML statique (Lambda/poids), ICS statique (PCAP Modbus). + reverse durci.
- **Finale (10 équipes, Bedrock OK)** : MCP agentique, injection aveugle
  LLMail-Inject, composante physique/sociale on-site.
- **Transverse** : appliquer le principe « écart aux specs + leurres » aux
  reverse/pwn existants pour relever leur résistance LLM (cf. `challenge-review.md`).
