# 02 · Shift points

> **Corrected 23.09.2026.** Until then this document read the matrix values as km/h. They are output shaft rpm / 32 (§3, proven by code). On the reference car one unit is 1.18 km/h, so every rpm figure derived the old way was 18 % too low, and the presets asked the box to shift at turbine speeds the engine never reaches (§4). The presets were recomputed the same day (doc 08).

## 1. Where

16 matrices 2D8 **8×11**. The header of program k is at `0x091B2 + k × 0x70`, pointers in the catalog `0x9B2C…0x9B68` (doc 01 §3).

```
header : 0x091B2 + k × 0x70        [00 08][00 0B]
X axis : +4,  8 bytes  = 1..8        (transition number)
Y axis : +12, 11 bytes = pedal 0..255 (each matrix has its own!)
data   : 0x091C9 + k × 0x70 + row × 8 + column   (byte, output shaft rpm / 32)
```

Columns: `0 = 1>2, 1 = 2>3, 2 = 3>4, 3 = 4>5` (up), `4 = 2>1, 5 = 3>2, 6 = 4>3, 7 = 5>4` (down). The value is the **output shaft speed / 32** at which the transition is allowed (§3). `250`/`255` in an upshift column means "never", `0` means "not applicable" (in 1>2 of program 13: start in 2nd).

The pedal input is `[0xFFFF9182]` (0..255): at `0x290F6 / 0x29120 / 0x29146 / 0x291A8 / 0x291CC` the matrices are looked up as `d0 = column 1..8, d1 = [0xFFFF9182]`, with linear interpolation between rows. Full throttle without kickdown reads ≈229 on the reference car, the kickdown switch is row 255.

The Y axes are **not the same** across programs (stock):

| Programs | Pedal axis |
|---|---|
| 00, 01, 02, 06, 11, 14, 15 | 0, 46, 83, 121, 160, 198, 203, 243, 244, 254, 255 |
| 03, 04, 05, 07 | 0, 10, 46, 83, 121, 160, 198, 234, 244, 254, 255 |
| 08, 09, 10, 12 | 0, 33, 59, 84, 113, 141, 170, 205, 240, 254, 255 |
| 13 | 0, 46, 83, 121, 160, 188, 189, 243, 244, 254, 255 |

Do not change the axes (doc 09), change data only.

## 2. Stock matrices (excerpts)

Program 03 (D, confirmed by log), values and the turbine rpm they mean:

```
pedal  |  1>2  2>3  3>4  4>5 |  2>1  3>2  4>3  5>4
     0 |   14   25   39   64 |   12   20   34   56
    83 |   15   29   45   75 |   12   20   36   58
   160 |   24   50   78  121 |   12   23   43   66
   234 |   41   76  111  184 |   13   36   64  100
   254 |   43   80  116  200 |   24   62   94  153
   255 |   49   95  137  200 |   41   86  129  189   kickdown

kickdown in turbine rpm: up 5747 / 6077 / 6168 / 6400, landing after the downshift 4808 / 5501 / 5808 / 6048
```

Program 01 (sport), stock: WOT `46 / 93 / 134 / 200`, closed throttle `20 / 58 / 109 / 200`, down `15 / 25 / 48 / 157`. Program 08 (manual), stock: all rows 0…254 identical `49 / 95 / 137 / 200 | 0 / 10 / 25 / 69`, kickdown down `33 / 70 / 112 / 183`. Program 13: column 1>2 = 0 (starts in 2nd). Program 05: upshift 250 everywhere (hold). Full print-outs: `tools/egs_tables.py shift stock.bin`, in turbine rpm with `--turbine`.

The factory never asks for more than 5747 / 6077 / 6168 turbine rpm for 1>2 / 2>3 / 3>4 (D kickdown and manual), with its own limiter at about 6500.

## 3. Units: output shaft rpm / 32

What the code compares (19C0/19D0):

| Step | Address | What is there |
|---|---|---|
| upshift | `0x24AC8` | `CMP.B (0xFFFF918F), D0` with D0 = matrix value, shift up when `918F ≥ value` |
| downshift | `0x24B20` | shift down when `918F < value − [0xFFFF919A]` (919A = 0 in S and M) |
| what 918F is | `0x24F56…0x24F66` | `MOVE.W D1,(0xFFFF8DA4)`, `LSR.W #5,D0`, `MOVE.B D0,(0xFFFF918F)`: the filtered speed shifted right by 5 |
| the filter | `0x24F1E…0x24F54` | `8DA4 = (a × old + b × new) / (a + b)` of the raw channel 0 (`0xFFFF8DA6`, written at `0x24EA8`), weights from the calibration: `a = [0x8F72] = 9`, `b = [0x8F73] = 1` |
| channel 0 | `0x116C4` | speed channel constants, `K = 1 666 666 = 60 × 10⁶ / 36` at `0x116C8` |
| channel 0 is the output shaft | `0x294CC…0x294F8` | slip = turbine `0xFFFF97B4` − n_out `0xFFFF97B2` × ratio from `0x12F9C` |

So one matrix unit is **32 rpm of the output shaft**. It is not road speed and it does not depend on the final drive or the tyres. The DS2 status frame carries the same quantity (byte 2 × 32 = n_out, doc 06). The TCC stage tables use the same variable for their speed axis (doc 03).

Gear ratios are hard-coded: `0x12F9C` (u16, ×1000) = **3.665 / 1.999 / 1.407 / 1.000 / 0.742**. Turbine rpm at a threshold = `value × 32 × i`:

