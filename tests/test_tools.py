#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-tests of the tools. Part of the GS8.60.0 community repository. License: MIT.

  python3 tests/test_tools.py
  python3 -m unittest discover -s tests -v
  GS860_STOCK=/path/to/stock_19C0_or_19D0_256K.bin GS8604_STOCK=/path/to/stock_20C0_512K.bin python3 tests/test_tools.py

Without images only the tests that need no firmware run (the repository holds no images): the
CRC algorithm, the shift-point rules, both catalogs (catalog/gs8600_19d0.json, catalog/gs8604_20c0.json)
and the XDF files generated from them. With GS860_STOCK (the stock calibration the recipes were built
from, recipes/README) every recipe is applied to that image and the result is checked: checksums, the
recipe's reference hashes, the shift-point rules of doc 02 §4 and a make_recipe round trip. With
GS8604_STOCK (a factory 20C0 image) the 20C0 layout of egs_tables, the three sums and every table of
the 20C0 catalog are checked against the image.
"""
import hashlib, json, os, re, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
RECIPES = os.path.join(ROOT, "recipes")
CATALOG_19D0 = os.path.join(ROOT, "catalog", "gs8600_19d0.json")
CATALOG_20C0 = os.path.join(ROOT, "catalog", "gs8604_20c0.json")
XDF = os.path.join(ROOT, "xdf")
sys.path.insert(0, TOOLS)

import gs860_crc                                    # noqa: E402
import egs_tables                                   # noqa: E402
import egs_patch                                    # noqa: E402
import make_xdf                                     # noqa: E402

STOCK = os.environ.get("GS860_STOCK")
STOCK20 = os.environ.get("GS8604_STOCK")
PRESET_SPARK, PRESET_CUT = 6656, 6784               # the engine the presets are built for (recipes/README)
VIN_LIKE = re.compile(r"W(BA|BS|AP)[A-Z0-9]{14}")    # nothing that looks like a VIN may be in the repository


def recipes(platform=None):
    """Recipe files; platform '19x0' or '20C0' filters by the base image (old recipes carry no platform: 19x0)."""
    out = sorted(os.path.join(RECIPES, n) for n in os.listdir(RECIPES)
                 if n.endswith(".json") and not n.endswith(".annotations.json"))
    return [p for p in out if platform is None or load(p)["base"].get("platform", "19x0") == platform]


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

    def test_recipes_never_carry_the_checksum(self):
        for p in recipes():
            rec = load(p)
            self.assertIn(rec["schema"], ("gs860-recipe/1", "gs860-recipe/2"), p)
            crc = 0x7FFFE if rec["base"].get("platform") == "20C0" else 0xFFFE
            for e in rec.get("bytes", []):
                a = int(e["addr"], 16)
                end = a + e["count"] * e["width"] // 8
                self.assertFalse(a < crc + 2 and end > crc, f"{p}: {e['addr']} covers 0x{crc:05X}")


class TestRepository(unittest.TestCase):
    def test_every_tool_has_help(self):
        for n in sorted(os.listdir(TOOLS)):
            if n.endswith(".py"):
                with self.subTest(tool=n):
                    r = run(os.path.join(TOOLS, n), "--help")
                    self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                    self.assertIn("Example", r.stdout)

    def test_recipes_carry_status(self):
        # every preset says it is not road-tested; the old 19x0 presets (doc 08 §6) also what they really change,
        # the presets built by egs_patch.py carry their patch chain (docs 13, 14)
        for p in recipes():
            with self.subTest(recipe=os.path.basename(p)):
                rec = load(p)
                st = rec.get("status", {})
                self.assertTrue(st.get("en") and st.get("ru"), p)
                self.assertIn("not road-tested", st["en"].lower().replace("not road-tested on", "not road-tested"))
                if "built_with" in rec:
                    chain = rec["built_with"]["chain"]
                    self.assertTrue(chain and all(c.split(":")[0] in egs_patch.PATCHES for c in chain), chain)
                    self.assertTrue(all("group" in e for e in rec["tables"] + rec["bytes"]), p)
                else:
                    self.assertIn("AGS", st["en"])
                    self.assertEqual(load(p[:-5] + ".annotations.json")["meta"].get("status"), st)


class TestShiftUnits(unittest.TestCase):
    def test_limits(self):
        up, down = egs_tables.shift_limits(egs_tables.RATIOS_19x0, PRESET_SPARK)
        self.assertEqual(up, [47, 94, 136, 195])
        self.assertEqual(down, [52, 96, 136, 192])
        # 20C0: the locked addition comes off the upshift limits
        up20, _ = egs_tables.shift_limits(egs_tables.RATIOS_19x0, 6528, adds=[4, 2, 2, 5, 0])
        self.assertEqual(up20, [42, 90, 132, 186])

    def test_manual_guard(self):
        # M holds the gear: guard 150 rpm over the hard cut, under the turbine monitor - 100 (docs 13 §7)
        R = egs_tables.RATIOS_19x0
        self.assertEqual(egs_tables.manual_guard(R, 6720, 7232)[0], [59, 108, 153, 215])
        # locked on the overrun in 2nd-4th (20C0 tcc-lock): still fits under 7232
        self.assertEqual(egs_tables.manual_guard(R, 6720, 7232, [0, 2, 2, 5, 0])[0], [59, 108, 153, 215])
        # 19x0 factory monitor 6720 with the factory cut 6592: no room, the monitor has to go up
        with self.assertRaises(ValueError):
            egs_tables.manual_guard(R, 6592, 6720)
        self.assertEqual(egs_tables.manual_guard(R, 6592, 6912)[0], [58, 106, 150, 211])

    def test_turbine(self):
        # 66 units in 1st: 66 * 32 * 3.665 = 7740 rpm of the turbine (the 16.09 preset value)
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

    def test_recipes(self):
        cal_sha = hashlib.sha256(self.stock[0x8000:0x10000]).hexdigest()
        for p in recipes("19x0"):
            with self.subTest(recipe=os.path.basename(p)):
                rec = load(p)
                if cal_sha != rec["base"]["stock_calibration_sha256"]:
                    self.skipTest("the image is not the stock calibration the recipes were built from "
                                  f"(label {self.stock[0xFFCE:0xFFDE].decode('latin1')})")
                out = os.path.join(self.tmp.name, os.path.basename(p)[:-5] + ".bin")
                r = run(os.path.join(TOOLS, "apply_recipe.py"), p, STOCK, "-o", out)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertTrue(gs860_crc.check_file(out, verbose=False))
                with open(out, "rb") as f:
                    d = f.read()
                self.assertEqual(d[:0x8000], self.stock[:0x8000])
                self.assertEqual(d[0x10000:], self.stock[0x10000:])
                if rec["schema"] == "gs860-recipe/2":
                    self.assertEqual(hashlib.sha256(d).hexdigest(), rec["result"]["full_sha256"])
                    self.assertEqual(hashlib.sha256(d[0x8000:0x10000]).hexdigest(), rec["result"]["partial_sha256"])
                # shift points of the result against doc 02 §4, cells equal to stock are the factory's
                fw, st = egs_tables.FW(out), egs_tables.FW(STOCK)
                bw = rec.get("built_with")
                spark, cut = (bw["spark"], bw["cut"]) if bw else (PRESET_SPARK, PRESET_CUT)
                found = egs_tables.verify_shift(fw, spark, cut, stock=st)
                errors = [f for f in found if f[0] == "ERROR" and not f[8]]
                if bw:
                    self.assertEqual(errors, [], f"{p}: {errors[:3]}")
                else:
                    # the old presets: only their manual thresholds 58/106/151/212 are known to sit above the
                    # factory turbine monitor 6720 (doc 08 §6); nothing else may be an error
                    self.assertEqual([f for f in errors if not (f[2] == "manual" and "turbine monitor" in f[7])], [],
                                     f"{p}: {errors[:3]}")
                # make_recipe round trip gives the same diff
                again = out[:-4] + ".again.json"
                r = run(os.path.join(TOOLS, "make_recipe.py"), STOCK, out, "-o", again)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                rec2 = load(again)
                strip = lambda es: [{k: v for k, v in e.items() if k not in ("group", "name", "comment")} for e in es]
                self.assertEqual(strip(rec2["tables"]), strip(rec["tables"]))
                self.assertEqual(strip(rec2["bytes"]), strip(rec["bytes"]))


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


class TestPatchesOffline(unittest.TestCase):
    """egs_patch.py without images: the code it adds, the threshold rules, the preset chains."""

    def test_first_gear_code_is_the_v41_routine(self):
        code = egs_patch.first_gear_code(0x3E3A0, 0x3E380)
        self.assertEqual(code.hex(), "207c0000897ad1c01c2800041039ffff91af0c00000167060c00000666141039ffff91a0"
                                     "0240000f207c0003e3801c3000004e75")

    def test_threshold_rules(self):
        # tcc-lock: the WOLF4X v25 groups 6-9 (2nd-5th) before the factory cap
        self.assertEqual([egs_patch.lock_trip(1600, g) for g in (2, 3, 4)], [(17, 19, 25), (24, 27, 36), (34, 38, 50)])
        # tcc-first: the WOLF4X v41 rows for S/M (group 5) and D (group 10), pedal axis of 19x0, coast on
        ys = [0, 5, 46, 59, 72, 97, 122]
        self.assertEqual(egs_patch.first_rows(ys, 1760, True),
                         [(11, 13, 15)] * 3 + [(12, 14, 16), (13, 15, 18), (14, 17, 20), (15, 18, 21)])
        self.assertEqual(egs_patch.first_rows(ys, 2110, True, d=True),
                         [(12, 15, 18)] * 3 + [(13, 16, 19), (14, 17, 21), (15, 18, 22), (16, 19, 23)])
        # coast off: no lock with the pedal released
        self.assertEqual(egs_patch.first_rows(ys, 1760, False)[:2], [(202, 202, 202)] * 2)

    def test_s_sport_weight(self):
        w = egs_patch.s_sport_weight
        self.assertEqual([w(y) for y in (0, 46, 60, 243, 255)], [0.0] * 5)
        self.assertEqual([round(w(y), 2) for y in (83, 121, 160, 198, 203)], [0.20, 0.35, 0.50, 0.65, 0.67])
        self.assertTrue(0.20 < w(100) < 0.35 and w(242) > w(203))

    def test_presets_and_parsing(self):
        for name, pr in egs_patch.PRESETS.items():
            for c in pr["chain"]:
                self.assertIn(egs_patch.parse_patch(c)[0], egs_patch.PATCHES, (name, c))
            self.assertTrue(pr["en"] and pr["ru"])
        self.assertEqual(egs_patch.parse_patch("tcc-first:modes=S+M,rpm=1800"), ("tcc-first", {"modes": "S+M", "rpm": "1800"}))
        with self.assertRaises(egs_patch.PatchError):
            egs_patch.parse_patch("no-such-patch")
        with self.assertRaises(egs_patch.PatchError):
            egs_patch.parse_modes("S")
        self.assertEqual(set(egs_patch.PATCH_TEXT), set(egs_patch.PATCHES) - {"gate"} | {"gate"})


def patch_checks(tc, src, out, P):
    """Common checks of an egs_patch output: sums, loader, only calibration (and the declared 19x0 code) changed."""
    with open(src, "rb") as f:
        a = f.read()
    with open(out, "rb") as f:
        b = f.read()
    tc.assertTrue(gs860_crc.check_file(out, verbose=False))
    tc.assertEqual(a[:0x4400], b[:0x4400])
    lo, hi = P["cal"]
    code = set()
    if P["first_hook"]:
        H = P["first_hook"]
        code = set(range(H["at"], H["at"] + 12)) | set(range(*H["free"]))
    sums = {at + k for *_, at, _st, _c in gs860_crc.sums(b) for k in (0, 1)}
    bad = [i for i in range(len(a)) if a[i] != b[i] and not (lo <= i < hi) and i not in code and i not in sums]
    tc.assertEqual(bad, [], [hex(i) for i in bad[:5]])
    return a, b


@unittest.skipUnless(STOCK and os.path.isfile(STOCK), "set GS860_STOCK to a stock 19C0/19D0 256K image")
class TestPatches19x0(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def apply(self, *patches, extra=()):
        out = os.path.join(self.tmp.name, "p%d.bin" % len(os.listdir(self.tmp.name)))
        r = run(os.path.join(TOOLS, "egs_patch.py"), "apply", STOCK, "-o", out, *extra, *patches)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return patch_checks(self, STOCK, out, egs_patch.PLAT["19x0"])

    def test_each_patch(self):
        a, b = self.apply("no-warmup")
        self.assertEqual(b[0x8B48], 0)
        a, b = self.apply("no-kickdown")
        self.assertEqual((b[0x8D1A], b[0x8246]), (0, 255))
        a, b = self.apply("s-no5", extra=("--spark", "6496"))
        self.assertEqual(b[0x887D], 0xC1)
        a, b = self.apply("tcc-lock")
        self.assertEqual([list(b[0x897E + 4 * p:0x897E + 4 * p + 4]) for p in (2, 3, 0xB, 0xD)], [[6, 7, 8, 9]] * 4)
        a, b = self.apply("tcc-first:modes=D+S+M,coast=1")
        self.assertEqual(b[0x8978:0x897A], b"\x00\x7e")
        self.assertEqual(b[0x290A0:0x290AC].hex(), "4eb90003e3a04e714e714e71")
        self.assertEqual(list(b[0x3E380:0x3E390]), [10, 10, 5, 5, 0, 0, 0, 0, 0, 0, 0, 5, 0, 5, 0, 0])
        r = run(os.path.join(TOOLS, "egs_patch.py"), "apply", STOCK, "-o", os.path.join(self.tmp.name, "x.bin"),
                "--cut", "6592", "manual-hold")
        self.assertEqual(r.returncode, 2, "the factory monitor 6720 leaves no room above 6592: must stop")
        a, b = self.apply("manual-hold:monitor=auto", extra=("--cut", "6592"))
        self.assertEqual((b[0x8B44] << 8) | b[0x8B45], 6912)

    def test_s_sport_and_no_shift_feel(self):
        stock = egs_tables.FW(STOCK)
        r = run(os.path.join(TOOLS, "egs_patch.py"), "apply", STOCK, "-o", os.path.join(self.tmp.name, "ss.bin"),
                "--spark", "6496", "--cut", "6592", "s-no5", "shift-wot:modes=S", "s-sport")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        fw = egs_tables.FW(os.path.join(self.tmp.name, "ss.bin"))
        found = egs_tables.verify_shift(fw, 6496, 6592, stock=stock)
        self.assertEqual([f for f in found if not f[8]], [])
        r = run(os.path.join(TOOLS, "egs_patch.py"), "apply", STOCK, "-o", os.path.join(self.tmp.name, "sf.bin"), "shift-feel")
        self.assertEqual(r.returncode, 2, "shift-feel is 20C0 only")

    def test_presets_pass_the_shift_rules(self):
        st = egs_tables.FW(STOCK)
        for name in egs_patch.PRESETS:
            with self.subTest(preset=name):
                out = os.path.join(self.tmp.name, name + ".bin")
                r = run(os.path.join(TOOLS, "egs_patch.py"), "preset", name, STOCK, "-o", out)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                patch_checks(self, STOCK, out, egs_patch.PLAT["19x0"])
                ref = egs_patch.PLAT["19x0"]["ref_engine"]
                found = egs_tables.verify_shift(egs_tables.FW(out), ref["spark"], ref["cut"], stock=st)
                self.assertEqual([f for f in found if not f[8]], [], name)


@unittest.skipUnless(STOCK20 and os.path.isfile(STOCK20), "set GS8604_STOCK to a factory 20C0 512K image")
class TestPatches20C0(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with open(STOCK20, "rb") as f:
            cls.stock = f.read()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_s_sport_and_shift_feel(self):
        out = os.path.join(self.tmp.name, "feel.bin")
        r = run(os.path.join(TOOLS, "egs_patch.py"), "apply", STOCK20, "-o", out, "--spark", "6560", "--cut", "6720",
                "gate:mode=S", "s-no5", "shift-wot:modes=S", "s-sport", "shift-feel")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        a, b = patch_checks(self, STOCK20, out, egs_patch.PLAT["20C0"])
        # S (k11 = 0x716F5, 11 rows x 8) is livelier below full throttle, never above its own full-throttle row, downshifts under upshifts
        for base in (0x716F5, 0x718B5):
            for r_ in range(11):
                ro = a[base + r_ * 8:base + r_ * 8 + 8]
                rn = b[base + r_ * 8:base + r_ * 8 + 8]
                y = (0, 46, 83, 121, 160, 198, 203, 243, 244, 254, 255)[r_]
                if 83 <= y <= 203:
                    for c in range(3):
                        self.assertTrue(ro[c] <= rn[c] <= b[base + 7 * 8 + c], (hex(base), y, c))
                        self.assertLessEqual(rn[4 + c], rn[c] - 6)
                if y in (0, 46):
                    self.assertEqual((ro[:3], ro[4:7]), (rn[:3], rn[4:7]))
        # D (k14, 0x71845) is untouched
        self.assertEqual(a[0x71845:0x71845 + 88], b[0x71845:0x71845 + 88])
        # shift-feel: light row x1.20, heavy row x0.80 (not below 28), garage shifts (0x7B726 / 0x7B73A) untouched
        self.assertEqual(list(b[0x7B712:0x7B712 + 3]), [round(a[0x7B712] * 1.2), round(a[0x7B713] * 1.2), round(a[0x7B714] * 1.2)])
        self.assertEqual(b[0x7B712 + 6], max(28, round(a[0x7B712 + 6] * 0.8)))
        self.assertEqual(a[0x7B726:0x7B726 + 9], b[0x7B726:0x7B726 + 9])
        self.assertEqual(a[0x7B73A:0x7B73A + 9], b[0x7B73A:0x7B73A + 9])
        # the on-coming pressure rises only on the upper torque rows; the first three rows are untouched
        self.assertEqual(a[0x784DA:0x784DA + 24], b[0x784DA:0x784DA + 24])
        self.assertGreater(sum(b[0x784DA + 24:0x784DA + 80]), sum(a[0x784DA + 24:0x784DA + 80]))
        self.assertEqual(b[0x7B94D], round(a[0x7B94D] * 1.10))
        found = egs_tables.verify_shift(egs_tables.FW(out), 6560, 6720, stock=egs_tables.FW(STOCK20))
        self.assertEqual([f for f in found if not f[8]], [])
        # parameters are checked
        r = run(os.path.join(TOOLS, "egs_patch.py"), "apply", STOCK20, "-o", os.path.join(self.tmp.name, "bad.bin"), "shift-feel:up_hard=0.2")
        self.assertEqual(r.returncode, 2)

    def test_presets_and_recipes(self):
        st = egs_tables.FW(STOCK20)
        ref = egs_patch.PLAT["20C0"]["ref_engine"]
        for name in egs_patch.PRESETS:
            with self.subTest(preset=name):
                out = os.path.join(self.tmp.name, name + ".bin")
                r = run(os.path.join(TOOLS, "egs_patch.py"), "preset", name, STOCK20, "-o", out)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                a, b = patch_checks(self, STOCK20, out, egs_patch.PLAT["20C0"])
                found = egs_tables.verify_shift(egs_tables.FW(out), ref["spark"], ref["cut"], stock=st)
                self.assertEqual([f for f in found if not f[8]], [], name)
                self.assertEqual(b[0x70966], 0xFE)                       # gate: S first
                # the recipe of the preset reproduces it byte for byte
                rj = os.path.join(self.tmp.name, name + ".json")
                r = run(os.path.join(TOOLS, "egs_patch.py"), "recipe", name, STOCK20, "-o", rj)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                ob = os.path.join(self.tmp.name, name + "_r.bin")
                r = run(os.path.join(TOOLS, "apply_recipe.py"), rj, STOCK20, "-o", ob)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                with open(ob, "rb") as f:
                    self.assertEqual(f.read(), b)

    def test_published_recipes(self):
        cal = hashlib.sha256(self.stock[0x70000:0x80000]).hexdigest()
        for p in recipes("20C0"):
            with self.subTest(recipe=os.path.basename(p)):
                rec = load(p)
                if cal != rec["base"]["stock_calibration_sha256"]:
                    self.skipTest("the image is not the calibration the 20C0 recipes were built from")
                out = os.path.join(self.tmp.name, os.path.basename(p)[:-5] + ".bin")
                r = run(os.path.join(TOOLS, "apply_recipe.py"), p, STOCK20, "-o", out)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                with open(out, "rb") as f:
                    d = f.read()
                self.assertEqual(d[:0x70000], self.stock[:0x70000])
                self.assertEqual(hashlib.sha256(d[0x70000:0x80000]).hexdigest(), rec["result"]["calibration_window_sha256"])
                bw = rec["built_with"]
                found = egs_tables.verify_shift(egs_tables.FW(out), bw["spark"], bw["cut"], stock=egs_tables.FW(STOCK20))
                self.assertEqual([f for f in found if f[0] == "ERROR" and not f[8]], [])
                again = out[:-4] + ".again.json"
                r = run(os.path.join(TOOLS, "make_recipe.py"), STOCK20, out, "-o", again)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                strip = lambda es: [{k: v for k, v in e.items() if k not in ("group", "name", "comment")} for e in es]
                self.assertEqual(strip(load(again)["tables"]), strip(rec["tables"]))
                self.assertEqual(strip(load(again)["bytes"]), strip(rec["bytes"]))


if __name__ == "__main__":
    unittest.main()
