# Build the challenge binary.
# Mitigations: NX enabled for the stack (default), but the program maps its own
# RWX buffer and executes it; PIE OFF so enc[]/dkey have fixed addresses.
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
