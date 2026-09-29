# Reproducible build for the 'strings-lie' artifact.
#
#   make           -> regenerate chall.c from src/gen.py and build ./chall
#   make verify    -> sanity-check that strings only shows the decoy
#   make clean
#
# The shipped artifact is ./chall (a stripped x86-64 PIE ELF). src/gen.py and
# src/chall.c are dev-only and are NOT distributed to players.

CC      ?= gcc
CFLAGS  ?= -O2 -s

.PHONY: all verify clean

all: chall

src/chall.c: src/gen.py
	cd src && python3 gen.py

chall: src/chall.c
	$(CC) $(CFLAGS) -o chall src/chall.c

verify: chall
	@echo "strings hits for NCTF{ (should be the decoy only):"
	@strings -n 6 chall | grep -a 'NCTF{' || true
	@echo "real flag present as plaintext? (want: 0)"
	@grep -a -c 'str1ngs_l1e_read' chall || true
	@echo "solve:"
	@cd solution && python3 solve.py ../chall

clean:
	rm -f chall src/chall.c
