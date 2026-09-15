/* healthcheck -- a trivial "node health" tool.
 *
 * Dynamically linked and NOT setuid. The (intentional) weakness is entirely in
 * the sudoers policy that lets `ctf` run this as root WITH `SETENV:` -- that tag
 * lets the caller keep LD_PRELOAD, so a preloaded shared library's constructor
 * runs as root. There is nothing exploitable in this file itself.
 */
#include <stdio.h>

int main(void) {
    printf("[healthcheck] node edge-01: services nominal\n");
    return 0;
}
