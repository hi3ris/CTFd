# Challenges IA : conception de la chaine et controle de charge

Note de conception pour le lot 3 (plugin `ai_challenges`) et le lot 4 (les
challenges eux-memes). A lire avant de les implementer.

## Le principe retenu

Les challenges IA forment une **chaine** : chaque niveau ne se debloque qu'en
resolvant le precedent. Le premier ne consomme aucune inference. Les suivants
sont de plus en plus durs et de plus en plus gourmands.

L'effet recherche n'est pas seulement pedagogique, il est budgetaire : sur
~300 participants en preselection, seule une fraction atteindra les niveaux
qui font tourner le GPU. Le gating est le principal levier de capacite du
dispositif.

## CTFd sait deja faire la chaine

Aucun developpement n'est necessaire pour le verrouillage lui-meme. Le champ
`requirements` d'un challenge accepte une liste `prerequisites` d'identifiants
de challenges, et CTFd l'applique cote serveur :

- `CTFd/api/v1/challenges.py` : la liste des challenges masque (`type:
  "hidden"`, nom `???`) ou retire ceux dont les prerequis ne sont pas remplis,
  selon l'option `anonymize` ;
- le meme fichier renvoie **403** sur `/api/v1/challenges/<id>/attempt` si les
  prerequis ne sont pas satisfaits ;
- la comparaison porte sur `account_id`, donc en mode equipes le deblocage est
  bien collectif, pas individuel.

Cote administration : *Challenge > Requirements*, en cochant les challenges
prealables.

## Le piege a ne pas rater

**CTFd applique les prerequis sur ses propres routes, pas sur les votres.**

Le plugin `ai_challenges` ajoutera une route de chat, par exemple
`POST /api/v1/ai/<challenge_id>/message`. C'est une route neuve : rien ne la
protege automatiquement. Sans verification explicite, n'importe quel joueur
peut scripter un appel vers le chat du niveau 3 sans jamais avoir resolu le
niveau 1.

Consequences, dans cet ordre de gravite :

1. **Capacite** : les 300 participants peuvent taper directement sur le
   niveau le plus lourd. Tout le raisonnement de dimensionnement s'effondre et
   le GPU sature des la premiere heure.
2. **Equite** : la progression imposee aux autres ne s'applique plus.
3. **Divulgation** : selon le challenge, le system prompt du niveau 3 peut
   fuiter avant que quiconque ait atteint ce niveau.

La route de chat doit donc rejouer exactement le controle que CTFd fait sur
`/attempt` : recuperer les `Solves` du compte, les intersecter avec
`challenge.requirements["prerequisites"]`, et abandonner en 403 sinon. La
verification se fait sur `account_id` pour rester coherente avec le mode
equipes.

## L'echelle proposee

| Niveau | Prerequis | Inference | Idee |
|---|---|---|---|
| 0 | aucun | **aucune** | Analyse statique : une fuite de system prompt dans un fichier fourni, une carte de modele, un historique de conversation exporte. Le flag s'obtient en lisant, pas en discutant. |
| 1 | niveau 0 | legere | System prompt naif gardant un flag. Quelques echanges suffisent. Reponses courtes imposees. |
| 2 | niveau 1 | moyenne | Filtre de sortie sur le flag (regex + variantes encodees). Il faut faire produire le flag sous une forme detournee. |
| 3 | niveau 2 | lourde | Le flag n'est jamais dans le contexte : il est accessible via un outil que le modele peut appeler. Le joueur doit detourner l'usage de l'outil. Contexte long, plusieurs tours. |

Le niveau 0 sans inference est ce qui rend la categorie accessible aux 300
participants sans aucun cout GPU, tout en filtrant naturellement la suite.

## Controle d'admission dans le plugin

Le gating reduit la charge mais ne la borne pas. Trois garde-fous a
implementer, du plus important au moins important :

1. **Plafond de sessions simultanees par niveau.** Le niveau 3 doit avoir un
   plafond bas (quelques equipes a la fois). Au-dela, reponse explicite
   « modele occupe, reessayez » plutot qu'une attente silencieuse.
2. **Budget de tokens par equipe et par niveau**, remis a zero sur une fenetre
   glissante. Empeche une equipe de monopoliser le GPU par du brute force
   automatise, sans penaliser une equipe qui reflechit.
3. **Rate-limit par equipe** sur le nombre de messages par minute, dans le
   meme esprit que `incorrect_submissions_per_min` deja present dans CTFd.

Cote infrastructure, `OLLAMA_MAX_QUEUE` borne deja la file et renvoie 503
quand elle est pleine. Le plugin doit traduire ce 503 en message lisible pour
le joueur, jamais en erreur brute.

## Ce que la chaine change pour le dimensionnement

Sans gating, il fallait prevoir ~300 joueurs simultanes sur le modele. Avec la
chaine, l'entonnoir attendu ressemble a :

- niveau 0 : ~300 joueurs, **0 inference** ;
- niveau 1 : quelques dizaines a une centaine de deblocages, pointe de l'ordre
  de 20-30 conversations simultanees ;
- niveaux 2 et 3 : quelques dizaines d'equipes au total, pointe d'une dizaine.

La `g4dn.xlarge` retenue reste le bon choix : avec `OLLAMA_NUM_PARALLEL=8` et
le modele epingle en VRAM, elle sert cette pointe confortablement au lieu
d'etre a la limite. Le gain se prend en marge et en qualite de service, pas en
reduction de la facture GPU, qui est deja au minimum de la gamme.

Ces chiffres sont des hypotheses de conception. A confirmer par une repetition
avec quelques dizaines de comptes de test avant le 23 octobre.

## Journalisation

Chaque tentative doit etre tracee : equipe, niveau, prompt, reponse, tokens
consommes, verdict. Trois usages : detecter la triche et le partage de
solution, ecrire les write-ups apres l'evenement, et mesurer la charge reelle
pour dimensionner l'edition suivante. La table doit etre exportee avant
`make season-down`, qui detruit les instances.
