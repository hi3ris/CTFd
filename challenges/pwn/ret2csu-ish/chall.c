/*
 * ret2csu-ish  --  static, no-PIE return-oriented programming to execve
 * ---------------------------------------------------------------------
 * Build (see Makefile):
 *   gcc -static -no-pie -fno-stack-protector -O1 -o chall chall.c
 *
 * Runtime contract (served, one process per TCP connection via socat):
 *   - Environment variable FLAG holds THIS team's flag. It is derived by the
 *     container entrypoint from the per-team TEAM_SECRET (see flag.py) and is
 *     NEVER compiled into the binary. The downloadable binary therefore cannot
 *     reveal any team's flag. The running SERVICE emits it, and only after you
 *     have actually executed code in the process: the flag lives in the
 *     process environment, so a shell (or any exec) inherits it and can print
 *     it (`echo "$FLAG"` / `env`). No arbitrary code execution -> no flag.
 *
 * The bug:
 *   vuln() reads up to 0x200 bytes into a 64-byte stack buffer -> a linear
 *   stack overflow, no canary (-fno-stack-protector), fixed addresses
 *   (-no-pie, -static). There is no win() and no reachable call to system();
 *   the intended solution is a ROP chain that performs the execve syscall.
 *
 * The twist (per-connection, defeats replay and naive copy-paste chains):
 *   Every connection prints a fresh 8-bit "landing key" K. Before your bytes
 *   are used, the whole overflow region is adjusted in place:
 *
 *        stack_byte[i] = (input_byte[i] + K) mod 256
 *
 *   so to place a target byte T on the stack you must send (T - K) mod 256.
 *   K changes every connection, so a hard-coded chain is worthless -- read K
 *   from the banner and pre-image your chain live.
 *
 * The "-ish":
 *   Modern glibc (>= 2.34) no longer ships __libc_csu_init, so the textbook
 *   ret2csu "universal gadget" that marshals rdx/rsi/rdi in one shot is gone.
 *   This binary reintroduces an equivalent argument-marshalling gadget
 *   (see the asm block below) so the intended, clean solve is a ret2csu-style
 *   register marshal into the execve syscall. Because the binary is fully
 *   static there are of course many incidental gadgets too; the marshal gadget
 *   is the intended path, not the only conceivable one (the writeup is honest
 *   about this).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>

/* Scratch global in .bss at a fixed (-no-pie) address. Not needed by the
 * intended solve -- the static glibc image already contains a "/bin/sh"
 * string -- but handy if a solver would rather stage its own path here. */
char scratch[256];

/*
 * ---------------------------------------------------------------------------
 * DECOY.  admin_panel() is never called from any reachable path and the string
 * below is a STATIC, hard-coded value baked into the downloadable binary. The
 * real flag is per-team and is emitted by the LIVE service only after you
 * execute code in the process (the flag is in the environment). By this
 * event's rules a hard-coded NCTF{...} sitting in a downloadable artifact is
 * never the real flag. You can refute it in under a minute: (a) nothing calls
 * admin_panel(), and (b) the flag is per-team/server-issued, not shipped.
 * ---------------------------------------------------------------------------
 */
__attribute__((used))
static void admin_panel(void)
{
    puts("NCTF{static_r0p_is_not_this_string_decoy}");
}

/*
 * ---------------------------------------------------------------------------
 * ret2csu-ish "universal" argument-marshalling gadget.
 *
 * marshal_regs mirrors the tail of the historical __libc_csu_init gadget that
 * glibc 2.34+ dropped: it copies three saved registers into the System V
 * argument registers and returns, letting a single ROP slot set rdi/rsi/rdx
 * for a following syscall gadget:
 *
 *     mov rdi, r13     ; 1st arg  (path)
 *     mov rsi, r14     ; 2nd arg  (argv)
 *     mov rdx, r15     ; 3rd arg  (envp)
 *     ret
 *
 * csu_pop is the matching register loader (same register set as the classic
 * __libc_csu_init pop gadget, so the technique transfers 1:1):
 *
 *     pop rbx ; pop rbp ; pop r12 ; pop r13 ; pop r14 ; pop r15 ; ret
 *
 * These are ordinary bytes in .text at fixed addresses; find them with a
 * gadget finder or `objdump -d`. They are marked `used` so -O1 cannot elide
 * them, and referenced from a never-taken branch so nothing calls them at
 * runtime.
 * ---------------------------------------------------------------------------
 */
__asm__(
    ".text\n"
    ".p2align 4\n"
    ".globl csu_pop\n"
    ".type  csu_pop,@function\n"
    "csu_pop:\n"
    "    pop %rbx\n"
    "    pop %rbp\n"
    "    pop %r12\n"
    "    pop %r13\n"
    "    pop %r14\n"
    "    pop %r15\n"
    "    ret\n"
    ".size csu_pop, .-csu_pop\n"
    ".p2align 4\n"
    ".globl marshal_regs\n"
    ".type  marshal_regs,@function\n"
    "marshal_regs:\n"
    "    mov %r13, %rdi\n"
    "    mov %r14, %rsi\n"
    "    mov %r15, %rdx\n"
    "    ret\n"
    ".size marshal_regs, .-marshal_regs\n"
    ".p2align 4\n"
    ".globl syscall_ret\n"
    ".type  syscall_ret,@function\n"
    "syscall_ret:\n"
    "    syscall\n"
    "    ret\n"
    ".size syscall_ret, .-syscall_ret\n"
);

extern void csu_pop(void);
extern void marshal_regs(void);
extern void syscall_ret(void);

static unsigned char landing_key(void)
{
    unsigned char k = (unsigned char)(time(NULL) ^ getpid());
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd >= 0) {
        unsigned char r = 0;
        if (read(fd, &r, 1) == 1)
            k = r;
        close(fd);
    }
    /* Never 0: a no-op transform would make the twist invisible. */
    if (k == 0)
        k = 0x5b;
    return k;
}

__attribute__((noinline))
static void vuln(void)
{
    char buf[64];
    unsigned char key = landing_key();

    printf("landing key: 0x%02x\n", key);
    puts("payload> ");
    fflush(stdout);

    /* The bug: 0x200 bytes into a 64-byte buffer. */
    int n = (int)read(0, buf, 0x200);
    if (n <= 0)
        return;

    /* Per-connection transform: every landed byte is (input + key) mod 256.
     * The compiler barrier keeps the stores live -- the transformed bytes are
     * what the saved return address / ROP chain is built from. */
    for (int i = 0; i < n; i++)
        buf[i] = (unsigned char)((unsigned char)buf[i] + key);
    __asm__ volatile("" : : "r"(buf) : "memory");

    /* Return here -> your (pre-imaged) ROP chain runs. */
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    /* Keep the gadgets provably reachable to the linker without ever calling
     * them (argc is always >= 1). */
    if (getpid() == 0) {
        ((void (*)(void))csu_pop)();
        ((void (*)(void))marshal_regs)();
        ((void (*)(void))syscall_ret)();
        admin_panel();
    }

    puts("ret2csu-ish :: statically linked, no PIE, no win().");
    puts("Overflow the buffer and syscall your way out.");
    vuln();
    puts("bye");
    return 0;
}
