#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egs_tables.py - table scanner / dumper for Bosch GS8.60.0 (ZF 5HP19) firmware images.
Part of the GS8.60.0 community repository. License: MIT.

Works on 256K full images (19C0 / 19D0) and on 32K partial images
(calibration window 0x8000-0x10000 saved as a separate file; addresses minus 0x8000).
GS8.60.4 (512K, e.g. 20C0) has a different layout - this tool does not know it.

Table formats (big-endian, Motorola 68k/CPU32):
  2D8  : [u16 nx][u16 ny][nx bytes X axis][ny bytes Y axis][nx*ny bytes data]
  2D16 : same, axes and data 16-bit
  1D8  : [u16 n][n bytes axis][n bytes data]
  1D16 : [u16 n][2n bytes axis][2n bytes data]
Axes strictly increase - that is how tables are detected. In 19C0/19D0 the zone
0x080D0-0x0E4A2 yields exactly 536 such tables (15284 bytes); the remaining bytes of
the zone are scalars, axis-less matrices, pointer catalogs and 2-3 point curves the
heuristic deliberately skips.

Usage:
  egs_tables.py scan     fw.bin [--csv out.csv] [--md out.md]   catalog of tables
  egs_tables.py dump     fw.bin 0xB974 [0xB80A ...]              print tables
  egs_tables.py cell     fw.bin 0x91B2 ROW COL                   file offset of one cell
  egs_tables.py shift    fw.bin                                  16 shift-point matrices
  egs_tables.py programs fw.bin                                  role of each matrix by shape
  egs_tables.py diff     a.bin b.bin [--all]                     changed tables (data / axes)
  egs_tables.py ids      fw.bin                                  identification strings
  egs_tables.py info     fw.bin                                  size, SHA-256, code hash, labels

