/*
 * synthvm - a bespoke register+stack bytecode machine (~80 opcodes).
 *
 * The embedded program (PROG[], see program.h) is what actually validates the
 * input. There is NO flag string in this binary: the accepted input *is* the
 * flag, and the program only stores its transformed image.
 *
 * Two features make static reading hard:
 *   1) The opcode dispatch is REMAPPED AT RUNTIME. The bytes in PROG are not the
 *      internal opcode numbers; init_dispatch() builds a 256-entry permutation
 *      (keyed Fisher-Yates over a xorshift32 PRNG) and every fetched byte is
 *      routed through it. You must recover (or trace) that permutation.
 *   2) Immediate operands use a custom varint: 7 payload bits in the HIGH bits
 *      of each byte, the LOW bit is the continuation flag. It is not LEB128.
 *
 * Build: cc -O2 -s -I src -o synthvm src/vm.c
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include "program.h"

#define OP_SEED   0x1F3D5B79u
#define SBOX_SEED 0xC0FFEE42u
#define MEMSZ     0x10000
#define STEP_MAX  20000000u

/* ---- opcode numbering (internal); PROG bytes are the *remapped* values ---- */
enum {
    NOP,HALT,MOV,MOVI,ADD,SUB,MUL,XOR,AND,OR,SHL,SHR,ROL,ROR,NOT,NEG,ADDI,
    SUBI,XORI,ANDI,ORI,MULI,SHLI,SHRI,ROLI,RORI,CMP,CMPI,TEST,LDB,LDW,LDD,STB,
    STW,STD,LEA,PUSH,POP,JMP,JZ,JNZ,JC,JNC,JG,JL,JGE,JLE,JA,JB,CALL,RET,IN,OUT,
    RND,SBOX_,ISBOX_,ROL8,ROR8,POPCNT,CLZ,BSWAP,REVB,SEXTB,MULH,DIV,MOD,MIN,MAX,
    SWP,INC,DEC,CLR,SETZ,NAND,NOR,ADC,SBB,MIX,ENTER,LEAVE,NUM_OPS
};

static uint8_t opmap[256];   /* opmap[raw_byte] = internal opcode */
static uint8_t sbox[256];
static uint8_t isbox[256];

static uint32_t xs32(uint32_t x) {
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return x;
}

/* keyed Fisher-Yates permutation of 0..255 */
static void permute(uint8_t out[256], uint32_t seed) {
    for (int i = 0; i < 256; i++) out[i] = (uint8_t)i;
    uint32_t st = seed;
    for (int i = 255; i > 0; i--) {
        st = xs32(st);
        int j = (int)(st % (uint32_t)(i + 1));
        uint8_t t = out[i]; out[i] = out[j]; out[j] = t;
    }
}

static void init_dispatch(void) {
    permute(opmap, OP_SEED);
    permute(sbox,  SBOX_SEED);
    for (int i = 0; i < 256; i++) isbox[sbox[i]] = (uint8_t)i;
}

/* custom varint: payload in bits 1..7, bit0 = "more follows" */
static uint32_t read_varint(uint32_t *pc) {
    uint32_t val = 0; int shift = 0;
    for (;;) {
        uint8_t b = PROG[(*pc)++];
        val |= (uint32_t)(b >> 1) << shift;
        shift += 7;
        if (!(b & 1)) break;
    }
    return val;
}

static uint8_t rol8b(uint8_t x, int n) {
    n &= 7; if (!n) return x;
    return (uint8_t)((x << n) | (x >> (8 - n)));
}
static uint8_t ror8b(uint8_t x, int n) {
    n &= 7; if (!n) return x;
    return (uint8_t)((x >> n) | (x << (8 - n)));
}

