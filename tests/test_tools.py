#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
"""
Self-tests of the tools. Part of the gs860-5hp19 repository. License: Apache-2.0 (LICENSE, NOTICE), credit: rudywolf, https://github.com/therudywolf/gs860-5hp19.

  python3 tests/test_tools.py
  python3 -m unittest discover -s tests -v
  GS860_STOCK=/path/to/stock_19C0_or_19D0_256K.bin GS8604_STOCK=/path/to/stock_20C0_512K.bin python3 tests/test_tools.py

Without images only the tests that need no firmware run (the repository holds no images): the
CRC algorithm, the shift-point rules, both catalogs (catalog/gs8600_19d0.json, catalog/gs8604_20c0.json)
and the XDF files generated from them. With GS860_STOCK (a stock 256 KB 19x0 image) the 19x0 layout,
the three sums and every table of the 19D0 catalog are checked against the image. With
GS8604_STOCK (a factory 20C0 image) the 20C0 layout of egs_tables, the three sums and every table of
the 20C0 catalog are checked against the image.
"""
import hashlib, json, os, re, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
CATALOG_19D0 = os.path.join(ROOT, "catalog", "gs8600_19d0.json")
CATALOG_20C0 = os.path.join(ROOT, "catalog", "gs8604_20c0.json")
XDF = os.path.join(ROOT, "xdf")
sys.path.insert(0, TOOLS)

import gs860_crc                                    # noqa: E402
import egs_tables                                   # noqa: E402
import make_xdf                                     # noqa: E402

STOCK = os.environ.get("GS860_STOCK")
STOCK20 = os.environ.get("GS8604_STOCK")
VIN_LIKE = re.compile(r"W(BA|BS|AP)[A-Z0-9]{14}")    # nothing that looks like a VIN may be in the repository


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=ROOT)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestCRC(unittest.TestCase):
    def test_xmodem_check_value(self):
        # CRC-16/XMODEM of "123456789" is 0x31C3 by definition of the algorithm
        self.assertEqual(gs860_crc.crc16(b"123456789", 0, 9), 0x31C3)

    def test_partial_roundtrip(self):
        d = bytearray(os.urandom(0x8000))
        d[0x7FFE:0x8000] = gs860_crc.crc16(d, 0, 0x7FCE).to_bytes(2, "big")
        self.assertTrue(all(s == c for *_, s, c in gs860_crc.sums(bytes(d))))
        d[0x100] ^= 0xFF
        self.assertFalse(all(s == c for *_, s, c in gs860_crc.sums(bytes(d))))
        fixed = gs860_crc.fixed(bytes(d))
        self.assertTrue(all(s == c for *_, s, c in gs860_crc.sums(fixed)))
        self.assertEqual(fixed[:0x7FFE], bytes(d[:0x7FFE]))

    def test_unknown_size(self):
        with self.assertRaises(gs860_crc.WrongImage):
            gs860_crc.sums(b"\0" * 1000)

    def test_full_image_without_table(self):
        with self.assertRaises(gs860_crc.WrongImage):
            gs860_crc.sums(b"\0" * 0x40000)
        with self.assertRaises(gs860_crc.WrongImage):
            gs860_crc.sums(b"\0" * 0x80000)

    def test_layout_20c0(self):
        # the three regions of the 512K image (docs 11 §2), each sum stored outside its region
        regions = gs860_crc.LAYOUTS[0x80000][2]
        self.assertEqual([(s, e, at) for s, e, at, _ in regions],
                         [(0x00000, 0x04400, 0x05FFE), (0x08000, 0x6FF7C, 0x6FFFE), (0x70000, 0x7FFCE, 0x7FFFE)])
        for s, e, at, _ in regions:
            self.assertFalse(s <= at < e)


