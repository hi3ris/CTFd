#!/usr/bin/env python3
"""Marble -- a tiny stack esolang, served inside a jail.

Marble is a Forth-flavoured, whitespace-delimited stack language. Bare integer
and "string" literals push themselves; everything else is an instruction word.
The interpreter is a REPL: it runs one line at a time and KEEPS the stack and
the 256-cell memory across lines within a single connection (it is stateful).

The jail's whole premise is that a Marble program can compute but cannot touch
the host: there is deliberately no file word, no import, no eval. The only bridge
to host-provided helpers is the SYS gate, and SYS is supposed to expose ONLY the
safe Marble standard library (slots 0..7). Anything at slot 8 or above is
rejected. A benign program is therefore fully contained.

(The escape is left as an exercise -- see solution/ for the write-up.)
"""
import os
import sys

# ------------------------------------------------------------------ limits ---
MAX_LINE = 65536          # bytes per input line
MAX_STEPS = 200000        # instruction words executed per line
MAX_STACK = 8192          # stack depth
MAX_STR = 1 << 20         # max string length produced on the stack
MEM_SIZE = 256            # cells of integer memory (persistent per connection)
MAX_READ = 1 << 20        # cap on bytes returned by a host file read


class JailError(Exception):
    """A contained, recoverable error. The REPL reports it and stays alive."""


class VM:
    def __init__(self):
        self.stack = []
        self.mem = [0] * MEM_SIZE
        self.out = []          # output buffer for the current line
        self.steps = 0

    # --- stack helpers -----------------------------------------------------
    def push(self, v):
        if len(self.stack) >= MAX_STACK:
            raise JailError("stack overflow")
        if isinstance(v, str) and len(v) > MAX_STR:
            raise JailError("string too large")
        self.stack.append(v)

    def pop(self):
        if not self.stack:
            raise JailError("stack underflow")
        return self.stack.pop()

    def pop_int(self):
        v = self.pop()
        if not isinstance(v, int):
            raise JailError("expected int on top of stack")
        return v

    def pop_str(self):
        v = self.pop()
        if not isinstance(v, str):
            raise JailError("expected string on top of stack")
        return v

    def emit(self, s):
        self.out.append(s)


# ============================================================ SYS dispatch ===
# The Marble standard library. Slots 0..SAFE_COUNT-1 are the ONLY entries the
# jail is meant to expose through the SYS gate. They are pure: they read and
# write the stack and never touch the host.
def _sys_strlen(vm):  # 0
    vm.push(len(vm.pop_str()))


def _sys_concat(vm):  # 1
    b = vm.pop_str(); a = vm.pop_str()
    vm.push(a + b)


def _sys_substr(vm):  # 2
    n = vm.pop_int(); start = vm.pop_int(); s = vm.pop_str()
    if start < 0 or n < 0:
        raise JailError("substr: negative bounds")
    vm.push(s[start:start + n])


def _sys_itoa(vm):    # 3
    vm.push(str(vm.pop_int()))


def _sys_atoi(vm):    # 4
    s = vm.pop_str().strip()
    if not (s.lstrip("-").isdigit()):
        raise JailError("atoi: not an integer")
    vm.push(int(s))


def _sys_upper(vm):   # 5
    vm.push(vm.pop_str().upper())


def _sys_ord(vm):     # 6
    s = vm.pop_str()
    if len(s) != 1:
        raise JailError("ord: expected a single character")
    vm.push(ord(s))


def _sys_chr(vm):     # 7
    n = vm.pop_int()
    if not (0 <= n <= 0x10FFFF):
        raise JailError("chr: code point out of range")
    vm.push(chr(n))


# ---- host natives -----------------------------------------------------------
# These live in the SAME dispatch table, right after the standard library, but
# they are NOT part of the exposed range: they are the interpreter's own
# host-side primitives, never meant to be reachable from a Marble program.
def _native_env(vm):  # 8  (hidden)
    name = vm.pop_str()
    vm.push(os.environ.get(name, ""))


