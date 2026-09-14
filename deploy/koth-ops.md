# King of the Hill — exploitation (KotH)

Le KotH est composé de deux morceaux :

1. **Le plugin CTFd `koth`** (`CTFd/plugins/koth/`) — dérive le jeton par équipe,
   affiche la page joueur (menu **King of the Hill**), et fait tourner un
   **scorer** qui attribue des points via des `Awards` (donc visibles sur le
   scoreboard kart sans rien d'autre).
2. **Un ou plusieurs services « colline »** partagés (`challenges/koth/throne/`,
   image `ctf-koth-throne`) — un seul conteneur que toutes les équipes attaquent.

Aucune table SQL nouvelle, aucune migration : le scoring passe par les `Awards`
du cœur de CTFd.

## Test en local (une commande)

Sur une machine avec Docker, après `make local-up` (+ `make local-seed`) :

```bash
cd deploy
make local-koth
```

Ça construit et lance **deux collines** (`profil koth`), génère un secret scorer
de dev et recrée le conteneur CTFd avec `KOTH_HILLS` + `KOTH_SCORER_SECRET` — le
plugin s'active alors (`KOTH_TICK=15 s` en local) :

- **The Throne** (HTTP) — `http://localhost:28900` : fuite XFF → tenue du trône
  par re-signature.
- **The Citadel** (SSH « root-wars ») — `ssh player@localhost -p 28901` (mot de
  passe `player`) : deviens root, écris ton jeton dans `/koth/king`, tiens-le.

Ouvre le menu **King of the Hill** dans CTFd, récupère le jeton de ton équipe,
puis tiens une colline :

```bash
challenges/koth/throne/solution/solve.sh  http://localhost:28900 <ton-jeton>
challenges/koth/citadel/solution/solve.sh localhost 28901 <ton-jeton>   # needs sshpass
```

Le plugin score **toutes** les collines de `KOTH_HILLS` en parallèle : une hill
peut être HTTP (Throne) ou une box SSH root-wars (Citadel), tant qu'elle expose
un `/king` lisible par le scorer.

Le score de l'équipe doit monter d'un cran de `points` à chaque tick tant que le
trône est tenu. `make local-down` / `make local-reset` arrêtent aussi la colline.
Le reste de ce document décrit le déploiement **arène** (prod).

## Secrets (trois, séparés)

| Secret               | Où                          | Rôle                                                         |
| -------------------- | --------------------------- | ------------------------------------------------------------ |
| `HILL_KEY`           | conteneur colline seulement | autorise une revendication ; **cible de l'exploit**          |
| `KOTH_SCORER_SECRET` | CTFd **et** colline         | lecture de `/king` par CTFd uniquement (`X-Scorer-Token`)    |
| `KOTH_GLOBAL_SECRET` | CTFd seulement              | dérive le jeton par équipe (défaut : `CTF_TEAM_FLAG_SECRET`) |

Générer : `openssl rand -hex 32` pour chacun. `HILL_KEY` peut être laissé vide
(la colline en génère un aléatoire au démarrage) ; le fixer le rend stable entre
redémarrages.

## Déployer une colline

```bash
docker build -t ctf-koth-throne challenges/koth/throne
# via le compose de la colline (challenges/koth/throne/docker-compose.yml) :
KOTH_SCORER_SECRET=<...> KOTH_THRONE_HILL_KEY=<...> docker compose up -d
```

La colline écoute en interne sur `:8080` (jamais publiée directement). Exposez-la
aux joueurs via le reverse-proxy front / FRP, comme les autres services servis.

## Configurer le plugin CTFd

Variables d'environnement sur le conteneur **CTFd** :

```bash
KOTH_SCORER_SECRET=<le même que la colline>
# KOTH_GLOBAL_SECRET=<...>          # sinon reprend CTF_TEAM_FLAG_SECRET
KOTH_TICK=30                        # secondes entre deux passes de scoring
# KOTH_FRESH_WINDOW=60              # défaut 2*TICK ; une revendication plus vieille ne compte plus
KOTH_HILLS='[
  {"id":"koth-throne","name":"The Throne",
   "url":"http://koth-throne:8080",
   "player_url":"https://ctf.exemple.tg/koth-throne",
   "points":5}
]'
```

- `url` = adresse **interne** (réseau compose) que CTFd interroge.
- `player_url` = ce que les joueurs voient / attaquent (via le front).
- `points` = points attribués **par tick** au tenant du trône.

Le plugin ne score que si `KOTH_SCORER_SECRET`, `KOTH_GLOBAL_SECRET` et au moins
une colline valide sont présents (`is_active()`), et un seul worker gunicorn
tient le scorer (verrou `fcntl`), comme le reaper de l'instancier.

## Présélection vs finale

Le plugin score **toutes** les collines de `KOTH_HILLS` en même temps — il suffit
de changer la liste selon la phase :

- **Présélection (~300 joueurs)** : une colline, `points` faibles (p.ex. 3–5) et
  `KOTH_TICK` ~30 s pour que le KotH complète le jeopardy sans l'écraser.
- **Finale (10 équipes)** : une (ou deux) colline(s) plus « chères » (p.ex. 10)
  et éventuellement un `KOTH_TICK` plus court pour rendre les retournements plus
  nerveux. Comptez le total : `points × (durée / tick)` = plafond de points si une
  équipe tient tout du long — calez-le sur le poids voulu vs les épreuves jeopardy.

Exemple finale 2 h, 1 colline, `points=10`, `tick=30` → plafond
`10 × (7200/30) = 2400` pts pour une tenue parfaite.

## Vérifier en vrai (bring-up arène)

1. `docker build` la colline, la lancer avec `SCORER_SECRET`.
2. Régler les `KOTH_*` sur CTFd, redémarrer CTFd.
3. Ouvrir le menu **King of the Hill** en tant qu'équipe → le jeton s'affiche.
4. Lancer `challenges/koth/throne/solution/solve.sh <player_url> <jeton>` →
   vérifier que la page montre l'équipe sur le trône et que son score monte d'un
   cran de `points` à chaque tick.
5. Arrêter le solveur > `FRESH_WINDOW` → le scoring s'arrête (trône « expiré »).

## Notes de sécurité

- `/king` n'est jamais lisible sans `X-Scorer-Token` : les équipes ne peuvent pas
  lire le trône directement (la page CTFd le montre, tronqué).
- Le jeton d'équipe est une **identité**, pas un secret exploitable : planter le
  jeton d'une autre équipe la ferait scorer, elle — aucun intérêt à tricher.
- La colline ne connaît aucune équipe et ne dérive aucun jeton : compromettre la
  colline n'expose pas le mapping jeton→équipe (il vit dans CTFd).