No dependencies beyond the Python 3 standard library.
"""
import sys, struct, csv, os, re, hashlib

CAL_LO, CAL_HI = 0x080D0, 0x0E4A2          # table zone inside the calibration window
WIN_LO, WIN_HI = 0x08000, 0x10000          # calibration window (partial image)
CODE_LO, CODE_HI = 0x10000, 0x40000        # program code; identical in 19C0 and 19D0
CODE_SHA256_19x0 = "e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546"

SHIFT_BASE, SHIFT_STRIDE = 0x091B2, 0x70
SHIFT_COLS = ["1>2", "2>3", "3>4", "4>5", "2>1", "3>2", "4>3", "5>4"]


class FW:
    """Firmware image. `off` is the value to subtract from a full-image address
    to get a file offset (0 for 256K, 0x8000 for a 32K partial)."""

    def __init__(self, path):
        self.path = path
        self.d = bytearray(open(path, "rb").read())
        self.N = len(self.d)
        if self.N == 0x40000:
            self.off = 0
        elif self.N == 0x8000:
            self.off = WIN_LO
        else:
            raise SystemExit(f"{path}: size {self.N} - expected 262144 (full) or 32768 (partial)")

    # --- raw access by full-image address -------------------------------
    def valid(self, a):
        return 0 <= a - self.off < self.N

    def u8(self, a):  return self.d[a - self.off]
    def u16(self, a): return (self.d[a - self.off] << 8) | self.d[a - self.off + 1]
    def u32(self, a): return struct.unpack(">I", bytes(self.d[a - self.off:a - self.off + 4]))[0]

    def inc8(self, a, n):
        return all(self.u8(a + i) < self.u8(a + i + 1) for i in range(n - 1))

    def inc16(self, a, n):
        return all(self.u16(a + 2 * i) < self.u16(a + 2 * i + 2) for i in range(n - 1))

    # --- table detection --------------------------------------------------
    def try_table(self, a, minx=3, miny=2):
        """Recognise a table at full-image address a. Returns dict or None."""
        if not self.valid(a) or not self.valid(a + 7):
            return None
        nx, ny = self.u16(a), self.u16(a + 2)
        end = self.off + self.N
        if minx <= nx <= 40 and miny <= ny <= 40:
            e = a + 4 + nx + ny + nx * ny
            if e <= end and self.inc8(a + 4, nx) and self.inc8(a + 4 + nx, ny):
                return dict(addr=a, kind="2D8", nx=nx, ny=ny, end=e)
            e = a + 4 + 2 * nx + 2 * ny + 2 * nx * ny
            if e <= end and self.inc16(a + 4, nx) and self.inc16(a + 4 + 2 * nx, ny):
                return dict(addr=a, kind="2D16", nx=nx, ny=ny, end=e)
        n = nx
        if 4 <= n <= 40:
            e = a + 2 + 2 * n
            if e <= end and self.inc8(a + 2, n):
                return dict(addr=a, kind="1D8", nx=n, ny=1, end=e)
            e = a + 2 + 4 * n
            if e <= end and self.inc16(a + 2, n):
                return dict(addr=a, kind="1D16", nx=n, ny=1, end=e)
        return None

    def tile(self, lo=CAL_LO, hi=CAL_HI):
        """Tile [lo, hi) with tables, byte by byte where nothing matches."""
        out, a = [], lo
        while a < hi - 8:
            t = self.try_table(a)
            if t:
                out.append(t); a = t["end"]
            else:
                a += 1
        return out

    # --- table access -------------------------------------------------------
    def layout(self, t):
        """Return (xaddr, yaddr, daddr, width) for a table dict."""
        a, nx, ny = t["addr"], t["nx"], t["ny"]
        if t["kind"] == "2D8":  return a + 4, a + 4 + nx, a + 4 + nx + ny, 1
        if t["kind"] == "2D16": return a + 4, a + 4 + 2 * nx, a + 4 + 2 * nx + 2 * ny, 2
        if t["kind"] == "1D8":  return a + 2, None, a + 2 + nx, 1
        return a + 2, None, a + 2 + 2 * nx, 2

    def read_table(self, t):
        """Return xs, ys, data(rows), data_addr, width."""
        xa, ya, da, w = self.layout(t)
        rd = self.u8 if w == 1 else self.u16
        xs = [rd(xa + w * i) for i in range(t["nx"])]
        ys = [rd(ya + w * i) for i in range(t["ny"])] if ya is not None else [0]
        data = [[rd(da + w * (r * t["nx"] + c)) for c in range(t["nx"])] for r in range(t["ny"])]
        return xs, ys, data, da, w

    def cell_addr(self, t, row, col):
        _, _, da, w = self.layout(t)
        return da + w * (row * t["nx"] + col)

    def fmt_table(self, t, title=""):
        xs, ys, data, _, w = self.read_table(t)
        wid = 7 if w == 2 else 5
        L = [f"{t['addr']:05X}  {t['kind']:5s} {t['nx']}x{t['ny']}  {title}".rstrip()]
        L.append("        X:" + "".join(f"{v:{wid}d}" for v in xs))
        for r, row in enumerate(data):
            lab = f"Y={ys[r]:5d}" if t["ny"] > 1 else "  value"
            L.append(f"  {lab}:" + "".join(f"{v:{wid}d}" for v in row))
        return "\n".join(L)

    # --- shift matrices -----------------------------------------------------
    def shift_matrices(self):
        """16 matrices 8x11: X = 1..8 (transition), Y = pedal 0..255, values km/h."""
        res = []
        for k in range(16):
            a = SHIFT_BASE + k * SHIFT_STRIDE
            if not self.valid(a + 0x6F):
                break
            t = self.try_table(a)
            if t and t["kind"] == "2D8" and t["nx"] == 8 and t["ny"] == 11:
                res.append(t)
            else:
                res.append(None)
        return res

    def sha256(self, lo=None, hi=None):
        lo = self.off if lo is None else lo
        hi = self.off + self.N if hi is None else hi
        return hashlib.sha256(bytes(self.d[lo - self.off:hi - self.off])).hexdigest()


# ------------------------------------------------------------------------------
def classify_programs(fw):
    """Role by shape only (not by address): manual = rows do not depend on pedal,
    winter = column 1>2 is 0 (start in 2nd), hold = upshift columns 250/255, drive = rest."""
    out = []
    for k, t in enumerate(fw.shift_matrices()):
        if t is None:
            continue
        xs, ys, data, _, _ = fw.read_table(t)
        body = data[:-1]
        pedal_indep = all(row == body[0] for row in body)
        winter = all(row[0] == 0 for row in body)
        hold = all(all(v >= 250 for v in row[:4]) for row in body)
        limit2 = all(all(v == 255 for v in row[1:4]) for row in body)
        role = ("manual" if pedal_indep and not hold and not limit2 else
                "hold" if hold else "2nd-only" if limit2 else "winter" if winter else "drive")
        out.append(dict(index=k, addr=t["addr"], role=role, y=ys,
                        idle_up=data[0][:4], wot_up=data[-2][:4], kd_up=data[-1][:4], kd_dn=data[-1][4:]))
    return out


def cmd_scan(fw, out_csv=None, out_md=None):
    lo = max(CAL_LO, fw.off); hi = min(CAL_HI, fw.off + fw.N)
    tabs = fw.tile(lo, hi)
    cov = sum(t["end"] - t["addr"] for t in tabs)
    gaps = []
    a = lo
    for t in tabs:
        if t["addr"] > a:
            gaps.append((a, t["addr"]))
        a = t["end"]
    print(f"file: {os.path.basename(fw.path)} ({fw.N} bytes, offset 0x{fw.off:X})")
    print(f"zone: {lo:05X}-{hi:05X}  tables: {len(tabs)}  covered: {cov} bytes  gaps: {len(gaps)}")
    for g in gaps[:10]:
        print(f"  gap {g[0]:05X}-{g[1]:05X}")
    rows = []
    for t in tabs:
        xs, ys, data, _, _ = fw.read_table(t)
        flat = [v for r in data for v in r]
        rows.append(dict(addr=f"{t['addr']:05X}", kind=t["kind"], nx=t["nx"], ny=t["ny"],
                         xmin=xs[0], xmax=xs[-1], ymin=ys[0], ymax=ys[-1],
                         vmin=min(flat), vmax=max(flat), bytes=t["end"] - t["addr"]))
    if out_csv:
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        print("csv:", out_csv)
    if out_md:
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(f"# Table catalog: {os.path.basename(fw.path)}\n\n{len(tabs)} tables, {cov} bytes, zone {lo:05X}-{hi:05X}\n\n")
            f.write("| addr | kind | size | X | Y | values |\n|---|---|---|---|---|---|\n")
            for r in rows:
                f.write(f"| `{r['addr']}` | {r['kind']} | {r['nx']}x{r['ny']} | {r['xmin']}-{r['xmax']} | {r['ymin']}-{r['ymax']} | {r['vmin']}-{r['vmax']} |\n")
        print("md:", out_md)
    if not out_csv and not out_md:
        for r in rows:
            print(f"{r['addr']}  {r['kind']:5s} {r['nx']:2d}x{r['ny']:<2d}  X {r['xmin']}-{r['xmax']}  Y {r['ymin']}-{r['ymax']}  Z {r['vmin']}-{r['vmax']}")


def cmd_shift(fw):
    hdr = "  pedal |  1>2  2>3  3>4  4>5 |  2>1  3>2  4>3  5>4"
    for k, t in enumerate(fw.shift_matrices()):
        if t is None:
            print(f"\n=== program {k:02d} @ {SHIFT_BASE + k * SHIFT_STRIDE:05X}: not a valid 8x11 matrix"); continue
        xs, ys, data, da, _ = fw.read_table(t)
        print(f"\n=== program {k:02d} @ {t['addr']:05X} (data at {da:05X}) ===")
        print(hdr)
        for r, row in enumerate(data):
            print(f"   {ys[r]:5d} |" + "".join(f"{v:5d}" for v in row[:4]) + " |" + "".join(f"{v:5d}" for v in row[4:]))


def cmd_programs(fw):
    print("  #   addr   role      pedal axis                                    up@idle             up@WOT              kickdown down")
    for p in classify_programs(fw):
        print(f"  {p['index']:02d}  {p['addr']:05X}  {p['role']:8s}  {str(p['y']):45s} {str(p['idle_up']):19s} {str(p['wot_up']):19s} {p['kd_dn']}")


def cmd_diff(a, b, show_all=False):
    lo = max(CAL_LO, a.off, b.off); hi = min(CAL_HI, a.off + a.N, b.off + b.N)
    ta = {t["addr"]: t for t in a.tile(lo, hi)}
    tb = {t["addr"]: t for t in b.tile(lo, hi)}
    common = sorted(set(ta) & set(tb))
    print(f"tables in A: {len(ta)}  in B: {len(tb)}  common addresses: {len(common)}")
    for ad in sorted(set(ta) ^ set(tb)):
        print(f"!! {ad:05X} present only in {'A' if ad in ta else 'B'} - layout differs, compare by hand")
    n = 0
    for ad in common:
        xa, ya, da_, _, _ = a.read_table(ta[ad]); xb, yb, db_, _, _ = b.read_table(tb[ad])
        ax = (xa != xb) or (ya != yb); dt = da_ != db_
        if ax or dt:
            n += 1
            cells = sum(1 for r in range(len(da_)) for c in range(len(da_[0])) if da_[r][c] != db_[r][c])
            print(f"--- {ad:05X} {ta[ad]['kind']} {ta[ad]['nx']}x{ta[ad]['ny']}: "
                  + ("AXES DIFFER " if ax else "") + (f"{cells} data cells differ" if dt else ""))
            if show_all and dt:
                for r in range(len(da_)):
                    for c in range(len(da_[0])):
                        if da_[r][c] != db_[r][c]:
                            print(f"      [{ya[r] if ta[ad]['ny'] > 1 else '-'} , {xa[c]}] {da_[r][c]} -> {db_[r][c]}")
    # bytes outside tables
    other = [i for i in range(lo, hi) if a.u8(i) != b.u8(i)]
    covered = set()
    for t in ta.values():
        covered.update(range(t["addr"], t["end"]))
    other = [i for i in other if i not in covered]
    print(f"changed tables: {n};  changed bytes outside tables in zone: {len(other)}"
          + (":  " + " ".join(f"{i:05X}" for i in other[:40]) if other else ""))
    wlo = max(WIN_LO, a.off, b.off); whi = min(WIN_HI, a.off + a.N, b.off + b.N)
    scal = [i for i in range(wlo, whi) if (i < lo or i >= hi) and a.u8(i) != b.u8(i)]
    if scal:
        print(f"changed bytes in window outside table zone: {len(scal)}:  " + " ".join(f"{i:05X}" for i in scal[:40]))


def cmd_ids(fw):
    for m in re.finditer(rb"[0-9A-Za-z_ .\-]{8,}", bytes(fw.d)):
        s = m.group().decode("latin1")
        if any(c.isdigit() for c in s) and any(c.isalpha() for c in s):
            print(f"{m.start() + fw.off:05X}  {s}")


def cmd_info(fw):
    print(f"file   : {fw.path}")
    print(f"size   : {fw.N} bytes ({'full 256K' if fw.N == 0x40000 else 'partial 32K, addresses = offset + 0x8000'})")
    print(f"sha256 : {fw.sha256()}")
    if fw.N == 0x40000:
        cs = fw.sha256(CODE_LO, CODE_HI)
        print(f"code 0x10000-0x40000 sha256: {cs}  {'== 19C0/19D0 reference' if cs == CODE_SHA256_19x0 else '!= reference (different software)'}")
        print(f"program label @0x4322: {bytes(fw.d[0x4322:0x4322 + 12]).decode('latin1')}")
    print(f"calibration window sha256: {fw.sha256(max(WIN_LO, fw.off), min(WIN_HI, fw.off + fw.N))}")
    print(f"calibration label @0xFFCE: {bytes(fw.d[0xFFCE - fw.off:0xFFDE - fw.off]).decode('latin1')}")
    tabs = fw.tile(max(CAL_LO, fw.off), CAL_HI)
    print(f"tables in 0x080D0-0x0E4A2: {len(tabs)} {'(expected 536)' if len(tabs) != 536 else '(ok)'}")


def main(argv):
    if len(argv) < 3:
        print(__doc__); return 1
    c = argv[1]
    if c == "scan":
        fw = FW(argv[2]); out_csv = out_md = None
        if "--csv" in argv: out_csv = argv[argv.index("--csv") + 1]
        if "--md" in argv: out_md = argv[argv.index("--md") + 1]
        cmd_scan(fw, out_csv, out_md)
    elif c == "dump":
        fw = FW(argv[2])
        for s in argv[3:]:
            a = int(s, 16) if not s.lower().startswith("0x") else int(s, 16)
            t = fw.try_table(a)
            print(fw.fmt_table(t) if t else f"{a:05X}: no table recognised here")
    elif c == "cell":
        fw = FW(argv[2]); a = int(argv[3], 16); r = int(argv[4]); col = int(argv[5])
        t = fw.try_table(a)
        if not t: print("no table here"); return 1
        ca = fw.cell_addr(t, r, col)
        xs, ys, data, _, _ = fw.read_table(t)
        print(f"table {a:05X} {t['kind']} row {r} (Y={ys[r] if t['ny'] > 1 else '-'}) col {col} (X={xs[col]}): address {ca:05X}, file offset {ca - fw.off:05X}, value {data[r][col]}")
    elif c == "shift":
        cmd_shift(FW(argv[2]))
    elif c == "programs":
        cmd_programs(FW(argv[2]))
    elif c == "diff":
        cmd_diff(FW(argv[2]), FW(argv[3]), "--all" in argv)
    elif c == "ids":
        cmd_ids(FW(argv[2]))
    elif c == "info":
        cmd_info(FW(argv[2]))
    else:
        print(__doc__); return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except BrokenPipeError:
        sys.exit(0)
