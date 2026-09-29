/*
 * notebackup -- "archive a user's notes" helper.
 *
 * Installed SETUID to the `svc` user (owner svc:svc, mode 4755) so that any
 * local user can archive a note bundle that is owned by the service account
 * `svc`. Usage: notebackup <bundle-name>
 *
 * VULNERABILITY (intentional, stage 2 of the chain): it raises its real UID to
 * its effective UID (so the child truly runs as `svc`) and then builds a shell
 * command by concatenating the caller-controlled <bundle-name> straight into a
 * system() string. No quoting, no validation. A bundle name such as
 *
 *     'x; /bin/sh'
 *
 * therefore runs an arbitrary command as `svc`. This is a classic SUID shell
 * argument-injection bug (distinct from a PATH hijack: here the injected text
 * is the command, not a hijacked relative binary).
 *
 * There is no flag here and no path to root here: exploiting this only moves
 * you laterally from `www` to `svc`.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    uid_t svc = geteuid();
    const char *bundle = (argc > 1) ? argv[1] : "daily";
    char cmd[512];

    /* Make the real uid match the effective uid so the spawned shell is a
     * genuine `svc` process, not merely euid=svc. */
    if (setreuid(svc, svc) != 0) {
        perror("setreuid");
        return 1;
    }

    fprintf(stderr, "[notebackup] archiving bundle '%s' as uid=%d...\n", bundle,
            (int)getuid());

    /* BUG: caller-controlled `bundle` concatenated into a /bin/sh command. */
    snprintf(cmd, sizeof(cmd),
             "tar -czf /var/backups/notes-%s.tgz /srv/notes 2>/dev/null", bundle);
    system(cmd);

    fprintf(stderr, "[notebackup] done.\n");
    return 0;
}
