# Deploiement du CTF sur AWS

Architecture pensee pour un evenement **annuel** avec un budget contraint :
la plateforme reste accessible toute l'annee, mais l'infrastructure lourde
n'existe que pendant l'evenement.

```
                        Internet
                            |
                  [ IP fixe / DNS du CTF ]
                            |
   +------------------------v--------------------------+
   |  FRONT  --  t4g.small (ARM)  --  ALLUME 365 j/an   |
   |  nginx + TLS | CTFd | MariaDB | Redis | frps       |
   |  ~17 USD/mois                                      |
   +------------------------+--------------------------+
                            |  tunnel frp + SSH + HTTP
                            |  (reseau prive uniquement)
   +------------------------v--------------------------+
   |  ARENA  --  c6a.2xlarge (x86)  --  N'EXISTE QUE    |
   |             PENDANT L'EVENEMENT                    |
   |  Docker Swarm (1 instance par equipe) | Ollama     |
   |  ~0.31 USD/h, soit ~15 USD pour 48 h               |
   +---------------------------------------------------+
```

## Pourquoi cette separation

Le front porte tout ce qui doit survivre entre deux editions : comptes,
scoreboards des editions passees, archives des challenges, write-ups,
inscriptions a l'edition suivante. Il est minuscule et pas cher.

L'arena porte tout ce qui coute cher : les conteneurs par equipe et le modele
de langage des challenges IA. Elle est **detruite** apres l'evenement, pas
seulement eteinte : une instance arretee ne facture plus le calcul mais
continue de facturer son disque.

## Cout reel (eu-west-3, tarifs a la demande)

| Poste | Quand | Cout |
|---|---|---|
| Front `t4g.small` | toute l'annee | ~12 USD/mois |
| Disque front gp3 20 Go | toute l'annee | ~1.60 USD/mois |
| IPv4 publique fixe | toute l'annee | ~3.60 USD/mois |
| **Sous-total hors evenement** | | **~17 USD/mois, soit ~205 USD/an** |
| Arena `c6a.2xlarge` | 48 h d'evenement | ~15 USD |
| Disque arena 100 Go | 48 h | ~0.50 USD |
| **Total annuel** | | **~220 USD** |

Trois leviers si c'est encore trop :

1. **Savings Plan Compute 1 an** sur le front : environ -30 % sur les 12 USD.
2. **`front_instance_type = "t4g.micro"`** (1 Go de RAM) : ~6 USD/mois. Tient
   hors evenement, mais il faut remonter en `t4g.small` avant l'evenement.
3. **`arena_use_spot = true`** pour les repetitions : ~-70 % sur l'arena. A
   laisser sur `false` le jour J, une interruption AWS tuerait toutes les
   instances des equipes en cours.

Les 100 USD de credits offerts aux nouveaux comptes AWS (jusqu'a 200 USD apres
les taches d'onboarding, plan gratuit valable 6 mois) couvrent donc environ la
premiere demi-annee.

## Mise en place, une seule fois

```bash
cd deploy
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# renseigner ssh_public_key, admin_cidrs, domain_name

make init
make front-up          # cree le VPC et le front
```

Pointer le DNS du CTF sur l'IP affichee, puis :

```bash
make ssh-front
# sur le front :
sudo -u ubuntu git clone -b claude/ctf-platform-free-ptiggj \
  https://github.com/hi3ris/CTFd.git /opt/ctfd/CTFd
cd /opt/ctfd/CTFd/deploy/front
cp .env.example .env
openssl rand -hex 32   # -> SECRET_KEY
openssl rand -hex 24   # -> DB_PASSWORD
openssl rand -hex 24   # -> DB_ROOT_PASSWORD
exit
```

```bash
make deploy            # build + demarrage de CTFd
```

## Rythme annuel

```bash
# ~1 semaine avant l'evenement
make event-up          # cree l'arena, la relie au front, telecharge le modele

# pendant l'evenement
make logs
make backup            # a lancer regulierement

# des la fin
make event-down        # sauvegarde puis detruit l'arena
make cost              # verifie qu'il ne reste que le front
```

Entre deux editions, le site reste en ligne : les joueurs consultent les
scoreboards passes et s'inscrivent pour l'edition suivante. Les challenges
Docker et IA affichent simplement « indisponible hors evenement ».

## Securite

- `admin_cidrs` doit contenir l'IP de votre bureau ou VPN, **jamais**
  `0.0.0.0/0` : c'est ce qui protege SSH.
- L'arena n'a aucun port ouvert sur Internet. Les instances des equipes sont
  exposees uniquement via le tunnel frp qui aboutit sur le front.
- CTFd pilote le Docker de l'arena par SSH (`ssh://`), pas par un port
  2375/2376 expose : rien a proteger par PKI, et une API Docker joignable
  vaut un shell root.
- IMDSv2 est obligatoire sur les deux instances : un SSRF dans un challenge
  ne permet pas de voler les credentials de l'instance.

## Ce qui reste a faire

Ce lot couvre l'infrastructure et le front. Les lots suivants :

- **Lot 2** : plugin `ctfd-whale` + un challenge Docker par equipe de demo,
  avec flag dynamique par equipe.
- **Lot 3** : plugin `ai_challenges` (backend Ollama, chat, rate-limit, logs).
- **Lot 4** : challenges d'exemple, type A (prompt injection, 3 niveaux) et
  type B (pickle RCE, adversarial example).
