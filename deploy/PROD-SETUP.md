# Setup CTFd en production — NCTF26 (ctf.tg)

> Checklist de configuration de la plateforme **après** que `make deploy` a mis le
> front en ligne (conteneurs Up). Se lit avec `deploy/RUNBOOK.md` (jour-J +
> incidents) et `deploy/DEPLOY-AWS.md` (infra). **Toutes les commandes depuis
> `deploy/`.**
>
> ⚠️ **Ne JAMAIS lancer `make local-seed` / `local/seed.py` contre la prod** :
> il crée `admin`/`admin` et `playtest`/`playtest` (comptes de la stack locale
> jetable). En prod = compromission immédiate.

État de départ : front up sur `http://13.37.197.230`, redirige vers `/setup`.

## 1. Domaine + HTTPS

Le domaine `ctf.tg` **n'est pas requis pour avancer** : il ne bloque que le HTTPS.
Tout le reste (setup, import, Lot-5, preflight, tests internes) se fait en HTTP sur
l'IP. On garde donc `ctf.tg` + HTTPS pour la **dernière étape, juste avant la
présélection**.

### 1a. Phase de test — maintenant, sans domaine

- **Simple (recommandé)** : rester en **HTTP sur `http://13.37.197.230`**. Zéro
  certificat, zéro DNS. On avance sur tout le reste.
- **Dérisquer la chaîne TLS une fois** (certbot est une panne classique le jour J) :
  utiliser un domaine gratuit/instantané qui résout déjà vers l'IP, sans rien
  enregistrer — `front/.env` : `CTF_DOMAIN=13.37.197.230.sslip.io` (ou `.nip.io`),
  puis `make tls-init` → vrai certificat Let's Encrypt. Prouve que le pipeline TLS
  marche ; on rebascule sur `ctf.tg` plus tard.

> ⚠️ Tant qu'on n'est pas sur `ctf.tg` + HTTPS : **ne PAS ouvrir les inscriptions
> publiques**. Garder `registration_visibility=private` (ou restreindre par
> `player_cidrs`) et `verify_emails=off`. Tester en interne : OK ; ouvrir au public
> sur une URL temporaire : non.

### 1b. Bascule finale — `ctf.tg` (avant la présélection)

1. **DNS** : enregistrement **A `ctf.tg` → 13.37.197.230** chez le registre `.tg`
   (peut être lent/manuel). Vérifier : `dig +short ctf.tg` renvoie l'IP.
