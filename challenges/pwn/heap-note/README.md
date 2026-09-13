# heap-note (pwn)

Tcache poisoning → `__free_hook` overwrite → `win()` (glibc 2.31, no safe-linking).
Flag servi par instance via `FLAG` (dérivé de `TEAM_SECRET`). Détails d'exploitation : `solution/`.

## Rebuild du binaire (glibc 2.31)

`handout/chall` doit être compilé contre glibc 2.31 (Ubuntu 20.04) sinon le
loader échoue au runtime (`GLIBC_2.34 not found`) et le Dockerfile refuse de
construire l'image. Si tu récupères un binaire compilé sur une glibc plus
récente, régénère-le en une commande (nécessite Docker) :

```bash
cd challenges/pwn/heap-note && ./rebuild-binary.sh
```

Le solveur résout `win()`/`__free_hook` dynamiquement : rien à re-dériver.
