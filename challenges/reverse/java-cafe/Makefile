# Reproducible build for the 'java-cafe' artifact.
#
#   make         -> compile src/Vault.java into ./Vault.class
#   make verify  -> confirm no plaintext flag, then run the solver
#   make clean
#
# The shipped artifact is ./Vault.class (JVM bytecode). src/Vault.java and
# src/gen.py are developer-only and are NOT distributed to players.

.PHONY: all verify clean

all: Vault.class

Vault.class: src/Vault.java src/gen.py
	cd src && python3 gen.py

verify: Vault.class
	@echo "plaintext flag present? (want: 0)"
	@grep -a -c 'byt3code_is_readable' Vault.class || true
	@cd solution && python3 solve.py ../Vault.class

clean:
	rm -f Vault.class src/Vault.class
	rm -rf src/__pycache__ solution/__pycache__
