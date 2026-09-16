# 07 · Reading a dump and flashing

EGS GS8.60.0 (256 KB) only. The tool used in the project was MS4X Flasher (see the ms4x.net wiki) with an FT232R K-line cable; other flashers that support GS8.60 should work with the same files. This is not a flasher manual — it is what you need to know about the **files** and the **order**.

## 1. Two file formats

| Format | Size | Contents | When |
|---|---|---|---|
| **Full** | 262,144 bytes | whole image: boot loader, identification, calibration, code | reading a dump — the only way; flashing — if the whole image must be restored |
| **Partial** | 32,768 bytes | calibration window `0x8000–0x10000`; file offset = image address − 0x8000 | **flashing — the default** |

In this repository's builds everything outside the `0x8000–0x10000` window is byte-identical to the original dump, so Full and Partial give the same result. Partial is safer: a power loss mid-write only corrupts the calibration, which a repeat write fixes; a power loss during a Full write can hit the boot loader.

`tools/apply_recipe.py` writes both files: `out.bin` and `out_partial32k.bin`; `tools/egs_tables.py info` shows size, SHA-256, code hash and calibration label of either.

## 2. Conditions

- battery on a charger (not paranoia: the ECU monitors its supply voltage, doc 05 §1);
- ignition ON, engine OFF;
- cable connected before the flasher starts, not touched until the write finishes;
- laptop on mains power.

## 3. Order

1. **Read a Full dump** and store it safely under a name with version and size. Dumps are never overwritten — they are the only real roll-back point.
2. Check the dump: `python3 tools/egs_tables.py info dump.bin` — size 262144, code hash `e151733e…` (= 19C0/19D0), 536 tables in the zone. If the code hash differs or there are not 536 tables, it is different software (e.g. GS8.60.4) and **nothing in this repository applies to it**.
3. If the flasher can read a Partial separately, read it too and verify that it is byte-identical to the `0x8000–0xFFFF` slice of the full dump. If not, this version lays out its calibration differently and you must stop.
4. Build the file: `python3 tools/apply_recipe.py recipes/<recipe>.json dump.bin -o build.bin` (doc 08). The tool refuses to write if the code does not match or if table axes do not match, and warns if old values do not match (a different base calibration — read doc 08 §4 before `--force`).
5. Verify the SHA-256 of the built file against the build log (`build.log`). If it does not match — do not flash.
6. Flash the **Partial**.
7. After writing — **Reset Adaptation** with a diagnostic tool. Mandatory: pressure/fill-time adaptations (`0xFFFF9480…`, `0xFFFF965E`, `0xFFFF9668`) were accumulated against the old calibration.
8. First drives — with a log (doc 06 §4).

## 4. Roll-back

Original Full dump → Partial slice `0x8000–0x10000` (or Full) → Reset Adaptation.

## 5. What a dump contains

A full dump carries identifiers of the **specific unit**: block 0x5FB6 with a 12-character string of the form `BX…` (looks like a serial number), programming history records 0x6002–0x605B (hypothesis), and the ECU's EEPROM (DS2 segment 3, 256 bytes — not part of the flash dump but readable) may contain the VIN. **Do not post full dumps publicly**; for exchanging calibrations a Partial or a recipe is enough (doc 08, CONTRIBUTING).

## 6. Checksum

No simple sum/XOR of the calibration window has been found in the tail at `0xFFFE`; edited calibrations with the tail untouched (`0x47DB` in stock) are accepted and drive. The conclusion "the ECU does not verify a window checksum" is a hypothesis, confirmed in practice on every build of the project (v1…v17) but not by code. Do not touch the tail `0x0FFCE–0x10000`.
