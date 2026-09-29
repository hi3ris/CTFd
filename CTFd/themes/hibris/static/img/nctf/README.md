# Images de l'accueil NCTF26

Déposer ici, avec **exactement** ces noms, les images de `C:\Users\rdagban\Pictures\nctf` :

| Fichier         | Contenu                                                       | Usage                                            |
| --------------- | ------------------------------------------------------------- | ------------------------------------------------ |
| `intro-bg.jpg`  | la fille au visage en binaire (sujet à droite, noir à gauche) | fond de la cinématique d'intro et du hero        |
| `logo-ctf.png`  | « Capture the Flag », drapeaux togolais + hacker              | carte titre et carte finale de l'intro           |
| `logo-cert.png` | mot-symbole `CERT.tg}<`                                       | barre du haut de l'intro (à la place du texte)   |
| `logo-c.png`    | le « C » dégradé bleu → vert                                  | disponible (favicon / réseaux), pas encore placé |

Tout est optionnel : un fichier absent laisse le texte de repli (`<img onerror>`),
le fond reste noir. Les chemins se règlent dans `deploy/theme-home-hero.html`,
objet `NCTF_INTRO.images`. Après dépôt : `git add`, commit, puis `make local-up`
(l'image du thème est reconstruite) et `make local-seed` (le contenu de l'accueil
est renvoyé). Pour la remontrer à tout le monde, incrémenter `NCTF_INTRO.version`.

Poids conseillé : `intro-bg.jpg` ≤ 400 Ko (1728 × 864 suffit), logos ≤ 100 Ko.