int main(void) {
    init_dispatch();

    static uint8_t mem[MEMSZ];
    uint32_t reg[16];
    memset(reg, 0, sizeof(reg));
    uint32_t sp = 0xF000;         /* stack pointer inside mem[] */
    uint32_t pc = 0;
    uint32_t ca = 0, cb = 0;      /* last compare operands */
    uint32_t steps = 0;

    for (;;) {
        if (pc >= PROG_LEN) { fprintf(stderr, "pc oob\n"); return 2; }
        if (++steps > STEP_MAX) { fprintf(stderr, "step limit\n"); return 3; }

        uint8_t raw = PROG[pc++];
        uint8_t op = opmap[raw];

        /* operand pre-decode by format */
        uint8_t d = 0, s = 0, base = 0;
        uint32_t imm = 0, off = 0, tgt = 0;

        switch (op) {
        /* NONE */
        case NOP: case HALT: case RET: case LEAVE:
            break;
        /* R1 */
        case NOT: case NEG: case PUSH: case POP: case IN: case OUT: case RND:
        case BSWAP: case REVB: case SEXTB: case INC: case DEC: case CLR: case SETZ: {
            uint8_t b = PROG[pc++]; d = b >> 4; break; }
        /* R2 */
        case MOV: case ADD: case SUB: case MUL: case XOR: case AND: case OR:
        case SHL: case SHR: case ROL: case ROR: case CMP: case TEST: case SBOX_:
        case ISBOX_: case POPCNT: case CLZ: case MULH: case DIV: case MOD:
        case MIN: case MAX: case SWP: case NAND: case NOR: case ADC: case SBB:
        case MIX: {
            uint8_t b = PROG[pc++]; d = b >> 4; s = b & 0xF; break; }
        /* RI */
        case MOVI: case ADDI: case SUBI: case XORI: case ANDI: case ORI:
        case MULI: case SHLI: case SHRI: case ROLI: case RORI: case CMPI:
        case ROL8: case ROR8: {
            uint8_t b = PROG[pc++]; d = b >> 4; imm = read_varint(&pc); break; }
        /* RM */
        case LDB: case LDW: case LDD: case STB: case STW: case STD: case LEA: {
            uint8_t b = PROG[pc++]; d = b >> 4; base = b & 0xF; off = read_varint(&pc); break; }
        /* BR */
        case JMP: case JZ: case JNZ: case JC: case JNC: case JG: case JL:
        case JGE: case JLE: case JA: case JB: case CALL:
            tgt = read_varint(&pc); break;
        /* IMM */
        case ENTER:
            imm = read_varint(&pc); break;
        default:
            fprintf(stderr, "bad op %u (raw %u)\n", op, raw); return 4;
        }

        uint32_t addr = (base < 16 ? reg[base] : 0) + off;
        addr &= (MEMSZ - 1);

        switch (op) {
        case NOP: break;
        case HALT: return 0;
        case MOV:  reg[d] = reg[s]; break;
        case MOVI: reg[d] = imm; break;
        case ADD:  reg[d] = reg[d] + reg[s]; break;
        case SUB:  reg[d] = reg[d] - reg[s]; break;
        case MUL:  reg[d] = reg[d] * reg[s]; break;
        case XOR:  reg[d] = reg[d] ^ reg[s]; break;
        case AND:  reg[d] = reg[d] & reg[s]; break;
        case OR:   reg[d] = reg[d] | reg[s]; break;
        case SHL:  reg[d] = reg[d] << (reg[s] & 31); break;
        case SHR:  reg[d] = reg[d] >> (reg[s] & 31); break;
        case ROL:  { uint32_t n = reg[s] & 31; reg[d] = n ? (reg[d] << n) | (reg[d] >> (32 - n)) : reg[d]; break; }
        case ROR:  { uint32_t n = reg[s] & 31; reg[d] = n ? (reg[d] >> n) | (reg[d] << (32 - n)) : reg[d]; break; }
        case NOT:  reg[d] = ~reg[d]; break;
        case NEG:  reg[d] = (uint32_t)(-(int32_t)reg[d]); break;
        case ADDI: reg[d] = reg[d] + imm; break;
        case SUBI: reg[d] = reg[d] - imm; break;
        case XORI: reg[d] = reg[d] ^ imm; break;
        case ANDI: reg[d] = reg[d] & imm; break;
        case ORI:  reg[d] = reg[d] | imm; break;
        case MULI: reg[d] = reg[d] * imm; break;
        case SHLI: reg[d] = reg[d] << (imm & 31); break;
        case SHRI: reg[d] = reg[d] >> (imm & 31); break;
        case ROLI: { uint32_t n = imm & 31; reg[d] = n ? (reg[d] << n) | (reg[d] >> (32 - n)) : reg[d]; break; }
        case RORI: { uint32_t n = imm & 31; reg[d] = n ? (reg[d] >> n) | (reg[d] << (32 - n)) : reg[d]; break; }
        case CMP:  ca = reg[d]; cb = reg[s]; break;
        case CMPI: ca = reg[d]; cb = imm; break;
        case TEST: ca = reg[d] & reg[s]; cb = 0; break;
        case LDB:  reg[d] = mem[addr]; break;
        case LDW:  reg[d] = mem[addr] | (mem[(addr + 1) & (MEMSZ - 1)] << 8); break;
        case LDD:  reg[d] = mem[addr] | (mem[(addr + 1) & (MEMSZ - 1)] << 8)
                          | (mem[(addr + 2) & (MEMSZ - 1)] << 16)
                          | ((uint32_t)mem[(addr + 3) & (MEMSZ - 1)] << 24); break;
        case STB:  mem[addr] = reg[d] & 0xFF; break;
        case STW:  mem[addr] = reg[d] & 0xFF; mem[(addr + 1) & (MEMSZ - 1)] = (reg[d] >> 8) & 0xFF; break;
        case STD:  mem[addr] = reg[d] & 0xFF; mem[(addr + 1) & (MEMSZ - 1)] = (reg[d] >> 8) & 0xFF;
                   mem[(addr + 2) & (MEMSZ - 1)] = (reg[d] >> 16) & 0xFF;
                   mem[(addr + 3) & (MEMSZ - 1)] = (reg[d] >> 24) & 0xFF; break;
        case LEA:  reg[d] = addr; break;
        case PUSH: sp -= 4; mem[sp & (MEMSZ - 1)] = reg[d] & 0xFF;
                   mem[(sp + 1) & (MEMSZ - 1)] = (reg[d] >> 8) & 0xFF;
                   mem[(sp + 2) & (MEMSZ - 1)] = (reg[d] >> 16) & 0xFF;
                   mem[(sp + 3) & (MEMSZ - 1)] = (reg[d] >> 24) & 0xFF; break;
        case POP:  reg[d] = mem[sp & (MEMSZ - 1)] | (mem[(sp + 1) & (MEMSZ - 1)] << 8)
                          | (mem[(sp + 2) & (MEMSZ - 1)] << 16)
                          | ((uint32_t)mem[(sp + 3) & (MEMSZ - 1)] << 24); sp += 4; break;
        case JMP:  pc = tgt; break;
        case JZ:   if (ca == cb) pc = tgt; break;
        case JNZ:  if (ca != cb) pc = tgt; break;
        case JC:   if (ca <  cb) pc = tgt; break;
        case JNC:  if (ca >= cb) pc = tgt; break;
        case JG:   if ((int32_t)ca >  (int32_t)cb) pc = tgt; break;
        case JL:   if ((int32_t)ca <  (int32_t)cb) pc = tgt; break;
        case JGE:  if ((int32_t)ca >= (int32_t)cb) pc = tgt; break;
        case JLE:  if ((int32_t)ca <= (int32_t)cb) pc = tgt; break;
        case JA:   if (ca >  cb) pc = tgt; break;
        case JB:   if (ca <  cb) pc = tgt; break;
        case CALL: sp -= 4; { uint32_t rv = pc;
                   mem[sp & (MEMSZ - 1)] = rv & 0xFF;
                   mem[(sp + 1) & (MEMSZ - 1)] = (rv >> 8) & 0xFF;
                   mem[(sp + 2) & (MEMSZ - 1)] = (rv >> 16) & 0xFF;
                   mem[(sp + 3) & (MEMSZ - 1)] = (rv >> 24) & 0xFF; } pc = tgt; break;
        case RET:  pc = mem[sp & (MEMSZ - 1)] | (mem[(sp + 1) & (MEMSZ - 1)] << 8)
                      | (mem[(sp + 2) & (MEMSZ - 1)] << 16)
                      | ((uint32_t)mem[(sp + 3) & (MEMSZ - 1)] << 24); sp += 4; break;
        case IN:   { int c = getchar(); reg[d] = (c == EOF) ? 0x100u : (uint32_t)(c & 0xFF); break; }
        case OUT:  putchar((int)(reg[d] & 0xFF)); break;
        case RND:  { static uint32_t rs = 0x2545F491u; rs = xs32(rs); reg[d] = rs; break; }
        case SBOX_:  reg[d] = sbox[reg[s] & 0xFF]; break;
        case ISBOX_: reg[d] = isbox[reg[s] & 0xFF]; break;
        case ROL8: reg[d] = rol8b((uint8_t)(reg[d] & 0xFF), (int)imm); break;
        case ROR8: reg[d] = ror8b((uint8_t)(reg[d] & 0xFF), (int)imm); break;
        case POPCNT: reg[d] = (uint32_t)__builtin_popcount(reg[s]); break;
        case CLZ:  reg[d] = reg[s] ? (uint32_t)__builtin_clz(reg[s]) : 32u; break;
        case BSWAP: reg[d] = __builtin_bswap32(reg[d]); break;
        case REVB: { uint32_t v = reg[d], o = 0; for (int i = 0; i < 32; i++) { o = (o << 1) | (v & 1); v >>= 1; } reg[d] = o; break; }
        case SEXTB: reg[d] = (uint32_t)(int32_t)(int8_t)(reg[d] & 0xFF); break;
        case MULH: reg[d] = (uint32_t)(((uint64_t)reg[d] * (uint64_t)reg[s]) >> 32); break;
        case DIV:  reg[d] = reg[s] ? reg[d] / reg[s] : 0xFFFFFFFFu; break;
        case MOD:  reg[d] = reg[s] ? reg[d] % reg[s] : reg[d]; break;
        case MIN:  reg[d] = reg[d] < reg[s] ? reg[d] : reg[s]; break;
        case MAX:  reg[d] = reg[d] > reg[s] ? reg[d] : reg[s]; break;
        case SWP:  { uint32_t t = reg[d]; reg[d] = reg[s]; reg[s] = t; break; }
        case INC:  reg[d] += 1; break;
        case DEC:  reg[d] -= 1; break;
        case CLR:  reg[d] = 0; break;
        case SETZ: reg[d] = (ca == cb) ? 1u : 0u; break;
        case NAND: reg[d] = ~(reg[d] & reg[s]); break;
        case NOR:  reg[d] = ~(reg[d] | reg[s]); break;
        case ADC:  reg[d] = reg[d] + reg[s] + 1; break;
        case SBB:  reg[d] = reg[d] - reg[s] - 1; break;
        case MIX:  reg[d] = (reg[d] * 0x01000193u) ^ reg[s]; break;
        case ENTER: sp -= imm; break;
        case LEAVE: break;
        default:
            fprintf(stderr, "unreachable op %u\n", op); return 5;
        }
    }
}
