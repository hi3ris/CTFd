/* fmt-key-leak -- format string leak of a per-run stack cookie.
 *
 * A random 64-bit cookie is created on the stack. Your first line of input is
 * passed straight to printf() as the format string, so format specifiers such
 * as %p / %lx read values off the stack, including the cookie. The program then
 * asks you to echo the cookie back; only when your number matches does reveal()
 * XOR-decode and print the embedded flag. The cookie is randomised each run, so
 * the leak must be done live. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "enc.h"

#define KEY 0x4D

static void reveal(void) {
    unsigned char out[64];
    for (int i = 0; i < enc_len; i++)
        out[i] = enc[i] ^ KEY;
    write(1, out, enc_len);
    write(1, "\n", 1);
}

int main(void) {
    char line[128];
    unsigned long cookie, guess;

    setvbuf(stdout, NULL, _IONBF, 0);
    srand((unsigned)(time(NULL) ^ getpid()));
    cookie = ((unsigned long)rand() << 32) ^ (unsigned long)rand();
    if (cookie == 0)
        cookie = 1;

    puts("say something:");
    if (!fgets(line, sizeof(line), stdin))
        return 1;
    printf(line); /* FORMAT STRING BUG */
    puts("");

    puts("now prove you saw the secret (decimal):");
    if (scanf("%lu", &guess) != 1)
        return 1;

    if (guess == cookie) {
        puts("verified.");
        reveal();
    } else {
        puts("nope.");
    }
    return 0;
}
