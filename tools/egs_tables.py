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
  egs_tables.py shift    fw.bin [--turbine] [--rpm-per-kmh K]    16 shift-point matrices
  egs_tables.py programs fw.bin                                  role of each matrix by shape
  egs_tables.py diff     a.bin b.bin [--all]                     changed tables (data / axes)
  egs_tables.py ids      fw.bin                                  identification strings
  egs_tables.py info     fw.bin                                  size, SHA-256, code hash, labels, checksums
  egs_tables.py verify-shift fw.bin --spark RPM [--cut RPM] [--margin a,b,c,d]
                         [--down-margin RPM] [--stock stock.bin] [--fix out.bin]
                                                                 shift points against the rules of doc 02 §4

Units of the shift matrices (proven 23.09.2026, doc 02 §3): the ECU compares the value
with [0xFFFF918F] = filtered output shaft rpm >> 5, so one unit is 32 rpm of the output
shaft, not km/h. Turbine rpm at a threshold = value * 32 * gear ratio. On an E39 2.5
with the stock final drive (27.11 output rpm per km/h) one unit is 1.18 km/h.

No dependencies beyond the Python 3 standard library (verify-shift --fix also uses
gs860_crc.py from this folder to recompute the calibration checksum).
"""
import sys, struct, csv, os, re, hashlib

CAL_LO, CAL_HI = 0x080D0, 0x0E4A2          # table zone inside the calibration window
WIN_LO, WIN_HI = 0x08000, 0x10000          # calibration window (partial image)
CODE_LO, CODE_HI = 0x10000, 0x40000        # program code; identical in 19C0 and 19D0
CODE_SHA256_19x0 = "e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546"

SHIFT_BASE, SHIFT_STRIDE = 0x091B2, 0x70
SHIFT_COLS = ["1>2", "2>3", "3>4", "4>5", "2>1", "3>2", "4>3", "5>4"]

# The shift decision compares the matrix value with [0xFFFF918F]: upshift at 0x24AC8
# (CMP.B, shift when 918F >= value), downshift at 0x24B20 (when 918F < value - [0xFFFF919A]).
# 918F is written at 0x24F60 as the filtered output shaft rpm [0xFFFF8DA4] >> 5 (LSR.W #5 at
# 0x24F5E); the speed channel constants are at 0x116C4 (K = 1 666 666 = 60e6/36 at 0x116C8).
UNIT_RPM = 32                              # one matrix unit = 32 rpm of the output shaft
RATIOS_AT = 0x12F9C                        # gear ratios x1000 (u16), 1st..5th, in the program code
RATIOS_19x0 = (3.665, 1.999, 1.407, 1.000, 0.742)
NEVER = 250                                # an upshift value >= 250 never triggers
# Default margins of verify-shift, turbine rpm (doc 02 §4). Upshift: from the command to the spark
# cut, per transition 1>2..4>5: torque converter slip plus the engine rise while the speed filter
# catches up and the shift executes. Taken from the WOLF4X E39 2.5 build of 23.09.2026 (1st gear
# from logs: slip 280-350, about 1600 rpm/s at full load); more conservative than the factory
# kickdown rows (the factory leaves about 330-850 rpm to its own limiter).
DEFAULT_MARGIN = (1120, 610, 490, 400)
DEFAULT_DOWN_MARGIN = 500                  # turbine rpm left below the spark cut after a downshift
OVERRUN_TOLERANCE = 100                    # a manual upshift may sit this much above the fuel cut
MIN_GAP = 6                                # units kept between an upshift and its downshift by --fix
ORD = ("1st", "2nd", "3rd", "4th", "5th")


class FW:
    """Firmware image. `off` is the value to subtract from a full-image address
    to get a file offset (0 for 256K, 0x8000 for a 32K partial)."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.d = bytearray(f.read())
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
    def ratios(self):
        """Gear ratios 1st..5th: from the image (0x12F9C) when it holds the program code,
        otherwise the 19C0/19D0 values."""
        if self.valid(RATIOS_AT) and self.valid(RATIOS_AT + 9):
            r = tuple(self.u16(RATIOS_AT + 2 * g) / 1000 for g in range(5))
            if all(0.5 < x < 5 for x in r) and list(r) == sorted(r, reverse=True):
                return r
        return RATIOS_19x0

    def shift_matrices(self):
        """16 matrices 8x11: X = 1..8 (transition), Y = pedal 0..255, values = output shaft rpm / 32."""
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


def turbine_rpm(value, col, ratios):
    """Turbine rpm at a threshold: upshift columns in the gear before the shift, downshift
    columns in the gear after it (where the engine lands)."""
    g = col if col < 4 else col - 4
    return round(value * UNIT_RPM * ratios[g])


