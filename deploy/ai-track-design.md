All facts confirmed against the code. Here is the deliverable.

---

# Plan de BUILD — Lot 3 (piste IA)

*Décision arrêtée à partir des quatre investigations et vérifiée dans le code (`security.tf`, `team_instancer/*`, `challenges/ai/*/app/`, les quatre `challenge.yml`, `deploy/Makefile`, `ROADMAP.md`). Toute hypothèse est signalée `⚠`. Décisions strictement organisateur signalées `🧑`.*

## Verdict d'architecture en une phrase

Ne pas construire de plugin de type de challenge, ni de route de chat CTFd, ni d'UI de chat : **tout cela existe déjà dans les conteneurs**. Le vrai travail de Lot 3 est **un seul composant neuf** — une **passerelle d'admission Ollama** posée sur le FRONT — plus **trois petits correctifs** (injection d'env dans l'instancier, une règle SG, câblage de la chaîne de prérequis) et **une table de log**.

Ceci **dévie de la lettre du ROADMAP Lot 3** (qui prévoyait `POST /api/v1/ai/<id>/message` + UI de chat dans le thème). Cette déviation est justifiée §3 et doit être validée `🧑` — le ROADMAP est à corriger en conséquence.

---

## 1. Correctif d'accessibilité (GAP A)

### Constat (en l'état, la piste IA ne peut pas fonctionner)

Deux défauts cumulatifs, chacun bloquant seul :

1. **Le SG bloque.** `ai_ollama_from_front` (security.tf) ouvre le 11434 du nœud IA **au seul SG front** (`referenced_security_group_id = aws_security_group.front.id`). Les conteneurs IA tournent sur l'**arène** (l'instancier ne parle qu'à `tcp://dockerproxy:2375`, `backend.spawn_container`), donc leur trafic sort avec le SG *arène* — que le nœud IA ne fait pas confiance en entrée.
2. **Aucun `OLLAMA_URL` n'atteint le conteneur.** `spawn()` ne construit `container_env` qu'avec `FLAG` et `CHALLENGE_SECRET` (`__init__.py` ~207-210, vérifié). Les apps retombent donc sur `http://localhost:11434` (`app.py:48`, vérifié) → connexion refusée.

### Option retenue : **(b) proxy par le FRONT** — rejet explicite de (a) et (c)