| Gear | i | turbine rpm per unit (32 × i) | old reading (km/h × 27.11 × i) |
|---|---|---|---|
| 1 | 3.665 | 117.3 | 99.6 |
| 2 | 1.999 | 64.0 | 54.3 |
| 3 | 1.407 | 45.0 | 38.3 |
| 4 | 1.000 | 32.0 | 27.1 |
| 5 | 0.742 | 23.7 | 20.1 |

For an upshift `g>g+1` take the ratio of g (the gear it leaves). For a downshift `g+1>g` take the ratio of g: that is where the engine lands.

Road speed, only to read the tables: `km/h = value × 32 / k`, with k the output shaft rpm per km/h of the car (27.11 on the reference car, E39 2.5 with the stock final drive: one unit = 1.18 km/h). A different final drive or tyre size changes the road speed of a shift, not its rpm, so shift points in rpm carry over unchanged.

## 4. Computing a point against the rev limiter

Rules the presets are checked with (`egs_tables.py verify-shift`, not by eye):

1. **Upshift before the spark cut.** `value × 32 × i_g ≤ n_spark − margin_g`. At the moment of the command the turbine is below the engine by the converter slip, then the engine keeps rising while the filtered speed catches up and the shift executes. Default margins: **1120 / 610 / 490 / 400** rpm for 1>2 / 2>3 / 3>4 / 4>5. Source: the reference car (E39 2.5 with 5HP19), full load in 1st from logs: slip 280…350 rpm and about 1600 rpm/s of engine rise, the other gears are estimates. The factory kickdown rows leave 330…850 rpm to its own limiter, so these margins are more conservative than BMW's, change them with `--margin`. A value whose turbine rpm reaches the spark cut is **never reached under load**: the box hangs at the limiter. Which engine limiter acts first (spark or fuel) and where depends on the engine ECU, take the lower one as `n_spark`. 4>5 at full load needs 4th gear near the limiter, above the top speed of most cars. The factory uses 200 there as "practically never", so the tool only warns about it.
2. **Downshift lands with room.** `value × 32 × i_(lower gear) ≤ n_spark − 500`. The value is the highest speed at which the downshift is allowed, so this is the worst case of where the engine lands. Landing above the spark cut means the wheels drive the engine past the limiter: no ECU can stop that.
3. **Hysteresis.** In one row `down < up` for the same gear pair, otherwise hunting. Where the tool lowers an upshift it keeps its downshift at least 6 units below (the factory kickdown rows keep 5…11).
4. **Monotonic.** Down a column values do not decrease with pedal. Along a row 1>2 < 2>3 < 3>4 < 4>5.
5. **All rows.** Edit all pedal rows, not just the top ones: an early build rewrote only rows 160…255, and at 16 % pedal the 3>2 line jumped from 28 to 78 while kickdown allowed 3>2 up to 100 against a 2>3 line at 112: "throws gears and hits the limiter".
6. **Manual programs keep the overrun protection** (§5).

Example, the engine the presets are built for: fuel cut 6784, spark from about 6656.

```
python3 tools/egs_tables.py verify-shift build.bin --spark 6656 --cut 6784 --stock stock.bin
limits (matrix units): up 1>2..4>5 [47, 94, 136, 195], down landing 2>1..5>4 [52, 96, 136, 192],
manual overrun guard [58, 106, 151, 212]
```

Upshift at full load at most 47 / 94 / 136 = turbine 5512 / 6013 / 6123 rpm at the command. `--fix out.bin` lowers only the cells that break the rules (cells equal to `--stock` are left to the factory), recomputes the checksum and writes a new file. With `--stock` the findings in cells equal to stock are listed as `stock` and not counted.

What the old reading did: the 16.09 presets asked for `66 / 120 / 171` in the upper rows of the sport programs, meant as 6550 rpm at 99.6 rpm per km/h. In real units that is 7740 / 7676 / 7699 turbine rpm: the box never shifted up at full throttle in S and hung at the limiter. The manual kickdown row `59 / 108 / 154 / 217` landed at 6920 / 6909 / 6934 / 6944 rpm, above the spark cut.

## 5. Manual programs

The upshift columns of 08/09/10 are the **overrun protection**: with the value at the fuel cut (`cut / (32 × i_g)`, 58 / 106 / 151 / 212 for 6784) the engine stops at the spark cut under load, the turbine never gets there and the box holds the gear, as a manual mode should. On the overrun (engine braking downhill) the turbine follows the wheels and the box shifts up before the engine is driven past the cut. Stock values 49 / 95 / 137 / 200 shift up by themselves near the stock limiter. `255` removes the protection altogether: do not use it.

**The downshift columns in rows 0…254 are the factory protection lines**, do not raise them: with `2>1 = 0` and `3>2 = 10` the ECU only forces a downshift near standstill. The kickdown row obeys rule 2. Stock kickdown-row downshifts of the manual programs: `33 / 70 / 112 / 183` (landing 3870 / 4478 / 5043 / 5856 rpm).

## 6. 4>5>4 hunting in D

Stock 03/04/07: 4>5 = 64, 5>4 = 56 (pedal rows 0…46), a gap of 8 units (9 km/h on the reference car), 5th engages at turbine 1520 rpm. The presets raise 4>5 to 75 in rows 0/10/46: a gap of 19 units (22 km/h), 5th at 1781 rpm.

## 7. Relation to TCC lockup and torque reduction

Shift points are the only "sport" lever that has its own branch (matrices are selected by program number `0xFFFF91B0`). Hydraulics (doc 04) and torque-reduction maps (doc 04 §9) are common to all programs.
