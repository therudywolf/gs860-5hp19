#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egs_patch.py - ready-made patches for Bosch GS8.60.0 (19C0 / 19D0, 256K) and GS8.60.4 (20C0, 512K).
Part of the GS8.60 community repository. License: MIT. Docs: docs/en/13-patches.md (RU: docs/ru/13-patches.md).

Every patch knows the addresses of both programs, checks the image before writing (program code
by SHA-256, table headers and axes, factory values where the patch depends on them, free groups,
free code area) and writes only the calibration, except tcc-first on 19x0, which needs 52 bytes of
code (the program checksum is recomputed). All three checksums are recomputed at the end.

Usage:
  egs_patch.py list                                  what each patch does
  egs_patch.py show   fw.bin                         the cells the patches use, as they are in this image
  egs_patch.py apply  fw.bin -o out.bin PATCH [PATCH ...] [--cut RPM] [--spark RPM] [--dry-run]
  egs_patch.py preset NAME fw.bin -o out.bin [--cut RPM] [--spark RPM] [--dry-run]
  egs_patch.py recipe NAME stock.bin -o recipe.json [--cut RPM] [--spark RPM]
                                                     the preset as a recipe (JSON diff, apply_recipe.py);
                                                     only for presets without program code (always on 20C0)

PATCH is name[:key=value[,key=value...]], for example
  tcc-first:modes=S+M,rpm=1760   tcc-lock:modes=D+S+M,rpm=1600   no-warmup   s-no5
  shift-wot:modes=S   no-kickdown:scope=M   manual-hold   gate:mode=S

Engine limits (turbine rpm = engine rpm when the converter is locked):
  --spark RPM   the lower engine limiter (spark or soft cut); used by shift-wot
  --cut RPM     the highest hard cut of the engine; used by s-no5 and manual-hold
Presets use the reference engine of each platform when they are not given (see `list`).

Examples:
  python3 tools/egs_patch.py show my_dump.bin
  python3 tools/egs_patch.py apply my_dump.bin -o build.bin no-warmup tcc-lock manual-hold --cut 6720
  python3 tools/egs_patch.py preset sport-daily my_20c0.bin -o build.bin

