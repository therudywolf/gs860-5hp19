# 07 · Reading a dump and flashing

EGS GS8.60.0 (256 KB) only. The tool used in the project was MS4X Flasher (see the ms4x.net wiki) with an FT232R K-line cable; other flashers that support GS8.60 should work with the same files. This is not a flasher manual — it is what you need to know about the **files** and the **order**.

## 1. Two file formats

| Format | Size | Contents | When |
|---|---|---|---|
| **Full** | 262,144 bytes | whole image: boot loader, identification, calibration, code | reading a dump — the only way; flashing — if the whole image must be restored |
| **Partial** | 32,768 bytes | calibration window `0x8000–0x10000`; file offset = image address − 0x8000 | **flashing — the default** |

In this repository's builds everything outside the `0x8000–0x10000` window is byte-identical to the original dump, so Full and Partial give the same result. Partial is safer: a power loss mid-write only corrupts the calibration, which a repeat write fixes; a power loss during a Full write can hit the boot loader.

`tools/apply_recipe.py` writes both files: `out.bin` and `out_partial32k.bin`. `tools/egs_tables.py info` shows size, SHA-256, code hash, calibration label and checksums of either, `tools/gs860_crc.py check` checks the checksums alone.

## 2. Conditions

- battery on a charger (not paranoia: the ECU monitors its supply voltage, doc 05 §1);
- ignition ON, engine OFF;
- cable connected before the flasher starts, not touched until the write finishes;
- laptop on mains power.

## 3. Order

1. **Read a Full dump** and store it safely under a name with version and size. Dumps are never overwritten — they are the only real roll-back point.
2. Check the dump: `python3 tools/egs_tables.py info dump.bin` — size 262144, code hash `e151733e…` (= 19C0/19D0), 536 tables in the zone, all three checksums ok. If the code hash differs or there are not 536 tables, it is different software and **documents 01–09, the recipes and the 19D0 XDF do not apply to it** (a 512 KB image with code hash `28d92179…` is the GS8.60.4 20C0, which has its own catalog, XDF and document 11). If the loader or program checksum does not match, the read is damaged: read again.
3. If the flasher can read a Partial separately, read it too and verify that it is byte-identical to the `0x8000–0xFFFF` slice of the full dump. If not, this version lays out its calibration differently and you must stop.
4. Build the file: `python3 tools/apply_recipe.py recipes/<recipe>.json dump.bin -o build.bin` (doc 08). The tool refuses to write if the code does not match or if table axes do not match, and warns if old values do not match (a different base calibration — read doc 08 §4 before `--force`).
5. Verify the SHA-256 of the built file against the build log (`build.log`) and the checksums: `python3 tools/gs860_crc.py check build.bin build_partial32k.bin`. If either does not match — do not flash.
6. Flash the **Partial**.
7. After writing — **Reset Adaptation** with a diagnostic tool. Mandatory: pressure/fill-time adaptations (`0xFFFF9480…`, `0xFFFF965E`, `0xFFFF9668`) were accumulated against the old calibration.
8. First drives — with a log (doc 06 §4).

## 4. Roll-back

Original Full dump → Partial slice `0x8000–0x10000` (or Full) → Reset Adaptation.

## 5. What a dump contains

A full dump carries identifiers of the **specific unit**: block 0x5FB6 with a 12-character string of the form `BX…` (looks like a serial number), programming history records 0x6002–0x605B (hypothesis), and the ECU's EEPROM (DS2 segment 3, 256 bytes — not part of the flash dump but readable) may contain the VIN. **Do not post full dumps publicly**; for exchanging calibrations a Partial or a recipe is enough (doc 08, CONTRIBUTING).

## 6. Checksum

Found 23.09.2026 in the handler of DS2 command `0x0A` (`0x1360`): three CRC-16 checksums computed by the routine `0x221C`.

| Region | Stored at | Stock 19D0 |
|---|---|---|
| loader `0x00000–0x042FF` | `0x05FFE` | 0xD5DE |
| program `0x10000–0x3F77B` | `0x3F7FE` | 0x021E |
| calibration `0x08000–0x0FFCD` | `0x0FFFE` | 0x47DB |

Algorithm: CRC-16/XMODEM (polynomial 0x1021, initial value 0, MSB first, no final XOR), table of 256 big-endian words at `0x3EDA` in the image. The right bound of a region is not included, the sum is stored big-endian. The stock E39 image and the factory Alpina B3 match on all three (0x1851 is the Alpina calibration sum).

The routine `0x221C` is called only from that handler (three calls at `0x13C4`, `0x1436`, `0x14AA`, no other reference in the image): the ECU computes the sums only when a tester asks. That is why edited calibrations with a stale sum were accepted and drove (every build of the project v1…v21). A tester or flasher that reads the sums sees the mismatch, so the tools keep the sum right:

- `apply_recipe.py` checks the loader and program sums of the input and recomputes the calibration sum after writing.
- `python3 tools/gs860_crc.py check image.bin` checks full images (256 KB, 512 KB of GS8.60.4) and 32 KB partials.
- `python3 tools/gs860_crc.py fix edited.bin fixed.bin` writes a new file with the sums recomputed, for an image edited by other means (TunerPro and the like). It refuses when the loader or program sum of the input does not match.

**Correction 08.10.2026: there is a background check.** Besides the tester path the unit checks all three sums by itself: the task `0x26926` (pointers in the task tables `0x12246`, `0x1240C`) computes the CRC-16 in chunks of 150 bytes with the routine `0x1DA66` (table copy `0x1147E`) over the same three areas, state in `[0xFFFF8B44]`. On a mismatch it sets bit 0 / 1 / 2 (loader / program / calibration) in `[0xFFFF8B45]`, copies the byte to `[0xFFFF91D4]` and reports the internal fault `0x0D` (`0x26AB2`, fault intake `0x1A3FA`). 20C0 has the same task (`0x22BD2`, document 11 §2). Which reaction the fault `0x0D` has on 19x0 (on 20C0 it is limp mode) is not established; the builds v1…v21 with a stale calibration sum did not go into limp mode on the road. So the sentence above "the ECU computes the sums only when a tester asks" is wrong: keep the sums right in any case, not only for the tester.

The label `0x0FFCE–0x0FFFD` is left as it is.
