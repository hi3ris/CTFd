/* ret2win-keyed -- ret2win that requires argument control.
 *
 * reveal(unsigned long k) only decodes the flag when k equals a per-run token
 * that the program prints at startup. Just jumping to reveal() is not enough:
 * the System-V ABI passes the first integer argument in RDI, so the exploit
 * must set RDI to the printed token (e.g. with a `pop rdi; ret` gadget) before
 * returning into reveal(). No canary, no PIE. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "enc.h"

#define KEY 0x1F

/* A convenient `pop rdi; ret` gadget so argument control is available in this
 * static binary (modern gcc no longer emits __libc_csu_init). */
__asm__(".text\n"
        ".globl gadget_pop_rdi\n"
        "gadget_pop_rdi:\n"
        "    pop %rdi\n"
        "    ret\n");

static unsigned long token;

void reveal(unsigned long k) {
    unsigned char out[64];
    if (k != token) {
        puts("wrong key");
        return;
    }
    for (int i = 0; i < enc_len; i++)
        out[i] = enc[i] ^ KEY;
    write(1, out, enc_len);
    write(1, "\n", 1);
    _exit(0);
}

void vuln(void) {
    char buf[64];
    puts("send your data:");
    read(0, buf, 256); /* overflow */
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    srand((unsigned)(time(NULL) ^ getpid()));
    token = ((unsigned long)rand() << 32) ^ (unsigned long)rand();
    printf("token: 0x%016lx\n", token);
    vuln();
    puts("bye");
    return 0;
}
