/* off-by-one-auth -- a one-byte overflow flips an authorization gate.
 *
 * The read loop uses `i <= n` instead of `i < n`, so when the caller asks for
 * the maximum allowed count (32) the loop writes ONE byte past the 32-byte
 * buffer. That byte lands on the low byte of the adjacent `authorized` field.
 * A single non-zero byte there unlocks reveal(), which XOR-decodes the flag. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "enc.h"

#define KEY 0x77

struct frame {
    char buf[32];
    volatile unsigned long authorized;
};

static void reveal(void) {
    unsigned char out[64];
    for (int i = 0; i < enc_len; i++)
        out[i] = enc[i] ^ KEY;
    write(1, out, enc_len);
    write(1, "\n", 1);
}

int main(void) {
    struct frame s;
    int n, c;

    setvbuf(stdout, NULL, _IONBF, 0);
    s.authorized = 0;

    puts("how many bytes (max 32)?");
    if (scanf("%d", &n) != 1)
        return 1;
    if (n < 0 || n > 32) {
        puts("bad length");
        return 0;
    }
    getchar(); /* consume the newline after the number */

    for (int i = 0; i <= n; i++) { /* BUG: <= writes buf[n], one past for n==32 */
        c = getchar();
        if (c == EOF)
            break;
        s.buf[i] = (char)c;
    }

    if (s.authorized) {
        puts("authorized.");
        reveal();
    } else {
        puts("denied.");
    }
    return 0;
}
