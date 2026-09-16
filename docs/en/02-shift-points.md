# 02 · Shift points

## 1. Where

16 matrices 2D8 **8×11**; the header of program k is at `0x091B2 + k·0x70`, pointers in the catalog `0x9B2C…0x9B68` (doc 01 §3).

```
header : 0x091B2 + k·0x70          [00 08][00 0B]
X axis : +4,  8 bytes  = 1..8        (transition number)
Y axis : +12, 11 bytes = pedal 0..255 (each matrix has its own!)
data   : 0x091C9 + k·0x70 + row·8 + column   (byte, km/h)
```

Columns: `0 = 1→2, 1 = 2→3, 2 = 3→4, 3 = 4→5` (up), `4 = 2→1, 5 = 3→2, 6 = 4→3, 7 = 5→4` (down). The value is the **road speed in km/h** at which the transition is allowed; `250`/`255` — "never" (up), `0` — "not applicable".

The pedal input is `[0xFFFF9182]` (0..255): at `0x290F6 / 0x29120 / 0x29146 / 0x291A8 / 0x291CC` the matrices are looked up as `d0 = column 1..8, d1 = [0xFFFF9182]`, with linear interpolation between rows. Full throttle without kickdown reads ≈229 on the reference car; the kickdown switch is row 255.

The Y axes are **not the same** across programs (stock):

| Programs | Pedal axis |
|---|---|
| 00, 01, 02, 06, 11, 14, 15 | 0, 46, 83, 121, 160, 198, 203, 243, 244, 254, 255 |
| 03, 04, 05, 07 | 0, 10, 46, 83, 121, 160, 198, 234, 244, 254, 255 |
| 08, 09, 10, 12 | 0, 33, 59, 84, 113, 141, 170, 205, 240, 254, 255 |
| 13 | 0, 46, 83, 121, 160, 188, 189, 243, 244, 254, 255 |

Do not change the axes (doc 09); change data only.

## 2. Stock matrices (excerpts)

Program 03 (D, confirmed by log):

```
pedal  |  1→2  2→3  3→4  4→5 |  2→1  3→2  4→3  5→4
     0 |   14   25   39   64 |   12   20   34   56
    83 |   15   29   45   75 |   12   20   36   58
   160 |   24   50   78  121 |   12   23   43   66
   234 |   41   76  111  184 |   13   36   64  100
   254 |   43   80  116  200 |   24   62   94  153
   255 |   49   95  137  200 |   41   86  129  189   ← kickdown
```

Program 01 (sport), stock: WOT `46 / 93 / 134 / 200`, closed throttle `20 / 58 / 109 / 200`, down `15 / 25 / 48 / 157`. Program 08 (manual), stock: all rows 0…254 identical `49 / 95 / 137 / 200 | 0 / 10 / 25 / 69`, kickdown down `33 / 70 / 112 / 183`. Program 13: column 1→2 = 0 (starts in 2nd). Program 05: upshift 250 everywhere (hold). Full print-outs: `tools/egs_tables.py shift stock.bin`.

## 3. Converting km/h ↔ rpm

Gear ratios are hard-coded: `0x12F9C` (u16, ×1000) = **3.665 / 1.999 / 1.407 / 1.000 / 0.742**. Output-shaft rpm per km/h depends on final drive and tyres: on the reference car (E39 2.5, stock final drive) the log gives **27.11 rpm per km/h**. Turbine rpm (≈ engine rpm with the converter locked) per 1 km/h:

| Gear | i | rpm per km/h (27.11 × i) | used in the project's calculations |
|---|---|---|---|
| 1 | 3.665 | 99.4 | 99.6 |
| 2 | 1.999 | 54.2 | 54.3 |
| 3 | 1.407 | 38.1 | 38.3 |
| 4 | 1.000 | 27.1 | 27.1 |
| 5 | 0.742 | 20.1 | 20.1 |

(The difference between the columns is measured 3.67/2.00/1.41 versus the hard-coded ratios.) Rpm at an upshift `g→g+1` = `v · k_g`; rpm after a downshift `g+1→g` = `v · k_g`.

**Different final drive or tyre size:** `k_g = i_g · FD · 1000 / (60 · L)`, where L is the tyre circumference in metres and FD the final drive ratio. Easier to measure: output shaft from the DS2 frame = byte 2 × 32 rpm (doc 06), divided by road speed. How exactly the ECU derives "km/h" for the matrix comparison (from n_out through a constant, or from CAN wheel speeds) has not been established from code; the TCC module reads speed from `0xFFFF918F`.

## 4. Computing a point against the rev limiter

Rules every preset was built with (checked by scripts, not by eye):

1. **Upshift below the spark cut.** `v · k_g ≤ n_spark − 150`. Otherwise the box never reaches the point and sits on the limiter. Which engine limiter acts first (spark or fuel) and how far below the rev limit it sits depends on the engine ECU; take the lower of the two.
2. **Downshift leaves margin.** After the downshift `v · k_g ≤ n_spark − 500`.
3. **Hysteresis.** In one row `down < up` for the same gear pair, otherwise hunting.
4. **Monotonic.** Down a column values do not decrease with pedal; along a row 1→2 < 2→3 < 3→4 < 4→5.
5. **All rows.** Edit all pedal rows, not just the top ones: an early build rewrote only rows 160…255, and at 16 % pedal the 3→2 line jumped from 28 to 78 km/h while kickdown allowed 3→2 up to 100 km/h (= 2nd at 5400 rpm) against a 2→3 line at 112 km/h — "throws gears and hits the limiter".

Example: rev limit 6784, spark ≈6656, WOT upshift target ≈6550 → `1→2 = 6550/99.6 = 66 km/h`, `2→3 = 120`, `3→4 = 171`. These are the v18 preset values (doc 08).

## 5. Manual programs

In 08/09/10 the upshift columns can be set to 255 — the ECU will not upshift by itself and the engine hits the limiter. **The downshift columns in rows 0…254 are the factory over-rev protection** — do not raise them: with `2→1 = 0` and `3→2 = 10` the ECU only forces a downshift near standstill. Stock kickdown-row downshifts of the manual programs: `33 / 70 / 112 / 183`.

## 6. 4↔5 hunting in D

Stock 03/04/07: 4→5 = 64 km/h, 5→4 = 56 (pedal rows 0…46) — 8 km/h hysteresis, 5th engages at ≈1286 rpm. The presets raise 4→5 to 75 in rows 0/10/46 (19 km/h hysteresis, ≈1508 rpm).

## 7. Relation to TCC lockup and torque reduction

Shift points are the only "sport" lever that has its own branch (matrices are selected by program number `0xFFFF91B0`). Hydraulics (doc 04) and torque-reduction maps (doc 04 §9) are common to all programs.
