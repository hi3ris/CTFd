# Reproducible build for the 'shell-lock' artifact.
#
#   make         -> regenerate ./lock.sh from src/gen.py
#   make verify  -> confirm no plaintext flag/password, then run the solver
#   make clean
#
# The shipped artifact is ./lock.sh (an obfuscated self-decrypting shell
# script). src/gen.py is developer-only and is NOT distributed.

.PHONY: all verify clean

all: lock.sh

lock.sh: src/gen.py
	cd src && python3 gen.py

verify: lock.sh
	@echo "plaintext flag present? (want: 0)"
	@grep -a -c 'pe3led' lock.sh || true
	@echo "plaintext password present? (want: 0)"
	@grep -a -c 'sh3ll_w1zard' lock.sh || true
	@cd solution && python3 solve.py ../lock.sh

clean:
	rm -f lock.sh
	rm -rf src/__pycache__ solution/__pycache__
