#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gs860_crc.py - checksums of Bosch GS8.60 (ZF 5HP19) images: check and recompute.
Part of the GS8.60.0 community repository. License: MIT.

Usage:
  gs860_crc.py check <image.bin> [<image.bin> ...]
  gs860_crc.py fix   <in.bin> <out.bin>

Examples:
  python3 tools/gs860_crc.py check build.bin build_partial32k.bin
  python3 tools/gs860_crc.py fix edited.bin fixed.bin

check  reads only. Exit code 0 when every checksum of every image matches.
fix    writes a NEW file (the input is never touched) with the checksums recomputed.
       It refuses when the loader or program checksum of the input does not match:
       such an image is damaged or is a different software, recomputing would hide that.
       Input and output must be different files; an existing output is not overwritten.

Algorithm (found 23.09.2026 in the handler of DS2 command 0x0A):
  CRC-16/XMODEM: polynomial 0x1021, initial value 0, MSB first, no final XOR,
      crc = ((crc << 8) & 0xFFFF) ^ T[((crc >> 8) ^ byte) & 0xFF]
  The table T is stored in the image itself (256 big-endian words) and is the standard
  one; the tool reads it from a full image and refuses an image where it is not.
  The right bound of a region is not included. The sum is stored big-endian, outside
  its region.

  GS8.60.0 19C0/19D0, 256 KB: table 0x3EDA, routine 0x221C, handler 0x1360
      loader      0x00000-0x042FF  stored at 0x05FFE
      program     0x10000-0x3F77B  stored at 0x3F7FE
      calibration 0x08000-0x0FFCD  stored at 0x0FFFE
  GS8.60.4 20C0, 512 KB: table 0x3EE2, routine 0x223C, handler 0x1392
      loader      0x00000-0x043FF  stored at 0x05FFE
      program     0x08000-0x6FF7B  stored at 0x6FFFE
      calibration 0x70000-0x7FFCD  stored at 0x7FFFE
  GS8.60.0 partial, 32 KB (the calibration window 0x8000-0x10000 alone): only the
      calibration sum; the table is not in the file, the standard one is used (it is
      byte-identical to the table of every full 19C0/19D0 and 20C0 image checked).

Checked 23.09.2026: stock 19D0, factory Alpina B3 19C0, factory Alpina 20C0 and a car
dump of 20C0 match on all three sums. Edited calibrations with a stale calibration sum
are accepted and drive (every WOLF4X build v1-v23); a tester reads the sums with 0x0A
and sees the mismatch, so the tools keep the sum right.