class TestRepository(unittest.TestCase):
    def test_every_tool_has_help(self):
        for n in sorted(os.listdir(TOOLS)):
            if n.endswith(".py"):
                with self.subTest(tool=n):
                    r = run(os.path.join(TOOLS, n), "--help")
                    self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                    self.assertIn("Example", r.stdout)

    def test_licence_and_credit(self):
        # code: Apache-2.0 with the credit in NOTICE; documents, catalogs and XDF: CC BY-SA 4.0 (NOTICE)
        def read(*p):
            with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
                return f.read()
        self.assertTrue(read("LICENSE").lstrip().startswith("Apache License"))
        self.assertIn("Attribution-ShareAlike 4.0 International Public License", read("LICENSE-docs"))
        self.assertIn("Attribution-NonCommercial-ShareAlike 4.0 International Public License", read("LICENSE-docs-nc"))
        for lang in ("en", "ru"):                     # the documents about the author's layer say their licence
            for n in sorted(os.listdir(os.path.join(ROOT, "docs", lang))):
                if n.startswith("14-"):
                    with self.subTest(file=f"docs/{lang}/{n}"):
                        head = read("docs", lang, n).split("\n## ")[0]
                        self.assertIn("CC BY-NC-SA 4.0", head)
                        self.assertIn("LICENSE-docs-nc", head)
        self.assertIn(make_xdf.CREDIT, read("NOTICE"))
        for d in ("tools", "tests"):
            for n in sorted(os.listdir(os.path.join(ROOT, d))):
                if n.endswith(".py"):
                    with self.subTest(file=f"{d}/{n}"):
                        self.assertIn("SPDX-License-Identifier: Apache-2.0", read(d, n))
        # every XDF carries the licence and the credit in its header, and import gives the catalog fields back
        for n in sorted(os.listdir(XDF)):
            with self.subTest(xdf=n):
                text = read("xdf", n)
                head = text.split("</XDFHEADER>")[0]
                self.assertIn(make_xdf.LICENCE_NOTE, head)
                self.assertIn(make_xdf.REPO_URL + "</author>", head)
        cat = load(CATALOG_19D0)
        back = make_xdf.import_xdf(make_xdf.render(cat)[0])
        self.assertEqual((back["description"], back["author"]), (cat["description"], cat["author"]))

    def test_nothing_private_in_the_tree(self):
        # no firmware images or dumps in any form (CONTRIBUTING, .gitignore); binary files only as pictures in
        # assets/; nothing that looks like a VIN in any text file
        firmware_ext = {".bin", ".hex", ".ori", ".mod", ".img", ".eep", ".s19", ".srec", ".zip", ".7z", ".rar",
                        ".ols", ".kp", ".a2l"}
        for d, dirs, files in os.walk(ROOT):
            dirs[:] = [x for x in dirs if x not in (".git", "__pycache__")]
            for n in files:
                p = os.path.join(d, n)
                rel = os.path.relpath(p, ROOT)
                with self.subTest(file=rel):
                    self.assertNotIn(os.path.splitext(n)[1].lower(), firmware_ext)
                    self.assertNotIn(os.path.getsize(p), (0x8000, 0x40000, 0x80000))   # partial, 19x0, 20C0 image
                    with open(p, "rb") as f:
                        b = f.read()
                    if b"\0" in b:
                        self.assertTrue(rel.startswith("assets" + os.sep) and n.endswith(".png"), rel)
                    else:
                        self.assertIsNone(VIN_LIKE.search(b.decode("utf-8", "replace")))


class TestShiftUnits(unittest.TestCase):
    def test_limits(self):
        up, down = egs_tables.shift_limits(egs_tables.RATIOS_19x0, 6656)
        self.assertEqual(up, [47, 94, 136, 195])
        self.assertEqual(down, [52, 96, 136, 192])
        # 20C0: the locked addition comes off the upshift limits
        up20, _ = egs_tables.shift_limits(egs_tables.RATIOS_19x0, 6528, adds=[4, 2, 2, 5, 0])
        self.assertEqual(up20, [42, 90, 132, 186])

    def test_manual_guard(self):
        # M holds the gear: guard 150 rpm over the hard cut, under the turbine monitor - 100 (docs 13 §7)
        R = egs_tables.RATIOS_19x0
        self.assertEqual(egs_tables.manual_guard(R, 6720, 7232)[0], [59, 108, 153, 215])
        # locked on the overrun in 2nd-4th (a 20C0 lock-up edit): still fits under 7232
        self.assertEqual(egs_tables.manual_guard(R, 6720, 7232, [0, 2, 2, 5, 0])[0], [59, 108, 153, 215])
        # 19x0 factory monitor 6720 with the factory cut 6592: no room, the monitor has to go up
        with self.assertRaises(ValueError):
            egs_tables.manual_guard(R, 6592, 6720)
        self.assertEqual(egs_tables.manual_guard(R, 6592, 6912)[0], [58, 106, 150, 211])

    def test_turbine(self):
        # 66 units in 1st: 66 * 32 * 3.665 = 7740 rpm of the turbine (an early tune's value)
        self.assertEqual(egs_tables.turbine_rpm(66, 0, egs_tables.RATIOS_19x0), 7740)
        self.assertEqual(egs_tables.turbine_rpm(41, 4, egs_tables.RATIOS_19x0), 4808)

    def test_layouts(self):
        L = egs_tables.LAYOUTS
        self.assertEqual(set(L), {0x8000, 0x40000, 0x80000})
        self.assertEqual(L[0x80000]["shift"], 0x7120E)
        self.assertEqual(L[0x80000]["zones"], [(0x70000, 0x71BC0), (0x78000, 0x7D858)])
        self.assertEqual(L[0x80000]["win"], (0x70000, 0x80000))
        self.assertEqual(L[0x80000]["manual"], (8, 10), "M = PB (k10) and PD (k08) by code (docs 11 §5)")
        self.assertEqual(L[0x40000]["manual"], (8, 10))
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(b"\0" * 1000)
            with self.assertRaises(SystemExit):
                egs_tables.FW(tmp)
        finally:
            os.remove(tmp)


