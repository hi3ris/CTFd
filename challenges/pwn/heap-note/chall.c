/*
 * heap-note  --  pwn-as-a-service tcache UAF note editor (glibc 2.31)
 * -----------------------------------------------------------------------
 * Build (see Makefile):
 *   gcc -O0 -fno-stack-protector -no-pie -Wall -o chall chall.c
 *
 * The SERVED binary is run against a PINNED glibc 2.31 (Ubuntu 20.04,
 * 2.31-0ubuntu9.18). The Dockerfile ships and patchelf-binds the exact
 * libc.so.6 / ld-2.31.so that players receive in the handout, so the heap
 * layout, tcache internals and libc offsets are identical to what you can
 * study offline. Modern-ish libc: tcache is present. glibc 2.31 predates
 * safe-linking (2.32), so tcache forward pointers are stored un-mangled.
 *
 * Runtime contract (served, one process per TCP connection via socat):
 *   - Environment variable FLAG holds this team's flag. It is derived by the
 *     container entrypoint from the per-team TEAM_SECRET (see flag.py) and is
 *     NEVER compiled into this binary. The downloadable binary therefore
 *     cannot reveal any team's flag. Control flow must actually be hijacked to
 *     win(): the live SERVICE emits the flag only from inside win(), and win()
 *     is not reachable by any normal menu path -- the server verifies the
 *     EFFECT (win() executed) rather than any particular payload shape.
 *
 * Intended vulnerability: a use-after-free. free() does NOT clear the slot,
 * and both `edit` and `view` operate on the raw slot pointer with no
 * allocated/freed check -- so you can read a freed chunk (leak) and write into
 * a freed chunk (edit-after-free -> tcache poisoning).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_NOTES 16
#define MAX_SIZE  0x1000

static char          *notes[MAX_NOTES];
static unsigned long   sizes[MAX_NOTES];

/*
 * win() -- reachable ONLY by hijacking control flow (e.g. tcache-poisoning a
 * libc hook to point here). It prints THIS team's flag, taken from the
 * environment at runtime. Nothing in the menu calls it.
 */
__attribute__((used))
void win(void)
{
    const char *flag = getenv("FLAG");
    puts("");
    puts("[+] win() reached -- control-flow hijack verified by the service.");
    printf("[+] flag: %s\n", flag ? flag : "NCTF{missing_FLAG_env_ask_organisers}");
    fflush(stdout);
    _exit(0);
}

/*
 * -----------------------------------------------------------------------
 * DECOY.  secret_backdoor() is never referenced by any reachable path, and
 * the string below is a STATIC value baked into the downloadable binary. By
 * this event's rules a hard-coded NCTF{...} in a shipped artifact is never the
 * real flag: the real flag is per-team and is printed only by win() on the
 * live service. You can refute this decoy in under a minute -- (a) nothing
 * jumps to secret_backdoor(), and (b) it reads no environment, it just puts()
 * a constant. Do not burn attempts on it.
 * -----------------------------------------------------------------------
 */
__attribute__((used))
static void secret_backdoor(void)
{
    puts("NCTF{uaf_but_this_hardcoded_string_is_a_decoy}");
}

static void flush_line(void)
{
    int c;
    while ((c = getchar()) != '\n' && c != EOF)
        ;
}

/* Read a decimal integer from one line of input. */
static long read_long(void)
{
    char line[32];
    if (!fgets(line, sizeof(line), stdin))
        _exit(0);
    return strtol(line, NULL, 0);
}

/* Read exactly n bytes of raw content into buf (no format, no null-stop). */
static void read_n(char *buf, unsigned long n)
{
    unsigned long got = 0;
    while (got < n) {
        ssize_t r = read(0, buf + got, n - got);
        if (r <= 0)
            _exit(0);
        got += (unsigned long)r;
    }
}

static int pick_index(void)
{
    printf("index (0-%d): ", MAX_NOTES - 1);
    long i = read_long();
    if (i < 0 || i >= MAX_NOTES) {
        puts("[-] bad index");
        return -1;
    }
    return (int)i;
}

static void do_alloc(void)
{
    int i = pick_index();
    if (i < 0)
        return;
    printf("size: ");
    long sz = read_long();
    if (sz <= 0 || sz > MAX_SIZE) {
        puts("[-] bad size");
        return;
    }
    char *p = malloc((size_t)sz);
    if (!p) {
        puts("[-] malloc failed");
        return;
    }
    notes[i] = p;
    sizes[i] = (unsigned long)sz;
    printf("[+] note %d allocated (%ld bytes)\n", i, sz);
}

static void do_free(void)
{
    int i = pick_index();
    if (i < 0)
        return;
    if (!notes[i]) {
        puts("[-] empty slot");
        return;
    }
    free(notes[i]);
    /* BUG: the slot pointer is intentionally NOT cleared -> use-after-free. */
    printf("[+] note %d freed\n", i);
}

static void do_edit(void)
{
    int i = pick_index();
    if (i < 0)
        return;
    if (!notes[i]) {
        puts("[-] empty slot");
        return;
    }
    printf("content (%lu bytes): ", sizes[i]);
    /* BUG: no allocated/freed check -> edit-after-free write. */
    read_n(notes[i], sizes[i]);
    puts("[+] saved");
}

static void do_view(void)
{
    int i = pick_index();
    if (i < 0)
        return;
    if (!notes[i]) {
        puts("[-] empty slot");
        return;
    }
    /* BUG: no allocated/freed check -> read of freed memory (leak). */
    printf("[+] note %d: ", i);
    fflush(stdout);
    write(1, notes[i], sizes[i]);
    puts("");
}

static void menu(void)
{
    puts("");
    puts("=== heap-note ===");
    puts(" 1) alloc");
    puts(" 2) free");
    puts(" 3) edit");
    puts(" 4) view");
    puts(" 5) exit");
    printf("> ");
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    for (;;) {
        menu();
        long choice = read_long();
        switch (choice) {
        case 1: do_alloc(); break;
        case 2: do_free();  break;
        case 3: do_edit();  break;
        case 4: do_view();  break;
        case 5: puts("bye"); return 0;
        default: puts("[-] ?"); break;
        }
    }
    (void)flush_line;
}