def _native_read(vm):  # 9  (hidden)
    path = vm.pop_str()
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_READ)
    except OSError as e:
        raise JailError(f"read: {e.__class__.__name__}")
    vm.push(data.decode("utf-8", "replace"))


DISPATCH = [
    _sys_strlen,   # 0
    _sys_concat,   # 1
    _sys_substr,   # 2
    _sys_itoa,     # 3
    _sys_atoi,     # 4
    _sys_upper,    # 5
    _sys_ord,      # 6
    _sys_chr,      # 7
    _native_env,   # 8  (hidden -- not part of the exposed range)
    _native_read,  # 9  (hidden -- not part of the exposed range)
]

# The jail only exposes the standard library, slots 0..7.
SAFE_COUNT = 8


def op_sys(vm):
    idx = vm.pop_int()
    # Guard: reject anything at or above the exposed standard-library range.
    if idx >= SAFE_COUNT:
        raise JailError(f"SYS {idx}: index out of exposed range (0..{SAFE_COUNT - 1})")
    try:
        fn = DISPATCH[idx]
    except IndexError:
        raise JailError(f"SYS {idx}: no such service")
    fn(vm)


# ================================================================= opcodes ===
def op_pop(vm):
    vm.pop()


def op_dup(vm):
    v = vm.pop(); vm.push(v); vm.push(v)


def op_swap(vm):
    b = vm.pop(); a = vm.pop(); vm.push(b); vm.push(a)


def op_over(vm):
    b = vm.pop(); a = vm.pop(); vm.push(a); vm.push(b); vm.push(a)


def _bin_int(fn):
    def run(vm):
        b = vm.pop_int(); a = vm.pop_int(); vm.push(fn(a, b))
    return run


