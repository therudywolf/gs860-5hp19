#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_xdf.py - TunerPro XDF files of this repository are generated from a catalog, never edited by hand.

Usage:
  make_xdf.py build <catalog.json> <out_full.xdf> [--partial <out_partial.xdf>]
  make_xdf.py import <in.xdf> <out_catalog.json> [--zero-based]   one-time import of an existing XDF
  make_xdf.py check <catalog.json>          bounds, overlaps, duplicate uids, categories, units

Examples:
  python3 tools/make_xdf.py check catalog/gs8600_19d0.json
  python3 tools/make_xdf.py build catalog/gs8600_19d0.json xdf/GS8600_19D0_Full256K.xdf --partial xdf/GS8600_19x0_Partial32K.xdf
  python3 tools/make_xdf.py build catalog/gs8604_20c0.json xdf/GS8604_20C0_Full512K.xdf

Catalogs: catalog/gs8600_19d0.json (GS8.60.0, 256 KB image, calibration window 0x8000-0xFFFF) and
catalog/gs8604_20c0.json (GS8.60.4, 512 KB image, calibration window 0x70000-0x7FFFF). The generator
takes the image size and the window from the catalog; nothing about the software is hard-coded here.

Catalog (JSON, UTF-8):
  {"format": 1, "title": ..., "description": ..., "author": ..., "image_size": 262144,
   "partial": {"start": 32768, "size": 32768, "title": ..., "description": ...}   (optional),
   "categories": ["1 ...", "2 ...", ...],
   "entries": [ {"kind": "table" | "constant", "uid": 4096, "title": ..., "description": ...,
                 "categories": [0], "confidence": "proven" | "structure" | "hypothesis" | "unknown" | "carried",
                 "proof": ..., "x": axis, "y": axis, "z": data} ... ]}
  axis: {"addr": int or null, "bits": 8|16, "count": n, "labels": [...], "units": ..., "math": "X",
         "signed": false, "lsb_first": false, "major": 0, "minor": 0}
  data: {"addr": int, "bits": 8|16|32, "rows": r, "cols": c, "signed": false, "lsb_first": false,
         "math": "X", "units": ..., "decimals": 1, "major": 0, "minor": 0}

check() refuses a catalog with: a byte span outside the image, two entries reading the same byte
(data or axes), a repeated uid, a missing or unknown category, an empty units string on a constant,
on table data or on an axis. "build" runs check() first and writes nothing when it fails.

Notes (found while importing the 2026 v2.1 file):
  - CATEGORYMEM category is 1-based in TunerPro (category="1" is the first CATEGORY, "0" is none).
    The v2.1 file wrote 0-based numbers, so in TunerPro every table sat one category off and the 16
    shift matrices had none. The generator always writes index + 1. "import --zero-based" corrects
    such a file, plain "import" keeps the numbers as written.
  - The partial XDF only gets entries whose data and axes lie inside the window; the v2.1 partial
    carried all 850 entries with out-of-window addresses.
  - GS8.60 is big-endian: mmedtypeflags bit 0 = signed, bit 1 = LSB first (not used here).

RU. XDF собираются из каталога этим скриптом, руками не правятся. Размер образа и окно калибровки
берутся из каталога (19D0: 256 КБ и 0x8000, 20C0: 512 КБ и 0x70000). check: границы, пересечения
байт между записями, повторы uid, категории, пустые единицы. Категории в CATEGORYMEM нумеруются с 1.
Частичный XDF получает только записи, целиком лежащие в окне.
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET


def _e(s):
    return html.escape(str(s), quote=False)


def _ea(s):
    return html.escape(str(s), quote=True)


def _flags(signed, lsb_first):
    return (1 if signed else 0) | (2 if lsb_first else 0)


def _math(eq):
    vars_ = sorted(set(re.findall(r"\b([A-Z])\b", eq))) or ["X"]
    inner = "".join(f'        <VAR id="{v}" />\n' for v in vars_)
    return f'      <MATH equation="{_ea(eq)}">\n{inner}      </MATH>\n'