class CatalogChecks:
    """Shared checks of a catalog and of the XDF files generated from it."""
    path = None
    full_xdf = None
    partial_xdf = None
    en_xdf = None
    window = None

    def setUp(self):
        self.cat = load(self.path)

    def test_check_passes(self):
        self.assertEqual(make_xdf.check(self.cat), [])

    def test_uids_unique_and_entries_inside_window(self):
        uids = [e["uid"] for e in self.cat["entries"]]
        self.assertEqual(len(uids), len(set(uids)))
        lo, hi = self.window
        for e in self.cat["entries"]:
            for s, t in make_xdf.spans(e):
                self.assertTrue(lo <= s < t <= hi, f"0x{e['uid']:X} {e['title'][:40]}: 0x{s:X}-0x{t:X}")

    def test_no_overlaps(self):
        ivs = sorted((s, t, e["uid"]) for e in self.cat["entries"] for s, t in make_xdf.spans(e))
        for i in range(len(ivs) - 1):
            self.assertLessEqual(ivs[i][1], ivs[i + 1][0], f"0x{ivs[i][2]:X} overlaps 0x{ivs[i + 1][2]:X}")

    def test_units_and_confidence(self):
        for e in self.cat["entries"]:
            self.assertTrue(e["z"].get("units"), e["title"])
            self.assertIn(e.get("confidence"), ("proven", "structure", "hypothesis", "unknown", "carried"), e["title"])
            if e["kind"] == "table":
                self.assertTrue(e["x"].get("units") and e["y"].get("units"), e["title"])

    def test_xdf_files_match_the_catalog(self):
        txt, n = make_xdf.render(self.cat)
        self.assertEqual(n, len(self.cat["entries"]))
        with open(self.full_xdf, encoding="utf-8", newline="") as f:
            self.assertEqual(f.read(), txt, f"{self.full_xdf} is not what the catalog renders: rebuild it with make_xdf.py")
        if self.partial_xdf:
            txt, n = make_xdf.render(self.cat, partial=True)
            with open(self.partial_xdf, encoding="utf-8", newline="") as f:
                self.assertEqual(f.read(), txt)
            p = self.cat["partial"]
            self.assertEqual(n, sum(1 for e in self.cat["entries"]
                                    if all(p["start"] <= s and t <= p["start"] + p["size"] for s, t in make_xdf.spans(e))))
        if self.en_xdf:
            txt, n = make_xdf.render(self.cat, en=True)
            with open(self.en_xdf, encoding="utf-8", newline="") as f:
                self.assertEqual(f.read(), txt, f"{self.en_xdf} is not what the catalog renders: rebuild it with make_xdf.py --en")

    def test_categories_one_based_in_xdf(self):
        txt, _ = make_xdf.render(self.cat)
        cats = {int(m) for m in re.findall(r'<CATEGORYMEM index="\d+" category="(\d+)"', txt)}
        self.assertTrue(cats)
        self.assertGreaterEqual(min(cats), 1)
        self.assertLessEqual(max(cats), len(self.cat["categories"]))
        self.assertEqual(txt.count("<XDFTABLE") + txt.count("<XDFCONSTANT"), len(self.cat["entries"]))

    def test_no_vin_or_serial(self):
        for p in (self.path, self.full_xdf, self.partial_xdf, self.en_xdf):
            if p:
                with open(p, encoding="utf-8") as f:
                    self.assertIsNone(VIN_LIKE.search(f.read()), p)

    def test_english_field_placement(self):
        # English goes only into these fields; everything else of the catalog stays as it is (CONTRIBUTING)
        allowed = {"root": {"title_en", "description_en", "categories_en"}, "entry": {"title_en", "description_en"},
                   "axis": {"units_en", "labels_en"}}
        cyr = re.compile("[а-яА-ЯёЁ]")

        def check(obj, level, where):
            for k, v in obj.items():
                if k.endswith("_en"):
                    self.assertIn(k, allowed[level], f"{where}: {k} is not an English field of a {level}")
                    vals = v if isinstance(v, list) else [v]
                    self.assertTrue(vals and all(isinstance(s, str) and s.strip() for s in vals), f"{where}: {k}")
                    self.assertTrue(all(not cyr.search(s) for s in vals), f"{where}: Cyrillic in {k}")
                    if k == "labels_en":
                        self.assertIsInstance(v, list, f"{where}: labels_en must be a list")
                        self.assertEqual(len(v), len(obj.get("labels") or []), where)

        check(self.cat, "root", "catalog")
        if "categories_en" in self.cat:
            self.assertEqual(len(self.cat["categories_en"]), len(self.cat["categories"]))
        for e in self.cat["entries"]:
            check(e, "entry", f"0x{e['uid']:X}")
            for ax in ("x", "y", "z"):
                if ax in e:
                    check(e[ax], "axis", f"0x{e['uid']:X}.{ax}")


