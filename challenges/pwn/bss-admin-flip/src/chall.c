/* bss-admin-flip -- global buffer overflow flips an is_admin gate.
 *
 * The name buffer and the is_admin flag live back-to-back in a global struct
 * (in .bss). read() copies more bytes than name can hold, so the overflow
 * spills into is_admin. When is_admin becomes non-zero, reveal() XOR-decodes
 * and prints the embedded flag (never stored in cleartext). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "enc.h"

#define KEY 0x3C

struct account {
    char name[64];
    volatile long is_admin;
};

static struct account user;

static void reveal(void) {
    unsigned char out[64];
    for (int i = 0; i < enc_len; i++)
        out[i] = enc[i] ^ KEY;
    write(1, out, enc_len);
    write(1, "\n", 1);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    user.is_admin = 0;
    puts("register your name:");
    read(0, user.name, 128); /* overflow: name is only 64 bytes */

    if (user.is_admin) {
        puts("welcome, admin.");
        reveal();
    } else {
        puts("standard users only.");
    }
    return 0;
}
