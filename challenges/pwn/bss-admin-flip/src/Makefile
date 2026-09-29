# Build the challenge binary.
# Mitigations: NX enabled (default), stack canary OFF, PIE OFF.
# The bug is in a .bss global, so PIE/canary are not the point -- disabled to
# keep the layout simple and deterministic.
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