- **(a) Ouvrir 11434 à l'arène + injecter l'IP du nœud IA.** Minimal, mais câble *chaque* conteneur de l'arène directement sur Ollama, **court-circuitant** le point d'admission (GAP B). Un joueur avec exec dans n'importe quel conteneur de l'arène (un pwn, un box IA compromis) fait fondre le GPU partagé. **Rejeté** — c'est précisément ce que le commentaire de `ai_ollama_from_front` interdit.
- **(c) Faire tourner les conteneurs IA sur le front.** L'instancier ne connaît qu'un seul endpoint Docker (l'arène via le tunnel ssh) ; le front n'a ni le plan frp/overlay ni la place pour ~300 conteneurs Flask+chat. **Rejeté.**
- **(b) Proxy par le front.** Le front est le **seul hôte déjà autorisé** par le SG IA, et `make link` y pose déjà `OLLAMA_URL`. On y place le point d'admission (GAP B), on pointe les conteneurs vers *lui*, et le SG IA reste fermé à l'arène. **Corrige GAP A et donne à GAP B son foyer d'un seul geste.** Le saut front↔IA est intra-`aws_subnet.public` (LAN sub-ms), négligeable face aux secondes de génération 8B/T4. **Retenu.**

### Diff exact

**1. SG — ouvrir le *port passerelle* du FRONT à l'arène ; `ai_ollama_from_front` inchangé.**
```hcl
resource "aws_vpc_security_group_ingress_rule" "front_ai_gw_from_arena" {
  security_group_id            = aws_security_group.front.id
  description                  = "Passerelle admission IA : conteneurs IA de l'arene"
  referenced_security_group_id = aws_security_group.arena.id
  from_port                    = 8600   # port passerelle, PAS 11434
  to_port                      = 8600
  ip_protocol                  = "tcp"
}
```
Ollama n'est jamais joignable depuis l'arène — uniquement depuis le front, via la passerelle.

**2. Terraform outputs + `make link`.**
- Ajouter l'output `front_private_ip = aws_instance.front[0].private_ip` (valeur déjà utilisée en `arena.tf:49`).
- Makefile : `FRONT_PRIV = $(call tfout,front_private_ip)`.
- **Garder** `upsert OLLAMA_URL http://$(AI_PRIV):11434` (la passerelle et le health-check du front consomment Ollama en direct).
- **Ajouter** `upsert AI_PROXY_URL http://$(FRONT_PRIV):8600` — la valeur injectée dans les conteneurs IA.

**3. Instancier — `settings.py`** : `AI_PROXY_URL = os.environ.get("AI_PROXY_URL", "").strip()`.

**4. Instancier — `__init__.py`, juste après la construction de `container_env` (~210) :**
```python
if _is_ai_challenge(challenge):
    if not settings.AI_PROXY_URL:
        return _json({"success": False, "error": "Passerelle IA non configuree (AI_PROXY_URL)."}, 500)
    container_env["OLLAMA_URL"]    = settings.AI_PROXY_URL          # les apps lisent deja OLLAMA_URL
    container_env["AI_PROXY_TOKEN"] = _mint_proxy_token(account_id, challenge)  # cf. GAP B
```
`backend.spawn_container` propage déjà tout le dict `env` (`environment=dict(env)`, vérifié) — aucun changement là.

### Détection du type IA (zéro migration, zéro changement de schéma)

Les quatre `challenge.yml` portent `category: ai` (vérifié). Seuls les servis (`type: team_instance`) atteignent `spawn()` — ai0 est statique/`type: dynamic`. Donc :
```python
def _is_ai_challenge(challenge):
    return (getattr(challenge, "category", "") or "").lower() == "ai"
```
`TeamInstanceChallenge` n'a pas de colonne libre ; réutiliser la catégorie évite toute migration. Alternative équivalente sans schéma : `challenge.docker_image.startswith("ctf-ai")` (convention déjà imposée par `make push-images`). **La catégorie est plus propre — retenue.**

---

## 2. Contrôle d'admission (GAP B)

### Pourquoi un proxy central et **pas** des limiteurs par conteneur

Les limiteurs actuels (`app.py:109-123`, `RL_MAX=30/60s` par IP) sont **structurellement inutilisables** :
- **Pas de vue globale** = pas de plafond réel : N limiteurs autorisent chacun leur part, rien ne borne la somme. 50 conteneurs finale = 25 msg/s ; si ai3 (jusqu'à **6 complétions/message**, `MAX_TOOL_STEPS=6`, vérifié), ~150 complétions/s contre un GPU à ~1,5/s.
- **Identité fausse** : derrière le tunnel frp, `X-Forwarded-For` est uniforme → « par IP » s'effondre en un seul seau.
- **Grandeurs globales impossibles à mesurer depuis un conteneur** : budget de tokens par équipe (fenêtre glissante), plafond de concurrence par niveau, état perdu à chaque reschedule.

### Où il vit

**Un service asynchrone mono-processus** (aiohttp ou FastAPI+uvicorn, **un worker**), co-localisé sur le front (SG front, déjà autorisé à joindre 11434), image dédiée. Le goulot GPU étant ~1,5 req/s, un process suffit largement, et le mono-process rend le compteur d'in-flight global et la file **exacts** sans coordination inter-workers (**pas de Redis requis** pour la correction ; Redis seulement si l'on veut que le grand livre de tokens survive à un redémarrage en cours d'épreuve — `⚠` à trancher, non bloquant).

### Interface

**Identité — jeton signé, jamais confiance au conteneur.** L'instancier injecte `AI_PROXY_TOKEN = HMAC(account_id | level | instance_id | exp)` signé d'une clé proxy (`_mint_proxy_token`, réutilise le modèle de confiance FLAG/CHALLENGE_SECRET déjà en place). Le proxy lit `(équipe, niveau)` du jeton. `level ∈ {ai1,ai2,ai3}` dérivé du label déjà en portée.

**Endpoints :**
- `POST /api/chat` — passthrough Ollama (`stream:false` uniquement). Pipeline : (1) vérif jeton → sinon `401` ; (2) pré-check rate + budget tokens sur la fenêtre glissante de l'équipe → sinon `429 {retry_after}` ; (3) acquisition d'un slot par-(équipe,niveau)=1 **et** d'un slot global par-niveau → sinon `429` ; (4) mise en file bornée gardant `GLOBAL_MAX_INFLIGHT` ; file pleine ou attente > `QUEUE_WAIT` → `503 {error:"modèle occupé, réessayez", retry_after}` ; (5) forward vers Ollama, dont le `503 OLLAMA_MAX_QUEUE` est **normalisé** au même `503` lisible ; (6) au succès, débit du grand livre de tokens depuis `prompt_eval_count + eval_count` (présents car `stream:false`, vérifié), libération des slots.
- `GET /healthz` — liveness.
- `GET /metrics` — in-flight par niveau, profondeur de file, dépense par équipe ; **puits de log finale-seulement** (GAP D).

**ai3 (fan-out) géré naturellement** : le proxy admet par requête `/api/chat`, donc les 6 appels séquentiels acquièrent/libèrent chacun le slot ai3 → la lourdeur se pondère seule. **Un garde-fou** : priorité de continuation — une requête d'une équipe détenant déjà son slot (tour en cours) passe devant les nouveaux tours, pour qu'une boucle d'outil à demi-finie se termine plutôt que de se bloquer contre le plafond global.

**Ordre de délestage (haut = gagne)** : `401` jeton invalide → `429` budget équipe épuisé → `429` concurrence pleine → `503` file/attente → `503` Ollama amont. Distinguer `429` (ton quota) de `503` (GPU partagé occupé) garde les logs honnêtes ; l'UI peut afficher les deux comme « modèle occupé ».

### Valeurs par défaut — à câbler en **env du proxy** (retune live sans redéploiement)

Ancrage `anti-llm-guardrails.md` §4.7 : **~1,5 complétion utile/s** sur un T4. **Les limites par équipe sont des molettes d'équité, pas de la capacité en plus — la file globale est le vrai plafond.**

**Global (les deux phases, un T4) :** Ollama `OLLAMA_NUM_PARALLEL=4`, `OLLAMA_MAX_QUEUE=16` (filet amont) ; proxy `GLOBAL_MAX_INFLIGHT=4`.

| Paramètre | Présélection (300 éq.) | Finale (~50 éq.) |
|---|---|---|
| Rate/équipe | **10 msg/min, 500/jour** | **30 msg/min, 3000/jour** |
| Budget tokens/équipe | **8k/60s, 200k/jour** | **24k/60s, 500k/jour** |
| In-flight par niveau (champ entier) | ai1=2, ai2=1, ai3=1 | ai1=3, ai2=2, ai3=2 |
| Slot par-(équipe,niveau) | 1 | 1 |
| File / attente → 503 | 24 / 15 s | 32 / 30 s |

`⚠` Ces valeurs sont des **points de départ, pas finaux** : le doc (§répétition générale) et le ROADMAP Lot 5 fixent les vrais rate-limits à la répétition sur infra de prod, pas à l'intuition. Réalité présélection à annoncer : 90 msg/min ÷ 300 ≈ 0,3 msg/min/équipe si tout le monde tape — le proxy rend cela **borné et équitable**, il ne fabrique pas de capacité.

**Résidu sous (b)** : un joueur avec exec dans son *propre* conteneur peut spammer la passerelle — c'est voulu : la passerelle applique le plafond **global**, le GPU reste protégé. Il ne peut **pas** joindre Ollama en direct (SG IA toujours front-seul, l'arène ne peut pas présenter le SG front). La clé d'équité par équipe ne peut être que la source (le conteneur peut forger un en-tête d'équipe), mais le plafond GPU agrégé ne dépend pas de l'honnêteté des équipes. **Ne surtout pas** ouvrir en plus le SG IA à l'arène « au cas où ».

