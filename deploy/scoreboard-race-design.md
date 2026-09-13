# Scoreboard « La Course NCTF » — étude & plan

Transformer le scoreboard en **course animée** : chaque équipe est un coureur
qui avance selon son score, les dépassements s'animent en direct, avec un
compte à rebours *avant* le départ et un *temps restant* pendant l'épreuve.
Objectif d'ambiance : un écran qu'on projette dans la salle, lisible, « waou »,
et qui ne ressemble en rien à un scoreboard CTFd standard.

> Cosmétique pure : **aucun impact sur le scoring**. La course ne fait que
> *lire* les données que CTFd expose déjà. Si le JS casse, la table reste.

---

## 1. Ce sur quoi on s'appuie (déjà présent, rien à développer côté serveur)

| Donnée | Source | Remarque |
|---|---|---|
| Rang + score + nom par équipe | `GET /api/v1/scoreboard` (`CTFd.api.get_scoreboard_list()`) | ordonné, public |
| Détail top N (courbe de score dans le temps) | `GET /api/v1/scoreboard/top/<count>` | pour d'éventuelles « accélérations » |
| Début / fin de l'épreuve | `init.start` / `init.end` (epoch) injectés dans `base.html` | alimente les deux countdowns |
| Gel du classement | géré serveur : l'API renvoie l'état gelé aux non-admins | la course se fige toute seule |
| Nonce CSRF, mode équipes | `init.csrfNonce`, `init.userMode` | déjà là |

**Conséquence** : c'est un travail **100 % thème** (un template + un JS + un CSS),
zéro modification de plugin, zéro risque pour le scoring ou la sécurité.

---

## 2. Le problème d'échelle (300 équipes) — décision de conception

On ne peut pas afficher 300 coureurs lisibles. Modèle retenu :

- **Top N coureurs pleins** (défaut 12, configurable) : nom, engin, score, rang.
- **Peloton agrégé** : une bulle « +288 équipes » derrière, qui respire, pour
  ne pas mentir sur la taille du champ.
- **Ton coureur** (si connecté et hors top N) : une voie surlignée « toi · 47ᵉ »
  fixée en bas, pour que chaque équipe se retrouve.
- **Mode vidéoprojecteur** (`?big=1` ou plein écran) : top 10-15, gros, sans
  chrome, pour l'écran de la salle.

---

## 3. Mécanique de la course

**Piste horizontale**, gauche = ligne de départ, droite = tête de course.

- **Position X** = `score / scoreMax_courant` mappé sur ~[5 %, 90 %] de la piste
  (le leader n'atteint jamais 100 % : la « ligne d'arrivée » n'est franchie qu'à
  la fin de l'épreuve, sinon plus rien ne bouge visuellement une fois qu'on a un
  gros leader). L'écart en X reflète l'écart de points → on *voit* la domination.
- **Voie Y** = rang courant. Quand deux équipes changent d'ordre, leurs voies
  s'échangent avec une transition douce : **c'est le dépassement**, l'effet clé.
- **Coup d'accélérateur** : à chaque nouveau solve détecté (score qui monte
  entre deux polls), petit boost visuel (traînée / poussière / flash tricolore)
  sur le coureur concerné + son nom qui pulse une fois.
