/*
 * format-string-101  --  pwn-as-a-service format string leak + write
 * -------------------------------------------------------------------
 * Build (see Makefile):
 *   gcc -m64 -O0 -fno-stack-protector -no-pie -Wl,-z,norelro \
 *       -o chall chall.c
 *
 * Runtime contract (served, one process per TCP connection via socat):
 *   - Environment variable FLAG holds this team's flag. It is derived by the
 *     container entrypoint from the per-team TEAM_SECRET (see flag.py) and is
 *     NEVER compiled into the binary. The downloadable binary therefore cannot
 *     reveal any team's flag; the running SERVICE emits it, and only after it
 *     verifies the effect (the auth cell now equals this connection's nonce).
 *   - Per connection a fresh 32-bit `nonce` is generated and printed. The
 *     write target `auth` starts at 0. You win when auth == nonce.
 *
 * There is exactly one intended vulnerability: the `printf(buf)` below uses
 * attacker-controlled data as the format string.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>

/* Global write target. Lives in .bss at a fixed address (binary is -no-pie),
 * so its address is stable across connections -- discover it with `nm chall`
 * or `objdump`, or just read the address the service prints for you. */
unsigned int auth = 0;

/* This connection's goal value. Randomised per connection, so a single
 * hard-coded %n payload can never be replayed -- you must read the printed
 * target and build the write live. */
volatile unsigned int nonce = 0;

/*
 * -------------------------------------------------------------------------
 * DECOY.  This function is never called from any reachable path, and the
 * string below is a STATIC, hard-coded value baked into the downloadable
 * binary. The real flag is per-team and is emitted by the live service only
 * after the auth check passes (see win condition). A hard-coded NCTF{...} in
 * a downloadable artifact is, by this event's rules, never the real flag --
 * you can refute it in seconds by noticing (a) nothing calls debug_dump(),
 * and (b) the flag format is per-team/server-issued, not shipped in a file.
 * -------------------------------------------------------------------------
 */
__attribute__((used))
static void debug_dump(void)
{
    puts("NCTF{fmt_str0_practice_r00m_decoy}");
}

static void seed_random(void)
{
    unsigned int s = (unsigned int)time(NULL) ^ (unsigned int)getpid();
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd >= 0) {
        unsigned int r = 0;
        if (read(fd, &r, sizeof(r)) == (ssize_t)sizeof(r))
            s ^= r;
        close(fd);
    }
    srand(s);
}

int main(void)
{
    char buf[256];

    /* Unbuffered I/O so the service works line-by-line over a socket. */
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    seed_random();
    /* Full 32-bit nonce (rand() is only 15/31 bits on some libcs). */
    nonce = ((unsigned int)rand() << 16) ^ (unsigned int)rand();
    if (nonce == 0)
        nonce = 0x1337c0de;

    puts("=== format-string-101 ===");
    puts("A classic: leak to find your offset, then write.");
    printf("The write target 'auth' lives at %p\n", (void *)&auth);
    printf("Make auth == 0x%08x\n", nonce);
    puts("You get up to 16 lines. Each line is printed back to you.");
    puts("--------------------------------------------------------");

    for (int i = 0; i < 16; i++) {
        printf("[%2d] > ", i);

        if (!fgets(buf, sizeof(buf), stdin))
            break;
        buf[strcspn(buf, "\n")] = '\0';

        /* THE VULNERABILITY: attacker-controlled format string. */
        printf(buf);
        putchar('\n');

        if (auth == nonce) {
            const char *flag = getenv("FLAG");
            puts("");
            puts("[+] auth overwritten -- effect verified by the service.");
            printf("[+] flag: %s\n", flag ? flag : "NCTF{missing_FLAG_env_ask_organisers}");
            fflush(stdout);
            return 0;
        }
    }

    printf("\nauth is still 0x%08x -- not this time.\n", auth);
    return 0;
}
