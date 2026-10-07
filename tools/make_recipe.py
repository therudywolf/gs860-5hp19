#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_recipe.py - build a recipe (JSON diff) from two images of the same program: stock -> tuned.
GS8.60.0 19C0/19D0 (256K) and GS8.60.4 20C0 (512K).
Part of the GS8.60 community repository. License: MIT.

A recipe records, for every changed table, its address, format, both axes, the old
and the new data; scalar / matrix changes outside tables are recorded as byte runs.
Axes are never part of a change: if the tuned image has different axes than the stock
image for any table, the tool stops (see docs 09-what-not-to-touch).
The calibration checksum (19x0: 0xFFFE-0xFFFF, 20C0: 0x7FFFE-0x7FFFF) is never part of a recipe
either: apply_recipe.py computes it (tools/gs860_crc.py). The recorded result hashes are those of the image
apply_recipe.py produces, that is the tuned image with the checksum recomputed.

Usage:
  make_recipe.py stock.bin tuned.bin -o recipe.json [-a annotations.json]

annotations.json (optional) adds names, groups and comments:
{
  "meta":   {"name": "...", "author": "...", "date": "...", "description": {"en": "...", "ru": "..."},
             "status": {"en": "...", "ru": "..."}},
  "groups": {"group_id": {"en": "...", "ru": "..."}},
  "by_addr": {"0x0BF9C": {"group": "group_id", "name": "...", "comment": {"en": "...", "ru": "..."}}},
  "ranges":  [{"from": "0x09222", "to": "0x098B2", "group": "...", "name": "...", "comment": {...}}],
  "history": [{"date": "...", "change": {"en": "...", "ru": "..."}, "full_sha256": "...", ...}]
}
"status" (optional) is copied into the recipe after "description": what is known to be wrong or
unchecked in the preset. "history" is copied into the recipe as is: earlier result hashes and why
they changed.

Example:
  python3 tools/make_recipe.py stock.bin tuned.bin -o recipes/my_recipe.json -a my_annotations.json
