#!/usr/bin/env python3
"""FZLP/1 -- Fictional Zoned Line Provisioning protocol (challenge service).

A small, invented, line-oriented text protocol for "provisioning channels".
It is served over TCP; the flag is a server-side oracle: it is emitted ONLY
after the service observes that the hidden maintenance channel has been armed.

Wire overview (the part players are told, in handout/PROTOCOL.md):

    On connect the server sends a banner:      FZLP/1 ready
    Requests are single lines terminated by \\n. Verbs are case-insensitive.

    PING            -> PONG
    HELP            -> lists supported verbs
    STAT            -> reports channel state and mask
    CFG <n>         -> provisions channels; n is the number of channels to
                       configure (documented range 0..3). After the header the
                       server reads <n> ENTRY lines, one per channel; entry line
                       k is a value for channel k (two hex digits, e.g. "01").
                       Replies: OK mask=0x..
    DUMP            -> (locked) maintenance dump

The catch (players discover this by driving the socket, it is NOT in the spec):
the CFG entry loop is off-by-one. It reads n+1 entry lines and writes channel
index i for i in range(n+1), never checking i against the documented channel
count. There is a fourth, undocumented channel -- index 3, the "maintenance"
channel -- adjacent to the three documented ones. It can be written ONLY when
the write index reaches 3, which happens ONLY at the boundary n == 3 (the
documented maximum): the off-by-one pushes the final write onto channel 3.
n is validated to 0..3, so you cannot simply say "CFG 7" to reach it.

Arming channel 3 (writing it non-zero) unlocks the DUMP command, which is the
hidden command; DUMP then returns the per-team flag.

Decoy: STAT advertises `reserved_admin_ch=0x07`, nudging solvers toward a
"channel 7". There is no channel 7 -- n>3 is rejected and the off-by-one only
ever reaches index 3. Refutable in one request.
"""
import os
import socket
import socketserver
import threading

from flag import get_flag

PORT = int(os.environ.get("PORT", "9109"))

# Number of DOCUMENTED channels (0..2). The maintenance channel is index 3 and
# is intentionally NOT part of the documented count -- it sits adjacent in the
# backing store and is only reachable through the CFG length off-by-one.
DOC_CHANNELS = 3
STORE_SIZE = 4          # channels 0..3; index 3 == maintenance
MAINT = 3

FLAG = get_flag()

BANNER = b"FZLP/1 ready\r\n"


def parse_hex_byte(token: str) -> int:
    """Lenient entry parser: two-hex-digit value, else 0.

    Leniency matters -- if a solver under-sends entry lines, the *next* command
    they type gets swallowed as an entry (and, not being valid hex, sets 0).
    That swallowing is itself an observable clue that the loop reads more lines
    than the header declared.
    """
    token = token.strip()
    try:
        return int(token, 16) & 0xFF
    except ValueError:
        return 0


class FZLPHandler(socketserver.StreamRequestHandler):
    timeout = 60  # drop idle/half-open connections

    def reply(self, text: str) -> None:
        try:
            self.wfile.write((text + "\r\n").encode())
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            raise EOFError

    def read_line(self):
        raw = self.rfile.readline()
        if not raw:
            raise EOFError
        return raw.decode("utf-8", "replace").rstrip("\r\n")

    def mask(self) -> int:
        m = 0
        for i in range(STORE_SIZE):
            if self.channels[i]:
                m |= (1 << i)
        return m

    def handle(self):
        # Per-connection state.
        self.channels = bytearray(STORE_SIZE)   # index 3 (MAINT) starts locked
        try:
            self.wfile.write(BANNER)
            self.wfile.flush()
        except OSError:
            return

        try:
            while True:
                line = self.read_line()
                if line == "":
                    # blank line at top level: ignore
                    continue
                parts = line.split()
                verb = parts[0].upper()
                args = parts[1:]

                if verb == "PING":
                    self.reply("PONG")

                elif verb == "HELP":
                    verbs = ["PING", "STAT", "CFG", "HELP", "SU"]
                    if self.channels[MAINT]:
                        # DUMP becomes advertised once maintenance is armed.
                        verbs.append("DUMP")
                    self.reply("verbs: " + " ".join(verbs))

                elif verb == "STAT":
                    self.reply(
                        "STAT ch0=%02x ch1=%02x ch2=%02x mask=0x%02x reserved_admin_ch=0x07"
                        % (self.channels[0], self.channels[1],
                           self.channels[2], self.mask())
                    )

                elif verb == "CFG":
                    self.handle_cfg(args)

                elif verb == "DUMP":
                    # Hidden command. Reachable in the verb table only after the
                    # maintenance channel is armed, and gated on the EFFECT here
                    # (not on any particular request shape) -- a server-side
                    # oracle: it verifies channel 3 is set, then emits the flag.
                    if self.channels[MAINT]:
                        self.reply("MAINT ok; flag follows")
                        self.reply(FLAG)
                    else:
                        self.reply("ERR locked: maintenance channel not armed")

                elif verb == "SU":
                    # Decoy dead-end. Always refuses regardless of input.
                    self.reply("ERR: SU disabled on this build; "
                               "channels are provisioned via CFG")

                else:
                    self.reply("ERR unknown verb (try HELP)")
        except EOFError:
            return
        except Exception:
            # Never leak a stack trace to the wire.
            try:
                self.reply("ERR internal")
            except Exception:
                pass
            return

    def handle_cfg(self, args):
        if len(args) != 1:
            self.reply("ERR usage: CFG <n>")
            return
        try:
            n = int(args[0])
        except ValueError:
            self.reply("ERR n must be an integer")
            return

        # The length field is validated against the DOCUMENTED range only.
        # 0..DOC_CHANNELS (i.e. 0..3). This is why "CFG 7" can't reach the
        # maintenance channel directly -- but the loop below over-reads by one.
        if not (0 <= n <= DOC_CHANNELS):
            self.reply("ERR n out of range (expected 0..%d)" % DOC_CHANNELS)
            return

        # --- the bug: inclusive bound. Reads n+1 entry lines and writes
        # channel index i for i in range(n+1), with NO check that i stays
        # within the documented channel count. At n == DOC_CHANNELS (==3) the
        # final iteration writes index 3 == the maintenance channel.
        for i in range(n + 1):
            entry = self.read_line()
            self.channels[i] = parse_hex_byte(entry)   # store is size 4: safe

        armed_now = bool(self.channels[MAINT])
        if armed_now:
            self.reply("OK mask=0x%02x MAINT-ARMED (see HELP)" % self.mask())
        else:
            self.reply("OK mask=0x%02x" % self.mask())


class ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    server = ThreadingTCPServer(("0.0.0.0", PORT), FZLPHandler)
    print("[*] FZLP/1 listening on 0.0.0.0:%d" % PORT, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
