#!/usr/bin/env python3
"""
decoder.py -- RV32I instruction decoder CLI

Usage:
    python decoder.py <hex>            decode a single instruction
    python decoder.py <hex> <hex> ...  decode multiple instructions
    python decoder.py -f <file>        decode a file of hex words (one per line)
    python decoder.py --regs           print register ABI name table

Examples:
    python decoder.py 0x00A50533      ->  add a0, a0, a0
    python decoder.py 00A50533        ->  same, 0x prefix optional
    python decoder.py -f program.hex
"""

import sys
import argparse
from rv32i import decode, format_instr, reg, DecodeError


def parse_word(s):
    """Parse a hex string to int, with or without 0x prefix."""
    s = s.strip()
    try:
        return int(s, 16)
    except ValueError:
        raise SystemExit(f"error: '{s}' is not a valid hex word")


def decode_and_print(word, addr=None, verbose=False):
    hex_str = f"{word:08X}"
    prefix  = f"{addr:#010x}:  " if addr is not None else ""

    try:
        d = decode(word)
        asm = format_instr(d)
        if verbose:
            print(f"{prefix}{hex_str}  {asm:<32}  # {d['fmt']}-type")
        else:
            print(f"{prefix}{hex_str}  {asm}")
    except DecodeError as e:
        print(f"{prefix}{hex_str}  <illegal: {e}>")


def print_reg_table():
    print("RISC-V ABI register names:")
    print(f"  {'Num':<5} {'ABI':<8} {'Description'}")
    print(f"  {'-'*40}")
    descs = [
        "hard-wired zero", "return address", "stack pointer",
        "global pointer", "thread pointer",
        "temp 0", "temp 1", "temp 2",
        "saved 0 / frame pointer", "saved 1",
        "arg/return 0", "arg/return 1",
        "arg 2", "arg 3", "arg 4", "arg 5", "arg 6", "arg 7",
        "saved 2", "saved 3", "saved 4", "saved 5",
        "saved 6", "saved 7", "saved 8", "saved 9", "saved 10", "saved 11",
        "temp 3", "temp 4", "temp 5", "temp 6",
    ]
    for i in range(32):
        print(f"  x{i:<4} {reg(i):<8} {descs[i]}")


def main():
    parser = argparse.ArgumentParser(
        description="Decode RV32I 32-bit instruction words into mnemonics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("words", nargs="*", help="hex instruction word(s)")
    parser.add_argument("-f", "--file",    help="file of hex words, one per line")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show instruction format alongside mnemonic")
    parser.add_argument("--regs",          action="store_true",
                        help="print register ABI name table and exit")
    parser.add_argument("--base-addr",     type=lambda x: int(x, 0), default=None,
                        metavar="ADDR",
                        help="starting address for address column (hex ok)")

    args = parser.parse_args()

    if args.regs:
        print_reg_table()
        return

    instructions = []

    if args.file:
        try:
            with open(args.file) as f:
                for line in f:
                    line = line.split("#")[0].strip()   # strip comments
                    if line:
                        instructions.append(parse_word(line))
        except FileNotFoundError:
            raise SystemExit(f"error: file not found: {args.file}")

    if args.words:
        instructions.extend(parse_word(w) for w in args.words)

    if not instructions:
        parser.print_help()
        return

    for i, word in enumerate(instructions):
        addr = (args.base_addr + i * 4) if args.base_addr is not None else None
        decode_and_print(word, addr=addr, verbose=args.verbose)


if __name__ == "__main__":
    main()