class TestEnglishAxisLabels(unittest.TestCase):
    """Synthetic opt-in translations against real unchanged catalog geometry."""

    def one_table(self, path, axis_name=None):
        cat = load(path)
        entry = next(e for e in cat["entries"]
                     if e["kind"] == "table"
                     and (e[axis_name].get("labels") if axis_name else
                          any(e[a].get("labels") for a in ("x", "y"))))
        cat["entries"] = [entry]
        axis = axis_name or ("x" if entry["x"].get("labels") else "y")
        return cat, entry[axis]

    @staticmethod
    def without_label_lines(xml):
        return re.sub(r'^\s*<LABEL index="\d+" value="[^"]*" />\n', "", xml, flags=re.M)

    def test_en_selects_translated_axis_labels_without_changing_ru_or_geometry(self):
        for path in (CATALOG_19D0, CATALOG_20C0):
            for axis_name in ("x", "y"):
                with self.subTest(path=os.path.basename(path), axis=axis_name):
                    cat, axis = self.one_table(path, axis_name)
                    ru_before, n = make_xdf.render(cat)
                    en_before, _ = make_xdf.render(cat, en=True)
                    labels = axis["labels"]
                    axis["labels_en"] = ['English "quote" & text'] + [
                        f"English index {i}" for i in range(1, len(labels))]
                    self.assertEqual(make_xdf.check(cat), [])
                    ru_after, _ = make_xdf.render(cat)
                    en_after, _ = make_xdf.render(cat, en=True)
                    self.assertEqual(n, 1)
                    self.assertEqual(ru_after, ru_before)
                    self.assertNotEqual(en_after, en_before)
                    self.assertIn('value="English &quot;quote&quot; &amp; text"', en_after)
                    self.assertEqual(self.without_label_lines(en_after),
                                     self.without_label_lines(en_before))
                    self.assertNotIn('value="English &quot;quote&quot; &amp; text"', ru_after)
                    imported = make_xdf.import_xdf(en_after)
                    self.assertEqual(imported["entries"][0][axis_name]["labels"],
                                     axis["labels_en"])

    def test_fallback_without_labels_en_keeps_original_labels(self):
        # without labels_en the English file carries the labels of the Russian one, Russian text included
        for path in (CATALOG_19D0, CATALOG_20C0):
            with self.subTest(path=os.path.basename(path)):
                cat = load(path)
                entry = next(e for e in cat["entries"] if e["kind"] == "table" and any("labels_en" in e[a] for a in ("x", "y")))
                for a in ("x", "y"):
                    entry[a].pop("labels_en", None)
                cat["entries"] = [entry]
                ru = re.findall(r'<LABEL index="\d+" value="[^"]*" />', make_xdf.render(cat)[0])
                en = re.findall(r'<LABEL index="\d+" value="[^"]*" />', make_xdf.render(cat, en=True)[0])
                self.assertTrue(ru)
                self.assertEqual(en, ru)

    def test_refuse_malformed_translation_arrays(self):
        cat, axis = self.one_table(CATALOG_19D0)
        count = len(axis["labels"])
        bad_cases = [
            ["English"] * (count + 1),
            [],
            [""] + ["English"] * (count - 1),
            [" \t"] + ["English"] * (count - 1),
            ["маска"] + ["English"] * (count - 1),
            [7] + ["English"] * (count - 1),
            "English" * count,
            None,
            {"0": "English"},
        ]
        for bad in bad_cases:
            with self.subTest(bad=repr(bad)[:60]):
                axis["labels_en"] = bad
                self.assertTrue(any("labels_en" in p for p in make_xdf.check(cat)),
                                "Invalid English axis label metadata must fail closed")

    def test_translation_requires_original_labels(self):
        for original in (None, [], "not a label array"):
            with self.subTest(original=original):
                cat, axis = self.one_table(CATALOG_19D0)
                axis["labels"] = original
                axis["labels_en"] = ["English"]
                self.assertTrue(any("labels_en" in p for p in make_xdf.check(cat)))

    def test_partial_render_retains_geometry_and_russian_labels(self):
        cat, axis = self.one_table(CATALOG_19D0)
        ru_before, count = make_xdf.render(cat, partial=True)
        en_before, _ = make_xdf.render(cat, partial=True, en=True)
        self.assertEqual(count, 1)
        axis["labels_en"] = [f"English {i}" for i in range(len(axis["labels"]))]
        self.assertEqual(make_xdf.render(cat, partial=True)[0], ru_before)
        en_after, _ = make_xdf.render(cat, partial=True, en=True)
        self.assertNotEqual(en_after, en_before)
        self.assertEqual(self.without_label_lines(en_after),
                         self.without_label_lines(en_before))

    def test_invalid_cli_input_preserves_existing_output_and_creates_no_en_file(self):
        cat, axis = self.one_table(CATALOG_19D0)
        axis["labels_en"] = ["English"] * (len(axis["labels"]) + 1)
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "invalid.json")
            output = os.path.join(tmp, "existing.xdf")
            english = os.path.join(tmp, "absent_en.xdf")
            with open(source, "w", encoding="utf-8") as f:
                json.dump(cat, f, ensure_ascii=False)
            with open(output, "wb") as f:
                f.write(b"preserve existing output\n")
            result = run(os.path.join(TOOLS, "make_xdf.py"), "build", source,
                         output, "--en", english)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("labels_en", result.stdout)
            with open(output, "rb") as f:
                self.assertEqual(f.read(), b"preserve existing output\n")
            self.assertFalse(os.path.exists(english))


