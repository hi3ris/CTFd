# Build the challenge binary.
# Mitigations: NX enabled (default), stack canary OFF, PIE OFF.
# Canary is disabled so the single-byte overflow reaches the adjacent field
# rather than a canary; that keeps the off-by-one deterministic.
CC      ?= gcc
CFLAGS  := -O0 -fno-stack-protector -no-pie -w
OUT     := ../chall

$(OUT): chall.c enc.h
	$(CC) $(CFLAGS) chall.c -o $(OUT)

enc.h: gen.py
	python3 gen.py

clean:
	rm -f enc.h $(OUT)

.PHONY: clean