Outputs: out.bin (full image, checksums recomputed), out.log (every changed byte with its reason).
The partial 32K of a 19x0 build is written only when no patch touched the program code.
No dependencies beyond the Python 3 standard library and the other tools of this folder.
"""
import sys, os, re, hashlib, argparse, datetime, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import egs_tables
from egs_tables import FW, CODE_SHA256_19x0, CODE_SHA256_20C0, GUARD_ABOVE_CUT, MONITOR_MARGIN
import gs860_crc

UNIT = 32                                       # one matrix / threshold unit = 32 rpm of the output shaft
RATIOS = (3.665, 1.999, 1.407, 1.000, 0.742)    # 1st..5th, same numbers in 19x0 (0x12F9C) and 20C0 (0x0E0D2)
NEVER = 255
GROUP_NEVER = 202                               # factory "never" in TCC threshold tables (n_out/32 202 in 1st)
PROG2K = {0: 14, 1: 6, 2: 11, 3: 15, 4: 0, 5: 1, 6: 2, 7: 13, 8: 9, 9: 12, 0xA: 5, 0xB: 10, 0xC: 7, 0xD: 8, 0xE: 4, 0xF: 3}
MODES = {"D": (0x0, 0x1), "S": (0x2, 0x3), "M": (0xB, 0xD)}     # programs of each mode (docs 01 §5, 11 §5)

# Platform constants. Every address is read by code at the place named in the comment (docs 01-05, 11, 13).
PLAT = {
    "19x0": dict(
        name="GS8.60.0 19C0/19D0 256K", size=0x40000, code=(0x10000, 0x40000), code_sha=CODE_SHA256_19x0,
        cal=(0x08000, 0x0FFCE), mat=0x091B2,
        gate=0x8975,                 # 0x230D8: code in the left gate before +/-: 0xFE = S (BMW), 0x0B = M
        warm_end=0x8B48,             # 0x28D6E: warm-up ends when n_out/32 >= value (factory 48)
        kd_src=0x8D1A, kd_thr=0x8246,    # 0x205FC: 0 = kickdown switch and pedal > [0x8246]; else DME2 byte 6 bit 2
        monitor=0x8B44,              # 0x26C96: turbine monitor, fault 0x25 and limp mode (u16)
        ags_low=0x887C,              # 0x1DCB2: lower bound of AGS points, D at +0, S at +1
        tcc_mask=0x8978, tcc_mask_factory=0x003C,    # 0x2906E
        tcc_groups=0x897E, tcc_codes=(2, 3, 4, 5),   # 0x290A0: [0x897E + 4 * program + gear - 2]
        tcc_tables=((0x993A, 1, 10),),               # 0x290D0 via 0x9B80: 30 x 7, Y = pedal 0xFFFF9182
        tcc_hyst=0x8B4C,
        lock_add=None,
        first_hook=dict(at=0x290A0, factory="207C0000897AD1C01C280004", code=0x3E3A0, table=0x3E380, free=(0x3E380, 0x3E400)),
        ref_engine=dict(name="M52TUB25 with the factory MS42 0110C6 limiter (automatic: 6496-6592)", spark=6496, cut=6592),
    ),
    "20C0": dict(
        name="GS8.60.4 20C0 512K", size=0x80000, code=(0x08000, 0x70000), code_sha=CODE_SHA256_20C0,
        cal=(0x70000, 0x7FFCE), mat=0x7120E,
        gate=0x70966,                # 0x1EB88 / 0x1EBE4: code in the left gate: 0x0B = M at once (this file), 0xFE = S
        warm_end=0x70BAC,            # 0x251A0
        kd_src=0x70D6A, kd_thr=0x70232,  # 0x1BC9C: 1 = DME2 byte 6 bit 2 (CAN, this file), 0 = switch and pedal
        monitor=0x70BA8,             # 0x23098
        ags_low=0x70890,             # 0x18E42
        tcc_mask=0x7096E, tcc_mask_factory=0x007E,   # 0x25494
        tcc_groups=0x70970, tcc_codes=(1, 2, 3, 4, 5, 6),    # 0x255F6: [0x70970 + 6 * program + code - 1]
        tcc_tables=((0x71996, 1, 10), (0x71AD0, 11, 12)),    # slots 35 and 36, Y = pedal 0xFFFF912A
        tcc_hyst=0x70BB0,
        lock_add=0x70B98,            # 0x20D8E: added to the upshift threshold while the converter is locked
        first_hook=None,
        ref_engine=dict(name="M54B30 with the factory MS43 limiter (soft 6528-6624, hard 6624-6720 by gear)", spark=6528, cut=6720),
    ),
}

# shift-wot margins, turbine rpm from the command to the spark cut (docs 02 §4)
WOT_MARGIN = (1120, 610, 490, 400)
DOWN_MARGIN = 500
MIN_GAP = 6
MONITOR_MAX = 7232               # highest factory value of the monitor seen for this hardware (Alpina 19x0 and 20C0)


class PatchError(Exception):
    pass


class Image:
    def __init__(self, path):
        self.path = path
        self.fw = FW(path)
        self.d = self.fw.d
        self.orig = bytes(self.d)
        size = self.fw.N
        self.key = None
        for k, P in PLAT.items():
            if P["size"] == size:
                lo, hi = P["code"]
                if hashlib.sha256(self.orig[lo:hi]).hexdigest() == P["code_sha"]:
                    self.key = k
        if self.key is None:
            raise PatchError(f"{path}: not a full 19C0/19D0 (256K) or 20C0 (512K) image with the known program code. "
                             "Other software (for example GS8.60.4 15C0) has other addresses - nothing is patched.")
        self.P = PLAT[self.key]
        bad = [n for n, _s, _e, _at, st, c in gs860_crc.sums(self.orig) if n != "calibration" and st != c]
        if bad:
            raise PatchError(f"{path}: {' and '.join(bad)} checksum of the input does not match - a damaged read "
                             "or a modified program; read the ECU again")
        self.changes = []             # (addr, old, new, why)
        self.code_areas = []          # code ranges a patch is allowed to write
        self.notes = []

    # --- access -------------------------------------------------------------
    def u8(self, a): return self.d[a]
    def u16(self, a): return (self.d[a] << 8) | self.d[a + 1]

    def allowed(self, a):
        lo, hi = self.P["cal"]
        return lo <= a < hi or any(x <= a < y for x, y in self.code_areas)

    def set8(self, a, v, why):
        v &= 0xFF
        if not self.allowed(a):
            raise PatchError(f"internal: write outside the calibration and declared code at 0x{a:05X}")
        old = self.d[a]
        if old != v:
            self.d[a] = v
            self.changes.append((a, old, v, why))

    def set16(self, a, v, why):
        self.set8(a, v >> 8, why); self.set8(a + 1, v & 0xFF, why)

    # --- tables ---------------------------------------------------------------
    def table(self, a, kind="2D8", nx=None, ny=None, x=None):
        t = self.fw.try_table(a)
        if not t or t["kind"] != kind or (nx and t["nx"] != nx) or (ny and t["ny"] != ny):
            raise PatchError(f"0x{a:05X}: expected a {kind} table {nx or '?'}x{ny or '?'} here - layout differs, stop")
        xs, ys, data, da, w = self.fw.read_table(t)
        if x is not None and xs != x:
            raise PatchError(f"0x{a:05X}: X axis {xs} differs from the factory {x} - stop")
        return t, xs, ys, data

    def matrix(self, k):
        a = self.P["mat"] + 0x70 * k
        t, xs, ys, data = self.table(a, "2D8", 8, 11, list(range(1, 9)))
        return t, ys, data

    def set_cell(self, t, r, c, v, why):
        self.set8(self.fw.cell_addr(t, r, c), v, why)

    # --- TCC groups -----------------------------------------------------------
    def groups(self, p):
        codes = self.P["tcc_codes"]
        a = self.P["tcc_groups"] + len(codes) * p
        return {code: self.d[a + i] for i, code in enumerate(codes)}

    def set_group(self, p, code, g, why):
        codes = self.P["tcc_codes"]
        self.set8(self.P["tcc_groups"] + len(codes) * p + codes.index(code), g, why)

    def used_groups(self, skip=()):
        return {g for p in range(16) if p not in skip for g in self.groups(p).values() if g}

    def tcc_table(self, g):
        """(table dict, pedal axis, data, first column of group g)"""
        for a, g0, g1 in self.P["tcc_tables"]:
            if g0 <= g <= g1:
                t = self.fw.try_table(a)
                if not t or t["kind"] != "2D8":
                    raise PatchError(f"0x{a:05X}: TCC threshold table not found")
                xs, ys, data, _, _ = self.fw.read_table(t)
                if xs != list(range(3 * (g0 - 1), 3 * (g0 - 1) + t["nx"])):
                    raise PatchError(f"0x{a:05X}: TCC threshold table X axis {xs} is not the factory threshold index")
                return t, ys, data, 3 * (g - g0)
        raise PatchError(f"TCC group {g} has no table on {self.P['name']}")

    def group_rows(self, g):
        t, ys, data, c0 = self.tcc_table(g)
        return ys, [tuple(row[c0:c0 + 3]) for row in data]

    def set_group_rows(self, g, rows, why):
        t, ys, data, c0 = self.tcc_table(g)
        if len(rows) != len(ys):
            raise PatchError("internal: row count")
        for r, trip in enumerate(rows):
            for k, v in enumerate(trip):
                self.set_cell(t, r, c0 + k, v, why)

    def lock_add(self, gear):
        a = self.P["lock_add"]
        return self.d[a + gear - 1] if a else 0


def turbine(v, gear):
    return round(v * UNIT * RATIOS[gear - 1])


def units(rpm, gear, rnd=round):
    return int(rnd(rpm / (UNIT * RATIOS[gear - 1])))


def parse_modes(s, allowed=("M", "S+M", "D+S+M")):
    s = (s or "").upper().replace(",", "+").replace(" ", "")
    if s not in allowed:
        raise PatchError(f"modes={s or '?'}: use one of {', '.join(allowed)}")
    return s.split("+")


def programs(modes):
    return [p for m in modes for p in MODES[m]]


# ------------------------------------------------------------------------------ patches
def p_gate(img, prm, ctx):
    """gate - left gate of the selector: S first and M on the first +/- tap (BMW factory, code 0xFE), or M at
    once (code 0x0B: Alpina, and the 20C0 6440 file). Docs 13 §8."""
    mode = prm.get("mode", "S").upper()
    code = {"S": 0xFE, "M": 0x0B}.get(mode)
    if code is None:
        raise PatchError("gate: mode=S or mode=M")
    a = img.P["gate"]
    if img.u8(a) not in (0xFE, 0x0B, 0x03):
        raise PatchError(f"gate: 0x{a:05X} = 0x{img.u8(a):02X}, expected 0xFE, 0x0B or 0x03 - stop")
    img.set8(a, code, f"gate: left gate code {'0xFE (S, M on the first tap)' if code == 0xFE else '0x0B (M at once)'}")


def p_no_warmup(img, prm, ctx):
    """no-warmup - switch off the warm-up program. After power-on the ECU holds program P0 and raises the pedal
    input of the shift matrices to the table 0x8142 / 0x7013A (P0, P1, P7: 40 % up to 55 C) until the output
    shaft reaches [end] (factory 48 x 32 rpm, about 57 km/h on an E39 2.5). end = 0 ends it on the first cycle.
    Docs 13 §3."""
    a = img.P["warm_end"]
    if img.u8(a) != 48 and not prm.get("force"):
        raise PatchError(f"no-warmup: 0x{a:05X} = {img.u8(a)}, factory is 48 - another calibration, check it by hand")
    img.set8(a, 0, "no-warmup: warm-up program ends at once (n_out/32 >= 0)")


def p_no_kickdown(img, prm, ctx):
    """no-kickdown - scope=all (default): the kickdown flag is never set: no row 255 in any matrix, no AGS freeze,
    and in M the +/- taps keep working with the pedal on the floor. scope=M: only the M matrices lose the kickdown
    row (row 255 = row 254), the flag itself stays. Docs 13 §6."""
    scope = prm.get("scope", "all").lower()
    if scope == "all":
        src, thr = img.P["kd_src"], img.P["kd_thr"]
        if img.u8(src) not in (0, 1):
            raise PatchError(f"no-kickdown: source select 0x{src:05X} = {img.u8(src)}, expected 0 or 1")
        img.set8(src, 0, "no-kickdown: kickdown from the switch path (not from the DME2 CAN bit)")
        img.set8(thr, 0xFF, "no-kickdown: switch path needs pedal > 255 - never")
    elif scope == "m":
        for p in MODES["M"]:
            t, ys, data = img.matrix(PROG2K[p])
            if ys[-1] != 255 or ys[-2] != 254:
                raise PatchError(f"no-kickdown: matrix k{PROG2K[p]} pedal axis {ys} has no 254/255 rows")
            for c in range(8):
                img.set_cell(t, 10, c, data[9][c], f"no-kickdown:M k{PROG2K[p]:02d}: kickdown row = row 254")
    else:
        raise PatchError("no-kickdown: scope=all or scope=M")


def p_s_no5(img, prm, ctx):
    """s-no5 - no 5th gear in S: 4>5 = 255 in the S matrices (P2 = k11, P3 = k15), 5>4 such that a downshift from
    5th lands at most 500 rpm under the spark cut in 4th (docs 02 §4), and (pin=1, default) the AGS points in S held at 193 or more, so
    S stays on level 4 (P3) and the D replacement PF and the hill step 2 cannot take over in S. Docs 13 §4."""
    lim = ctx.get("spark") or ctx.get("cut")
    if not lim:
        raise PatchError("s-no5 needs --spark (or --cut): the 5>4 value lands the 4th gear at most 500 rpm under it")
    v54 = min(250, units(lim - DOWN_MARGIN, 4, math.floor))
    for p in MODES["S"]:
        k = PROG2K[p]
        t, ys, data = img.matrix(k)
        for r in range(11):
            img.set_cell(t, r, 3, NEVER, f"s-no5 k{k:02d}: 4>5 never")
            img.set_cell(t, r, 7, v54, f"s-no5 k{k:02d}: 5>4 below {v54} (lands at {turbine(v54, 4)} rpm in 4th)")
    if str(prm.get("pin", "1")) == "1":
        a = img.P["ags_low"] + 1
        if img.u8(a) != 0x81:
            raise PatchError(f"s-no5: AGS lower bound S 0x{a:05X} = {img.u8(a)}, factory is 129")
        img.set8(a, 0xC1, "s-no5: AGS points in S >= 193 (level 4, P3); no PF / hill step 2 in S")


def p_shift_wot(img, prm, ctx):
    """shift-wot - upshift points at full throttle (pedal rows 243-255 of D/S, all rows of M) put right under the
    engine limiter by the rules of docs 02 §4: command at spark - margin (1120 / 610 / 490 rpm for 1>2 / 2>3 / 3>4),
    downshift landing at most spark - 500 and at least 6 units below the upshift. On 20C0 the threshold rises by
    0x70B98 while the converter is locked, so that amount is subtracted. modes=S (default), D, or D+S.
    rpm=a/b/c sets the turbine rpm of the command for 1>2/2>3/3>4 directly instead of the margins. Docs 13 §5."""
    spark = ctx.get("spark")
    if not spark:
        raise PatchError("shift-wot needs --spark (the lower engine limiter)")
    modes = (prm.get("modes", "S").upper().replace(",", "+")).split("+")
    if not set(modes) <= {"D", "S"}:
        raise PatchError("shift-wot: modes=S, D or D+S (the M thresholds are set by manual-hold)")
    if prm.get("rpm"):
        cmd = [int(x) for x in str(prm["rpm"]).split("/")]
        if len(cmd) != 3:
            raise PatchError("shift-wot: rpm=a/b/c, turbine rpm of the 1>2/2>3/3>4 command")
    else:
        cmd = [spark - WOT_MARGIN[g] for g in range(3)]
    ups = []
    for g in range(3):
        if cmd[g] > spark - 200:
            raise PatchError(f"shift-wot: {g + 1}>{g + 2} at {cmd[g]} rpm leaves less than 200 rpm to the spark cut {spark}")
        ups.append(units(cmd[g], g + 1, math.floor) - img.lock_add(g + 1))
    downs = [units(spark - DOWN_MARGIN, g + 1, math.floor) for g in range(4)]
    for m in modes:
        for p in MODES[m]:
            k = PROG2K[p]
            t, ys, data = img.matrix(k)
            for r, y in enumerate(ys):
                if y < 243:
                    continue
                for g in range(3):
                    img.set_cell(t, r, g, ups[g], f"shift-wot {m} k{k:02d} pedal {y}: {g + 1}>{g + 2} at {turbine(ups[g], g + 1)} rpm"
                                 + (f" (+{img.lock_add(g + 1)} units while locked)" if img.lock_add(g + 1) else ""))
                for g in range(4):
                    dn = data[r][4 + g]
                    up = ups[g] if g < 3 else data[r][3]
                    lim = min(downs[g], up - MIN_GAP) if up < 250 else downs[g]
                    if dn > lim:
                        img.set_cell(t, r, 4 + g, lim, f"shift-wot {m} k{k:02d} pedal {y}: {g + 2}>{g + 1} at most {lim}")
            # rows below 243 must not rise above the new full-throttle points (monotonic pedal columns),
            # and their downshift stays MIN_GAP under a lowered upshift
            for r, y in enumerate(ys):
                if y >= 243:
                    continue
                for g in range(3):
                    if ups[g] < data[r][g] < 250:
                        img.set_cell(t, r, g, ups[g], f"shift-wot {m} k{k:02d} pedal {y}: {g + 1}>{g + 2} not above full throttle")
                        if data[r][4 + g] > ups[g] - MIN_GAP:
                            img.set_cell(t, r, 4 + g, ups[g] - MIN_GAP, f"shift-wot {m} k{k:02d} pedal {y}: {g + 2}>{g + 1} under the upshift")


def overrun_adds(img):
    """Locked additions per gear 1..5 that apply on the overrun in M (egs_tables.FW.overrun_lock_adds on the image
    as it is now, after the patches before this one)."""
    img.fw.d = img.d
    return img.fw.overrun_lock_adds()


def manual_guard(img, cut, monitor):
    try:
        return egs_tables.manual_guard(RATIOS, cut, monitor, overrun_adds(img))
    except ValueError as e:
        raise PatchError(f"manual-hold: {e} (or give monitor=RPM, at most {MONITOR_MAX}, or a lower --cut)")


def monitor_needed(img, cut):
    """Lowest turbine monitor under which every guard sits GUARD_ABOVE_CUT over the cut, rounded up to 16 rpm."""
    adds = overrun_adds(img)
    need = 0
    for g in range(1, 5):
        need = max(need, (units(cut + GUARD_ABOVE_CUT, g, math.ceil) + adds[g - 1]) * UNIT * RATIOS[g - 1] + MONITOR_MARGIN)
    return int(math.ceil(need / 16) * 16)


def p_manual_hold(img, prm, ctx):
    """manual-hold - M (PB = k10, PD = k8) holds the gear on the limiter: the box shifts up by itself only when the
    wheels drive the turbine above the hard cut (overrun guard), always under the turbine monitor; the kickdown row
    does not downshift (kd=0 keeps it). up=never puts 255 (no protection on the overrun). monitor=RPM raises the
    turbine monitor when the guard does not fit under it (19x0 factory 6720). Docs 13 §7."""
    cut = ctx.get("cut")
    if not cut:
        raise PatchError("manual-hold needs --cut (the highest hard cut of the engine)")
    ma = img.P["monitor"]
    monitor = img.u16(ma)
    if prm.get("monitor") == "auto":
        need = monitor_needed(img, cut)
        prm = dict(prm, monitor=str(need)) if need > monitor else {k: v for k, v in prm.items() if k != "monitor"}
    if prm.get("monitor"):
        new = int(prm["monitor"])
        if new > MONITOR_MAX:
            raise PatchError(f"manual-hold: monitor={new} is above {MONITOR_MAX}, the highest factory value seen for this box")
        if new < monitor:
            raise PatchError(f"manual-hold: monitor={new} is below the image value {monitor}")
        new = (new + 15) // 16 * 16
        img.set16(ma, new, f"manual-hold: turbine monitor {monitor} -> {new} rpm (fault 0x25 / limp mode above it)")
        monitor = new
    up = prm.get("up", "guard")
    if up == "never":
        if cut + GUARD_ABOVE_CUT > monitor - MONITOR_MARGIN:
            raise PatchError(f"manual-hold:up=never: the limiter {cut} + {GUARD_ABOVE_CUT} is too close to the monitor {monitor}")
        vals = [NEVER] * 4
        img.notes.append("manual-hold: up=never - no overrun protection: the wheels can drive the engine past the cut")
    elif up == "guard":
        vals, notes = manual_guard(img, cut, monitor)
        img.notes += [f"manual-hold: {n}" for n in notes]
    else:
        raise PatchError("manual-hold: up=guard (default) or up=never")
    for p in MODES["M"]:
        k = PROG2K[p]
        t, ys, data = img.matrix(k)
        for r, y in enumerate(ys):
            for g in range(4):
                img.set_cell(t, r, g, vals[g], f"manual-hold k{k:02d} pedal {y}: {g + 1}>{g + 2} "
                             + ("never" if vals[g] == NEVER else f"only above {turbine(vals[g], g + 1)} rpm turbine"))
        if str(prm.get("kd", "0")) == "0":
            for c in range(4, 8):
                img.set_cell(t, 10, c, data[9][c], f"manual-hold k{k:02d}: kickdown row does not downshift (= row 254)")


def first_gear_code(org, table):
    """19x0: the routine 0x290A0 jumps to. It does what the three factory instructions did (d6 = group byte
    [0x897A + 4 + d0]); for gear 1 or code 6 ([0xFFFF91AF]) it takes d6 = [table + (program [0xFFFF91A0] & 15)].
    d0 and a0 are not read after 0x290A8 before being written again (0x290BC, 0x2917A); 52 bytes, the same
    bytes as the WOLF4X v41 build."""
    items = [bytes.fromhex("207C0000897A"), bytes.fromhex("D1C0"), bytes.fromhex("1C280004"),   # factory three
             bytes.fromhex("1039FFFF91AF"),                                                    # move.b gear, d0
             bytes.fromhex("0C000001"), ("beq", "g1"),
             bytes.fromhex("0C000006"), ("bne", "ret"),
             "g1", bytes.fromhex("1039FFFF91A0"), bytes.fromhex("0240000F"),                   # d0 = program & 15
             bytes.fromhex("207C") + table.to_bytes(4, "big"), bytes.fromhex("1C300000"),      # d6 = [table + d0]
             "ret", bytes.fromhex("4E75")]
    op = {"beq": 0x67, "bne": 0x66}
    code, labels, fix = bytearray(), {}, []
    for it in items:
        if isinstance(it, str):
            labels[it] = len(code)
        elif isinstance(it, tuple):
            fix.append((len(code), it)); code += b"\0\0"
        else:
            code += it
    for pos, (mn, lab) in fix:
        disp = labels[lab] - (pos + 2)
        assert 0 < disp < 128
        code[pos:pos + 2] = bytes([op[mn], disp])
    assert len(code) == 52 and code[22:24] == b"\x67\x06" and code[28:30] == b"\x66\x14"
    return bytes(code)


def first_rows(ys, rpm, coast, d=False):
    """1st-gear thresholds (open, slip, lock) in n_out/32 by pedal row: lock at rpm on light pedal, later under load.
    The steps are those of the WOLF4X v41 build (S/M: open 4 and slip 2 units under the lock, D: 6 and 3)."""
    lock = units(rpm, 1)
    base = (lock - 6, lock - 3, lock) if d else (lock - 4, lock - 2, lock)
    steps = [(59, (0, 0, 0)), (72, (1, 1, 1)), (97, (2, 2, 3)),
             (122, (3, 3, 4) if d else (3, 4, 5)), (256, (4, 4, 5) if d else (4, 5, 6))]
    rows = []
    for y in ys:
        inc = next(i for lim, i in steps if y < lim)
        trip = tuple(b + i for b, i in zip(base, inc))
        if y < 46 and not coast:
            trip = (GROUP_NEVER,) * 3
        rows.append(trip)
    return rows


def p_tcc_first(img, prm, ctx):
    """tcc-first - lock the torque converter in 1st gear (gear code 1 and code 6). modes=S+M (default), M or D+S+M;
    rpm = turbine rpm of the lock request on light pedal (default 1760 S/M, rpm_d 2110 D), later with more pedal;
    coast=0 (default): no lock with the pedal released, so braking in 1st opens the converter at once.
    20C0: calibration only (the program allows 1st gear: mask 0x7E, group 11 locks at 230+ pedal from the factory).
    19x0: the mask excludes 1st and the group index of 1st points into the next program, so 52 bytes of code at
    0x3E3A0 and a group table per program at 0x3E380 are added (the WOLF4X v41 hook): full flash only. Docs 13 §1."""
    modes = parse_modes(prm.get("modes", "S+M"))
    rpm = int(prm.get("rpm", 1760)); rpm_d = int(prm.get("rpm_d", rpm + 350))
    coast = str(prm.get("coast", "0")) == "1"
    if not 1300 <= rpm <= 3000 or not 1300 <= rpm_d <= 3500:
        raise PatchError("tcc-first: rpm between 1300 and 3000 (D up to 3500)")
    hyst = img.u8(img.P["tcc_hyst"])
    sm = [p for m in modes if m != "D" for p in MODES[m]]
    d_on = "D" in modes
    if img.key == "20C0":
        if img.u16(img.P["tcc_mask"]) != 0x007E:
            raise PatchError("tcc-first: 20C0 gear mask is not 0x007E")
        if 12 in img.used_groups():
            raise PatchError("tcc-first: TCC group 12 is in use in this calibration - no free group for 1st gear")
        ys, rows11 = img.group_rows(11)
        new12 = first_rows(ys, rpm, coast)
        for r, y in enumerate(ys):            # full-throttle rows: never later than the factory group 11
            if y >= 230:
                new12[r] = tuple(min(a, b) for a, b in zip(new12[r], rows11[r]))
        img.set_group_rows(12, new12, f"tcc-first: group 12 = 1st gear S/M, lock from {rpm} rpm turbine on light pedal")
        for p in sm:
            for code in (1, 6):
                img.set_group(p, code, 12, f"tcc-first: P{p:X} 1st gear (code {code}) -> group 12")
        if d_on:
            newd = first_rows(ys, rpm_d, coast, d=True)
            for r, y in enumerate(ys):
                if y >= 230:
                    newd[r] = rows11[r]
            if any(img.groups(p)[1] != 11 for p in (0, 1)) or any(g == 11 for p in range(16) if p not in (0, 1, 2, 3, 0xB) for g in img.groups(p).values()):
                raise PatchError("tcc-first: group 11 is not the factory 1st-gear group of D here")
            img.set_group_rows(11, newd, f"tcc-first: group 11 = 1st gear D, lock from {rpm_d} rpm on light pedal (full throttle = factory)")
    else:
        H = img.P["first_hook"]
        if img.u16(img.P["tcc_mask"]) != 0x003C:
            raise PatchError("tcc-first: 19x0 gear mask is not the factory 0x003C")
        if bytes(img.d[H["at"]:H["at"] + 12]) != bytes.fromhex(H["factory"]):
            raise PatchError("tcc-first: the group select at 0x290A0 is not the factory code (already patched?)")
        lo, hi = H["free"]
        if any(x != 0xFF for x in img.d[lo:hi]):
            raise PatchError("tcc-first: 0x3E380-0x3E3FF is not free (0xFF) in this image")
        used = img.used_groups()
        free = [g for g in range(1, 11) if g not in used]
        need = 2 if d_on else 1
        if len(free) < need:
            raise PatchError(f"tcc-first: needs {need} free TCC group(s), used are {sorted(used)}")
        g_sm, g_d = free[0], (free[1] if d_on else None)
        ys, _ = img.group_rows(g_sm)
        img.set_group_rows(g_sm, first_rows(ys, rpm, coast), f"tcc-first: group {g_sm} = 1st gear S/M from {rpm} rpm")
        if d_on:
            img.set_group_rows(g_d, first_rows(ys, rpm_d, coast, d=True), f"tcc-first: group {g_d} = 1st gear D from {rpm_d} rpm")
        img.set16(img.P["tcc_mask"], 0x007E, "tcc-first: gear mask 0x3C -> 0x7E (1st, 2nd-5th, code 6)")
        img.code_areas += [(H["at"], H["at"] + 12), (lo, hi)]
        tab = [0] * 16
        for p in sm:
            tab[p] = g_sm
        if d_on:
            for p in MODES["D"]:
                tab[p] = g_d
        for p in range(16):
            img.set8(H["table"] + p, tab[p], f"tcc-first: 1st-gear group of P{p:X} = {tab[p]}")
        code = first_gear_code(H["code"], H["table"])
        for i, b in enumerate(code):
            img.set8(H["code"] + i, b, "tcc-first: 1st-gear group select (code, WOLF4X v41)")
        hook = bytes.fromhex("4EB9") + H["code"].to_bytes(4, "big") + bytes.fromhex("4E714E714E71")
        for i, b in enumerate(hook):
            img.set8(H["at"] + i, b, "tcc-first: 0x290A0 jsr 0x3E3A0 + 3 x nop")
        img.notes.append("tcc-first: program code changed - flash the FULL image only (the 32K partial would carry the mask "
                         "without the code and read a wrong group for 1st gear)")
    if hyst != 3:
        img.notes.append(f"tcc-first: TCC hysteresis is {hyst}, factory 3")


def lock_trip(rpm, gear):
    """(open, slip, lock) in n_out/32 for a gear: lock at rpm, slip from rpm - 385, open below rpm - 512."""
    u = UNIT * RATIOS[gear - 1]
    return (round((rpm - 512) / u), round((rpm - 385) / u), round(rpm / u))


def p_tcc_lock(img, prm, ctx):
    """tcc-lock - lock the torque converter early and keep it locked with any pedal in gears 2-5: lock from rpm
    turbine (default 1600), slip from rpm - 385, open below rpm - 512 (the WOLF4X v25 values), never later than
    the factory at any pedal. modes=S+M (default), M or D+S+M (D gets gears 3-5, d_gears=2-5 for all four).
    19x0 uses groups 6-9 (factory: only PB and PD), 20C0 groups 5, 8, 9, 10 (factory: only PB). Docs 13 §2."""
    modes = parse_modes(prm.get("modes", "S+M"))
    rpm = int(prm.get("rpm", 1600))
    if not 1300 <= rpm <= 3500:
        raise PatchError("tcc-lock: rpm between 1300 and 3500")
    d_gears = (2, 3, 4, 5) if prm.get("d_gears", "3-5") == "2-5" else (3, 4, 5)
    target = {2: 6, 3: 7, 4: 8, 5: 9} if img.key == "19x0" else {2: 5, 3: 8, 4: 9, 5: 10}
    own = (0xB, 0xD) if img.key == "19x0" else (0xB,)
    sel = programs(modes)
    users = {g: sorted(p for p in range(16) for c, gg in img.groups(p).items() if gg == g) for g in target.values()}
    for g, ps in users.items():
        if any(p not in own and p not in sel for p in ps):
            raise PatchError(f"tcc-lock: group {g} is used by {['P%X' % p for p in ps]} in this calibration - not the factory layout")
    hyst = img.u8(img.P["tcc_hyst"])
    plan = {}
    for gear, g in target.items():       # everything is computed from the image as it is, then written
        ys, rows = img.group_rows(g)
        # flat over the pedal (the converter does not open when the pedal moves); the lock threshold is never
        # later than the lock this image has for S (P3) or M (PB) in this gear at any pedal (WOLF4X v25 rule)
        caps = [img.group_rows(gg)[1][r][2] for p in (3, 0xB) for gg in [img.groups(p).get(gear, 0)] if gg
                for r in range(len(ys))]
        o, sl, lk = lock_trip(rpm, gear)
        if caps:
            lk = min([lk] + caps)
        trip = (o, sl, lk)
        if not (o < sl <= lk and lk - hyst > o):
            raise PatchError(f"tcc-lock: thresholds {trip} for gear {gear} break the order open < slip <= lock")
        plan[g] = (gear, [trip] * len(ys))
    for g, (gear, new) in plan.items():
        img.set_group_rows(g, new, f"tcc-lock: group {g} = gear {gear}, lock from {turbine(new[0][2], gear)} rpm turbine "
                                   f"(slip {turbine(new[0][1], gear)}, open below {turbine(new[0][0], gear)})")
    for p in sel + [q for q in own if q not in sel]:
        gears = d_gears if p in MODES["D"] else (2, 3, 4, 5)
        for gear in gears:
            img.set_group(p, gear, target[gear], f"tcc-lock: P{p:X} gear {gear} -> group {target[gear]}")


PATCHES = {
    "tcc-first": p_tcc_first,
    "tcc-lock": p_tcc_lock,
    "no-warmup": p_no_warmup,
    "s-no5": p_s_no5,
    "shift-wot": p_shift_wot,
    "no-kickdown": p_no_kickdown,
    "manual-hold": p_manual_hold,
    "gate": p_gate,
}

# Group texts of the recipes built from presets (make_recipe annotations)
PATCH_TEXT = {
    "gate": ("Left gate: S first, M on the first +/- tap (code 0xFE, BMW factory) instead of M at once (0x0B).",
             "Кулиса: сначала S, M по первому нажатию +/- (код 0xFE, как у BMW) вместо сразу M (0x0B)."),
    "s-no5": ("S without 5th: 4>5 never in k11 / k15, 5>4 lands at most 500 rpm under the spark cut, AGS points in S "
              "held at 193 or more (level 4, no PF / hill step 2 in S).",
              "S без 5-й: 4>5 никогда в k11 / k15, 5>4 с посадкой не ближе 500 об/мин к искре, очки AGS в S от 193 "
              "(уровень 4, без PF и горной ступени 2 в S)."),
    "shift-wot": ("Full-throttle upshifts (pedal 243-255) under the spark cut by docs 02 §4, locked addition of 20C0 "
                  "subtracted; downshifts kept under the upshifts and under the spark cut.",
                  "Повышения в пол (педаль 243-255) под искру по документу 02 §4 с вычетом прибавки 20C0 при замкнутой "
                  "ГДТ; понижения ниже повышений и ниже искры."),
    "tcc-lock": ("Torque converter locked early and with any pedal in gears 2-5 (lock 1600, slip 1215, open 1088 rpm "
                 "turbine, the WOLF4X v25 values), never later than the factory.",
                 "ГДТ замкнута рано и при любой педали во 2-5-й (замыкание 1600, скольжение 1215, размыкание 1088 об/мин "
                 "турбины, значения WOLF4X v25), не позже завода."),
    "tcc-first": ("Torque converter locked in 1st gear under throttle (lock 1760 rpm turbine S/M, 2110 D, later with "
                  "more pedal; opens at once with the pedal released).",
                  "ГДТ на 1-й под газом (замыкание 1760 об/мин турбины S/M, 2110 D, позже с ростом педали; с отпущенной "
                  "педалью размыкается сразу)."),
    "manual-hold": ("M holds the gear on the limiter: up only on the overrun above the hard cut, under the turbine "
                    "monitor; the kickdown row does not downshift in M.",
                    "M держит передачу на отсечке: повышение только на накате выше отсечки и ниже монитора турбины; "
                    "строка кикдауна в M не понижает."),
    "no-kickdown": ("Kickdown off: the flag is never set (switch path with pedal > 255); in M the +/- taps work with "
                    "the pedal on the floor.",
                    "Кикдаун выключен: флаг не ставится никогда (ветка контакта с педалью > 255); в M нажатия +/- "
                    "работают с педалью в полу."),
    "no-warmup": ("Warm-up program off: it ends on the first cycle after power-on.",
                  "Режим прогрева выключен: заканчивается на первом такте после включения."),
}

# Presets: chains of patches. The engine limits come from --spark / --cut or the reference engine of the platform.
PRESETS = {
    "sport-daily": dict(
        en="D factory. S on the gate (M on the first tap), S without 5th and with full-throttle upshifts under the limiter, "
           "converter locked from 1600 rpm in S and M; M holds the gear on the limiter, kickdown does not downshift in M.",
        ru="D заводской. В кулисе S (M по первому нажатию), S без 5-й и с повышениями в пол под отсечку, ГДТ замкнута с "
           "1600 об/мин в S и M; M держит передачу на отсечке, кикдаун в M не понижает.",
        chain=["gate:mode=S", "s-no5", "shift-wot:modes=S", "tcc-lock:modes=S+M", "manual-hold:monitor=auto"]),
    "street-hard": dict(
        en="sport-daily plus the converter locked in 1st gear in S and M under throttle, no warm-up program, no kickdown at all.",
        ru="sport-daily плюс ГДТ на 1-й в S и M под газом, без режима прогрева, без кикдауна вообще.",
        chain=["gate:mode=S", "s-no5", "shift-wot:modes=S", "tcc-lock:modes=S+M", "tcc-first:modes=S+M",
               "manual-hold:monitor=auto", "no-kickdown", "no-warmup"]),
    "track-hard": dict(
        en="street-hard plus D: full-throttle upshifts under the limiter and the converter locked from 1600 rpm in 3rd-5th "
           "and in 1st under throttle.",
        ru="street-hard плюс D: повышения в пол под отсечку и ГДТ с 1600 об/мин в 3-5-й и на 1-й под газом.",
        chain=["gate:mode=S", "s-no5", "shift-wot:modes=D+S", "tcc-lock:modes=D+S+M", "tcc-first:modes=D+S+M",
               "manual-hold:monitor=auto", "no-kickdown", "no-warmup"]),
}


def parse_patch(s):
    name, _, rest = s.partition(":")
    prm = {}
    if rest:
        for kv in rest.split(","):
            if not kv:
                continue
            k, _, v = kv.partition("=")
            prm[k.strip()] = v.strip() if v else "1"
    if name not in PATCHES:
        raise PatchError(f"unknown patch {name!r}; known: {', '.join(PATCHES)}")
    return name, prm


def run(img, chain, ctx):
    for s in chain:
        name, prm = parse_patch(s)
        n0 = len(img.changes)
        PATCHES[name](img, prm, ctx)
        img.notes.append(f"{s}: {len(img.changes) - n0} bytes")


def recompute_sums(d):
    """All three checksums recomputed (gs860_crc.fixed refuses a changed program, which tcc-first on 19x0 is)."""
    table, off, regions = gs860_crc.layout(d)
    out = bytearray(d)
    for s, e, at, _name in regions:
        out[at - off:at - off + 2] = gs860_crc.crc16(out, s - off, e - off, table).to_bytes(2, "big")
    return bytes(out)


def finish(img, out_path, dry, title):
    if not img.changes:
        raise PatchError("nothing changed (the image already has these patches?)")
    data = recompute_sums(bytes(img.d))
    sums = gs860_crc.sums(data)
    if not all(s == c for *_, s, c in sums):
        raise PatchError("internal: checksums do not match after recomputing")
    lo_cal, hi_cal = img.P["cal"]
    crc_bytes = {at + k for _n, _s, _e, at, _st, _c in sums for k in (0, 1)}
    for i in range(len(data)):
        if data[i] != img.orig[i] and not img.allowed(i) and i not in crc_bytes:
            raise PatchError(f"internal: byte 0x{i:05X} changed outside the calibration and the declared code")
    if data[:0x4400] != img.orig[:0x4400]:
        raise PatchError("internal: the loader changed")
    code_touched = any(not (lo_cal <= a < hi_cal) for a, *_ in img.changes)
    log = [f"egs_patch.py  {datetime.datetime.now():%Y-%m-%d %H:%M}  {title}",
           f"input : {img.path}  ({img.P['name']})  sha256 {hashlib.sha256(img.orig).hexdigest()}"]
    log += [f"note  : {n}" for n in img.notes]
    for a, o, n, why in img.changes:
        log.append(f"0x{a:05X}: {o:3d} -> {n:3d}   {why}")
    for name, s, e, at, st, c in sums:
        old = (img.orig[at] << 8) | img.orig[at + 1]
        log.append(f"checksum {name:11s} at 0x{at:05X}: 0x{old:04X} -> 0x{st:04X}")
    log.append(f"bytes changed: {sum(1 for i in range(len(data)) if data[i] != img.orig[i])} (with checksums)")
    log.append(f"output sha256: {hashlib.sha256(data).hexdigest()}")
    if code_touched:
        log.append("PROGRAM CODE CHANGED: flash the full image only; no partial file is written")
    if dry:
        print("\n".join(log)); print("dry run - nothing written"); return data
    if os.path.exists(out_path) or os.path.abspath(out_path) == os.path.abspath(img.path):
        raise PatchError(f"{out_path}: exists or is the input - not overwriting")
    with open(out_path, "wb") as f:
        f.write(data)
    base = os.path.splitext(out_path)[0]
    if img.key == "19x0" and not code_touched:
        with open(base + "_partial32k.bin", "wb") as f:
            f.write(data[0x8000:0x10000])
        log.append(f"partial 32K: {base}_partial32k.bin  sha256 {hashlib.sha256(data[0x8000:0x10000]).hexdigest()}")
    with open(base + ".log", "w", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log)); print(f"written: {out_path}, {base}.log")
    return data


def cmd_show(img):
    P, d = img.P, img.d
    print(f"{img.path}: {P['name']}")
    g = img.u8(P["gate"])
    print(f"left gate code 0x{P['gate']:05X} = 0x{g:02X}  ({'S first, M on +/-' if g == 0xFE else 'M at once' if g == 0x0B else 'P3 (S level 4)' if g == 3 else '?'})")
    print(f"warm-up end 0x{P['warm_end']:05X} = {img.u8(P['warm_end'])} (n_out/32; 0 = no warm-up program)")
    src = img.u8(P["kd_src"])
    print(f"kickdown source 0x{P['kd_src']:05X} = {src} ({'DME2 byte 6 bit 2 (CAN)' if src else 'switch and pedal'}), "
          f"pedal threshold 0x{P['kd_thr']:05X} = {img.u8(P['kd_thr'])} ({'never' if img.u8(P['kd_thr']) == 255 else 'switch path'})")
    print(f"turbine monitor 0x{P['monitor']:05X} = {img.u16(P['monitor'])} rpm")
    print(f"AGS lower bound D / S 0x{P['ags_low']:05X} = {img.u8(P['ags_low'])} / {img.u8(P['ags_low'] + 1)}")
    if P["lock_add"]:
        print(f"upshift threshold + while locked 0x{P['lock_add']:05X} = {list(d[P['lock_add']:P['lock_add'] + 6])} (gear codes 1-6)")
    print(f"TCC gear mask 0x{P['tcc_mask']:05X} = 0x{img.u16(P['tcc_mask']):04X}")
    if P["first_hook"]:
        H = P["first_hook"]
        hooked = bytes(d[H["at"]:H["at"] + 6]) == bytes.fromhex("4EB9") + H["code"].to_bytes(4, "big")
        print(f"1st-gear hook 0x{H['at']:05X}: {'present, table ' + str(list(d[H['table']:H['table'] + 16])) if hooked else 'factory'}")
    for m in ("D", "S", "M"):
        for p in MODES[m]:
            grp = img.groups(p)
            parts = []
            for code, gg in grp.items():
                if not gg:
                    parts.append(f"{code}: -"); continue
                ys, rows = img.group_rows(gg)
                gear = 1 if code == 6 else code
                top = max(i for i, y in enumerate(ys) if y < 255)
                lo, hi = rows[0], rows[top]
                fmt = lambda tr: "/".join("never" if v >= 200 else str(turbine(v, gear)) for v in tr)
                parts.append(f"{code}: g{gg} {fmt(lo)}..{fmt(hi)}")
            print(f"  TCC {m} P{p:X}: " + "  ".join(parts))
    for m in ("D", "S", "M"):
        for p in MODES[m]:
            k = PROG2K[p]
            t, ys, data = img.matrix(k)
            r = 9
            up = " ".join("never" if v >= 250 else str(turbine(v, g + 1)) for g, v in enumerate(data[r][:4]))
            dn = " ".join("-" if v == 0 else str(turbine(v, g + 1)) for g, v in enumerate(data[r][4:]))
            print(f"  shift {m} P{p:X} k{k:02d} pedal {ys[r]}: up {up} | down {dn}")


def cmd_recipe(a):
    """Build preset NAME on the stock image and write it as a recipe with annotations from the patch log."""
    import make_recipe
    if len(a.args) < 2 or a.args[0] not in PRESETS or not a.out:
        raise PatchError(f"recipe NAME stock.bin -o recipe.json; names: {', '.join(PRESETS)}")
    name, stock = a.args[0], a.args[1]
    img = Image(stock)
    pr = PRESETS[name]
    ref = img.P["ref_engine"]
    ctx = dict(spark=a.spark or ref["spark"], cut=a.cut or ref["cut"])
    run(img, pr["chain"], ctx)
    if img.code_areas and any(not (img.P["cal"][0] <= ad < img.P["cal"][1]) for ad, *_ in img.changes):
        raise PatchError(f"preset {name} changes the program code on {img.P['name']} (tcc-first): a recipe cannot "
                         "carry code; use `egs_patch.py preset` on the image instead")
    data = recompute_sums(bytes(img.d))
    tables = img.fw.tile()
    span = {}
    for t in tables:
        for x in range(t["addr"], t["end"]):
            span[x] = t["addr"]
    by_addr, ranges = {}, []
    for ad, _o, _n, why in img.changes:
        patch = why.split(":")[0].split(" ")[0]
        ranges.append({"from": f"0x{ad:05X}", "to": f"0x{ad + 1:05X}", "group": patch, "name": why})
    groups = {k: {"en": v[0], "ru": v[1]} for k, v in PATCH_TEXT.items()
              if any(r["group"] == k for r in ranges)}
    plat = "GS8.60.4 20C0" if img.key == "20C0" else "GS8.60.0 19C0/19D0"
    label = bytes(img.orig[img.fw.L["labels"][1]:img.fw.L["labels"][1] + 16]).decode("latin1")
    chain = " ".join(pr["chain"])
    meta = {
        "name": f"WOLF4X {plat} {name}",
        "author": "rudywolf (WOLF4X)",
        "date": datetime.date.today().isoformat(),
        "description": {
            "en": f"{pr['en']} Built by tools/egs_patch.py from the patches of docs 13 on the calibration {label}, "
                  f"for {ref['name'] if not (a.spark or a.cut) else 'an engine'} (spark {ctx['spark']}, hard cut {ctx['cut']} rpm). "
                  f"Chain: {chain}. For another engine rebuild it: egs_patch.py preset {name} your.bin -o out.bin "
                  "--spark RPM --cut RPM.",
            "ru": f"{pr['ru']} Собран tools/egs_patch.py из патчей документа 13 на калибровке {label}, под "
                  f"{'эталонный мотор платформы' if not (a.spark or a.cut) else 'мотор'} (искра {ctx['spark']}, отсечка "
                  f"{ctx['cut']} об/мин). Цепочка: {chain}. Под другой мотор пересобрать: egs_patch.py preset {name} "
                  "your.bin -o out.bin --spark RPM --cut RPM."},
        "status": {
            "en": "Not road-tested on this platform as a whole preset. Every patch in it is proven by code (docs 13); "
                  "the 19x0 counterparts of tcc-lock, tcc-first, s-no5 and manual-hold ran on the reference car "
                  "(WOLF4X v24-v42). Check with a log before trusting it.",
            "ru": "Целиком на этой платформе на машине не проверен. Каждый патч доказан кодом (документ 13); "
                  "аналоги tcc-lock, tcc-first, s-no5 и manual-hold на 19x0 ездили на референсной машине "
                  "(WOLF4X v24-v42). Проверить логом, прежде чем доверять."},
    }
    ann = {"meta": meta, "groups": groups, "by_addr": by_addr, "ranges": ranges}
    try:
        rec, notes = make_recipe.make(stock, None, ann, f"{img.key.lower()}_{name}", tuned_data=data)
    except make_recipe.RecipeError as e:
        raise PatchError(str(e))
    # names: every change inside an entry, the pedal rows folded, no repeats
    reasons = {ad: why for ad, _o, _n, why in img.changes}
    def label(lo, hi):
        rs = [re.sub(r" pedal \d+", "", reasons[x]) for x in range(lo, hi) if x in reasons]
        rs = list(dict.fromkeys(rs))
        groups_ = list(dict.fromkeys(r.split(":")[0].split(" ")[0] for r in rs))
        return groups_[0] if groups_ else "", "; ".join(rs)[:400]
    for e in rec["tables"]:
        t = img.fw.try_table(int(e["addr"], 16))
        e["group"], e["name"] = label(t["addr"], t["end"])
    for e in rec["bytes"]:
        a0 = int(e["addr"], 16)
        e["group"], e["name"] = label(a0, a0 + e["count"] * e["width"] // 8)
    rec["built_with"] = {"tool": "tools/egs_patch.py", "preset": name, "chain": pr["chain"],
                         "spark": ctx["spark"], "cut": ctx["cut"]}
    for n in notes + img.notes:
        print(n)
    make_recipe.write(rec, a.out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "show", "apply", "preset", "recipe"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("-o", "--out")
    ap.add_argument("--cut", type=int)
    ap.add_argument("--spark", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_intermixed_args(argv)
    try:
        if a.cmd == "list":
            for name, fn in PATCHES.items():
                print(f"{name}\n    " + " ".join(fn.__doc__.split()).replace(name + " - ", "", 1) + "\n")
            print("presets (engine limits: --spark / --cut, otherwise the reference engine):")
            for k, P in PLAT.items():
                print(f"  reference engine {k}: {P['ref_engine']['name']}, spark {P['ref_engine']['spark']}, cut {P['ref_engine']['cut']}")
            for name, pr in PRESETS.items():
                print(f"  {name}: {pr['en']}\n      {' '.join(pr['chain'])}")
            return 0
        if not a.args:
            ap.error("give the image")
        if a.cmd == "show":
            cmd_show(Image(a.args[0])); return 0
        if a.cmd == "recipe":
            return cmd_recipe(a)
        if a.cmd == "apply":
            img = Image(a.args[0]); chain = a.args[1:]
            if not chain:
                ap.error("give at least one patch")
            title = "apply " + " ".join(chain)
        else:
            if len(a.args) < 2 or a.args[0] not in PRESETS:
                ap.error(f"preset NAME image; names: {', '.join(PRESETS)}")
            img = Image(a.args[1]); chain = PRESETS[a.args[0]]["chain"]
            title = f"preset {a.args[0]}: " + " ".join(chain)
        ref = img.P["ref_engine"]
        ctx = dict(spark=a.spark or (ref["spark"] if a.cmd == "preset" else None),
                   cut=a.cut or (ref["cut"] if a.cmd == "preset" else None))
        if a.cmd == "preset" and not (a.spark and a.cut):
            img.notes.append(f"engine limits of the reference engine: {ref['name']} (spark {ctx['spark']}, cut {ctx['cut']})")
        if not a.out and not a.dry_run:
            ap.error("give -o out.bin (or --dry-run)")
        run(img, chain, ctx)
        finish(img, a.out, a.dry_run, title)
        return 0
    except PatchError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