def _axis_xml(name, ax):
    """X or Y axis of a table."""
    out = [f'    <XDFAXIS id="{name}" uniqueid="0x0">\n']
    if ax.get("addr") is not None:
        out.append(f'      <EMBEDDEDDATA mmedtypeflags="0x{_flags(ax.get("signed"), ax.get("lsb_first")):02X}" '
                   f'mmedaddress="0x{ax["addr"]:X}" mmedelementsizebits="{ax.get("bits", 8)}" '
                   f'mmedcolcount="{ax["count"]}" mmedmajorstridebits="{ax.get("major", 0)}" '
                   f'mmedminorstridebits="{ax.get("minor", 0)}" />\n')
    else:
        out.append(f'      <EMBEDDEDDATA mmedelementsizebits="{ax.get("bits", 8)}" '
                   f'mmedmajorstridebits="{ax.get("major", -32)}" mmedminorstridebits="0" />\n')
    out.append(f'      <units>{_e(ax.get("units", name.upper()))}</units>\n')
    out.append(f'      <indexcount>{ax["count"]}</indexcount>\n')
    out.append('      <datatype>0</datatype>\n      <unittype>0</unittype>\n      <DALINK index="0" />\n')
    for i, lab in enumerate(ax.get("labels") or []):
        out.append(f'      <LABEL index="{i}" value="{_ea(lab)}" />\n')
    out.append(_math(ax.get("math", "X")))
    out.append('    </XDFAXIS>\n')
    return "".join(out)


def _cats_xml(cats):
    return "".join(f'    <CATEGORYMEM index="{i}" category="{c + 1}" />\n' for i, c in enumerate(cats))


def _entry_xml(e, shift):
    title = e["title"]
    desc = e.get("description", "")
    if e["kind"] == "constant":
        d = e["z"]
        out = [f'  <XDFCONSTANT uniqueid="0x{e["uid"]:X}" flags="0x0">\n',
               f'    <title>{_e(title)}</title>\n']
        if desc:
            out.append(f'    <description>{_e(desc)}</description>\n')
        out.append(_cats_xml(e.get("categories", [])))
        out.append(f'    <EMBEDDEDDATA mmedtypeflags="0x{_flags(d.get("signed"), d.get("lsb_first")):02X}" '
                   f'mmedaddress="0x{d["addr"] - shift:X}" mmedelementsizebits="{d.get("bits", 8)}" '
                   f'mmedmajorstridebits="0" mmedminorstridebits="0" />\n')
        if d.get("units"):
            out.append(f'    <units>{_e(d["units"])}</units>\n')
        out.append(f'    <decimalpl>{d.get("decimals", 0)}</decimalpl>\n    <outputtype>1</outputtype>\n')
        out.append(_math(d.get("math", "X")).replace("      ", "    ", 1))
        out.append('  </XDFCONSTANT>\n')
        return "".join(out)
    z = e["z"]
    out = [f'  <XDFTABLE uniqueid="0x{e["uid"]:X}" flags="0x0">\n', f'    <title>{_e(title)}</title>\n']
    if desc:
        out.append(f'    <description>{_e(desc)}</description>\n')
    out.append(_cats_xml(e.get("categories", [])))
    for name in ("x", "y"):
        ax = dict(e[name])
        if ax.get("addr") is not None:
            ax["addr"] -= shift
        out.append(_axis_xml(name, ax))
    out.append('    <XDFAXIS id="z">\n')
    out.append(f'      <EMBEDDEDDATA mmedtypeflags="0x{_flags(z.get("signed"), z.get("lsb_first")):02X}" '
               f'mmedaddress="0x{z["addr"] - shift:X}" mmedelementsizebits="{z.get("bits", 8)}" '
               f'mmedrowcount="{z["rows"]}" mmedcolcount="{z["cols"]}" '
               f'mmedmajorstridebits="{z.get("major", 0)}" mmedminorstridebits="{z.get("minor", 0)}" />\n')
    out.append(f'      <decimalpl>{z.get("decimals", 1)}</decimalpl>\n')
    out.append(f'      <units>{_e(z.get("units", ""))}</units>\n')
    out.append('      <outputtype>1</outputtype>\n')
    out.append(_math(z.get("math", "X")))
    out.append('    </XDFAXIS>\n  </XDFTABLE>\n')
    return "".join(out)


