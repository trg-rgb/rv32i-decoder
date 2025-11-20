# test/test_decoder.py
#
# Test cases are derived from known-good instruction encodings.
# I generated most of these with: echo "add a0,a0,a0" | riscv64-unknown-elf-as
# then read the .o with riscv64-unknown-elf-objdump -d
#
# Run with: python -m pytest test/ -v
# or just:  python test/test_decoder.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rv32i import decode, format_instr, DecodeError

passed = 0
failed = 0

def check(label, word, expected_asm):
    global passed, failed
    try:
        d   = decode(word)
        got = format_instr(d)
        if got == expected_asm:
            passed += 1
        else:
            failed += 1
            print(f"FAIL  {label}")
            print(f"      got  '{got}'")
            print(f"      want '{expected_asm}'")
    except DecodeError as e:
        failed += 1
        print(f"FAIL  {label}")
        print(f"      raised DecodeError: {e}")

def check_error(label, word):
    """Expect a DecodeError."""
    global passed, failed
    try:
        decode(word)
        failed += 1
        print(f"FAIL  {label}  (expected DecodeError, got none)")
    except DecodeError:
        passed += 1


# ---- R-type --------------------------------------------------------------
# add a0, a0, a0        -> 0x00A50533
# sub t0, t1, t2        -> 0x40730133  (note funct7=0x20)
# xor a1, a2, a3        -> 0x00D645B3
# sra s0, s1, s2        -> 0x41249433  (funct7=0x20)

check("R: add a0,a0,a0",       0x00A50533, "add a0, a0, a0")
check("R: sub t0,t1,t2",       0x407302B3, "sub t0, t1, t2")  # rd=x5, rs1=x6, rs2=x7, funct7=0x20
check("R: xor a1,a2,a3",       0x00D645B3, "xor a1, a2, a3")
check("R: and a4,a5,a6",       0x0107F733, "and a4, a5, a6")  # rd=x14, rs1=x15, rs2=x16
check("R: srl a0,a1,a2",       0x00C5D533, "srl a0, a1, a2")
check("R: sra a0,a1,a2",       0x40C5D533, "sra a0, a1, a2")
check("R: slt a0,a1,a2",       0x00C5A533, "slt a0, a1, a2")

# ---- I-type arithmetic ---------------------------------------------------
# addi a0, a0, 1        -> 0x00150513
# addi sp, sp, -16      -> 0xFF010113  (sign-extended -16)
# xori a0, a0, -1       -> 0xFFF54513

check("I: addi a0,a0,1",       0x00150513, "addi a0, a0, 1")
check("I: addi sp,sp,-16",     0xFF010113, "addi sp, sp, -16")
check("I: xori a0,a0,-1",      0xFFF54513, "xori a0, a0, -1")
check("I: ori  a1,a2,7",       0x00766593, "ori a1, a2, 7")
check("I: slli a0,a0,3",       0x00351513, "slli a0, a0, 3")
check("I: srli a0,a0,1",       0x00155513, "srli a0, a0, 1")
check("I: srai a0,a0,1",       0x40155513, "srai a0, a0, 1")

# ---- loads ---------------------------------------------------------------
# lw a0, 0(sp)          -> 0x00012503
# lb a1, -4(s0)         -> 0xFFC40583
# lhu a2, 8(a3)         -> 0x00869603  (zero-extending load)

check("I: lw  a0,0(sp)",       0x00012503, "lw a0, 0(sp)")
check("I: lb  a1,-4(s0)",      0xFFC40583, "lb a1, -4(s0)")
check("I: lhu a2,8(a3)",       0x0086D603, "lhu a2, 8(a3)")   # funct3=5 for lhu, was wrong (had funct3=1=lh)

# ---- jalr ----------------------------------------------------------------
# jalr zero, 0(ra)      -> 0x00008067  (the standard ret encoding)

check("I: jalr zero,0(ra)",    0x00008067, "jalr zero, ra, 0")

# ---- S-type stores -------------------------------------------------------
# sw  a0, 0(sp)         -> 0x00A12023
# sb  a1, -1(s0)        -> 0xFEB40FA3

check("S: sw a0,0(sp)",        0x00A12023, "sw a0, 0(sp)")
check("S: sb a1,-1(s0)",       0xFEB40FA3, "sb a1, -1(s0)")

# ---- B-type branches -----------------------------------------------------
# beq a0, a1, +8        -> 0x00B50463
# bne a0, zero, -4      -> 0xFE051EE3  (negative offset)
# blt a2, a3, +16       -> 0x00D64863

check("B: beq a0,a1,+8",       0x00B50463, "beq a0, a1, 8")
check("B: bne a0,zero,-4",     0xFE051EE3, "bne a0, zero, -4")
check("B: blt a2,a3,+16",      0x00D64863, "blt a2, a3, 16")

# ---- U-type --------------------------------------------------------------
# lui  a0, 0x12345      -> 0x12345537
# auipc a1, 0x0         -> 0x00000597

check("U: lui  a0,0x12345",    0x12345537, "lui a0, 0x12345")
check("U: auipc a1,0",         0x00000597, "auipc a1, 0x0")

# ---- J-type --------------------------------------------------------------
# jal  ra, +4           -> 0x004000EF
# jal  zero, 0          -> 0x0000006F  (infinite loop in practice)

check("J: jal ra,+4",          0x004000EF, "jal ra, 4")
check("J: jal zero,0",         0x0000006F, "jal zero, 0")

# ---- system --------------------------------------------------------------
check("system: ecall",         0x00000073, "ecall")
check("system: ebreak",        0x00100073, "ebreak")

# ---- error cases ---------------------------------------------------------
check_error("16-bit compressed (illegal here)", 0x00000001)
check_error("unknown opcode",                   0xDEADBEEF & ~0x7F | 0x7C)


# ---- report --------------------------------------------------------------
print(f"\n{passed} passed, {failed} failed")
if __name__ == "__main__":
    sys.exit(0 if failed == 0 else 1)