class TestCatalog19D0(CatalogChecks, unittest.TestCase):
    path = CATALOG_19D0
    full_xdf = os.path.join(XDF, "GS8600_19D0_Full256K.xdf")
    partial_xdf = os.path.join(XDF, "GS8600_19x0_Partial32K.xdf")
    window = (0x8000, 0x10000)

    def test_shift_matrices_and_voltage_units(self):
        z = {e["z"]["addr"]: e for e in self.cat["entries"]}
        for k in range(16):
            e = z[0x91B2 + k * 0x70 + 4 + 8 + 11]
            self.assertEqual((e["z"]["rows"], e["z"]["cols"]), (11, 8))
        for a in (0x8EE8, 0x8EEA, 0x8EF0, 0x8EFA, 0x8EFC, 0x8EFE, 0x8F00, 0x8F08, 0x8F0A, 0x8F0C, 0x8F0E):
            self.assertEqual(z[a]["z"]["units"], "мВ", hex(a))
            self.assertEqual(z[a]["kind"], "constant")
        # f21 of the automaton records is one u16 word per pointer, not a 3-point table
        f21 = [e for e in self.cat["entries"] if e["title"].startswith("[k") and " f21]" in e["title"]]
        self.assertEqual(len(f21), 9)
        self.assertTrue(all(e["kind"] == "constant" and e["z"]["bits"] == 16 for e in f21))

    def test_corrections_of_14_10_2026(self):
        u = {e["uid"]: e for e in self.cat["entries"]}
        # 0x80D0 is a list of seven zone thresholds read by 0x1651E, not a 1D table: its old "data row" holds constants
        e = u[0x1000]
        self.assertIsNone(e["x"]["addr"])
        self.assertEqual((e["z"]["addr"], e["z"]["cols"]), (0x80D2, 7))
        for a in (0x80DA, 0x80DC, 0x80DE):
            self.assertTrue(any(c["kind"] == "constant" and c["z"]["addr"] == a for c in self.cat["entries"]), hex(a))
        # converter torque ratio muGDT (pair of the 20C0 entry 0x781D6)
        mu = [c for c in self.cat["entries"] if c["z"]["addr"] == 0xE393]
        self.assertEqual(len(mu), 1)
        self.assertEqual((mu[0]["x"]["addr"], mu[0]["confidence"]), (0xE390, "proven"))
        self.assertIn("224, 230", u[0x1032]["description"])            # TCC pedal axis differs per calibration
        # readers found through the pointer slots of 0x9ADC: the "no reader" note must be gone there
        for uid in (0x102D, 0x102E, 0x102F, 0x1030, 0x1031, 0x1033, 0x1034, 0x1038):
            self.assertNotIn("не найдено", u[uid]["proof"] + u[uid]["description"], hex(uid))
            self.assertIn("pea.l $9B", u[uid]["proof"], hex(uid))


