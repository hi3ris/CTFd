/* shellcode-decoder -- run arbitrary shellcode in an RWX buffer.
 *
 * The flag section `enc` is masked at runtime with a random byte r, and the
 * matching decode byte dkey = K ^ r is stored in a global. So the effective key
 * only exists inside the running process -- a static XOR of the file does not
 * reveal the flag. The program hands you an executable buffer and jumps into
 * your bytes. Intended shellcode reads enc[] and dkey (fixed addresses, no PIE),
 * XOR-decodes, and writes the result to stdout. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#include "enc.h"

#define K 0x2B

unsigned char enc[64];  /* .bss, fixed address (no PIE), writable */
unsigned char dkey = 0; /* .bss, set at runtime to K ^ r */

int main(void) {
    unsigned char r;
    void (*sc)(void);
    void *buf;

    setvbuf(stdout, NULL, _IONBF, 0);
    srand((unsigned)(time(NULL) ^ getpid()));
    r = (unsigned char)(rand() & 0xff);

    for (int i = 0; i < enc_len; i++)
        enc[i] = enc_src[i] ^ r; /* enc = flag ^ K ^ r */
    dkey = (unsigned char)(K ^ r); /* flag = enc ^ dkey */

    buf = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC,
               MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (buf == MAP_FAILED)
        return 1;

    printf("enc @ %p, dkey @ %p, len = %d\n", (void *)enc, (void *)&dkey,
           enc_len);
    puts("send shellcode:");
    if (read(0, buf, 0x1000) <= 0)
        return 1;

    sc = (void (*)(void))buf;
    sc();
    return 0;
}
