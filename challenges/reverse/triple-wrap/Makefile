# Reproducible build for the 'triple-wrap' artifact.
#
#   make         -> regenerate chall.c from src/gen.py and build ./chall
#   make verify  -> confirm strings shows only the decoy, then run the solver
#   make clean
#
# The shipped artifact is ./chall (a stripped x86-64 ELF). src/ is dev-only.

CC     ?= gcc
CFLAGS ?= -O2 -s

.PHONY: all verify clean

all: chall

src/chall.c: src/gen.py
	cd src && python3 gen.py

chall: src/chall.c
	$(CC) $(CFLAGS) -o chall src/chall.c

verify: chall
	@echo "NCTF{ hits in strings (should be the decoy only):"
	@strings -a chall | grep -a 'NCTF{' || true
	@echo "real flag present as plaintext? (want: 0)"
	@grep -a -c 'peel_b64_rot13' chall || true
	@cd solution && python3 solve.py ../chall

clean:
	rm -f chall src/chall.c