- **Égalités** : CTFd départage par *date du dernier solve* (déjà dans l'ordre
  de l'API) → on garde l'ordre de l'API tel quel, pas de tri maison.

**Engins** : pas d'assets lourds (décision déjà prise : pas de 3D, pas de packs
d'images). Coureurs en **CSS/SVG inline** — silhouette de voiture ou de coureur
stylisée, couleur dérivée du nom d'équipe (hash → teinte), numéro = rang. Option
« emoji » (🏎️/🏃) en repli ultra-léger. Cohérent avec le thème (tricolore Togo,
Tourney, terminal).

---

## 4. Les états de l'écran (machine à états, pilotée par start/end/freeze)

1. **Avant le départ** (`now < start`) : grille de départ, coureurs alignés,
   gros **« DÉPART DANS HH:MM:SS »**, feux de F1 (5 rouges → vert) sur les
   dernières secondes.
2. **En course** (`start ≤ now < end`) : course live, bandeau **« TEMPS RESTANT
   HH:MM:SS »**, polling + animations de dépassement.
3. **Classement gelé** (freeze actif) : les coureurs se figent, ruban « GELÉ » ;
   on n'affiche plus les mouvements (l'API renvoie déjà l'état gelé).
4. **Arrivée** (`now ≥ end`) : ligne d'arrivée franchie par le trio de tête,
   **podium** 1-2-3 surélevé, confettis tricolores discrets, chrono à zéro.
5. **Hors événement** (`start`/`end` non définis) : pas de countdown, course
   « libre » sur les scores courants (utile en répétition / entraînement).

---

## 5. Contraintes non négociables

- **Perf & charge** : polling **10-15 s** (pas 1 s), un seul `get_scoreboard_list`
  léger ; réutiliser le cache public 60 s existant ; `requestAnimationFrame`
  pour l'anim, pas de timer par coureur ; se mettre en pause quand l'onglet est
  caché (`visibilitychange`). Cible : tenir 300 équipes + salle qui rafraîchit.
- **`prefers-reduced-motion`** : dépassements = saut instantané, pas de confettis,
  pas de traînées. Obligatoire (déjà la règle du thème).
- **Accessibilité** : la **table classante reste** (repli + lecteurs d'écran),
  `aria-live="polite"` annonce les changements de tête ; contrôle clavier du
  plein écran.
- **Mobile (~400 px)** : moins de coureurs, piste qui scrolle verticalement,
  chrono compact. Jamais de scroll horizontal du body.
- **Pas de tell CTFd** : on retire le titre « Top 10 Teams » d'echarts et le
  bouton « saveAsImage » ; branding NCTF partout.
- **Respect du gel & de la visibilité** : si `score_visibility` = admins, la
  course ne s'affiche pas aux joueurs (comme la table). On ne contourne rien.
- **Dégradation** : JS en échec ou API muette → on garde la table `{% cache %}`
  déjà rendue côté serveur. La course est un *enrichissement*, pas un prérequis.

---

## 6. Rendu technique (choix)

- **DOM + CSS transforms** (`translate3d`, `transition`), pas de canvas/WebGL :
  léger, net, thémable, accessible, et compatible avec le CSP (pas de lib
  externe à charger). Un `<div class="racer">` par coureur, positionné en
  `transform` ; le changement de voie = transition CSS → dépassement gratuit.
- **Zéro dépendance** : on n'ajoute pas echarts-bis. Tout est vanilla + le CSS
  du thème. (echarts reste dispo pour l'onglet « courbe » si on le garde.)
- **Trois vues, un sélecteur** : `Course` (défaut) · `Courbe` · `Table`. La
  course devient la vue par défaut de `/scoreboard`.

---

## 7. Plan de livraison (incrémental, testable à chaque étape)

- [ ] **Lot A — squelette statique** : `templates/scoreboard.html` gagne un
      conteneur `#race` + le sélecteur de vue ; `static` CSS de la piste, des
      voies, d'un coureur (couleur = hash du nom). Données bidon. Rien de live.
- [ ] **Lot B — données live** : `assets/js/pages/scoreboard.js` lit
      `get_scoreboard_list`, place les coureurs (X = score normalisé, Y = rang),
      poll 12 s, pause si onglet caché. Top N + peloton agrégé + « ton coureur ».
- [ ] **Lot C — animations** : transitions de voie (dépassement), boost sur
      nouveau solve, `prefers-reduced-motion`. `aria-live` sur la tête.
- [ ] **Lot D — countdowns & états** : machine à états start/end/freeze/arrivée,
      feux de départ, temps restant, podium + confettis tricolores.
- [ ] **Lot E — mode vidéoprojecteur** : `?big=1` plein écran, top 10-15, gros,
      auto-refresh, pensé pour la salle ; raccourci clavier `f`.
- [ ] **Lot F — validation** : test à 300 équipes simulées (seed de faux
      comptes/scores) dans la stack locale ; test mobile 400 px ; reduced-motion ;
      gel ; avant/pendant/après (en forçant `start`/`end`). Screenshots.
- [ ] **Lot G — repli & a11y finalisés** : couper le JS → table intacte ;
      lecteur d'écran ; pas de scroll horizontal ; documentation dans le RUNBOOK
      (« l'écran de la salle : ouvrir /scoreboard?big=1 en plein écran »).

Chaque lot est **thème-only**, se teste dans `deploy/local/` (`make local-up`
+ un seed de faux scores), et se replie proprement sur la table existante.

---

## 8. Risques & garde-fous

| Risque | Mitigation |
|---|---|
| Charge serveur (300 éq. × N viewers × polling) | 12-15 s d'intervalle, cache 60 s réutilisé, pause onglet caché, un seul endpoint léger |
| Illisible à 300 | Top N + peloton agrégé + ta voie ; mode salle = top 10-15 |
| Distraction / triche visuelle | 100 % cosmétique, lit l'API publique, aucun accès scoring |
| Fuite post-gel | on lit l'API non-admin qui est déjà gelée ; on ne recalcule rien |
| Épilepsie / motion sickness | `prefers-reduced-motion`, confettis discrets et optionnels |
| Régression scoreboard | la course est un calque ; la table `{% cache %}` reste le socle |

---

## 9. Non-objectifs (pour rester cadré)

- Pas de 3D / WebGL (décision déjà prise).
- Pas d'assets images lourds : tout en CSS/SVG/emoji.
- Pas de nouveau backend ni de WebSocket : polling de l'API existante suffit.
- Pas de modification du scoring, du gel, ni des règles de visibilité.
