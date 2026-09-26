# GOAL — NCTF26

> CTF national du Togo, édition 2026, opéré par CERT.tg.
> Ce fichier est le _north-star_ du projet : toute décision de contenu, d'archi
> ou d'ops se juge à l'aune de ces objectifs. Il est figé — on le fait évoluer
> par commit, pas par dérive.

## Énoncé

**Livrer une plateforme CTF prête pour l'événement, équitable face aux agents
IA, et opérable par une petite équipe.**

Un challenge qui n'est pas jouable-et-vérifié n'existe pas pour l'événement ; un
challenge cassable « en une seconde » par un agent IA n'a pas sa place. La
qualité vérifiée prime sur le volume affiché.

## Contraintes dures (le calendrier ne bouge pas)

| Phase        | Dates                               | Joueurs | Mode    |
| ------------ | ----------------------------------- | ------- | ------- |
| Présélection | ven 23 oct 19:00 → lun 26 oct 00:00 | ~300    | Équipes |
| Finale       | 29–30 oct, Lomé                     | ~10 éq. | Équipes |

La plateforme doit tenir 300 joueurs simultanés (test de charge k6 en place).

## Objectifs

### 1. Résistance au solve-par-IA (cœur du projet)

- **Ne pas interdire l'IA.** L'interdit ne tient pas ; l'objectif est qu'aucun
  challenge ne tombe instantanément sous un agent.
- Basculer le poids du catalogue vers :
  - les **challenges servis par équipe** (`type: team_instance`), flag **HMAC
    unique par équipe**, sans artefact téléchargeable — l'agent ne peut pas
    exfiltrer un flag partagé ni raisonner sur un binaire local ;
  - les **chaînes de vulnérabilités** combinées (l'étape N ne se débloque que
    comme effet de l'étape N-1, oracle de succès côté serveur).
- Passer les statiques au crible de `make ai-audit` ; retirer ou re-tier ceux
  qui tombent trop vite.

### 2. Contenu honnête et vérifié

- Ce qui est `visible` est **jouable et vérifié** (`solution/solve.py` réussit).
- Ce qui n'est pas fini reste `state: hidden` et marqué STUB — jamais présenté
  comme terminé, ni aux joueurs ni dans les writeups.
- **Porte de qualité (Lot 5).** Un servi ne passe `visible` qu'après une
  répétition Docker/qemu où le solveur de référence récupère le flag de bout en
  bout. Pas de servi non répété en production.
- Le nombre de challenges servis doit être **calibré à l'échelle réelle** (~300
  joueurs, 53 h) : mieux vaut un catalogue plus petit et intégralement vérifié
  qu'un grand catalogue de stubs.

### 3. Opérabilité par une petite équipe

- Anti-triche : flags uniques par équipe → partage détectable
  (plugin + page admin).
- Sauvegardes automatiques (15 min) + répétition de restauration chronométrée.
- Tableau de bord ops, first-bloods, KotH moderne, `make preflight` avant prod.
- Writeups en page in-app, masquée par défaut, révélée par l'admin à la clôture.

### 4. Coût maîtrisé

- Infra AWS **éphémère** : hors événement, aucune instance EC2. Estimation
  ~120 USD pour l'édition, couverte par les crédits AWS.
- Quota GPU (« Running On-Demand G and VT instances ») à demander **maintenant**
  (`make check-gpu-quota`), pas en octobre.

## Définition de « fini » (served)

Un challenge servi est **fini** quand, et seulement quand :

1. le service vulnérable est réellement implémenté (le flag n'est lisible que par
   la vulnérabilité voulue, jamais servi par une route) ;
2. `solution/solve.py` récupère le flag de bout en bout ;
3. la répétition Docker (Lot 5) passe ;
4. le writeup `solution/README.md` documente le chemin voulu ;
5. les hints progressifs sont remplis (l'éventuel CVE-id en hint payant, jamais
   dans la description) ;
6. alors seulement `state: visible`.

Tant que ces six points ne sont pas réunis, le challenge reste `hidden`.

## État (au gel de ce fichier)

- 505 challenges au total ; 328 servis, dont **301 encore STUB** (`hidden`),
  27 servis implémentés/visibles.
- Prochaine étape : finir les servis — implémenter réellement les services
  vulnérables et leurs solveurs, les vérifier en Lot 5, puis calibrer le
  catalogue à l'échelle de l'événement (retirer le surplus de stubs plutôt que
  de le publier non vérifié).
