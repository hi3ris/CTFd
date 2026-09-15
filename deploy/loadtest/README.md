# Test de charge (k6)

Outil du chantier 3 (`TODO-ameliorations.md`) : mesurer le front **avant** le
vendredi 23 octobre, sur le front de répétition, avec 300 équipes simulées.

| Fichier        | Rôle                                                                        |
| -------------- | --------------------------------------------------------------------------- |
| `seed.py`      | crée/purge les équipes `lt-0001…` et écrit `out/accounts.json` (flags, ids) |
| `scenarios.js` | un VU = une équipe : login, challenges, soumissions, scoreboard, KotH       |
| `instancer.js` | 50 équipes demandent/détruisent une instance servie en 10 min               |
| `lib.js`       | login + CSRF, métriques, rapport HTML/JSON (`out/*-summary.{html,json}`)    |

Un seul binaire à installer : [k6](https://grafana.com/docs/k6/latest/set-up/install/)
(`K6=/chemin/k6` si hors du PATH). Aucun import réseau dans les scripts.

```bash
cd deploy
make local-loadtest                      # stack locale, 100 VU, profil court (smoke)
make loadtest URL=https://ctf.exemple.tg # front de répétition, 300 VU, 5 + 15 + 1 min
make loadtest-instancer URL=...          # instancier, 50 équipes / 10 min
make loadtest-purge URL=...              # supprime les équipes lt-* et recalcule les valeurs
```

Seuils (verdict VERT/ROUGE en fin de run et dans `out/scenarios-summary.html`) :
`p95 < 800 ms` sur la liste des challenges, un challenge et le scoreboard ;
`0 %` de 5xx ; flags justes acceptés à `100 %` ; le rate-limit (429) observé par le
scénario `spammer` ; instancier : `spawn` ≥ 95 %, instance `running` en `p95 < 60 s`.

## Règles

- **Jamais sur la base de l'épreuve.** `seed.py` refuse une URL non locale sans
  `--allow-remote`, et refuse de toute façon une plateforme qui porte plus de 20
  équipes hors `lt-` (c'est l'épreuve). `make loadtest` passe `--allow-remote`.
- **Avant les fenêtres.** `/attempt` et `/spawn` répondent 403 hors `start`/`end` ;
  le seed refuse si `start` est dans le futur. Ordre : charge → `make backup` ou
  restauration du dump d'avant test → fenêtres → `make preflight`.
- **Après le test** : `make loadtest-purge` (équipes, solves, valeurs dynamiques
  recalculées) **puis** restauration du dump pris avant le test (`make restore`),
  qui remet aussi les first bloods et les statistiques à zéro. Le purge seul
  suffit pour la stack locale.
- Les chiffres servent à figer `WORKERS`, la taille du front et `POLL_MS` du
  scoreboard (ROADMAP « Décider Savings Plan / taille du front »). Noter le run
  dans `infra-audit.md` (section « Test de charge »).
