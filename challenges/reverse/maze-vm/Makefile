# Reproducible build for the 'maze-vm' artifact.
#
#   make          -> regenerate src/program.h from src/gen.py and build ./chall
#   make verify   -> confirm no plaintext flag/passphrase in the binary, then solve
#   make clean
#
# Only ./chall is distributed to players. src/gen.py, chall.c and the generated
# program.h are dev-only and are NOT shipped.

CC     ?= gcc
CFLAGS ?= -O2 -Wall

.PHONY: all verify clean

all: chall

program.h: src/gen.py
	cd src && python3 gen.py && mv program.h ../program.h

chall: chall.c program.h
	$(CC) $(CFLAGS) -o chall chall.c

verify: chall
	@echo "== plaintext flag/passphrase in binary? (want: clean) =="
	@strings -n 4 chall | grep -aE 'm4ze_vm_thr34d3d|NCTF\{m4ze|thr34d3d' || echo "  (clean)"
	@echo "== solve (extract bytecode + oracle-recover input + verify) =="
	@cd solution && python3 solve.py ../chall

clean:
	rm -f chall program.h src/program.h
