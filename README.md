# rv32i-decoder

A command-line tool that decodes 32-bit RISC-V machine words into human-readable assembly mnemonics.

Supports all R, I, S, B, U, and J format instructions from the RV32I base integer ISA, including correct sign-extension and immediate reconstruction across all formats.

## Usage

```
python decoder.py <hex>                 decode a single instruction
python decoder.py <hex> <hex> ...       decode multiple instructions
python decoder.py -f <file>             decode a file of hex words
python decoder.py -v <hex>              verbose: also show instruction format
python decoder.py --base-addr 0x1000 -f prog.hex   show addresses alongside output
python decoder.py --regs                print ABI register name table
```

### Examples

```
$ python decoder.py 0x00A50533
00A50533  add a0, a0, a0

$ python decoder.py FF010113 00112623 00008067
FF010113  addi sp, sp, -16
00112623  sw ra, 12(sp)
00008067  jalr zero, ra, 0

$ python decoder.py --base-addr 0x80000000 -f sample.hex
0x80000000:  FF010113  addi sp, sp, -16
0x80000004:  00112623  sw ra, 12(sp)
0x80000008:  00050513  addi a0, a0, 0
0x8000000c:  00150513  addi a0, a0, 1
0x80000010:  FFF50513  addi a0, a0, -1
0x80000014:  00008067  jalr zero, ra, 0

$ python decoder.py -v 0x40C5D533
40C5D533  sra a0, a1, a2                   # R-type
```

## Supported instructions

| Format | Instructions |
|--------|-------------|
| R      | add, sub, sll, slt, sltu, xor, srl, sra, or, and |
| I      | addi, slti, sltiu, xori, ori, andi, slli, srli, srai, lb, lh, lw, lbu, lhu, jalr |
| S      | sb, sh, sw |
| B      | beq, bne, blt, bge, bltu, bgeu |
| U      | lui, auipc |
| J      | jal |
| system | ecall, ebreak |

## Running the tests

```
python test/test_decoder.py
```

No dependencies outside the standard library.

## File format for -f

One hex word per line. The `0x` prefix is optional. Lines starting with `#` or containing `#` mid-line are treated as comments and ignored:

```
FF010113    # addi sp, sp, -16
00112623    # sw ra, 12(sp)
00008067    # ret
```

## Why

Useful when reading raw binary output from an assembler or linker, inspecting memory dumps from a RISC-V simulation, or just learning how the ISA encodes instructions. The immediate reconstruction handles the scrambled bit layouts (especially B and J formats) that the spec deliberately uses to simplify hardware decoder design.

## License

MIT
