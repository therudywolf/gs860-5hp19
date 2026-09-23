#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-tests of the tools. Part of the GS8.60.0 community repository. License: MIT.

  python3 -m unittest discover -s tests -v
  GS860_STOCK=/path/to/stock_19C0_or_19D0_256K.bin python3 -m unittest discover -s tests -v

Without GS860_STOCK only the tests that need no firmware run (the repository holds no
images). With it (the stock calibration the recipes were built from, recipes/README),
every recipe is applied to that image and the result is checked: checksums, the
recipe's reference hashes, the shift-point rules of doc 02 §4 and a make_recipe round trip.
"""
import hashlib, json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
RECIPES = os.path.join(ROOT, "recipes")
sys.path.insert(0, TOOLS)

import gs860_crc                                    # noqa: E402
import egs_tables                                   # noqa: E402

STOCK = os.environ.get("GS860_STOCK")
PRESET_SPARK, PRESET_CUT = 6656, 6784               # the engine the presets are built for (recipes/README)


def recipes():
    return sorted(os.path.join(RECIPES, n) for n in os.listdir(RECIPES)
                  if n.endswith(".json") and not n.endswith(".annotations.json"))


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=ROOT)


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

    def test_recipes_never_carry_the_checksum(self):
        for p in recipes():
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
            self.assertIn(rec["schema"], ("gs860-recipe/1", "gs860-recipe/2"), p)
            for e in rec.get("bytes", []):
                a = int(e["addr"], 16)
                end = a + e["count"] * e["width"] // 8
                self.assertFalse(a < 0x10000 and end > 0xFFFE, f"{p}: {e['addr']} covers 0xFFFE")


class TestShiftUnits(unittest.TestCase):
    def test_limits(self):
        up, down = egs_tables.shift_limits(egs_tables.RATIOS_19x0, PRESET_SPARK)
        self.assertEqual(up, [47, 94, 136, 195])
        self.assertEqual(down, [52, 96, 136, 192])
        self.assertEqual(egs_tables.overrun_guard(egs_tables.RATIOS_19x0, PRESET_CUT), [58, 106, 151, 212])

    def test_turbine(self):
        # 66 units in 1st: 66 * 32 * 3.665 = 7740 rpm of the turbine (the 16.09 preset value)
        self.assertEqual(egs_tables.turbine_rpm(66, 0, egs_tables.RATIOS_19x0), 7740)
        self.assertEqual(egs_tables.turbine_rpm(41, 4, egs_tables.RATIOS_19x0), 4808)


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

    def test_recipes(self):
        cal_sha = hashlib.sha256(self.stock[0x8000:0x10000]).hexdigest()
        for p in recipes():
            with self.subTest(recipe=os.path.basename(p)):
                with open(p, encoding="utf-8") as f:
                    rec = json.load(f)
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
                found = egs_tables.verify_shift(fw, PRESET_SPARK, PRESET_CUT, stock=st)
                errors = [f for f in found if f[0] == "ERROR" and not f[8]]
                self.assertEqual(errors, [], f"{p}: {errors[:3]}")
                # make_recipe round trip gives the same diff
                again = out[:-4] + ".again.json"
                r = run(os.path.join(TOOLS, "make_recipe.py"), STOCK, out, "-o", again)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                with open(again, encoding="utf-8") as f:
                    rec2 = json.load(f)
                strip = lambda es: [{k: v for k, v in e.items() if k not in ("group", "name", "comment")} for e in es]
                self.assertEqual(strip(rec2["tables"]), strip(rec["tables"]))
                self.assertEqual(strip(rec2["bytes"]), strip(rec["bytes"]))


if __name__ == "__main__":
    unittest.main()
