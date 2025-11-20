# rv32i.py
# RV32I instruction decoding -- format detection, field extraction,
# immediate reconstruction, and mnemonic lookup.
#
# Reference: The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA
# (https://riscv.org/technical/specifications/)
#
# All instructions are exactly 32 bits. The opcode lives in bits [6:0] and
# tells us the format. From there the field positions are fixed per format.

# ---- register ABI names --------------------------------------------------
# Using ABI names (a0, sp, ra...) instead of x0-x31 since that's what
# everyone actually writes in assembly.

REGS = [
    "zero", "ra", "sp",  "gp",  "tp",
    "t0",   "t1", "t2",  "s0",  "s1",
    "a0",   "a1", "a2",  "a3",  "a4",  "a5",  "a6",  "a7",
    "s2",   "s3", "s4",  "s5",  "s6",  "s7",  "s8",  "s9", "s10", "s11",
    "t3",   "t4", "t5",  "t6",
]

def reg(n):
    return REGS[n] if 0 <= n < 32 else f"x{n}"


# ---- bit manipulation helpers --------------------------------------------

def bits(word, hi, lo):
    """Extract bits [hi:lo] inclusive from word."""
    mask = (1 << (hi - lo + 1)) - 1
    return (word >> lo) & mask

def sign_ext(val, width):
    """Sign-extend val from width bits to a Python int."""
    if val & (1 << (width - 1)):
        val -= (1 << width)
    return val


# ---- immediate reconstruction --------------------------------------------
# Each format scrambles the immediate bits differently to simplify the
# hardware. We reassemble them here in software.

def imm_i(word):
    # imm[11:0] = inst[31:20]
    return sign_ext(bits(word, 31, 20), 12)

def imm_s(word):
    # imm[11:5] = inst[31:25], imm[4:0] = inst[11:7]
    hi = bits(word, 31, 25)
    lo = bits(word, 11,  7)
    return sign_ext((hi << 5) | lo, 12)

def imm_b(word):
    # imm[12]   = inst[31]
    # imm[10:5] = inst[30:25]
    # imm[4:1]  = inst[11:8]
    # imm[11]   = inst[7]
    # imm[0]    = 0 (branches are always 2-byte aligned)
    b12  = bits(word, 31, 31)
    b10_5 = bits(word, 30, 25)
    b4_1  = bits(word, 11,  8)
    b11   = bits(word,  7,  7)
    raw = (b12 << 12) | (b11 << 11) | (b10_5 << 5) | (b4_1 << 1)
    return sign_ext(raw, 13)

def imm_u(word):
    # upper immediate -- already in the right place, just zero the low 12 bits
    # returned as a plain integer (the assembler would write lui rd, val>>12)
    return bits(word, 31, 12)   # caller handles the <<12 for display

def imm_j(word):
    # imm[20]    = inst[31]
    # imm[10:1]  = inst[30:21]
    # imm[11]    = inst[20]
    # imm[19:12] = inst[19:12]
    # imm[0]     = 0
    b20    = bits(word, 31, 31)
    b10_1  = bits(word, 30, 21)
    b11    = bits(word, 20, 20)
    b19_12 = bits(word, 19, 12)
    raw = (b20 << 20) | (b19_12 << 12) | (b11 << 11) | (b10_1 << 1)
    return sign_ext(raw, 21)


# ---- instruction tables --------------------------------------------------
# Keyed by (opcode,) or (opcode, funct3) or (opcode, funct3, funct7)

OPCODES = {
    0b0110011: "R",
    0b0010011: "I_arith",
    0b0000011: "I_load",
    0b1100111: "I_jalr",
    0b1110011: "I_system",
    0b0100011: "S",
    0b1100011: "B",
    0b0110111: "U_lui",
    0b0010111: "U_auipc",
    0b1101111: "J",
}

# R-type: keyed by (funct3, funct7)
R_OPS = {
    (0x0, 0x00): "add",
    (0x0, 0x20): "sub",
    (0x1, 0x00): "sll",
    (0x2, 0x00): "slt",
    (0x3, 0x00): "sltu",
    (0x4, 0x00): "xor",
    (0x5, 0x00): "srl",
    (0x5, 0x20): "sra",
    (0x6, 0x00): "or",
    (0x7, 0x00): "and",
}

# I-type arithmetic: keyed by funct3 (srai is a special case -- same funct3 as srli)
I_ARITH_OPS = {
    0x0: "addi",
    0x2: "slti",
    0x3: "sltiu",
    0x4: "xori",
    0x6: "ori",
    0x7: "andi",
    0x1: "slli",   # funct7 must be 0x00
    0x5: "srli",   # funct7 0x00 = srli, 0x20 = srai (handled below)
}

I_LOAD_OPS = {
    0x0: "lb",
    0x1: "lh",
    0x2: "lw",
    0x4: "lbu",
    0x5: "lhu",
}

B_OPS = {
    0x0: "beq",
    0x1: "bne",
    0x4: "blt",
    0x5: "bge",
    0x6: "bltu",
    0x7: "bgeu",
}

S_OPS = {
    0x0: "sb",
    0x1: "sh",
    0x2: "sw",
}


# ---- main decode function ------------------------------------------------

class DecodeError(Exception):
    pass