RU. Контрольные суммы образа GS8.60: check только читает, fix пишет новый файл с
пересчитанными суммами и отказывается, если не сходятся загрузчик или программа.
Алгоритм CRC-16/XMODEM, таблица в самом образе, области перечислены выше.
Один и тот же файл лежит в публичном репо gs860-5hp19 и в WOLF4X (tools/gs860_crc.py).
"""
import os, sys, hashlib

POLY = 0x1021


def _standard_table():
    t = []
    for i in range(256):
        c = i << 8
        for _ in range(8):
            c = ((c << 1) ^ POLY) if c & 0x8000 else (c << 1)
            c &= 0xFFFF
        t.append(c)
    return t


STANDARD_TABLE = _standard_table()

# image size: (table address or None, file offset of address 0, [(start, end, stored at, name), ...])
# addresses are ECU addresses; for the 32K partial the file holds 0x8000-0xFFFF
LAYOUTS = {
    0x40000: (0x3EDA, 0, [(0x00000, 0x04300, 0x05FFE, "loader"),
                          (0x10000, 0x3F77C, 0x3F7FE, "program"),
                          (0x08000, 0x0FFCE, 0x0FFFE, "calibration")]),
    0x80000: (0x3EE2, 0, [(0x00000, 0x04400, 0x05FFE, "loader"),
                          (0x08000, 0x6FF7C, 0x6FFFE, "program"),
                          (0x70000, 0x7FFCE, 0x7FFFE, "calibration")]),
    0x08000: (None, 0x8000, [(0x08000, 0x0FFCE, 0x0FFFE, "calibration")]),
}


class WrongImage(Exception):
    """Not a GS8.60 image of a known layout, or a damaged / foreign one."""


def crc16(d, start, end, table=STANDARD_TABLE):
    """CRC over d[start:end] (file offsets)."""
    c = 0
    for b in d[start:end]:
        c = ((c << 8) & 0xFFFF) ^ table[((c >> 8) ^ b) & 0xFF]
    return c


def layout(d):
    """(table, offset, regions) for an image; raises WrongImage for an unknown size or table."""
    if len(d) not in LAYOUTS:
        raise WrongImage(f"size {len(d)} bytes: not a GS8.60 image "
                         "(expected 256 KB or 512 KB full, or the 32 KB partial of GS8.60.0)")
    addr, off, regions = LAYOUTS[len(d)]
    if addr is None:
        return STANDARD_TABLE, off, regions
    table = [int.from_bytes(d[addr + 2 * i:addr + 2 * i + 2], "big") for i in range(256)]
    if table != STANDARD_TABLE:
        raise WrongImage(f"no CRC-16 table at 0x{addr:05X} (T[1] = 0x{table[1]:04X}): different software")
    return table, off, regions


def sums(d):
    """[(name, start, end, stored_at, stored, computed), ...] with ECU addresses."""
    table, off, regions = layout(d)
    return [(name, s, e, at, int.from_bytes(d[at - off:at - off + 2], "big"), crc16(d, s - off, e - off, table))
            for s, e, at, name in regions]


def check_file(path, verbose=True):
    """True when every sum of the image at `path` matches."""
    with open(path, "rb") as f:
        d = f.read()
    try:
        rows = sums(d)
    except WrongImage as e:
        if verbose:
            print(f"{path}: {e}")
        return False
    if verbose:
        print(f"{path}\n  SHA-256 {hashlib.sha256(d).hexdigest()}")
        if len(d) == 0x8000:
            print("  partial 32K: calibration sum only, standard CRC-16 table")
        for name, s, e, at, stored, computed in rows:
            print(f"  {name:11s} 0x{s:05X}-0x{e - 1:05X}  stored at 0x{at:05X}: 0x{stored:04X}, "
                  f"computed 0x{computed:04X}  {'ok' if stored == computed else 'MISMATCH'}")
    return all(stored == computed for *_, stored, computed in rows)


def fixed(d):
    """Bytes of the image with every sum recomputed. Loader and program must already match."""
    rows = sums(d)
    foreign = [name for name, _s, _e, _at, stored, computed in rows
               if name != "calibration" and stored != computed]
    if foreign:
        raise WrongImage(" and ".join(foreign) + " checksum does not match: the image is damaged or "
                         "a different software, recomputing the sums would hide that")
    _table, off, _regions = layout(d)
    out = bytearray(d)
    for _name, _s, _e, at, _stored, computed in rows:
        out[at - off:at - off + 2] = computed.to_bytes(2, "big")
    assert all(stored == computed for *_, stored, computed in sums(bytes(out)))
    return bytes(out)


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if len(argv) >= 2 and argv[0] == "check":
        results = [check_file(p) for p in argv[1:]]
        return 0 if all(results) else 1
    if len(argv) == 3 and argv[0] == "fix":
        src, dst = argv[1], argv[2]
        if os.path.abspath(src) == os.path.abspath(dst):
            print("input and output must be different files: the input is never overwritten")
            return 2
        if os.path.exists(dst):
            print(f"{dst} already exists: not overwriting, choose another name")
            return 2
        with open(src, "rb") as f:
            d = f.read()
        try:
            new = fixed(d)
        except WrongImage as e:
            print(f"{src}: {e}")
            return 1
        with open(dst, "wb") as f:
            f.write(new)
        for name, _s, _e, at, stored, computed in sums(d):
            print(f"  {name:11s} 0x{at:05X}: was 0x{stored:04X}, now 0x{computed:04X}"
                  + ("" if stored == computed else "  (recomputed)"))
        print(f"written: {dst}\n  SHA-256 {hashlib.sha256(new).hexdigest()}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
