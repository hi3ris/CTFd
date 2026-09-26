# Reproducible build for the 'pyc-ghost' artifact.
#
#   make         -> compile src/vault.py into ./vault.pyc
#   make verify  -> confirm no plaintext flag, then run the solver
#   make clean
#
# The shipped artifact is ./vault.pyc (marshalled CPython bytecode).
# src/vault.py and src/gen.py are dev-only and are NOT distributed.

.PHONY: all verify clean

all: vault.pyc

vault.pyc: src/vault.py src/gen.py
	cd src && python3 gen.py

verify: vault.pyc
	@echo "plaintext flag present? (want: 0)"
	@grep -a -c 'marsh4l_unp1' vault.pyc || true
	@cd solution && python3 solve.py ../vault.pyc

clean:
	rm -f vault.pyc
	rm -rf src/__pycache__ solution/__pycache__