def decode(word):
    """
    Decode a 32-bit RV32I instruction word.
    Returns a dict with at minimum 'mnemonic' and 'fmt'.
    Raises DecodeError for unknown/illegal encodings.
    """
    if word & 0x3 != 0x3:
        raise DecodeError(f"not a 32-bit instruction (low bits = {word & 0x3:#x})")

    opcode = bits(word, 6, 0)
    fmt    = OPCODES.get(opcode)

    if fmt is None:
        raise DecodeError(f"unknown opcode {opcode:#09b}")

    rd     = bits(word, 11,  7)
    funct3 = bits(word, 14, 12)
    rs1    = bits(word, 19, 15)
    rs2    = bits(word, 24, 20)
    funct7 = bits(word, 31, 25)

    if fmt == "R":
        mnemonic = R_OPS.get((funct3, funct7))
        if mnemonic is None:
            raise DecodeError(f"unknown R-type funct3={funct3:#x} funct7={funct7:#x}")
        return {
            "fmt": "R", "mnemonic": mnemonic,
            "rd": rd, "rs1": rs1, "rs2": rs2,
        }

    elif fmt == "I_arith":
        if funct3 == 0x5:
            # srli vs srai distinguished by funct7
            mnemonic = "srai" if funct7 == 0x20 else "srli"
            shamt = bits(word, 24, 20)
            return {"fmt": "I_shift", "mnemonic": mnemonic,
                    "rd": rd, "rs1": rs1, "shamt": shamt}
        elif funct3 == 0x1:
            shamt = bits(word, 24, 20)
            return {"fmt": "I_shift", "mnemonic": "slli",
                    "rd": rd, "rs1": rs1, "shamt": shamt}
        mnemonic = I_ARITH_OPS.get(funct3)
        if mnemonic is None:
            raise DecodeError(f"unknown I-arith funct3={funct3:#x}")
        return {"fmt": "I", "mnemonic": mnemonic,
                "rd": rd, "rs1": rs1, "imm": imm_i(word)}

    elif fmt == "I_load":
        mnemonic = I_LOAD_OPS.get(funct3)
        if mnemonic is None:
            raise DecodeError(f"unknown load funct3={funct3:#x}")
        return {"fmt": "I_load", "mnemonic": mnemonic,
                "rd": rd, "rs1": rs1, "imm": imm_i(word)}

    elif fmt == "I_jalr":
        return {"fmt": "I_jalr", "mnemonic": "jalr",
                "rd": rd, "rs1": rs1, "imm": imm_i(word)}

    elif fmt == "I_system":
        if word == 0x00000073:
            return {"fmt": "system", "mnemonic": "ecall"}
        elif word == 0x00100073:
            return {"fmt": "system", "mnemonic": "ebreak"}
        raise DecodeError(f"unknown system instruction {word:#010x}")

    elif fmt == "S":
        mnemonic = S_OPS.get(funct3)
        if mnemonic is None:
            raise DecodeError(f"unknown store funct3={funct3:#x}")
        return {"fmt": "S", "mnemonic": mnemonic,
                "rs1": rs1, "rs2": rs2, "imm": imm_s(word)}

    elif fmt == "B":
        mnemonic = B_OPS.get(funct3)
        if mnemonic is None:
            raise DecodeError(f"unknown branch funct3={funct3:#x}")
        return {"fmt": "B", "mnemonic": mnemonic,
                "rs1": rs1, "rs2": rs2, "imm": imm_b(word)}

    elif fmt == "U_lui":
        return {"fmt": "U", "mnemonic": "lui",
                "rd": rd, "imm": imm_u(word)}

    elif fmt == "U_auipc":
        return {"fmt": "U", "mnemonic": "auipc",
                "rd": rd, "imm": imm_u(word)}

    elif fmt == "J":
        return {"fmt": "J", "mnemonic": "jal",
                "rd": rd, "imm": imm_j(word)}

    raise DecodeError("unreachable")   # shouldn't get here


def format_instr(d):
    """Turn a decoded instruction dict into an assembly string."""
    mn  = d["mnemonic"]
    fmt = d["fmt"]

    if fmt == "R":
        return f"{mn} {reg(d['rd'])}, {reg(d['rs1'])}, {reg(d['rs2'])}"

    elif fmt in ("I", "I_jalr"):
        return f"{mn} {reg(d['rd'])}, {reg(d['rs1'])}, {d['imm']}"

    elif fmt == "I_load":
        return f"{mn} {reg(d['rd'])}, {d['imm']}({reg(d['rs1'])})"

    elif fmt == "I_shift":
        return f"{mn} {reg(d['rd'])}, {reg(d['rs1'])}, {d['shamt']}"

    elif fmt == "S":
        return f"{mn} {reg(d['rs2'])}, {d['imm']}({reg(d['rs1'])})"

    elif fmt == "B":
        return f"{mn} {reg(d['rs1'])}, {reg(d['rs2'])}, {d['imm']}"

    elif fmt == "U":
        return f"{mn} {reg(d['rd'])}, {d['imm']:#x}"

    elif fmt == "J":
        return f"{mn} {reg(d['rd'])}, {d['imm']}"

    elif fmt == "system":
        return mn

    return f"<unknown fmt {fmt}>"