def spans(e):
    """[(start, end_exclusive)] of every byte an entry reads (data and axes with an address)."""
    z = e["z"]
    n = z.get("rows", 1) * z.get("cols", 1) if e["kind"] == "table" else 1
    out = [(z["addr"], z["addr"] + n * z.get("bits", 8) // 8)]
    if e["kind"] == "table":
        for name in ("x", "y"):
            ax = e[name]
            if ax.get("addr") is not None:
                out.append((ax["addr"], ax["addr"] + ax["count"] * ax.get("bits", 8) // 8))
    return out


def render(cat, partial=False):
    """XDF text for the full image, or for the partial calibration window."""
    if partial:
        p = cat["partial"]
        start, size = p["start"], p["size"]
        entries = [e for e in cat["entries"] if all(start <= s and t <= start + size for s, t in spans(e))]
        title, desc, shift = p["title"], p["description"], start
    else:
        size, entries = cat["image_size"], cat["entries"]
        title, desc, shift = cat["title"], cat["description"], 0
    head = ['<!DOCTYPE xdf>\n<XDFFORMAT version="1.60">\n  <XDFHEADER>\n    <flags>0x1</flags>\n',
            f'    <deftitle>{_e(title)}</deftitle>\n', f'    <description>{_e(desc)}</description>\n',
            f'    <author>{_e(cat.get("author", ""))}</author>\n    <baseoffset>0</baseoffset>\n',
            f'    <REGION type="0xFFFFFFFF" startaddress="0x0" size="0x{size:X}" regionflags="0x0" '
            f'name="Binary File" desc="" />\n']
    for i, name in enumerate(cat["categories"]):
        head.append(f'    <CATEGORY index="0x{i:X}" name="{_ea(name)}" />\n')
    head.append('  </XDFHEADER>\n')
    body = [_entry_xml(e, shift) for e in entries]
    return "".join(head) + "".join(body) + "</XDFFORMAT>\n", len(entries)


# ---------------------------------------------------------------- import of an existing XDF
def _num(v, default=0):
    return int(v, 16) if isinstance(v, str) and v.lower().startswith("0x") else int(v) if v not in (None, "") else default


def import_xdf(text, zero_based=False):
    """Catalog dict from an XDF. With zero_based=True the CATEGORYMEM numbers of the file are taken
    as 0-based (the v2.1 files) and stored as "categories"; otherwise 1-based numbers are converted."""
    root = ET.fromstring(re.sub(r"<!DOCTYPE[^>]*>", "", text))
    hdr = root.find("XDFHEADER")
    region = hdr.find("REGION")
    cats = [c.get("name") for c in sorted(hdr.findall("CATEGORY"), key=lambda c: _num(c.get("index")))]
    cat = {"format": 1, "title": hdr.findtext("deftitle", ""), "description": hdr.findtext("description", ""),
           "author": hdr.findtext("author", ""), "image_size": _num(region.get("size")),
           "categories": cats, "entries": []}
    for el in root:
        if el.tag not in ("XDFTABLE", "XDFCONSTANT"):
            continue
        e = {"kind": "table" if el.tag == "XDFTABLE" else "constant", "uid": _num(el.get("uniqueid")),
             "title": el.findtext("title", ""), "description": el.findtext("description", "") or "",
             "categories": [int(c.get("category")) - (0 if zero_based else 1) for c in el.findall("CATEGORYMEM")]}
        if e["kind"] == "constant":
            d = el.find("EMBEDDEDDATA")
            tf = _num(d.get("mmedtypeflags", "0"))
            e["z"] = {"addr": _num(d.get("mmedaddress")), "bits": int(d.get("mmedelementsizebits", 8)),
                      "signed": bool(tf & 1), "lsb_first": bool(tf & 2), "units": el.findtext("units", "") or "",
                      "decimals": int(el.findtext("decimalpl", "0") or 0),
                      "math": el.find("MATH").get("equation") if el.find("MATH") is not None else "X"}
        else:
            for ax in el.findall("XDFAXIS"):
                d = ax.find("EMBEDDEDDATA")
                tf = _num(d.get("mmedtypeflags", "0"))
                m = ax.find("MATH")
                a = {"bits": int(d.get("mmedelementsizebits", 8)), "signed": bool(tf & 1), "lsb_first": bool(tf & 2),
                     "units": ax.findtext("units", "") or "", "math": m.get("equation") if m is not None else "X",
                     "major": int(d.get("mmedmajorstridebits", 0)), "minor": int(d.get("mmedminorstridebits", 0))}
                if ax.get("id") == "z":
                    a.update(addr=_num(d.get("mmedaddress")), rows=int(d.get("mmedrowcount", 1)),
                             cols=int(d.get("mmedcolcount", 1)), decimals=int(ax.findtext("decimalpl", "1") or 1))
                else:
                    a.update(addr=_num(d.get("mmedaddress")) if d.get("mmedaddress") else None,
                             count=int(ax.findtext("indexcount", "1")),
                             labels=[l.get("value") for l in sorted(ax.findall("LABEL"), key=lambda l: int(l.get("index")))])
                e[ax.get("id")] = a
        cat["entries"].append(e)
    return cat


def check(cat):
    """Problems as a list of strings (empty = fine): bounds, overlaps, uids, categories, units."""
    probs, size = [], cat["image_size"]
    seen_uid = set()
    ivs = []
    for e in cat["entries"]:
        if e["uid"] in seen_uid:
            probs.append(f"uid 0x{e['uid']:X} repeated")
        seen_uid.add(e["uid"])
        for s, t in spans(e):
            if not (0 <= s < t <= size):
                probs.append(f"0x{e['uid']:X} {e['title'][:40]}: bytes 0x{s:X}-0x{t:X} outside the image")
            ivs.append((s, t, e["uid"], e["title"][:40]))
        for c in e.get("categories", []):
            if not 0 <= c < len(cat["categories"]):
                probs.append(f"0x{e['uid']:X}: category {c} does not exist")
        if not e.get("categories"):
            probs.append(f"0x{e['uid']:X} {e['title'][:40]}: no category")
        units = [("z", e["z"].get("units"))]
        if e["kind"] == "table":
            units += [("x", e["x"].get("units")), ("y", e["y"].get("units"))]
        for name, u in units:
            if not u:
                probs.append(f"0x{e['uid']:X} {e['title'][:40]}: no units on {name}")
    ivs.sort()
    for i in range(len(ivs)):
        for j in range(i + 1, len(ivs)):
            if ivs[j][0] >= ivs[i][1]:
                break
            if ivs[i][2] != ivs[j][2]:
                probs.append(f"overlap: 0x{ivs[i][2]:X} {ivs[i][3]} (0x{ivs[i][0]:X}-0x{ivs[i][1]:X}) and "
                             f"0x{ivs[j][2]:X} {ivs[j][3]} (0x{ivs[j][0]:X}-0x{ivs[j][1]:X})")
    return probs


def main(argv):
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if len(argv) >= 3 and argv[0] == "build":
        cat = json.load(open(argv[1], encoding="utf-8"))
        probs = check(cat)
        if probs:
            print("\n".join(probs[:40]))
            return 1
        txt, n = render(cat)
        open(argv[2], "w", encoding="utf-8", newline="\n").write(txt)
        print(f"{argv[2]}: {n} entries")
        if "--partial" in argv:
            out = argv[argv.index("--partial") + 1]
            txt, n = render(cat, partial=True)
            open(out, "w", encoding="utf-8", newline="\n").write(txt)
            print(f"{out}: {n} entries")
        return 0
    if len(argv) >= 3 and argv[0] == "import":
        cat = import_xdf(open(argv[1], encoding="utf-8").read(), "--zero-based" in argv)
        json.dump(cat, open(argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{argv[2]}: {len(cat['entries'])} entries")
        return 0
    if len(argv) == 2 and argv[0] == "check":
        probs = check(json.load(open(argv[1], encoding="utf-8")))
        print("\n".join(probs) if probs else "ok")
        return 1 if probs else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