class TestCatalog20C0(CatalogChecks, unittest.TestCase):
    path = CATALOG_20C0
    full_xdf = os.path.join(XDF, "GS8604_20C0_Full512K.xdf")
    partial_xdf = None                                    # not published until the flasher's partial is checked
    en_xdf = os.path.join(XDF, "GS8604_20C0_Full512K_EN.xdf")
    window = (0x70000, 0x80000)

    def test_english_fields(self):
        cyr = re.compile("[а-яА-ЯёЁ]")
        self.assertEqual(len(self.cat["categories_en"]), len(self.cat["categories"]))
        self.assertIsNone(cyr.search(self.cat["title_en"] + self.cat["description_en"] + "".join(self.cat["categories_en"])))
        for e in self.cat["entries"]:
            for k in ("title_en", "description_en"):
                self.assertTrue(e.get(k), f"0x{e['uid']:X} {e['title'][:40]}: no {k}")
                self.assertIsNone(cyr.search(e[k]), f"0x{e['uid']:X}: {e[k][:60]}")
            for ax in ("x", "y", "z"):
                if ax in e:
                    self.assertTrue(e[ax].get("units_en"), f"0x{e['uid']:X} {ax}")
                    self.assertIsNone(cyr.search(e[ax]["units_en"]), e[ax]["units_en"])
            if e["kind"] == "table":
                for ax in ("x", "y"):
                    if any(cyr.search(s) for s in e[ax].get("labels") or []):
                        self.assertTrue(e[ax].get("labels_en"), f"0x{e['uid']:X} {ax}: Russian labels without labels_en")
        # the English XDF shows no Russian axis label
        with open(self.en_xdf, encoding="utf-8") as f:
            labels = re.findall(r'<LABEL index="\d+" value="([^"]*)" />', f.read())
        self.assertTrue(labels)
        self.assertEqual([s for s in labels if cyr.search(s)], [])

    def test_record_roles_by_code(self):
        # docs 11 §9: record fields of the 8 shift sets and of the root 0xFFFF9804 carry roles read by 20C0 code
        cats = self.cat["categories"]
        per = {}
        for e in self.cat["entries"]:
            c = cats[e["categories"][0]]
            per.setdefault(c[:2], []).append(e)
        for code in ("04", "05", "06", "07", "08", "09", "10"):
            self.assertTrue(per.get(code), code)
            for e in per[code]:
                self.assertEqual(e["confidence"], "proven", e["title"])
                self.assertRegex(e["proof"], r"код: 0x4[0-9A-F]{4}", e["title"])
        self.assertEqual(len(per["10"]), 216)                                   # root 0xFFFF9804, every object one role
        zone2 = [e for e in self.cat["entries"] if 0x78000 <= e["z"]["addr"] < 0x7D858]
        roles = sum(1 for e in zone2 if e["confidence"] == "proven")
        self.assertGreaterEqual(roles / len(zone2), 0.80)

    def test_signed_tables(self):
        # 0x78A34: 2D16 4x4 with signed axes (slip to synchronism), was typed as 1D16 4x1 before 30.09.2026
        by = {}
        for e in self.cat["entries"]:
            if e["kind"] == "table" and e["x"].get("addr") is not None:
                by[e["x"]["addr"] - (4 if e["y"].get("addr") is not None else 2)] = e
        e = by[0x78A34]
        self.assertEqual((e["x"]["count"], e["y"]["count"]), (4, 4))
        self.assertTrue(e["x"]["signed"] and e["y"]["signed"] and e["z"]["signed"])
        self.assertIn("0x43A7A", e["proof"])                                  # phase 6 reads it with X = [0x93B5], Y = [0x9338]

    def test_image_size_and_meta(self):
        self.assertEqual(self.cat["image_size"], 0x80000)
        self.assertEqual(self.cat["software"], "20C0")
        self.assertEqual(self.cat["program_sha256_0x8000_0x70000"], egs_tables.CODE_SHA256_20C0)
        self.assertEqual(self.cat["partial"]["start"], 0x70000)
        self.assertEqual(self.cat["partial"]["size"], 0x10000)

    def test_proven_entries_cite_an_instruction(self):
        for e in self.cat["entries"]:
            if e["confidence"] == "proven":
                self.assertRegex(e.get("proof", ""), r"код: 0x[0-9A-F]{5}", e["title"])
            if e["confidence"] == "structure":
                self.assertTrue(e.get("proof", "").startswith("структура:"), e["title"])

    def test_key_entries(self):
        z = {e["z"]["addr"]: e for e in self.cat["entries"]}
        for k in range(16):                              # the 16 matrices, 8x11, in output shaft rpm / 32
            e = z[0x7120E + k * 0x70 + 4 + 8 + 11]
            self.assertEqual((e["z"]["rows"], e["z"]["cols"]), (11, 8))
            self.assertEqual(e["x"]["addr"], 0x7120E + k * 0x70 + 4)
            self.assertEqual(e["z"]["units"], "об/мин вых. вала / 32")
            self.assertEqual(e["confidence"], "proven")
        self.assertEqual(z[0x70BA8]["z"]["units"], "об/мин турбины")           # turbine monitor threshold 7232
        self.assertEqual(z[0x70F40]["z"]["units"], "мВ")                        # 7.0 V, not a "turbine protection"
        self.assertEqual(z[0x7096E]["z"]["bits"], 16)                           # lockup gear mask 0x7E
        t = z[0x71996 + 4 + 30 + 9]                                             # lockup thresholds 30x9
        self.assertEqual((t["z"]["rows"], t["z"]["cols"]), (9, 30))
        t = z[0x71AD0 + 4 + 6 + 9]                                              # groups 11-12, 6x9
        self.assertEqual((t["z"]["rows"], t["z"]["cols"]), (9, 6))
        self.assertEqual((z[0x70970]["z"]["rows"], z[0x70970]["z"]["cols"]), (16, 6))
        self.assertEqual((z[0x709D0]["z"]["rows"], z[0x709D0]["z"]["cols"]), (16, 6))
        self.assertEqual((z[0x70B3C]["z"]["rows"], z[0x70B3C]["z"]["cols"]), (16, 5))


