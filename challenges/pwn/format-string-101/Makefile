# Build the challenge binary.
#
#   -O0                 : keep the stack layout simple/predictable for an easy
#                         format-string offset.
#   -fno-stack-protector: no canary noise between buf and the saved frame.
#   -no-pie             : globals (auth) live at a fixed, discoverable address.
#   -Wl,-z,norelro      : not strictly required here, kept for a plain layout.
#
# The binary contains NO flag. The live service supplies the per-team flag via
# the FLAG environment variable (set by entrypoint.sh from TEAM_SECRET).
CC      ?= gcc
CFLAGS  ?= -m64 -O0 -fno-stack-protector -no-pie -Wl,-z,norelro -Wall
TARGET  := chall

.PHONY: all clean
all: $(TARGET)

$(TARGET): chall.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(TARGET)