def cmd_shift(fw, turbine=False, rpm_per_kmh=None):
    R = fw.ratios()
    print("values: output shaft rpm / 32 (compared with 0xFFFF918F); turbine rpm per unit: "
          + ", ".join(f"{ORD[g]} {UNIT_RPM * r:.1f}" for g, r in enumerate(R)))
    if rpm_per_kmh:
        print(f"with {rpm_per_kmh} output rpm per km/h one unit is {UNIT_RPM / rpm_per_kmh:.3f} km/h")
    if turbine:
        print("shown: turbine rpm (upshift columns in the gear before the shift, downshift columns in the gear after); "
              "'never' = 250/255, '-' = 0")
    hdr = "  pedal |  1>2  2>3  3>4  4>5 |  2>1  3>2  4>3  5>4"
    for k, t in enumerate(fw.shift_matrices()):
        if t is None:
            print(f"\n=== program {k:02d} @ {SHIFT_BASE + k * SHIFT_STRIDE:05X}: not a valid 8x11 matrix"); continue
        xs, ys, data, da, _ = fw.read_table(t)
        print(f"\n=== program {k:02d} @ {t['addr']:05X} (data at {da:05X}) ===")
        print(hdr if not turbine else hdr.replace("  1>2  2>3  3>4  4>5", "   1>2   2>3   3>4   4>5")
              .replace("  2>1  3>2  4>3  5>4", "   2>1   3>2   4>3   5>4"))
        for r, row in enumerate(data):
            if not turbine:
                print(f"   {ys[r]:5d} |" + "".join(f"{v:5d}" for v in row[:4]) + " |" + "".join(f"{v:5d}" for v in row[4:]))
            else:
                cell = lambda c, v: (" never" if v >= NEVER else "     -" if v == 0 else f"{turbine_rpm(v, c, R):6d}")
                print(f"   {ys[r]:5d} |" + "".join(cell(c, v) for c, v in enumerate(row[:4]))
                      + " |" + "".join(cell(c + 4, v) for c, v in enumerate(row[4:])))


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
    try:
        import gs860_crc
        rows = gs860_crc.sums(bytes(fw.d))
    except ImportError:
        print("checksums: gs860_crc.py not found next to this tool"); return
    except Exception as e:
        print(f"checksums: {e}"); return
    for name, s, e, at, stored, computed in rows:
        state = "ok" if stored == computed else "MISMATCH" + (
            " (edited calibration: recompute with gs860_crc.py fix)" if name == "calibration" else
            " (damaged read or different software)")
        print(f"checksum {name:11s} 0x{s:05X}-0x{e - 1:05X} at 0x{at:05X}: stored 0x{stored:04X}, "
              f"computed 0x{computed:04X}  {state}")


# ------------------------------------------------------------------------------
MANUAL_19x0 = (8, 9, 10)                   # manual (M) matrices of 19C0/19D0: stock and Alpina agree by shape


def roles_for(fw, stock=None):
    """Role of each matrix for the rules: by shape of the stock image when given, otherwise by shape of
    the image itself, except that 08/09/10 of 19C0/19D0 stay "manual" even when a tune made their
    upshift columns 255 (by shape that would look like a hold program)."""
    roles = {p["index"]: p["role"] for p in classify_programs(stock if stock else fw)}
    if stock is None and (fw.N == 0x8000 or fw.sha256(CODE_LO, CODE_HI) == CODE_SHA256_19x0):
        for k in MANUAL_19x0:
            roles[k] = "manual"
    return roles


