# Build the challenge binary.
#
#   -O0                 : predictable, un-inlined heap code paths.
#   -fno-stack-protector: no canary noise (this is a heap bug, not a stack bug).
#   -no-pie             : win() lives at a fixed, discoverable address, so no
#                         binary/PIE leak is needed -- only a libc leak to find
#                         __free_hook.
#
# The binary contains NO flag. The live service supplies the per-team flag via
# the FLAG environment variable (set by entrypoint.sh from TEAM_SECRET), and it
# is printed only from win(), which no normal path reaches.
#
# AUTHORITATIVE ARTIFACT: handout/chall is the prebuilt, verified binary that
# the service serves and that players download (built against the pinned glibc
# 2.31, symbols fixed). The Dockerfile ships THAT file; it does not rebuild.
# This target is for source-level dev only -- built here it links against your
# host libc, so re-derive win()'s address from your own build if you use it.
# To reproduce the shipped binary, build on Ubuntu 20.04 (glibc 2.31).
CC      ?= gcc
CFLAGS  ?= -O0 -fno-stack-protector -no-pie -Wall
TARGET  := chall

.PHONY: all clean
all: $(TARGET)

$(TARGET): chall.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f $(TARGET)