"""
import sys, json, hashlib, argparse, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from egs_tables import FW
import gs860_crc

SCHEMA = "gs860-recipe/2"
# per image size: calibration window, program code, calibration checksum (computed by apply_recipe.py, never
# recorded), software text
PLATFORMS = {
    0x40000: dict(win=(0x08000, 0x10000), code=(0x10000, 0x40000), crc=0x0FFFE, platform="19x0",
                  software="Bosch GS8.60.0 (ZF 5HP19), 256K, program 19C0/19D0"),
    0x80000: dict(win=(0x70000, 0x80000), code=(0x08000, 0x70000), crc=0x7FFFE, platform="20C0",
                  software="Bosch GS8.60.4 (ZF 5HP19), 512K, program 20C0"),
}

# Structures the table heuristic mis-detects as tables (their "axis" is really data),
# or that are not tables at all but have a known shape. addr -> (width_bits, count, name)
KNOWN_BLOCKS = {
    0x0888C: (8, 4,  "TCC stage duty ladder 0x888C (stage 1..4)"),
    0x0889C: (8, 16, "TCC stage transition matrix, branch 0 (4x4)"),
    0x088B0: (8, 16, "TCC stage transition matrix, branch 1 (4x4)"),
    0x088C0: (8, 1,  "TCC duty ramp up per cycle"),
    0x088C1: (8, 1,  "TCC duty ramp down per cycle"),
    0x08214: (8, 1,  "TCC number of stages"),
    0x08E88: (8, 1,  "TCC dwell cycles after stage change"),
    0x08D92: (8, 21, "calibration branch select table (selector x sub-mode)"),
}
NOT_TABLES = {0x0888A}                       # 1D8 4x1 detected here is really the ladder + 4 bytes
for a in range(0x8EE0, 0x8F10, 2):           # block of 16-bit diagnostic thresholds (mV)
    KNOWN_BLOCKS[a] = (16, 1, f"16-bit scalar 0x{a:04X} (diagnostic threshold block 0x8EE0-0x8F0E)")


class RecipeError(Exception):
    pass


def make(stock_path, tuned_path, ann=None, out_name="recipe", tuned_data=None):
    """The recipe dict for stock -> tuned (tuned_data: the tuned image bytes instead of a file)."""
    st = FW(stock_path)
    tn = FW(stock_path if tuned_data is not None else tuned_path)
    if tuned_data is not None:
        tn.d = bytearray(tuned_data)
    ann = ann or {}
    if st.N != tn.N or st.N not in PLATFORMS:
        raise RecipeError("both images must be full and of the same size: 256K (GS8.60.0) or 512K (GS8.60.4 20C0)")
    PL = PLATFORMS[st.N]
    WIN_LO, WIN_HI = PL["win"]
    CODE_LO, CODE_HI = PL["code"]
    CRC_AT = PL["crc"]
    if st.sha256(CODE_LO, CODE_HI) != st.L["code_sha"]:
        raise RecipeError(f"stock image: program code 0x{CODE_LO:05X}-0x{CODE_HI:05X} is not the known {PL['platform']} program")
    if st.d[:WIN_LO] != tn.d[:WIN_LO] or st.d[WIN_HI:] != tn.d[WIN_HI:]:
        d = [i for i in range(st.N) if st.d[i] != tn.d[i] and not (WIN_LO <= i < WIN_HI)]
        raise RecipeError(f"tuned image differs outside the calibration window 0x{WIN_LO:05X}-0x{WIN_HI:05X} at {len(d)} bytes "
                 f"(first {d[0]:05X}); a recipe cannot describe that (a code patch, egs_patch.py tcc-first on 19x0?) - stop")

    for name, img in (("stock", st), ("tuned", tn)):
        bad = [n for n, _s, _e, _at, s, c in gs860_crc.sums(bytes(img.d)) if n != "calibration" and s != c]
        if bad:
            raise RecipeError(f"{name} image: {' and '.join(bad)} checksum does not match - damaged or a different software")
    notes = []
    result = gs860_crc.fixed(bytes(tn.d))            # what apply_recipe.py will produce from stock + recipe
    crc_stock = int.from_bytes(st.d[CRC_AT:CRC_AT + 2], "big")
    crc_tuned = int.from_bytes(tn.d[CRC_AT:CRC_AT + 2], "big")
    crc_result = int.from_bytes(result[CRC_AT:CRC_AT + 2], "big")
    if crc_tuned != crc_result:
        notes.append(f"note: the tuned image carries a stale calibration checksum 0x{crc_tuned:04X} "
              f"(computed 0x{crc_result:04X}); the recipe leaves it out, apply_recipe.py recomputes it")

    by_addr = {int(k, 16): v for k, v in ann.get("by_addr", {}).items()}
    ranges = [(int(r["from"], 16), int(r["to"], 16), r) for r in ann.get("ranges", [])]

    def annotate(addr, entry):
        info = by_addr.get(addr)
        if info is None:
            for lo, hi, r in ranges:
                if lo <= addr < hi:
                    info = r; break
        if info:
            for k in ("group", "name", "comment"):
                if k in info:
                    entry[k] = info[k]
        return entry

    tables = st.tile()
    covered = set()
    out_tables, axis_errors = [], []
    for t in tables:
        if t["addr"] in NOT_TABLES:
            continue
        covered.update(range(t["addr"], t["end"]))
        xs, ys, d_old, da, w = st.read_table(t)
        t2 = tn.try_table(t["addr"])
        if not t2 or t2["kind"] != t["kind"] or t2["nx"] != t["nx"] or t2["ny"] != t["ny"]:
            axis_errors.append(f"{t['addr']:05X}: header/axes changed in tuned image"); continue
        xs2, ys2, d_new, _, _ = tn.read_table(t2)
        if xs2 != xs or ys2 != ys:
            axis_errors.append(f"{t['addr']:05X}: axes differ (stock X={xs} Y={ys}; tuned X={xs2} Y={ys2})"); continue
        if d_new != d_old:
            e = dict(addr=f"0x{t['addr']:05X}", kind=t["kind"], nx=t["nx"], ny=t["ny"],
                     x=xs, y=ys if t["ny"] > 1 else None, data_addr=f"0x{da:05X}",
                     old=d_old, new=d_new,
                     cells_changed=sum(1 for r in range(t["ny"]) for c in range(t["nx"]) if d_old[r][c] != d_new[r][c]))
            out_tables.append(annotate(t["addr"], e))
    if axis_errors:
        raise RecipeError("\n".join(axis_errors) + "\naxes changed - refusing to build a recipe (axes are never part of a recipe)")

    # bytes outside tables (the checksum is not a calibration change)
    changed = [i for i in range(WIN_LO, WIN_HI) if st.d[i] != tn.d[i] and i not in covered
               and not CRC_AT <= i < CRC_AT + 2]
    out_bytes, i = [], 0
    handled = set()
    for a, (bits, cnt, name) in sorted(KNOWN_BLOCKS.items() if PL["platform"] == "19x0" else []):
        span = range(a, a + cnt * bits // 8)
        if any(x in changed for x in span):
            rd = (lambda f, x: f.u8(x)) if bits == 8 else (lambda f, x: f.u16(x))
            step = bits // 8
            e = dict(addr=f"0x{a:05X}", width=bits, count=cnt, name=name,
                     old=[rd(st, a + k * step) for k in range(cnt)], new=[rd(tn, a + k * step) for k in range(cnt)])
            out_bytes.append(annotate(a, e)); handled.update(span)
    rest = [x for x in changed if x not in handled]
    while rest:
        a = rest[0]; run = [a]; j = 1
        while j < len(rest) and rest[j] == a + j:
            run.append(rest[j]); j += 1
        rest = rest[j:]
        e = dict(addr=f"0x{a:05X}", width=8, count=len(run), name=f"unnamed bytes 0x{a:05X}",
                 old=[st.u8(x) for x in run], new=[tn.u8(x) for x in run])
        out_bytes.append(annotate(a, e))
    out_bytes.sort(key=lambda e: int(e["addr"], 16))

    meta = ann.get("meta", {})
    rec = {
        "schema": SCHEMA,
        "name": meta.get("name", out_name),
        "author": meta.get("author", ""),
        "date": meta.get("date", ""),
        "description": meta.get("description", {}),
        "base": {
            "software": PL["software"],
            "platform": PL["platform"],
            "image_size": st.N,
            "code_sha256": st.sha256(CODE_LO, CODE_HI),
            "stock_calibration_sha256": st.sha256(WIN_LO, WIN_HI),
            "stock_calibration_label": bytes(st.d[st.L["labels"][1]:st.L["labels"][1] + 16]).decode("latin1"),
        },
        "result": {
            "full_sha256": hashlib.sha256(result).hexdigest(),
            ("partial_sha256" if PL["platform"] == "19x0" else "calibration_window_sha256"):
                hashlib.sha256(result[WIN_LO:WIN_HI]).hexdigest(),
            "bytes_changed": sum(1 for x in range(st.N) if st.d[x] != result[x]),
        },
        "checksum": {
            "calibration": f"CRC-16/XMODEM over 0x{WIN_LO:05X}-0x{CRC_AT - 0x31:05X}, stored at 0x{CRC_AT:05X}; computed by "
                           "apply_recipe.py, not part of the recipe (tools/gs860_crc.py)",
            "stock": f"0x{crc_stock:04X}",
            "result": f"0x{crc_result:04X}",
        },
        "rules": [
            "axes are never changed; apply_recipe.py refuses a table whose axes differ from the recipe",
            f"only 0x{WIN_LO:05X}-0x{WIN_HI:05X} is ever written",
            "old values are checked before writing; a mismatch means a different base calibration",
            f"the calibration checksum at 0x{CRC_AT:05X} is recomputed after writing",
        ],
        "groups": ann.get("groups", {}),
        "tables": out_tables,
        "bytes": out_bytes,
    }
    if meta.get("status"):
        # the status note (not road-tested, corrected group roles) goes right after the description
        items = list(rec.items())
        i = [k for k, _ in items].index("description") + 1
        rec = dict(items[:i] + [("status", meta["status"])] + items[i:])
    if ann.get("history"):
        rec["history"] = ann["history"]
    return rec, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stock", help="stock full image (256K GS8.60.0 or 512K GS8.60.4 20C0)")
    ap.add_argument("tuned", help="tuned full image of the same software")
    ap.add_argument("-o", "--out", required=True, help="recipe JSON to write")
    ap.add_argument("-a", "--annotations", help="annotations JSON: names, groups, comments, status, history")
    args = ap.parse_args()
    ann = {}
    if args.annotations:
        with open(args.annotations, encoding="utf-8") as f:
            ann = json.load(f)
    try:
        rec, notes = make(args.stock, args.tuned, ann, os.path.splitext(os.path.basename(args.out))[0])
    except RecipeError as e:
        sys.exit(str(e))
    for n in notes:
        print(n)
    write(rec, args.out)


def write(rec, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.write("\n")
    out_tables, out_bytes = rec["tables"], rec["bytes"]
    print(f"tables changed: {len(out_tables)}  byte blocks: {len(out_bytes)}  total bytes: {rec['result']['bytes_changed']}")
    unnamed = [e["addr"] for e in out_tables + out_bytes if "group" not in e]
    if unnamed:
        print(f"entries without annotation: {len(unnamed)}: {' '.join(unnamed)}")
    print("written:", path)


if __name__ == "__main__":
    main()