def shift_limits(ratios, spark, margin=DEFAULT_MARGIN, down_margin=DEFAULT_DOWN_MARGIN):
    """Largest matrix values allowed by doc 02 §4: upshift 1>2..4>5 and downshift landing 2>1..5>4."""
    up = [int((spark - margin[g]) // (UNIT_RPM * ratios[g])) for g in range(4)]
    down = [int((spark - down_margin) // (UNIT_RPM * ratios[g])) for g in range(4)]
    return up, down


def overrun_guard(ratios, cut):
    """Manual upshift values at the fuel cut: the box shifts up by itself only on the overrun."""
    return [round(cut / (UNIT_RPM * ratios[g])) for g in range(4)]


def verify_shift(fw, spark, cut=None, margin=DEFAULT_MARGIN, down_margin=DEFAULT_DOWN_MARGIN, stock=None):
    """Findings [(level, k, role, pedal, column, value, turbine, message, is_stock)] for all 16 matrices.
    ERROR: cannot work (never reached under load, lands above the spark cut, hunting, no overrun
    protection in a manual program). WARN: works, but with less room than the margins."""
    R = fw.ratios()
    cap_up, cap_down = shift_limits(R, spark, margin, down_margin)
    roles = roles_for(fw, stock)
    st_m = stock.shift_matrices() if stock else None
    out = []
    for k, t in enumerate(fw.shift_matrices()):
        if t is None:
            out.append(("ERROR", k, "?", None, None, None, None, "not a valid 8x11 matrix", False)); continue
        role = roles.get(k, "?")
        _xs, ys, data, _da, _w = fw.read_table(t)
        sd = stock.read_table(st_m[k])[2] if st_m and st_m[k] else None

        def add(level, r, cols, msg, c=None):
            c = cols[0] if c is None else c
            v = data[r][c]
            same = sd is not None and all(sd[r][x] == data[r][x] for x in cols)
            out.append((level, k, role, ys[r], SHIFT_COLS[c], v, turbine_rpm(v, c, R) if 0 < v < NEVER else None,
                        msg, same))

        for r, row in enumerate(data):
            for g in range(4):
                up, dn = row[g], row[4 + g]
                tu = turbine_rpm(up, g, R)
                if role == "manual":
                    if up >= NEVER:
                        add("ERROR" if g < 3 else "WARN", r, [g],
                            "never shifts up: no protection on the overrun, the wheels can drive the engine past the cut"
                            + (f" (guard at the cut: {overrun_guard(R, cut)[g]})" if cut else ""))
                    elif cut and tu > cut + OVERRUN_TOLERANCE:
                        add("WARN", r, [g], f"overrun protection only at {tu} rpm, fuel cut {cut}")
                elif role in ("drive", "winter") and 0 < up < NEVER:
                    # 4>5 at full load needs 4th gear near the limiter, above the top speed of most cars:
                    # the factory uses 200 there as "practically never", so it is only a warning
                    if tu >= spark:
                        add("ERROR" if g < 3 else "WARN", r, [g],
                            f"never reached under load (turbine {tu} >= spark cut {spark}): the box hangs at the "
                            f"limiter{' in 4th' if g == 3 else ''}; limit {cap_up[g]}")
                    elif up > cap_up[g]:
                        add("WARN", r, [g], f"{spark - tu} rpm to the spark cut, margin {margin[g]}: limit {cap_up[g]}")
                if 0 < dn < NEVER:
                    td = turbine_rpm(dn, 4 + g, R)
                    if td >= spark:
                        add("ERROR", r, [4 + g], f"lands at {td} >= spark cut {spark}: the wheels over-rev the engine; "
                                                 f"limit {cap_down[g]}")
                    elif dn > cap_down[g]:
                        add("WARN", r, [4 + g], f"lands {spark - td} rpm below the spark cut, margin {down_margin}: "
                                                f"limit {cap_down[g]}")
                    if 0 < up < NEVER and dn >= up:
                        add("ERROR", r, [g, 4 + g], f"downshift {dn} >= upshift {up}: gear hunting", c=4 + g)
            ups = [v for v in row[:4] if 0 < v < NEVER]
            if ups != sorted(ups) or len(set(ups)) != len(ups):
                add("WARN", r, [0, 1, 2, 3], f"upshift order 1>2 < 2>3 < 3>4 < 4>5 broken: {row[:4]}", c=0)
        for c in range(8):
            col = [data[r][c] for r in range(len(data))]
            for r in range(1, len(col)):
                if col[r] < col[r - 1] and col[r - 1] < NEVER:
                    add("WARN", r, [c], f"falls with more pedal ({col[r - 1]} at pedal {ys[r - 1]})", c=c)
    return out


def fix_shift(fw, spark, cut=None, margin=DEFAULT_MARGIN, down_margin=DEFAULT_DOWN_MARGIN, stock=None):
    """Bring the drive, sport and manual matrices within the limits of doc 02 §4 by lowering only the
    cells that break them. Returns [(k, pedal, column, old, new)] and edits fw.d in place.
    Upshift 1>2..3>4 above the limit: set to the limit (4>5 is not touched). Manual upshift that never
    triggers: set to the overrun guard at the fuel cut (needs cut). Downshift landing too high: set to
    the limit, and at least MIN_GAP below its upshift where the upshift was lowered or the pair hunts.
    With `stock`, cells equal to stock are the factory's choice and are not moved, except a downshift
    whose upshift was lowered (otherwise the pair would hunt)."""
    R = fw.ratios()
    cap_up, cap_down = shift_limits(R, spark, margin, down_margin)
    guard = overrun_guard(R, cut) if cut else None
    roles = roles_for(fw, stock)
    st_m = stock.shift_matrices() if stock else None
    changes = []
    for k, t in enumerate(fw.shift_matrices()):
        role = roles.get(k)
        if t is None or role not in ("drive", "winter", "manual"):
            continue
        _xs, ys, data, _da, _w = fw.read_table(t)
        sd = stock.read_table(st_m[k])[2] if st_m and st_m[k] else None
        factory = lambda r, c: sd is not None and sd[r][c] == data[r][c]
        for r, row in enumerate(data):
            new = row[:]
            for g in range(4):
                up = row[g]
                if factory(r, g):
                    pass
                elif role == "manual":
                    if up >= NEVER or (cut and up * UNIT_RPM * R[g] > cut + OVERRUN_TOLERANCE):
                        if guard is None:
                            raise SystemExit("manual programs without an overrun guard: give --cut (the fuel cut) "
                                             "so the guard can sit above the spark cut")
                        new[g] = guard[g]
                elif 0 < up < NEVER and up > cap_up[g] and g < 3:     # 4>5 is left alone (see verify_shift)
                    new[g] = cap_up[g]
                dn = row[4 + g]
                if 0 < dn < NEVER:
                    lim = cap_down[g] if not factory(r, 4 + g) else dn
                    if 0 < new[g] < NEVER and (new[g] != up or dn >= new[g]):
                        lim = min(lim, new[g] - MIN_GAP)
                    if dn > lim:
                        new[4 + g] = max(0, lim)
            for c in range(8):
                if new[c] != row[c]:
                    fw.d[fw.cell_addr(t, r, c) - fw.off] = new[c]
                    changes.append((k, ys[r], SHIFT_COLS[c], row[c], new[c]))
    return changes


def cmd_verify_shift(fw, spark, cut=None, margin=DEFAULT_MARGIN, down_margin=DEFAULT_DOWN_MARGIN,
                     stock=None, fix_out=None):
    R = fw.ratios()
    cap_up, cap_down = shift_limits(R, spark, margin, down_margin)
    print(f"file: {fw.path}")
    print(f"spark cut {spark}" + (f", fuel cut {cut}" if cut else "") + f"; ratios {'/'.join(f'{r:.3f}' for r in R)}; "
          f"margins up {'/'.join(map(str, margin))}, down {down_margin}")
    print(f"limits (matrix units): up 1>2..4>5 {cap_up}, down landing 2>1..5>4 {cap_down}"
          + (f", manual overrun guard {overrun_guard(R, cut)}" if cut else ""))
    if fix_out:
        if os.path.abspath(fix_out) == os.path.abspath(fw.path) or os.path.exists(fix_out):
            print(f"{fix_out}: exists or is the input - not overwriting"); return 2
        changes = fix_shift(fw, spark, cut, margin, down_margin, stock)
        for k, y, col, a, b in changes:
            print(f"  fix k{k:02d} pedal {y:3d} {col}: {a} -> {b}")
        import gs860_crc
        data = gs860_crc.fixed(bytes(fw.d))
        with open(fix_out, "wb") as f:
            f.write(data)
        fw.d = bytearray(data)
        print(f"{len(changes)} cells changed, checksum recomputed; written {fix_out}\n"
              f"  SHA-256 {hashlib.sha256(data).hexdigest()}\nchecking the result:")
    found = verify_shift(fw, spark, cut, margin, down_margin, stock)
    n_err = n_warn = n_stock = 0
    for level, k, role, y, col, v, tu, msg, same in found:
        if same:
            n_stock += 1
        elif level == "ERROR":
            n_err += 1
        else:
            n_warn += 1
        tag = "stock" if same else level
        where = f"k{k:02d} {role:8s}" + (f" pedal {y:3d} {col}" if y is not None else "")
        val = f" value {v:3d}" + (f" = {tu:5d} rpm" if tu is not None else "") if v is not None else ""
        print(f"{tag:5s} {where}{val}  {msg}")
    print(f"errors {n_err}, warnings {n_warn}" + (f", same as stock {n_stock} (not counted)" if stock else ""))
    return 1 if n_err else 0


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
        k = float(argv[argv.index("--rpm-per-kmh") + 1]) if "--rpm-per-kmh" in argv else None
        cmd_shift(FW(argv[2]), "--turbine" in argv, k)
    elif c == "verify-shift":
        def opt(name, conv=int, default=None):
            return conv(argv[argv.index(name) + 1]) if name in argv else default
        spark = opt("--spark")
        if not spark:
            print("verify-shift needs --spark RPM (the lower of the engine limiters, doc 02 §4)"); return 2
        margin = opt("--margin", lambda s: tuple(int(x) for x in s.split(",")), DEFAULT_MARGIN)
        if len(margin) != 4:
            print("--margin takes four numbers: 1>2,2>3,3>4,4>5"); return 2
        stock = opt("--stock", FW)
        return cmd_verify_shift(FW(argv[2]), spark, opt("--cut"), margin,
                                opt("--down-margin", int, DEFAULT_DOWN_MARGIN), stock, opt("--fix", str))
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
