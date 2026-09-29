# Audit de résistance au solve par IA — NCTF26

_Outil : `deploy/scripts/ai_resistance_audit.py` (`make ai-audit`). Ce document
est le cadre d'interprétation ; les chiffres bruts sortent de l'outil._

## La question, précisément

Pour chaque challenge : **un seul appel LLM, sans outils, à partir du paquet
public (énoncé + fichiers joints), récupère-t-il le flag ?** C'est le plancher
qu'un agent franchit trivialement. Un challenge qui échoue à ce test **et** qui
siège dans la bande de points qui décide le classement est là où un agent
achète du rang — pas de la compétence.

Ce n'est pas « l'IA peut-elle le résoudre » (un agent avec outils va plus loin) ;
c'est le **plancher**. Ce qui tombe au plancher tombe a fortiori face à un agent.

## État actuel (mesuré le 23/09)

|                                                             | Nombre  |
| ----------------------------------------------------------- | ------- |
| Challenges                                                  | **204** |
| Servis (`team_instance`, flag par équipe, état live)        | **27**  |
| Statiques (fichier à télécharger + transformer)             | **177** |
| Statiques dans la bande **150–350 pts** (décide le tableau) | **115** |

**Le constat central : 177/204 sont des artefacts statiques téléchargeables, et
115 d'entre eux sont dans la zone qui classe.** C'est le profil « un fichier, une
transformation, un flag » — exactement ce qu'un agent traite en un coup.

Nuance qui compte : ce n'est pas un défaut en soi. Les 16 warmups à 50 pts,
tout le monde les résout, ils ne classent personne — un agent qui les fait en
1 s ne change rien. **Le danger, c'est l'épreuve à 300–500 qui tombe en un
coup** : celle-là distribue les points à la meilleure boucle, pas à la meilleure
tête. Le haut de la liste d'exposition (`risque × points`) sort en tête du CSV.

## Comment lire l'outil

- **`--heuristic`** (défaut, hors-ligne) : score structurel par features (servi
  vs statique, artefact binaire ou texte, prior de catégorie, points), trié par
  **impact = risque × points**. Une triage rapide, **pas une vérité** — elle dit
  où pointer la passe coûteuse en premier.
- **`--model` / `--ollama`** (vérité terrain) : assemble le paquet une-passe et
  demande au modèle **le flag seul, ou UNKNOWN**, sans outils, un tour ; note
  contre le vrai flag. **À lancer avec le modèle le plus fort dont tu disposes** —
  `llama3.1:8b` en local sous-estime massivement et te rassurera à tort.

```bash
# vérité terrain contre un endpoint OpenAI-compatible :
AI_AUDIT_API_KEY=... make ai-audit MODEL=https://api.example/v1 MODEL_NAME=<fort>
# ou en local :
make ai-audit OLLAMA=http://localhost:11434 MODEL_NAME=llama3.1:70b
```

Sortie : CSV `challenge,category,points,kind,risk,impact,verdict`. Les lignes à
traiter : `kind=static` **+** `verdict=SOLVED` **+** points élevés.

## Le cadre d'action (croisement points × fragilité)

On agit sur le **croisement**, pas sur la fragilité seule :

|             | Tombe en un coup                                                                      | Résiste        |
| ----------- | ------------------------------------------------------------------------------------- | -------------- |
| **50–150**  | laisser — c'est un warmup, il fait son travail                                        | bien           |
| **300–500** | **le problème** : convertir en servi, ajouter une étape, re-tarifer à 150, ou retirer | le cœur du CTF |

Quatre leviers, du moins au plus coûteux :

1. **Re-tarifer** (1 ligne de YAML) — un one-shot à 450 pts descend à 150. Gratuit,
   immédiat. À faire sur tout `SOLVED` au-dessus de 300.
2. **Retirer** (gratuit) — un doublon fragile en trop.
3. **Ajouter une étape serveur** — transformer le « colle le fichier » en « il faut
   interroger un service » (déplace vers le servi).
4. **Réécrire en servi / CVE / chaîné** — le plus cher, le plus résistant. C'est
   la direction des nouvelles catégories (`cve/`, challenges à chaîne de vuln).

## Ce qui résiste déjà, structurellement

Les **27 servis** (web instanciés, pwn, cloud, IA, boot2root KotH, + `cve/hookrelay`)
sont les plus résistants **par construction** : flag unique par équipe, état
serveur, aucun artefact à coller dans un chat. Toute la stratégie « anti-solve
IA » est de **déplacer le poids du tableau vers eux** — pas de piéger les
statiques.

## Limites honnêtes

- Le test une-passe est un **plancher**. Un agent qui pilote des outils (pwntools,
  un désassembleur, un solveur) va au-delà ; l'audit ne le mesure pas.
- Le **modèle choisi change le résultat**. Fais-le avec le plus fort accessible,
  sinon l'audit te ment par optimisme.
- Les artefacts **binaires** (pcap, images, binaires) sont sous-lus par la passe
  texte : l'outil les signale mais un modèle multimodal / un agent les ouvre. Les
  lignes binaires à haut score méritent une vérification manuelle.
- La présélection **filtre**, la finale **décide**. L'objectif n'est pas une
  présélection inviolable — c'est qu'elle soit assez discriminante pour que les
  ~10 bonnes équipes en sortent. La finale sur site tranche pour de bon.

## Prochaine action

1. Lancer `make ai-audit` avec ton modèle le plus fort → CSV de vérité terrain.
2. Trier `SOLVED` × points ; re-tarifer/retirer le haut de liste (gratuit).
3. Sur les 3–4 épreuves de tête, décider : re-tarifage suffisant, ou réécriture
   en servi/chaîné (cf. `deploy/challenge-chains-blueprint.md`).
