# Build the challenge binary.
#
#   -static             : fully static -- there is no libc to leak; every gadget
#                         you need (including "/bin/sh") is inside this file.
#   -no-pie             : .text/.bss at fixed addresses, so gadget and string
#                         addresses are stable across connections (no leak
#                         needed).
#   -fno-stack-protector: no canary between buf and the saved return address.
#   -O1                 : compact code; keeps the intended layout tidy.
#
# The binary contains NO flag. The live service supplies the per-team flag via
# the FLAG environment variable (set by entrypoint.sh from TEAM_SECRET); a shell
# obtained through the ROP chain inherits it.
CC      ?= gcc
CFLAGS  ?= -m64 -O1 -fno-stack-protector -no-pie -static -Wall \
           -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0
TARGET  := chall

.PHONY: all clean
all: $(TARGET)

$(TARGET): chall.c
	$(CC) $(CFLAGS) -o $@ $<
	# Intentionally NOT stripped: the ret2csu-ish marshal/pop gadgets keep their
	# symbol names so the technique is discoverable (nm chall | grep -E 'csu|marshal').
	# The difficulty lives in the per-connection transform, not in symbol hiding.

clean:
	rm -f $(TARGET)
