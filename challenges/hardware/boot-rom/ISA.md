# NANO-8 boot ROM — ISA reference

`rom.bin` is a program for the NANO-8, a minimal 8-bit virtual CPU. Implement
the machine below, load the ROM at address 0, run from PC = 0, and observe the
bytes it emits with `OUT`.

## Machine model

- **Registers:** `R0`..`R7`, each 8-bit. All arithmetic wraps mod 256.
- **Memory:** one flat, byte-addressable space (256 bytes). The ROM image is
  loaded starting at address 0, so code and data live in the same memory.
- **PC:** program counter, measured in **bytes**.
- **Instruction width:** every instruction is exactly **3 bytes**:
  `opcode, arg1, arg2`. After a normal instruction, `PC += 3`.
- **Output:** `OUT` appends one byte to the output stream.

## Instruction set

| opcode | mnemonic | operands  | effect                        |
| ------ | -------- | --------- | ----------------------------- |
| `0x01` | `LDI`    | `r, imm`  | `Rr = imm`                    |
| `0x05` | `XOR`    | `r, s`    | `Rr = Rr ^ Rs`                |
| `0x08` | `OUT`    | `r, _`    | emit byte `Rr`                |
| `0x09` | `JNZ`    | `r, addr` | if `Rr != 0` then `PC = addr` |
| `0x0A` | `ADDI`   | `r, imm`  | `Rr = (Rr + imm) & 0xFF`      |
| `0x0B` | `HLT`    | `_, _`    | stop execution                |
| `0x0C` | `LDX`    | `r, p`    | `Rr = mem[Rp]` (indexed load) |

Unused operand slots are `0`. `addr` in `JNZ` is an absolute byte offset into
memory.