def op_div(vm):
    b = vm.pop_int(); a = vm.pop_int()
    if b == 0:
        raise JailError("division by zero")
    vm.push(a // b)


def op_mod(vm):
    b = vm.pop_int(); a = vm.pop_int()
    if b == 0:
        raise JailError("modulo by zero")
    vm.push(a % b)


def op_neg(vm):
    vm.push(-vm.pop_int())


def op_not(vm):
    vm.push(0 if vm.pop_int() else 1)


def op_load(vm):
    addr = vm.pop_int()
    if not (0 <= addr < MEM_SIZE):
        raise JailError(f"LOAD: address {addr} out of range (0..{MEM_SIZE - 1})")
    vm.push(vm.mem[addr])


def op_store(vm):
    addr = vm.pop_int(); val = vm.pop_int()
    if not (0 <= addr < MEM_SIZE):
        raise JailError(f"STORE: address {addr} out of range (0..{MEM_SIZE - 1})")
    vm.mem[addr] = val


def op_print(vm):
    v = vm.pop()
    vm.emit(v if isinstance(v, str) else str(v))
    vm.emit("\n")


def op_emit(vm):
    n = vm.pop_int()
    if not (0 <= n <= 0x10FFFF):
        raise JailError("EMIT: code point out of range")
    vm.emit(chr(n))


def op_stack(vm):
    parts = []
    for v in vm.stack:
        parts.append(repr(v) if isinstance(v, str) else str(v))
    vm.emit("<%d> %s\n" % (len(vm.stack), " ".join(parts)))


def op_reset(vm):
    vm.stack.clear()
    vm.mem[:] = [0] * MEM_SIZE
    vm.emit("reset\n")


HELP_TEXT = """\
Marble reference (stack machine; top of stack is the last-pushed value)
  <int>        push a non-negative integer literal (e.g. 42)
  "text"       push a string literal (escapes: \\n \\t \\\\ \\")
  POP DUP SWAP OVER          stack shuffles
  ADD SUB MUL DIV MOD NEG    integer arithmetic
  EQ NE LT GT NOT            comparisons / logic -> 1 or 0
  AND OR                     logic on int truthiness
  LOAD STORE                 256-cell integer memory (addr checked 0..255)
  PRINT                      pop and print a value + newline
  EMIT                       pop an int and print it as one character
  STACK                      show the current stack (debug)
  RESET                      clear stack and memory
  HELP                       this text
  SYS                        pop index i, invoke standard-library service i
                             exposed services (0..7):
                               0 strlen  1 concat  2 substr  3 itoa
                               4 atoi    5 upper   6 ord     7 chr
The jail exposes only standard-library slots 0..7 through SYS; the host
filesystem and environment are not reachable from a Marble program.
"""


def op_help(vm):
    vm.emit(HELP_TEXT)


OPS = {
    "POP": op_pop, "DUP": op_dup, "SWAP": op_swap, "OVER": op_over,
    "ADD": _bin_int(lambda a, b: a + b),
    "SUB": _bin_int(lambda a, b: a - b),
    "MUL": _bin_int(lambda a, b: a * b),
    "DIV": op_div, "MOD": op_mod, "NEG": op_neg,
    "EQ": _bin_int(lambda a, b: 1 if a == b else 0),
    "NE": _bin_int(lambda a, b: 1 if a != b else 0),
    "LT": _bin_int(lambda a, b: 1 if a < b else 0),
    "GT": _bin_int(lambda a, b: 1 if a > b else 0),
    "AND": _bin_int(lambda a, b: 1 if (a and b) else 0),
    "OR": _bin_int(lambda a, b: 1 if (a or b) else 0),
    "NOT": op_not,
    "LOAD": op_load, "STORE": op_store,
    "PRINT": op_print, "EMIT": op_emit,
    "SYS": op_sys,
    "STACK": op_stack, "RESET": op_reset, "HELP": op_help,
}


# ============================================================== tokenizer ===
_ESC = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def tokenize(line):
    """Split a line into tokens: integers (int), strings (str), words (upper)."""
    toks = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c.isspace():
            i += 1
            continue
        if c == "#":                     # comment to end of line
            break
        if c == '"':                     # string literal
            i += 1
            buf = []
            while i < n and line[i] != '"':
                if line[i] == "\\":
                    i += 1
                    if i >= n:
                        raise JailError("unterminated escape in string")
                    buf.append(_ESC.get(line[i], line[i]))
                else:
                    buf.append(line[i])
                i += 1
            if i >= n:
                raise JailError("unterminated string literal")
            i += 1                       # consume closing quote
            toks.append(("str", "".join(buf)))
            continue
        # bare token up to next whitespace
        j = i
        while j < n and not line[j].isspace():
            j += 1
        word = line[i:j]
        i = j
        if word.isdigit():               # non-negative integer literal only
            toks.append(("int", int(word)))
        else:
            toks.append(("word", word.upper()))
    return toks


def run_line(vm, line):
    vm.out = []
    for kind, val in tokenize(line):
        vm.steps += 1
        if vm.steps > MAX_STEPS:
            raise JailError("step budget exceeded")
        if kind == "int" or kind == "str":
            vm.push(val)
        else:
            op = OPS.get(val)
            if op is None:
                raise JailError(f"unknown word: {val}")
            op(vm)
    return "".join(vm.out)


BANNER = (
    "== Marble jail ==\n"
    "A tiny stack esolang. Type HELP for the instruction reference.\n"
    "Programs run one line at a time; the stack persists across lines.\n"
    "The interpreter is sandboxed: no filesystem, no environment, no host.\n"
)


def main():
    vm = VM()
    sys.stdout.write(BANNER)
    sys.stdout.write("marble> ")
    sys.stdout.flush()
    while True:
        line = sys.stdin.readline()
        if not line:                     # EOF / disconnect
            break
        line = line[:MAX_LINE].rstrip("\n").rstrip("\r")
        vm.steps = 0
        try:
            out = run_line(vm, line)
            if out:
                sys.stdout.write(out)
                if not out.endswith("\n"):
                    sys.stdout.write("\n")
        except JailError as e:
            sys.stdout.write(f"error: {e}\n")
        except Exception:                # never leak a host traceback
            sys.stdout.write("error: internal\n")
        sys.stdout.write("marble> ")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
