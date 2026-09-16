# 10 · Methodology: how the reverse was done and what counts as proven

## 1. Tools

- **capstone** ≥ 5, `CS_ARCH_M68K`, mode `CS_MODE_M68K_040` — otherwise `muls.l` / `divs.l` (CPU32) do not decode. A linear listing of the whole image from `0x400`; gaps and data inside code show up as garbage instructions — that is normal; the landmarks are `link.w a6`, `movem.l`, `rts` and jump tables.
- Own Python scripts with no dependencies: table slicing by the "axes strictly increase" rule (`tools/egs_tables.py`), searching for 32-bit pointers to an address (xref), comparing images table by table (`diff`).
- DS2 logs (doc 06) — for verification.

## 2. Five steps that are never skipped

1. **Observation first, then hypothesis.** Not "let's try raising this parameter" but "the car does this, the log shows that".
2. **Narrow the bracket with an experiment.** Example: the box dropped into limp mode at the engine rev limiter; a series of revs in neutral with a rising ceiling gave "6613 — fine, ~7008 — failure".
3. **Find the constant.** Scan the image for u16/u8 in the required range. Round numbers (7000, 9000, 1500) in a scalar block are almost always calibration thresholds.
4. **Prove it with a code reference — and with the variable's write site.** A constant found by value means nothing until you see who reads it **and what variable it is compared with**. This step was once done half-way here: the read of `0x8EEA` in `0x265F4` was found, the comparison with `0xFFFF906E` seen, the variable labelled "turbine rpm" from the round number — and nobody checked who writes `0xFFFF906E`. The check showed `raw_ADC × 25250 / 1024` (doc 05 §1). **Rule: for every variable in a proof, find all writes (`move.w d0, $ffffXXXX`), not just the reads.**
5. **Check against the log, including the cases where the effect did not occur.** If it does not explain everything, the hypothesis is incomplete and gets written down as an open question, not bent to fit.

## 3. How the hydraulic tables were found

A direct search for references to a table address (e.g. `0xB974`) in code finds nothing — the execution module reads calibrations through pointer records (doc 04 §2). Chain: RAM `0xFFFF94F8` → root `0x3CBCC` → set directory `0x3CBBA` → record `→` field `→` table. Found as follows:

1. In the 0x34000+ module every calibration access looks like `movea.l (a5), a0; move.l $NN(a0), -(a7); jsr $2ca2a` — offset `$NN` = 4 × field number.
2. Records are found as arrays of consecutive pointers into the calibration window (0x3B372…); their length is the minimum stride between unique record addresses (78 × 4 for kind1).
3. The set directory is found as an array of 4 pointers to those arrays (0x3CBBA), the root as the only reference to the directory (0x3CBCC), the RAM pointer by the write of `0x3CBCC` into `0xFFFF94F8`.
4. Then for each read of field `$NN` one follows where the result goes (phase, timer, pressure) — that is how a field gets its meaning. All offsets and code addresses are in doc 04.

Record selection by transition type (`0x12FDC`) and set selection by class/direction (`0x13012`) come from the code at 0x343B6 / 0x3425E.

## 4. Reproducibility

The catalog of 536 tables: `python3 tools/egs_tables.py scan stock.bin --csv catalog.csv`. The field → table mapping of the records is reproduced in ten lines: read `u16 n` and `n` pointers at each of the four directory addresses, for each record read `len/4` fields, collect `(kind, type, field) → address`. That is how the names in the XDF were built (categories "Hydraulics", "Shift phases").

Every number in this documentation has been checked against the stock 19D0 dump and the Alpina B3 dump (19D0 620P). If you have another revision of the 19x0 calibration, `egs_tables.py diff` will show what differs.

## 5. Order of changes and A/B

One step — one build — one log. Do not combine in a first build steps that cannot later be separated (e.g. target slip time and on-coming pressure). The order in which v17 was assembled (v18 = v17 with 0x8EEA reverted): (a) revert the excess firmness of B974 in the low-torque rows + upshift target times 3×3; (b) on-coming pressure 2→3 + downshift target times; (c) off-going pressure 3→2 from Alpina. Log evaluation criteria — doc 06 §4.

## 6. Confidence scale used in the documents

| Label | Meaning |
|---|---|
| **proven / P** | a read in code, a write of the variable, agreement with a log |
| **E** | role proven from code, magnitude of the effect estimated |
| **hypothesis / H** | structure or number found, semantics not confirmed by code; do not tune by shape |
| **refuted** | an old reading withdrawn by code: "0x81A0 = solenoid phases", "B73E… = fill time", "0x8F00/0x8F08 = TCC temperature", "0xAB0C… = TCC slip maps", "0xA066… = TCC thresholds", "0x265F4 = turbine protection at 7000 rpm" (the variables are voltages, doc 05 §1) |

## 7. Open questions

- The cause of limp mode when the engine hits the ~7000 rpm limiter (doc 05 §1).
- Which PWM channel / register corresponds to which solenoid (EDS1…5, MV1…3).
- Semantics of fields kind1 f70 (4×4) and kind3 f65 (6×6), of tables `0xA066…0xA20A`, `0x917E`, `0x8142`, `0x824A`, of slots 0…11 of the descriptors `0x3AA60`.
- The argument format of DS2 command `0x06` (segment/address/length) — to be captured from a factory tester.
- How the ECU derives road speed in km/h (`0xFFFF918F`): from n_out via a constant or from CAN.
- Purpose of `0xFFFF90C2` and of bytes 21 / 13 / 19 of the status frame.
- Mapping of internal fault numbers (6–9 at `0x12640`) to DS2 codes (e.g. 0x95).
