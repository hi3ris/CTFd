/*
 * maze-vm  --  a bespoke bytecode machine that validates a passphrase.
 *
 * The embedded program is a byte stream for a small stack+register VM. It is
 * stored rolling-XOR obfuscated and decoded at startup, then executed through
 * a threaded (computed-goto) dispatch loop. The program transforms the input
 * and compares the result against an embedded target. There is no plaintext
 * flag and no plaintext passphrase inside the binary -- only target = F(pass).
 *
 * When (and only when) the accepted input is supplied, the program validates
 * and the binary prints NCTF{<input>}. Recover the input from the bytecode.
 *
 *   build:  gcc -O2 -o chall chall.c
 *   run:    ./chall   (reads one line from stdin)
 */
#include <stdio.h>
#include <string.h>
#include "program.h"

int main(void)
{
    /* ---- parse the embedded blob ---- */
    const unsigned char *p = BLOB;
    if (memcmp(p, "MZVMv1\x00\x00", 8) != 0) return 2;
    unsigned char xor_seed = p[8], xor_mul = p[9], plen = p[10];
    unsigned int prog_len = p[11] | (p[12] << 8);
    const unsigned char *obf = p + 13;
    const unsigned char *target = obf + prog_len;

    /* ---- de-obfuscate the bytecode (rolling keystream) ---- */
    static unsigned char prog[8192];
    unsigned char key = xor_seed;
    for (unsigned int i = 0; i < prog_len; i++) {
        unsigned char o = obf[i];
        prog[i] = o ^ key;
        key = (unsigned char)(key * xor_mul + o);
    }

    /* ---- read one line of input ---- */
    unsigned char in[64];
    memset(in, 0, sizeof(in));
    char line[256];
    if (!fgets(line, sizeof(line), stdin)) return 1;
    size_t n = strlen(line);
    while (n && (line[n - 1] == '\n' || line[n - 1] == '\r')) line[--n] = 0;
    if (n != plen) { puts("Denied."); return 0; }
    memcpy(in, line, plen);

    /* ---- VM state ---- */
    unsigned char st[64];
    memset(st, 0, sizeof(st));
    unsigned char stack[256];
    int sp = 0;
    int fail = 0;
    unsigned int pc = 0;

    /* threaded dispatch table, indexed by opcode byte */
    static void *tbl[256];
    for (int i = 0; i < 256; i++) tbl[i] = &&op_bad;
    tbl[0x10] = &&op_nop;   tbl[0x11] = &&op_halt;
    tbl[0x12] = &&op_pushi; tbl[0x13] = &&op_ldin;
    tbl[0x14] = &&op_ldst;  tbl[0x15] = &&op_stst;
    tbl[0x16] = &&op_pop;   tbl[0x17] = &&op_dup;   tbl[0x18] = &&op_swap;
    tbl[0x19] = &&op_add;   tbl[0x1A] = &&op_sub;   tbl[0x1B] = &&op_xor;
    tbl[0x1C] = &&op_and;   tbl[0x1D] = &&op_or;    tbl[0x1E] = &&op_mulmod;
    tbl[0x1F] = &&op_rol;   tbl[0x20] = &&op_ror;   tbl[0x21] = &&op_perm;
    tbl[0x22] = &&op_cmp;   tbl[0x23] = &&op_jmp;

#define NEXT()  goto *tbl[prog[pc++]]
#define A       (stack[sp - 1])
    NEXT();

op_nop:                             NEXT();
op_pushi: stack[sp++] = prog[pc++]; NEXT();
op_ldin:  stack[sp++] = in[prog[pc++]]; NEXT();
op_ldst:  stack[sp++] = st[prog[pc++]]; NEXT();
op_stst:  st[prog[pc++]] = stack[--sp]; NEXT();
op_pop:   --sp;                     NEXT();
op_dup:   stack[sp] = stack[sp - 1]; sp++; NEXT();
op_swap: { unsigned char t = stack[sp-1]; stack[sp-1]=stack[sp-2]; stack[sp-2]=t; } NEXT();
op_add:  { unsigned char b = stack[--sp]; A = (unsigned char)(A + b); } NEXT();
op_sub:  { unsigned char b = stack[--sp]; A = (unsigned char)(A - b); } NEXT();
op_xor:  { unsigned char b = stack[--sp]; A = A ^ b; } NEXT();
op_and:  { unsigned char b = stack[--sp]; A = A & b; } NEXT();
op_or:   { unsigned char b = stack[--sp]; A = A | b; } NEXT();
op_mulmod:{unsigned char b = stack[--sp]; A = (unsigned char)(A * b); } NEXT();
op_rol:  { int c = prog[pc++] & 7; A = (unsigned char)((A << c) | (A >> (8 - c))); } NEXT();
op_ror:  { int c = prog[pc++] & 7; A = (unsigned char)((A >> c) | (A << (8 - c))); } NEXT();
op_perm: {
    unsigned char tmp[64];
    for (unsigned char i = 0; i < plen; i++) tmp[i] = st[prog[pc + i]];
    for (unsigned char i = 0; i < plen; i++) st[i] = tmp[i];
    pc += plen;
} NEXT();
op_cmp:  { unsigned char b = stack[--sp], a = stack[--sp]; if (a != b) fail = 1; } NEXT();
op_jmp:  { pc = prog[pc]; } NEXT();
op_bad:  fail = 1; goto op_halt;

op_halt:
    if (!fail) {
        /* reconstruct the flag from the accepted input; nothing stored */
        fputs("NCTF{", stdout);
        fwrite(in, 1, plen, stdout);
        puts("}");
    } else {
        puts("Denied.");
    }
    (void)target; /* target is consumed by the CMP immediates in prog */
    return 0;
}
