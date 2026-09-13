# Validation locale — toute la plateforme sur une machine, avant AWS

Objectif : voir et tester **exactement** ce que verront les participants
(theme hibris, accueil, 36 challenges, instances par equipe, chaine IA) sans
toucher a AWS ni depenser un centime. Tout tourne dans Docker sur votre
machine ; les memes images, le meme code, les memes plugins qu'en production.

Pre-requis : Docker (avec Compose v2), Python 3.10+, `pip install ctfcli requests`.
~8 Go de disque pour les images de challenges ; +5 Go si vous activez l'IA
(modele Ollama).

## Le parcours complet

```bash
cd deploy
make local-up               # CTFd + MariaDB + Redis  ->  http://localhost:8000
make local-build-images     # les 20 images ctf-* des challenges servis
make local-seed             # setup (NCTF25, equipes, theme hibris), accueil, 36 challenges
make local-smoke            # pages, theme, assets, API, prerequis de la chaine IA
make local-playtest         # spawn -> solveur de reference -> soumission, pour chacun
```

Puis ouvrez http://localhost:8000 : `admin` / `admin` pour l'administration,
`playtest` / `playtest` pour jouer (deja dans une equipe). Naviguez comme un
participant : accueil, board, un challenge servi (bouton *Demarrer l'instance*),
scoreboard, une 404.

Avec l'IA (optionnel, CPU) :

```bash
make local-up-ai            # + Ollama + passerelle d'admission ; tire llama3.1:8b (~5 Go)
OLLAMA_MODEL=llama3.2:3b make local-up-ai   # variante legere pour un portable
make local-playtest ARGS="--ai --only ai/ai1-naive-guard"
```

## Ce que chaque etape prouve

| Etape | Ce qui est verifie | Ce qui casserait sur AWS sinon |
|---|---|---|
| `local-up` | l'image CTFd se construit, les plugins chargent, migrations OK | `make deploy` en echec au premier `phase-setup` |
| `local-build-images` | chaque Dockerfile de challenge construit | `make push-images` pousse une image manquante -> instance 500 |
| `local-seed` | les 36 `challenge.yml` s'importent (types, flags `team_hmac`, fichiers, prerequis) | import a la main le jour J, erreurs silencieuses |
| `local-smoke` | theme hibris rendu, aucune trace CTFd, tous les assets en 200, chaine IA verrouillee | participants voient du CTFd / du CSS casse |
| `local-playtest` | l'instancier spawne, le solveur obtient le flag, la plateforme l'accepte (`team_hmac`) | un challenge insoluble decouvert par les joueurs |

Le playtest donne un verdict par challenge : `PASS`, `FAIL`, `GATED`
(prerequis IA ; `--unlock-chain` pour tester ai2/ai3 sans ai1), `STUB` (ai3 et
agent-tool-abuse : seul le self-test hors-ligne est automatisable, le jailbreak
d'un LLM se rejoue a la main), `SKIP` (ai1 sans `--ai`).

## Differences assumees avec la production

- Pas de nginx/TLS : CTFd ecoute directement sur :8000.
- L'instancier pilote **le Docker de votre machine** (socket monte) et publie
  les ports en direct sur `127.0.0.1:28000-28100` (`INSTANCER_PUBLISH=direct`)
  au lieu de passer par le tunnel ssh + frp de l'arena. Le code de spawn, les
  limites (memoire, CPU, pids), l'injection de `FLAG`/`CHALLENGE_SECRET` et la
  validation `team_hmac` sont **identiques**.
- Les conteneurs IA joignent la passerelle via `host.docker.internal:8600`
  (injecte par l'instancier en mode direct) au lieu de l'IP privee du front.
- Secrets de dev en clair dans le compose : ils ne servent qu'ici.

Ce qui n'est **pas** couvert localement et reste pour la repetition AWS (Lot 5) :
le tunnel ssh/frp, le Swarm de l'arena, la charge a 300 equipes, TLS/DNS.

## Sans Docker du tout

`make test` a la racine (ou `pytest tests/test_theme_hibris.py
tests/test_team_instancer_publish.py`) rend toutes les pages du theme sur
SQLite et verifie que chaque asset reference existe : c'est le filet de
securite minimal, il tourne en 5 secondes.

## Nettoyage

```bash
make local-down     # arrete, garde la base et les uploads
make local-reset    # arrete et efface tout (base, uploads, modele Ollama, instances)
```
