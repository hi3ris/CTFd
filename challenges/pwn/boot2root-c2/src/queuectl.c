/*
 * queuectl -- "run the queued jobs" helper for the Phantom Wire panel.
 *
 * Installed SETUID to the `deploy` operator account (owner deploy:deploy, mode
 * 4755) so any local worker can kick the job runner, which must run as the
 * operator that owns the job spool.
 *
 * VULNERABILITY (intentional, stage 2 of the chain): the path of the runner
 * script is NOT hardcoded -- it is read from the config file
 * /etc/phantom/queue.conf (line `runner=/path/to/script`). That config file is
 * world-writable by mistake (mode 0666). queuectl raises its real UID to
 * `deploy` and then executes whatever `runner=` points at, via /bin/sh. Any
 * local user (www) can therefore rewrite the `runner=` line to point at their
 * own script and have it executed as `deploy`. This is a writable-config /
 * trusted-path SUID bug (distinct from a PATH hijack or an argument injection).
 *
 * There is no flag here and no path to root here: exploiting this only moves
 * you laterally from `www` to `deploy`.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CONF "/etc/phantom/queue.conf"

int main(void) {
    uid_t deploy = geteuid();
    FILE *f;
    char line[512];
    char runner[512] = {0};

    /* Genuine `deploy` process, not merely euid=deploy. */
    if (setreuid(deploy, deploy) != 0) {
        perror("setreuid");
        return 1;
    }

    f = fopen(CONF, "r");
    if (!f) {
        fprintf(stderr, "[queuectl] cannot open %s\n", CONF);
        return 1;
    }
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "runner=", 7) == 0) {
            /* copy the value, trimming a trailing newline */
            char *v = line + 7;
            size_t n = strlen(v);
            if (n && v[n - 1] == '\n')
                v[n - 1] = '\0';
            snprintf(runner, sizeof(runner), "%s", v);
            break;
        }
    }
    fclose(f);

    if (!runner[0]) {
        fprintf(stderr, "[queuectl] no runner= in %s\n", CONF);
        return 1;
    }

    fprintf(stderr, "[queuectl] running job runner '%s' as uid=%d...\n", runner,
            (int)getuid());

    /* BUG: executes an operator-writable... in fact WORLD-writable path. */
    execl("/bin/sh", "sh", runner, (char *)NULL);
    perror("execl");
    return 1;
}
