/*
 * logsync -- "rotate & sync application logs" helper.
 *
 * Installed SETUID to the `app` user (owner app:app, mode 4755) so that any
 * local user can trigger a log sync that runs as the log owner `app`.
 *
 * VULNERABILITY (intentional, stage 2 of the chain): it raises its real UID to
 * its effective UID (so the child truly runs as `app`, not just euid=app) and
 * then invokes helper commands (`ps`, `date`) via system(), i.e. through
 * /bin/sh, WITHOUT an absolute path and WITHOUT sanitising PATH. Any caller who
 * controls PATH can plant a malicious `ps` earlier in PATH and have it executed
 * as `app`. This is a classic SUID + relative-binary / PATH-hijack bug.
 *
 * There is no flag here and no path to root here: exploiting this only moves
 * you laterally from `www` to `app`.
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    uid_t app = geteuid();

    /* Make the real uid match the effective uid so the spawned shell is a
     * genuine `app` process (survives a later setuid check, keeps $HOME logic
     * simple, etc.). This is what turns the PATH hijack into a real `app`
     * shell rather than an euid-only one. */
    if (setreuid(app, app) != 0) {
        perror("setreuid");
        return 1;
    }

    fprintf(stderr, "[logsync] rotating application logs as uid=%d...\n",
            (int)getuid());

    /* BUG: relative program names resolved through $PATH under /bin/sh. */
    system("date");
    system("ps -o pid,user,comm 2>/dev/null | head -n 5");

    fprintf(stderr, "[logsync] done.\n");
    return 0;
}
