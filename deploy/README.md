# Deploiement du CTF sur AWS

CTF annuel a deux phases rapprochees. Rien ne tourne en dehors de ces
fenetres : les comptes joueurs sont supprimes entre deux editions (nouveaux
participants, nouvelles equipes), donc rien ne justifie de payer un serveur
toute l'annee.

## Calendrier 2026

| Phase | Dates | Joueurs | Ce qui tourne |
|---|---|---|---|
| `setup` | avant le 23 octobre | equipe d'organisation | front seul |
| `preselection` | **23-24 octobre** | ~300 | front + arena + noeud IA |
| `final` | **29-30 octobre** | ~50 (10 equipes de 4-5) | front + arena + noeud IA |
| `off` | le reste de l'annee | — | rien, sauf les archives S3 |

Entre le 24 et le 29 octobre, repassez en `setup` : l'arena et le noeud IA,
qui sont les postes chers, disparaissent pendant que le front continue
d'afficher les resultats de la preselection.

## Architecture

```
                          Internet
                              |
    phase off  ->  archives statiques S3/CloudFront (~0.50 USD/mois)
    phase live ->  [ front : nginx/TLS + CTFd + MariaDB + Redis + frps ]
                              |
              +---------------+----------------+
              |                                |
   [ arena : Docker Swarm ]          [ noeud IA : Ollama sur GPU ]
   instances par equipe              challenges prompt injection
   aucun port public                 aucun port public
```

Trois machines, trois roles, chacune allumee uniquement quand elle sert :

- **Front** — ARM (Graviton), le moins cher. Porte CTFd et la base. C'est le
  seul point d'entree public.
- **Arena** — x86 obligatoire : les challenges pwn et reverse sont compiles
  pour cette architecture. Heberge un conteneur par equipe et par challenge.
- **Noeud IA** — GPU T4 (`g4dn.xlarge`). En preselection, ~300 joueurs peuvent
  discuter avec le modele en meme temps ; sur CPU un modele 8B sert quelques
  tokens par seconde et s'effondre des la dizaine de requetes paralleles. Le
  GPU absorbe la charge pour ~0.60 USD/h.

## Cout estime pour l'edition 2026

| Poste | Duree | Estimation |
|---|---|---|
| `setup` (front `t4g.small`) | 10 jours avant | ~5 USD |
| `preselection` 23-24 oct (front + `c6a.4xlarge` + `g4dn.xlarge`) | 48 h | ~62 USD |
| Entre-deux en `setup` | 5 jours | ~2 USD |
| `final` 29-30 oct (front + `c6a.2xlarge` + `g4dn.xlarge`) | 48 h | ~46 USD |
| Archives S3 + CloudFront | 12 mois | ~6 USD |
| **Total edition 2026** | | **~120 USD** |

Ce sont des estimations a partir des tarifs a la demande d'`eu-west-3` ;
verifiez avec le calculateur AWS avant de vous engager. Les 100 USD de credits
offerts aux nouveaux comptes (jusqu'a 200 USD apres les taches d'onboarding)
couvrent donc l'essentiel de la premiere edition.

Deux leviers si besoin :

- `arena_use_spot = true` pendant les repetitions : ~-70 % sur l'arena. A
  laisser sur `false` les 23-24 et 29-30 octobre, une interruption AWS tuerait
  les instances des equipes en pleine resolution.
- Eteindre l'arena et le noeud IA la nuit si l'epreuve ferme : `make
  phase-setup` le soir, `make phase-preselection` le matin. Environ -40 % sur
  les deux jours, au prix d'une manipulation quotidienne.

## A FAIRE DES MAINTENANT : le quota GPU

Sur un compte AWS neuf, le quota **« Running On-Demand G and VT instances »**
est frequemment a 0, et son augmentation prend souvent plusieurs jours ouvres.
Sans ce quota, aucune `g4dn.xlarge` ne demarrera le 23 octobre.

```bash
cd deploy
make check-gpu-quota
```

Une `g4dn.xlarge` consomme 4 vCPU de ce quota. Demandez au moins 8 pour avoir
de la marge.

## Mise en place

```bash
cd deploy
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# renseigner ssh_public_key, admin_cidrs, domain_name

make init
make check-gpu-quota      # a faire en premier
make phase-setup          # cree le front
```

Puis, sur le front, creer `deploy/front/.env` a partir de `.env.example`
(trois secrets a generer avec `openssl rand -hex 32`), et relancer
`make deploy`.

## Deroule d'une edition

```bash
# avant                          front seul, preparation des challenges
make phase-setup

# 23 octobre au matin            ~300 joueurs
make phase-preselection
make gpu                         # verifie que le modele est charge en VRAM

# 24 octobre au soir             on garde les resultats affiches
make backup
make phase-setup                 # arena + GPU detruits, front conserve

# 29 octobre au matin            10 equipes finalistes
make phase-final

# 30 octobre au soir             fin de l'edition
make season-down                 # sauvegarde, archive, puis detruit tout

make cost                        # doit afficher "phase off"
```

`make season-down` fait trois choses dans l'ordre : dump de la base vers S3,
export statique du scoreboard vers `s3://<bucket>/site/<annee>/`, puis
destruction de toutes les instances EC2. Le domaine peut ensuite pointer sur
le site statique jusqu'a l'edition suivante.

## Securite

- `admin_cidrs` n'a pas de valeur par defaut : Terraform refuse de tourner
  tant que vous n'avez pas designe les IPs autorisees en SSH.
- Ni l'arena ni le noeud IA n'ont de port ouvert sur Internet. Les instances
  des equipes passent par un tunnel frp qui aboutit sur le front.
- Ollama n'est joignable que depuis le front. Un joueur qui l'atteindrait
  directement contournerait les garde-fous et le rate-limit du plugin.
- CTFd pilote le Docker de l'arena en `ssh://` plutot que par un socket
  2375/2376 expose : une API Docker joignable vaut un shell root.
- IMDSv2 impose partout : un SSRF dans un challenge ne donne pas acces aux
  credentials d'instance.
- Le bucket d'archives porte `prevent_destroy` : `terraform destroy` ne peut
  pas effacer l'historique des editions par accident. Seul le prefixe `site/`
  y est public, les sauvegardes de base restent privees.

## Ce qui reste a faire

- **Lot 2** — plugin `ctfd-whale` + challenge Docker par equipe de demo, avec
  flag dynamique par equipe.
- **Lot 3** — plugin `ai_challenges` : backend Ollama, chat, rate-limit par
  equipe, journalisation des tentatives, gestion du 503 quand la file est
  pleine.
- **Lot 4** — challenges d'exemple, type A (prompt injection, 3 niveaux) et
  type B (pickle RCE, adversarial example).