2. **Config** (hors git, sur le front) : `terraform/terraform.tfvars`
   `domain_name = "ctf.tg"` ; `front/.env` `CTF_DOMAIN=ctf.tg` +
   `CERTBOT_EMAIL=<email d'ops CERT.tg>` (Let's Encrypt y envoie les avis
   d'expiration — pas une boîte perso jetable) + `REDIS_PASSWORD=<openssl rand -hex 32>`
   (obligatoire : le compose lance Redis avec `--requirepass`).
3. **TLS** : `make tls-init` si le domaine pointe **directement** sur le front (DNS only).
   **ctf.tg est proxifié par Cloudflare** (nuage orange) : utiliser à la place
   `CF_API_TOKEN=<jeton> make tls-cloudflare` (certificat d'origine Cloudflare 15 ans,
   mode SSL _Full (strict)_, TLS ≥ 1.2, vraies IP clients via `CF-Connecting-IP`), puis
   réserver 80/443 aux plages Cloudflare : `web_cidrs` dans `terraform.tfvars`
   (`scripts/cloudflare-ips.sh --tfvars`) + `terraform apply`. Détails :
   `deploy/scripts/cloudflare-origin-tls.sh`. Ancien mode : `make tls-init`. Vérifier `https://ctf.tg/` en 200, certificat valide.
   Coût du switch : quasi nul (les instances servies utilisent `FRONT_PUBLIC_IP:port`,
   pas le domaine). Sans DNS résolu, certbot échoue (challenge HTTP-01).

## 2. Setup initial CTFd (admin fort, PAS de seed local)

Faire le `/setup` **manuellement** avec un mot de passe fort, puis générer un
jeton API pour la suite scriptée :

1. Générer le mot de passe admin : `openssl rand -base64 24` (le **conserver** dans
   ton gestionnaire de secrets).
2. Ouvrir `https://ctf.tg/setup` (ou HTTP tant que le TLS n'est pas prêt) et
   renseigner :
   - **CTF name** : `NCTF26`
   - **Admin** : login d'équipe CERT.tg + le mot de passe fort ci-dessus (jamais
     `admin`/`admin`)
   - **User mode** : **Teams** (équipes)
   - **Theme** : **hibris**
   - **Registration visibility** : `public` (présélection ouverte) — à passer
     `private` pour la finale
   - **Verify emails** : selon ta politique (off si pas de SMTP configuré)
3. **Taille d'équipe** : 4 à 5 joueurs. Le maximum est le réglage CTFd `team_size`,
   le minimum vient du plugin `team_min_size` (config `team_size_min`) : une équipe
   incomplète peut s'inscrire et lire les énoncés, mais ne peut ni soumettre de flag
   ni lancer d'instance tant qu'elle n'a pas 4 membres.
   ```
   curl -H "Authorization: Token $CTFD_TOKEN" -H 'Content-Type: application/json' \
     -X PATCH $URL/api/v1/configs -d '{"team_size": 5, "team_size_min": 4}'
   ```
4. Une fois connecté admin : **Admin → Settings → Access Tokens** → créer un jeton.
   L'exporter pour les commandes suivantes (jamais en argument CLI en clair) :
   ```
   export CTFD_TOKEN=<jeton>
   export URL=https://ctf.tg
   ```

## 3. Contenu

1. **Règlement dans /tos** (obligatoire, `make preflight` le vérifie) :
   ```
   make reglement-publish URL=$URL CTFD_TOKEN=$CTFD_TOKEN
   ```
2. **Champ « Université »** sur l'inscription (custom field) + **page d'accueil**
   (hero, `deploy/theme-home-hero.html`) : les poser via l'admin, ou via les
   étapes de `local/seed.py` réutilisables avec `CTFD_TOKEN` (elles ciblent l'URL
   fournie ; ne PAS relancer la partie /setup admin/admin).
3. **Import des challenges (ctfcli)** — cf. RUNBOOK §2 :
   ```
   python3 -m pip install --user ctfcli
   ctf init --url "$URL" --api-key "$CTFD_TOKEN"
   # installer les dossiers voulus (respecter les prérequis IA : ai0->ai1->ai2->ai3)
   ctf challenge install challenges/<cat>/<slug>   # ... pour chaque challenge retenu
   ```
   Les **86 servis implémentés sont `state: hidden`** → importés masqués (voulu).
   Ils ne deviennent jouables qu'après le Lot-5 (§4).

## 4. Lot-5 — rendre les servis jouables (AVANT de les publier)

Sur une machine **Docker** (arena ou poste), pour chaque servi : build image →
rejoue le solveur → flip `visible` si vert.

```
make lot5              # rapport pass/fail sur les 86 implémentés
make lot5 FLIP=1       # passe les OK en state: visible
```

Puis répercuter en prod : soit **ré-importer** les challenges passés `visible`
(ctfcli), soit basculer leur état dans **Admin → Challenges**. Côté arène, les
images doivent exister : `make check-arena` / `make push-images`.

> Sans Lot-5 vert, garder les servis `hidden`. Un servi visible sans image
> exploitable = joueurs bloqués.

## 5. Fenêtre + preflight (le gate)

1. **Calibrer les compteurs attendus** : `make preflight` a des défauts
   `EXPECT=369 challenges / CATS=20 catégories` (état du 23 septembre 2026). **Les ajuster au set réellement
   importé** (sinon FAIL sur les compteurs) :
   ```
   CTFD_TOKEN=$CTFD_TOKEN make preflight PHASE=preselection URL=$URL EXPECT=<n> CATS=<c>
   ```
2. **Fenêtre de présélection** (ven 23 19:00 → lun 26 00:00) :
   ```
   make presel-window APPLY=1 URL=$URL CTFD_TOKEN=$CTFD_TOKEN
   ```
3. **`make preflight` DOIT être 0 FAIL** avant d'ouvrir. Un FAIL = on ne bascule
   pas. Les `WARN`/`MANUAL` se lisent une par une (instancier, IA, images).

## 6. Sécurité avant ouverture

- [ ] **Resserrer `admin_cidrs`** : `196.170.0.0/15` est très large (~131k IP).
      Mettre l'IP fixe/VPN d'admin en `/32` si possible ; l'**agent SSM Online**
      reste la voie de secours si tu te verrouilles. `terraform apply` après
      changement.
- [ ] **Mot de passe admin fort** confirmé (aucun `admin`/`admin`, aucun compte
      `playtest` en prod).
- [ ] **HTTPS** actif (`https://ctf.tg`), redirection HTTP→HTTPS.
- [ ] **Sauvegardes** : timer `ctfd-backup` armé (`make backup-status` < 15 min) ;
      un `make backup` manuel avant toute grosse manip.
- [ ] **IMDSv2**, pas de port arène/IA ouvert sur Internet (déjà en Terraform).

## 7. Piste IA (conditionnelle au GPU)

Quota GPU en `CASE_OPENED` (0 vCPU). **Si le quota n'est pas accordé avant le
23** : lancer la présélection **sans la piste IA** (le reste tourne sans GPU).
Ne pas rendre les challenges IA visibles tant que le nœud Ollama n'est pas up
(`OLLAMA_URL` vide = challenges IA indisponibles). Décision à trancher côté humain.

## 8. Divers repérés

- [ ] **heap-note** : committer le binaire recompilé (ou `make local-fix-heapnote`),
      sinon l'image `ctf-pwn-heap-note` ne se reconstruit pas sur l'arène.

---

**Ordre résumé** —
_Maintenant (test, HTTP sur l'IP, inscriptions fermées)_ : `/setup` admin fort
(teams, hibris) → jeton API → `reglement-publish` + hero + université → import
ctfcli → **Lot-5** (`make lot5 FLIP=1`) → calibrer + `make preflight`.
_Avant la présélection_ : DNS `ctf.tg` → `make tls-init` → `make preflight` 0 FAIL
→ resserrer `admin_cidrs` → `presel-window` → ouvrir les inscriptions.
