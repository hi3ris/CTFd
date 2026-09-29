# Reproducible build for the 'packed-vm-lite' artifact.
#
#   make            -> regenerate program.h from src/gen.py and build ./vmcheck
#   make verify     -> confirm the flag/serial are NOT plaintext, run solver
#   make clean
#
# The shipped artifact is ./vmcheck (a stripped x86-64 PIE ELF). src/gen.py,
# src/vm.c and src/program.h are dev-only and are NOT distributed to players.

CC     ?= gcc
CFLAGS ?= -O2 -s

.PHONY: all verify clean

all: vmcheck

src/program.h: src/gen.py
	cd src && python3 gen.py

vmcheck: src/vm.c src/program.h
	$(CC) $(CFLAGS) -I src -o vmcheck src/vm.c

verify: vmcheck
	@echo "plaintext flag/serial in binary? (want: nothing):"
	@strings -n 5 vmcheck | grep -aE 'vm_bytec0de|n0t_h4rd|CTF\{vm' || echo "  (clean)"
	@echo "decoy string present (expected):"
	@strings -n 6 vmcheck | grep -a DEADBEEF || true
	@echo "solve:"
	@cd solution && python3 solve.py ../vmcheck

clean:
	rm -f vmcheck src/program.h