@unittest.skipUnless(STOCK and os.path.isfile(STOCK), "set GS860_STOCK to a stock 19C0/19D0 256K image")
class TestWithStock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with open(STOCK, "rb") as f:
            cls.stock = f.read()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_stock_checksums(self):
        self.assertTrue(gs860_crc.check_file(STOCK, verbose=False))

    def test_layout_and_info(self):
        fw = egs_tables.FW(STOCK)
        self.assertEqual(fw.N, 0x40000)
        self.assertEqual(fw.sha256(*fw.L["code"]), egs_tables.CODE_SHA256_19x0)
        self.assertEqual(len(fw.tile()), 536)
        self.assertEqual(sum(1 for t in fw.shift_matrices() if t), 16)
        r = run(os.path.join(TOOLS, "egs_tables.py"), "info", STOCK)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("(ok)", r.stdout)

    def test_catalog_axes_read_from_the_image(self):
        # every table of the 19D0 catalog with an axis in the image reads a strictly increasing axis.
        # Entries carried from the v2.1 XDF without re-checking are left out: some record fields there
        # (f02, f04, f05, f06, f50, f01, f44 of the automaton records) carry the wrong element width
        # (handed over 25.09.2026, not yet corrected), and this test must not hide that behind a skip.
        fw = egs_tables.FW(STOCK)
        for e in load(CATALOG_19D0)["entries"]:
            if e["kind"] != "table" or e.get("confidence") == "carried":
                continue
            for ax in ("x", "y"):
                a = e[ax]
                if a.get("addr") is None or a["count"] < 2:
                    continue
                rd = fw.u8 if a["bits"] == 8 else fw.u16
                vals = [rd(a["addr"] + a["bits"] // 8 * i) for i in range(a["count"])]
                if a.get("signed"):
                    top = 1 << a["bits"]
                    vals = [v - top if v >= top // 2 else v for v in vals]
                self.assertEqual(vals, sorted(set(vals)), f"0x{e['uid']:X} {e['title'][:40]} axis {ax}")

    def test_arrays_and_converter_ratio_in_the_image(self):
        b = self.stock
        u16 = lambda a: int.from_bytes(b[a:a + 2], "big")
        # [u16 count] headers of the arrays the code indexes as base + 2 + index (or + 4 for two counts)
        self.assertEqual((u16(0x80D0), u16(0x80EA), u16(0x88F0), u16(0x831A), u16(0x8322)), (7, 7, 7, 4, 4))
        self.assertEqual((u16(0x8FAA), u16(0x8FAC)), (3, 21))
        thr = list(b[0x80D2:0x80D9])
        self.assertEqual(thr, sorted(set(thr)))
        self.assertEqual(thr[-1], 255)
        # muGDT 0xE38E: [u16 3], slip axis ending at 255, 100 % at the coupling point, rising to the stall value
        self.assertEqual(u16(0xE38E), 3)
        x, z = list(b[0xE390:0xE393]), list(b[0xE393:0xE396])
        self.assertEqual((x, x[-1]), (sorted(set(x)), 255))
        self.assertEqual(z[0], 100)
        self.assertEqual(z, sorted(z))


@unittest.skipUnless(STOCK20 and os.path.isfile(STOCK20), "set GS8604_STOCK to a factory 20C0 512K image")
class TestWithStock20C0(unittest.TestCase):
    """The 20C0 layout against a factory image (docs 11)."""

    @classmethod
    def setUpClass(cls):
        cls.fw = egs_tables.FW(STOCK20)
        cls.cat = load(CATALOG_20C0)

    def test_checksums(self):
        self.assertTrue(gs860_crc.check_file(STOCK20, verbose=False))
        rows = gs860_crc.sums(self.fw.d)
        self.assertEqual([r[0] for r in rows], ["loader", "program", "calibration"])

    def test_layout(self):
        fw = self.fw
        self.assertEqual(fw.N, 0x80000)
        self.assertTrue(fw.is_20c0)
        self.assertEqual(fw.sha256(0x8000, 0x70000), egs_tables.CODE_SHA256_20C0)
        self.assertEqual(bytes(fw.d[0x6FF7C:0x6FF88]), b"B223K_0520C0")
        self.assertEqual(len(fw.tile()), 614)
        self.assertEqual(fw.ratios(), (3.665, 1.999, 1.407, 1.0, 0.742))
        # the pointer catalog: 43 slots, every one inside the calibration, then 0xFF
        slots = [fw.u32(0x71BC2 + 4 * k) for k in range(43)]
        self.assertTrue(all(0x70000 <= p < 0x71C72 for p in slots))
        self.assertEqual(fw.u32(0x71C6E), 0xFFFFFFFF)
        self.assertEqual(slots[14:30], [0x7120E + k * 0x70 for k in range(16)])

    def test_shift_matrices(self):
        fw = self.fw
        ms = fw.shift_matrices()
        self.assertEqual(len(ms), 16)
        self.assertTrue(all(t and t["kind"] == "2D8" and t["nx"] == 8 and t["ny"] == 11 for t in ms))
        xs, ys, data, da, w = fw.read_table(ms[10])
        self.assertEqual(da, 0x71225 + 10 * 0x70)
        self.assertEqual(ys, [0, 33, 59, 84, 113, 141, 170, 205, 240, 254, 255])
        self.assertEqual(data[-1], [44, 102, 151, 211, 41, 93, 138, 203])      # PB, kickdown row (docs 11 §4)
        self.assertEqual(egs_tables.turbine_rpm(102, 1, fw.ratios()), 6525)
        roles = {p["index"]: p["role"] for p in egs_tables.classify_programs(fw)}
        self.assertEqual(roles[12], "2nd-only")
        self.assertEqual(roles[13], "winter")
        self.assertTrue(egs_tables.verify_shift(fw, 6500, 6600))                # runs; findings are advisory here

    def test_constants(self):
        fw = self.fw
        self.assertEqual(fw.u16(0x70BA8), 7232)                                 # turbine monitor
        self.assertEqual(fw.u16(0x7096E), 0x7E)                                 # lockup gear mask
        self.assertEqual((fw.u16(0x70F40), fw.u16(0x70F46)), (7000, 1500))      # voltage monitor, mV
        self.assertEqual(fw.d[0x70302], 36)                                     # pulses per rev, channel 0
        self.assertEqual((fw.d[0x70FC4], fw.d[0x70FC5]), (9, 1))                # output shaft filter
        self.assertEqual((fw.d[0x70966], fw.d[0x70967]), (0x0B, 0x03))          # gate program codes
        self.assertEqual(list(fw.d[0x70B98:0x70B9E]), [4, 2, 2, 5, 0, 4])       # upshift threshold addition
        t = fw.try_table(0x71996)
        self.assertEqual((t["kind"], t["nx"], t["ny"]), ("2D8", 30, 9))
        t = fw.try_table(0x71AD0)
        self.assertEqual((t["kind"], t["nx"], t["ny"]), ("2D8", 6, 9))

    def test_catalog_against_the_image(self):
        # every table of the catalog with an axis in the image reads a strictly increasing axis,
        # every headed table starts with its own dimensions
        fw = self.fw
        for e in self.cat["entries"]:
            if e["kind"] != "table":
                continue
            for ax in ("x", "y"):
                a = e[ax]
                if a.get("addr") is None or a["count"] < 2:
                    continue
                rd = fw.u8 if a["bits"] == 8 else fw.u16
                vals = [rd(a["addr"] + a["bits"] // 8 * i) for i in range(a["count"])]
                if a.get("signed"):
                    top = 1 << a["bits"]
                    vals = [v - top if v >= top // 2 else v for v in vals]
                self.assertEqual(vals, sorted(set(vals)), f"0x{e['uid']:X} {e['title'][:40]} axis {ax}")
            if e["x"].get("addr") is not None:
                hdr = e["x"]["addr"] - (4 if e["y"].get("addr") is not None else 2)
                self.assertEqual(fw.u16(hdr), e["x"]["count"], f"0x{e['uid']:X} {e['title'][:40]}: nx")
                if e["y"].get("addr") is not None:
                    self.assertEqual(fw.u16(hdr + 2), e["y"]["count"], f"0x{e['uid']:X}: ny")

    def test_cli(self):
        for args in (("info", STOCK20), ("shift", STOCK20, "--turbine"), ("programs", STOCK20),
                     ("verify-shift", STOCK20, "--spark", "6500", "--cut", "6600"), ("dump", STOCK20, "0x71996")):
            r = run(os.path.join(TOOLS, "egs_tables.py"), *args)
            self.assertIn(r.returncode, (0, 1), args)          # verify-shift returns 1 on findings
            self.assertNotIn("Traceback", r.stderr, args)
        r = run(os.path.join(TOOLS, "egs_tables.py"), "info", STOCK20)
        self.assertIn("== 20C0 reference", r.stdout)
        self.assertIn("614 (ok)", r.stdout)


if __name__ == "__main__":
    unittest.main()