---

## 3. À CONSTRUIRE vs ce qui EXISTE déjà

### N'existe PAS — à construire
- **La passerelle d'admission Ollama** (§2) : le seul vrai composant neuf. Concurrence globale + par-niveau, budget/rate par équipe, file équitable, normalisation 503, puits de log.
- **Injection d'env dans l'instancier** (`OLLAMA_URL`→proxy + `AI_PROXY_TOKEN`) + `_is_ai_challenge` + `_mint_proxy_token` : ~15 lignes.
- **Une règle SG** arène→passerelle (§1).
- **Câblage de la chaîne de prérequis** + **table de log** (§4).

### Existe DÉJÀ — NE PAS reconstruire (`🧑` déviation ROADMAP à acter)
- **UI de chat** : chaque app sert une console HTML+JS complète en `/` (ai1 `INDEX_HTML`, ai3 rend même les événements d'outil). **Ne pas** bâtir de seconde UI dans le thème CTFd.
- **Oracle de validation déterministe** : ai1/ai2 exposent `POST /verify` (`hmac.compare_digest`, sans appel modèle) ; ai3 vérifie l'état serveur via `executor.solved()`. C'est exactement le « appel d'outil déterministe, pas le texte du modèle » exigé — **déjà fait**.
- **Émission du flag** : calculée depuis `FLAG`/`CHALLENGE_SECRET`, n'entre jamais dans le contexte modèle ; le joueur colle le `CTF{...}` dans le scoreboard normal (`team_hmac_flag`). Aucun chemin de flag côté CTFd.
- **Type de challenge & cycle de vie** : `team_instancer` fait déjà spawn/FRP/caps/TTL/reaper et **rejoue déjà le gate de prérequis** dans `spawn()` (`_prereqs_met`, vérifié).

**Conséquence pour le ROADMAP** : les deux lignes « Route `POST /api/v1/ai/<id>/message` » et « UI de chat dans le thème » sont **à remplacer** par « passerelle d'admission + injection d'env ». Le seul ajout CTFd justifiable est une **vue admin cosmétique** en lecture sur les logs (facultatif).

---

## 4. Chaîne de prérequis (GAP C) + journalisation (GAP D)

### GAP C — câblage qui survit à un import ctfcli neuf

**Découverte vérifiée** : dans les quatre `challenge.yml`, `requirements:` n'existe **qu'en commentaire** — la chaîne est **totalement non câblée** aujourd'hui.

CTFd stocke `requirements = {"prerequisites":[<id int>], "anonymize":<bool>}` (JSON), appliqué par **id entier** dans `api/v1/challenges.py` (liste, détail, et `/attempt`→`403`), comparé sur `account_id` (déblocage collectif en mode équipe). ctfcli traduit à l'`install`/`sync` les **`name`** (chaînes) en ids via la table des challenges installés → **le prérequis doit exister au moment du sync du dépendant**.

Deux défauts à corriger dans les YAML :
1. **Décommenter** le bloc en clé racine réelle.
2. **Bon jeton** : utiliser le `name` du challenge (`ai0-leaked-transcript`), **pas** le label HMAC `ai-ai0-...` (qui est le `flags[].content` de `team_hmac`) — sinon la résolution échoue en silence.

Câblage exact :
- `ai0-leaked-transcript` : pas de `requirements`.
- `ai1-naive-guard` : `requirements: [ai0-leaked-transcript]`
- `ai2-output-filter` : `requirements: [ai1-naive-guard]`
- `ai3-tool-abuse` : `requirements: [ai2-output-filter]`

(Noms nus. `anonymize: true` facultatif si l'on veut afficher les niveaux verrouillés en `???` plutôt que masqués.)

Procédure d'import propre : installer/sync **dans l'ordre ai0→ai1→ai2→ai3** ; **double passe** `ctf challenge sync` (idempotent) pour résoudre tout nom non encore présent à la 1re passe. Vérifier via `GET /api/v1/challenges/<id>/requirements` que chaque dépendant montre l'id prérequis attendu. Aucun code nouveau : le core CTFd applique sur ses routes, `_prereqs_met` couvre déjà `/spawn`.

### GAP D — journalisation, exportée avant `season-down`

**Quoi** (par tour modèle) : `ts`, `team` (`account_id`), `level`, `session_id`, `prompt`, `response`, `prompt_tokens`, `completion_tokens`, `model`. ai0 statique = pas de log (seul signal : le Solve).

**Où** : **une table de plugin CTFd sur le front** (`ai_attempts`, un petit modèle comme `TeamInstance`). Elle **profite du backup déjà vérifié** : `make backup` (Makefile L260-283) dump MariaDB `--single-transaction` → S3, et `season-down` lance `backup` **avant** `apply -var phase=off`. Donc **zéro nouveau code d'export**, et destruction-proof. **Ne pas** compter sur les logs de conteneur (reapés/détruits à `phase=off`).

**Qui écrit** : la passerelle §2 (elle voit chaque requête/réponse/tokens et connaît `(équipe,niveau)` par le jeton) écrit la ligne en localhost dans la DB CTFd. **Puits activé finale-seulement** (§5.1 du doc ; ne pas activer en présélection).
`⚠` Si GAP B devait finalement rester en-conteneur (non retenu), l'équivalent est un `POST /api/v1/ai/attempt` HMAC-signé par `CHALLENGE_SECRET`, + un env non-secret `TEAM_TAG=account_id` au spawn (les apps ne reçoivent pas `account_id` aujourd'hui).

**Verdict** : déjà dans MariaDB (`Solves`) et déjà sauvegardé — aucun mécanisme neuf. Ajout utile pour les write-ups : chaque `/verify` émet un enregistrement `pending|decoy|correct` (une ligne/soumission) ; les soumissions `decoy` (jeton démo public) sont un signal de détection propre.

---

## 5. Checklist pas-à-pas, mappée au ROADMAP Lot 3

Légende : `🤖` build Claude · `🧑` décision/action humaine · **NOW** = faisable maintenant en statique · **REHEARSAL** = valeurs/validation fixées à la répétition Lot 5.

**Bloc A — Accessibilité (NOW)**
1. `🤖` NOW — Ajouter output `front_private_ip` + règle SG `front_ai_gw_from_arena` (arène→8600). `ai_ollama_from_front` inchangé.
2. `🤖` NOW — `make link` : `FRONT_PRIV` + `upsert AI_PROXY_URL`.
3. `🤖` NOW — `settings.py` (`AI_PROXY_URL`) + `__init__.py` (`_is_ai_challenge`, injection `OLLAMA_URL`/`AI_PROXY_TOKEN`, `_mint_proxy_token`).

**Bloc B — Passerelle d'admission** *(remplace les lignes ROADMAP « route /message » + « UI chat » — `🧑` acter)*
4. `🤖` NOW — Écrire le service (image, `POST /api/chat`, `/healthz`, `/metrics`, jeton HMAC, files/slots, normalisation 503). Numéros en env.
5. `🤖` NOW — `docker-compose`/déploiement front du proxy (SG front, upstream `AI_PRIV:11434`).
6. `🤖` NOW — Correspond à « Contrôle d'admission par niveau » + « Traduire le 503 » du ROADMAP : couverts par le proxy.
7. `🧑` **REHEARSAL** — Fixer les quatre numéros/phase (rate, tokens, in-flight, file) à la répétition 20-30 pers. (ligne ROADMAP « Décider quota exact »).
8. `🧑🤖` **REHEARSAL** — Valider joignabilité arène→8600→Ollama, latence, comportement 503/429 réels.

**Bloc C — Chaîne de prérequis (NOW)**
9. `🤖` NOW — Décommenter/corriger `requirements` (noms nus) dans ai1/ai2/ai3 (ligne ROADMAP « Câbler la chaîne de prérequis IA » / Lot 4).
10. `🧑🤖` Lot 5 — Import ordonné ai0→ai3 + double `sync` + vérif `/requirements`.

**Bloc D — Journalisation (NOW build, REHEARSAL activation)**
11. `🤖` NOW — Table `ai_attempts` + écriture par la passerelle (ligne ROADMAP « Journalisation »).
12. `🤖` NOW — Émission `/verify` `pending|decoy|correct` dans les apps.
13. `🤖` NOW — Vérifier que `ai_attempts` part bien dans `make backup` (aucun code — table DB).
14. `🧑` **REHEARSAL/finale** — Activer le puits de contenu (prompts/réponses) **finale-seulement** (§5.1) ; notice de collecte juridique déjà en Phase 0.

**Retirés du build** : `🤖` route CTFd `/message`, `🤖` UI de chat, tout plugin de type de challenge, tout oracle de flag côté CTFd — **existent déjà** (§3).

---

## 6. Décisions strictement organisateur (`🧑`)

1. **La piste IA en présélection, ou réservée à la finale ?** (Phase 0 + §4.7.) Le doc recommande de la **différer à la finale** ou de la tenir en **side-event à quota strict annoncé**. Un T4 ne tient pas 300 équipes en simultané ; le proxy borne, il n'ajoute pas de capacité. **Décision qui conditionne les valeurs présélection du §2.**
2. **Acter la déviation ROADMAP** : supprimer les lignes « route `/message` » et « UI de chat dans le thème » de Lot 3, les remplacer par « passerelle d'admission + injection d'env ». Sans cet accord, ne pas construire d'UI.
3. **Quotas exacts par phase** (§2) : à figer à la répétition Lot 5, pas à l'intuition.
4. **Activation du log de contenu (prompts/réponses)** : finale-seulement, sous notice de collecte de données (Phase 0, juridique/RH). Décider si la présélection ne journalise que les métadonnées (tokens/verdict) sans le texte.
5. **Persistance du grand livre de tokens** (`⚠`) : Redis pour survivre à un redémarrage du proxy en cours d'épreuve, ou acceptable de repartir de zéro ? Non bloquant ; défaut = en mémoire.
6. **Quota GPU AWS** (Phase 0, `[!]`) : sans instance G disponible, toute la piste IA saute — prérequis dur à tous les points ci-dessus.

Fichiers touchés : `deploy/terraform/security.tf`, `deploy/terraform/` (output), `deploy/Makefile`, `CTFd/plugins/team_instancer/{settings.py,__init__.py}`, `challenges/ai/ai{1,2,3}-*/challenge.yml`, + **nouveau** service passerelle et **nouvelle** table de plugin `ai_attempts`. Aucun changement à `backend.py` ni au code des apps (elles lisent déjà `OLLAMA_URL` ; retrait éventuel du limiteur par-IP trompeur en option).