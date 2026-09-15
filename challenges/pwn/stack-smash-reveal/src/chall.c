/* stack-smash-reveal -- classic ret2win.
 *
 * No stack canary, no PIE. vuln() reads far more than its buffer holds, so a
 * saved return address on the stack can be overwritten to redirect control to
 * win(). win() XOR-decodes the embedded flag with KEY and prints it. The flag
 * never appears in cleartext in the binary. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "enc.h"

#define KEY 0x5A

void win(void) {
    unsigned char out[64];
    for (int i = 0; i < enc_len; i++)
        out[i] = enc[i] ^ KEY;
    write(1, out, enc_len);
    write(1, "\n", 1);
    _exit(0);
}

void vuln(void) {
    char buf[64];
    puts("send your data:");
    read(0, buf, 256); /* overflow: buf is only 64 bytes */
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    puts("stack-smash-reveal");
    vuln();
    puts("bye");
    return 0;
}
