#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_recipe.py - build a recipe (JSON diff) from two GS8.60.0 256K images: stock -> tuned.
Part of the GS8.60.0 community repository. License: MIT.

A recipe records, for every changed table, its address, format, both axes, the old
and the new data; scalar / matrix changes outside tables are recorded as byte runs.
Axes are never part of a change: if the tuned image has different axes than the stock
image for any table, the tool stops (see docs 09-what-not-to-touch).

Usage:
  make_recipe.py stock.bin tuned.bin -o recipe.json [-a annotations.json]

annotations.json (optional) adds names, groups and comments:
{
  "meta":   {"name": "...", "author": "...", "date": "...", "description": {"en": "...", "ru": "..."}},
  "groups": {"group_id": {"en": "...", "ru": "..."}},
  "by_addr": {"0x0BF9C": {"group": "group_id", "name": "...", "comment": {"en": "...", "ru": "..."}}},
  "ranges":  [{"from": "0x09222", "to": "0x098B2", "group": "...", "name": "...", "comment": {...}}]
}
"""
import sys, json, hashlib, argparse, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from egs_tables import FW, CAL_LO, CAL_HI, WIN_LO, WIN_HI, CODE_LO, CODE_HI

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stock"); ap.add_argument("tuned")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("-a", "--annotations")
    args = ap.parse_args()

    st, tn = FW(args.stock), FW(args.tuned)
    if st.N != 0x40000 or tn.N != 0x40000:
        sys.exit("both images must be full 256K")
    if st.d[:WIN_LO] != tn.d[:WIN_LO] or st.d[WIN_HI:] != tn.d[WIN_HI:]:
        d = [i for i in range(st.N) if st.d[i] != tn.d[i] and not (WIN_LO <= i < WIN_HI)]
        sys.exit(f"tuned image differs outside the calibration window 0x8000-0x10000 at {len(d)} bytes "
                 f"(first {d[0]:05X}); a recipe cannot describe that - stop")

    ann = json.load(open(args.annotations, encoding="utf-8")) if args.annotations else {}
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

    tables = st.tile(CAL_LO, CAL_HI)
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
        print("\n".join(axis_errors))
        sys.exit("axes changed - refusing to build a recipe (axes are never part of a recipe)")

    # bytes outside tables
    changed = [i for i in range(WIN_LO, WIN_HI) if st.d[i] != tn.d[i] and i not in covered]
    out_bytes, i = [], 0
    handled = set()
    for a, (bits, cnt, name) in sorted(KNOWN_BLOCKS.items()):
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
        "schema": "gs860-recipe/1",
        "name": meta.get("name", os.path.splitext(os.path.basename(args.out))[0]),
        "author": meta.get("author", ""),
        "date": meta.get("date", ""),
        "description": meta.get("description", {}),
        "base": {
            "software": "Bosch GS8.60.0 (ZF 5HP19), 256K, program 19C0/19D0",
            "code_sha256": st.sha256(CODE_LO, CODE_HI),
            "stock_calibration_sha256": st.sha256(WIN_LO, WIN_HI),
            "stock_calibration_label": bytes(st.d[0xFFCE:0xFFDE]).decode("latin1"),
        },
        "result": {
            "full_sha256": tn.sha256(),
            "partial_sha256": tn.sha256(WIN_LO, WIN_HI),
            "bytes_changed": sum(1 for x in range(st.N) if st.d[x] != tn.d[x]),
        },
        "rules": [
            "axes are never changed; apply_recipe.py refuses a table whose axes differ from the recipe",
            "only 0x8000-0x10000 is ever written",
            "old values are checked before writing; a mismatch means a different base calibration",
        ],
        "groups": ann.get("groups", {}),
        "tables": out_tables,
        "bytes": out_bytes,
    }
    json.dump(rec, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"tables changed: {len(out_tables)}  byte blocks: {len(out_bytes)}  total bytes: {rec['result']['bytes_changed']}")
    unnamed = [e["addr"] for e in out_tables + out_bytes if "group" not in e]
    if unnamed:
        print(f"entries without annotation: {len(unnamed)}: {' '.join(unnamed)}")
    print("written:", args.out)


if __name__ == "__main__":
    main()
