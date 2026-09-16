#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_recipe.py - apply a recipe (JSON diff) to a stock GS8.60.0 256K image.
Part of the GS8.60.0 community repository. License: MIT.

Checks before writing anything:
  1. the input is a full 256K image;
  2. program code 0x10000-0x40000 hashes to the SHA-256 the recipe was built for
     (19C0 and 19D0 share it; a mismatch means different software - hard stop);
  3. every table in the recipe is found at its address with the same format and
     the SAME axes (hard stop otherwise - axes are never touched);
  4. every old value matches the input (warning; hard stop unless --force).
Only bytes inside 0x8000-0x10000 are ever written; this is asserted at the end.

Usage:
  apply_recipe.py recipe.json stock.bin -o out.bin [--force] [--dry-run]
Outputs: out.bin (256K), out_partial32k.bin (0x8000-0x10000), out.log
"""
import sys, json, hashlib, argparse, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from egs_tables import FW, WIN_LO, WIN_HI, CODE_LO, CODE_HI


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recipe"); ap.add_argument("stock")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--force", action="store_true", help="write even where old values do not match")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rec = json.load(open(args.recipe, encoding="utf-8"))
    if rec.get("schema") != "gs860-recipe/1":
        sys.exit(f"unknown recipe schema {rec.get('schema')!r}")
    fw = FW(args.stock)
    log = [f"apply_recipe.py  {datetime.datetime.now():%Y-%m-%d %H:%M}",
           f"recipe : {args.recipe}  ({rec.get('name')}, {rec.get('author')}, {rec.get('date')})",
           f"input  : {args.stock}  sha256 {fw.sha256()}"]

    # 1-2. size and code
    if fw.N != 0x40000:
        sys.exit("input must be a full 256K image (apply to the full dump, flash the partial if you like)")
    code_sha = fw.sha256(CODE_LO, CODE_HI)
    if code_sha != rec["base"]["code_sha256"]:
        sys.exit(f"program code 0x10000-0x40000 sha256 {code_sha} != recipe base {rec['base']['code_sha256']}\n"
                 "This is a different software - the recipe addresses do not apply. Stop.")
    log.append(f"code sha256 ok: {code_sha}")
    cal_sha = fw.sha256(WIN_LO, WIN_HI)
    same_base = cal_sha == rec["base"].get("stock_calibration_sha256")
    log.append(f"calibration window sha256 {cal_sha} "
               + ("== recipe stock (byte-exact result expected)" if same_base else "!= recipe stock (different base calibration: old values are checked cell by cell)"))

    out = bytearray(fw.d)
    problems, mismatches, nbytes = [], 0, 0

    def put8(a, v):
        nonlocal nbytes
        if out[a] != v:
            out[a] = v & 0xFF; nbytes += 1

    # 3-4. tables
    for e in rec.get("tables", []):
        a = int(e["addr"], 16)
        t = fw.try_table(a)
        if not t or t["kind"] != e["kind"] or t["nx"] != e["nx"] or t["ny"] != e["ny"]:
            problems.append(f"{a:05X}: table not found or format differs (expected {e['kind']} {e['nx']}x{e['ny']})"); continue
        xs, ys, data, da, w = fw.read_table(t)
        if xs != e["x"] or (e.get("y") is not None and ys != e["y"]):
            problems.append(f"{a:05X}: AXES differ from recipe (image X={xs} Y={ys}; recipe X={e['x']} Y={e.get('y')})"); continue
        bad = [(r, c) for r in range(t["ny"]) for c in range(t["nx"]) if data[r][c] != e["old"][r][c]]
        if bad:
            mismatches += len(bad)
            log.append(f"WARN {a:05X} {e.get('name', '')}: {len(bad)} old values differ from input (first cell row {bad[0][0]} col {bad[0][1]}: image {data[bad[0][0]][bad[0][1]]}, recipe {e['old'][bad[0][0]][bad[0][1]]})")
        for r in range(t["ny"]):
            for c in range(t["nx"]):
                v = e["new"][r][c]; ca = da + w * (r * t["nx"] + c)
                if not (WIN_LO <= ca < WIN_HI - w + 1):
                    problems.append(f"{a:05X}: cell address {ca:05X} outside calibration window"); continue
                if w == 1:
                    put8(ca, v)
                else:
                    put8(ca, v >> 8); put8(ca + 1, v & 0xFF)
        log.append(f"table {a:05X} {e['kind']} {e['nx']}x{e['ny']}  {e.get('name', '')}  [{e.get('group', '')}]  cells {e.get('cells_changed', '?')}")

    # byte blocks
    for e in rec.get("bytes", []):
        a = int(e["addr"], 16); step = e["width"] // 8
        span = (a, a + e["count"] * step)
        if not (WIN_LO <= span[0] and span[1] <= WIN_HI):
            problems.append(f"{a:05X}: byte block outside calibration window"); continue
        rd = fw.u8 if step == 1 else fw.u16
        old = [rd(a + k * step) for k in range(e["count"])]
        if old != e["old"]:
            mismatches += sum(1 for k in range(e["count"]) if old[k] != e["old"][k])
            log.append(f"WARN {a:05X} {e.get('name', '')}: old values differ (image {old}, recipe {e['old']})")
        for k, v in enumerate(e["new"]):
            if step == 1:
                put8(a + k, v)
            else:
                put8(a + 2 * k, v >> 8); put8(a + 2 * k + 1, v & 0xFF)
        log.append(f"bytes {a:05X} x{e['count']} w{e['width']}  {e.get('name', '')}  [{e.get('group', '')}]  {e['old']} -> {e['new']}")

    if problems:
        print("\n".join(problems)); sys.exit("hard errors - nothing written")
    if mismatches and not args.force:
        print("\n".join(l for l in log if l.startswith("WARN")))
        sys.exit(f"{mismatches} old values differ from the input image. This is not the calibration the recipe was made for.\n"
                 "Read docs/08-recipes-and-presets before continuing; re-run with --force to write anyway.")

    # final guard: nothing outside the window changed
    assert out[:WIN_LO] == fw.d[:WIN_LO] and out[WIN_HI:] == fw.d[WIN_HI:], "internal error: write outside window"
    full_sha = hashlib.sha256(bytes(out)).hexdigest(); part_sha = hashlib.sha256(bytes(out[WIN_LO:WIN_HI])).hexdigest()
    log.append(f"bytes changed: {nbytes}   old-value mismatches: {mismatches}{' (forced)' if mismatches else ''}")
    log.append(f"output sha256 full   : {full_sha}")
    log.append(f"output sha256 partial: {part_sha}")
    exp = rec.get("result", {})
    if exp.get("full_sha256"):
        log.append("result matches recipe reference: " + ("YES" if full_sha == exp["full_sha256"] else "no (expected only when applied to the recipe's own stock)"))
    if args.dry_run:
        print("\n".join(log)); print("dry run - nothing written"); return
    base = os.path.splitext(args.out)[0]
    open(args.out, "wb").write(bytes(out))
    open(base + "_partial32k.bin", "wb").write(bytes(out[WIN_LO:WIN_HI]))
    open(base + ".log", "w", encoding="utf-8").write("\n".join(log) + "\n")
    print("\n".join(log))
    print(f"written: {args.out}, {base}_partial32k.bin, {base}.log")


if __name__ == "__main__":
    main()
