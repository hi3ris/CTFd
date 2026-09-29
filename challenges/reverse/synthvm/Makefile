# Reproducible build for the 'synthvm' artifact.
#
#   make            -> regenerate src/program.h from src/gen.py and build ./synthvm
#   make verify     -> confirm no plaintext flag in the binary, then run the solver
#   make clean
#
# The shipped artifact is ./synthvm (a stripped x86-64 PIE ELF). src/gen.py,
# src/vm.c and src/program.h are dev-only and are NOT distributed to players.

CC     ?= gcc
CFLAGS ?= -O2 -s

.PHONY: all verify clean

all: synthvm

src/program.h: src/gen.py
	cd src && python3 gen.py program.h

synthvm: src/vm.c src/program.h
	$(CC) $(CFLAGS) -I src -o synthvm src/vm.c

verify: synthvm
	@echo "== plaintext flag in binary? (want: clean) =="
	@strings -n 5 synthvm | grep -aE 'synthvm_d1|rem4pped|runtime\}|CTF\{synth' || echo "  (clean)"
	@echo "== decoy fake-flag in plaintext? (want: clean; only stored transformed) =="
	@strings -n 5 synthvm | grep -aE 'dead_c0de|keep_tracing' || echo "  (clean)"
	@echo "== solve (disassemble + invert + verify) =="
	@cd solution && python3 solve.py ../synthvm

clean:
	rm -f synthvm src/program.h
