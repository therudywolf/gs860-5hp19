# 03 · Torque converter lockup (WÜK / TCC)

## 1. The essentials

- Lockup in GS8.60.0 is a **ladder of four stages** of a control value (constant `0x8214 = 4`), not on/off and not a closed-loop slip controller. There are no target-slip tables as a class; slip is what remains at a given stage and torque. Confirmed by measurement: manual mode, 3rd gear, pedal 225/255, 100 → 142 km/h with the stage unchanged — slip 128, 256, 160, 128, 96, 64, 0, 0 rpm.
- Stage thresholds are **in pedal 0..255**, the Y axis of the tables is **road speed in km/h**. ATF temperature never enters the stage decision. There is no separate "speed limit for lockup".
- There are two threshold branches (doc 01 §4). There is no hysteresis in the stage decision — its role is played by the dwell `0x8E88 = 5` cycles after a stage change.

## 2. Code

| Address | What |
|---|---|
| `0x1DEBC` | stage selection |
| `0x1E11E–0x1E230` | control-value drive: ramps, transition matrices |
| `0x1E848` | 2D interpolator |
| `0x9B00–0x9B28` | catalog of 11 table pointers (doc 01 §3) |

Algorithm of `0x1DEBC` (from the disassembly):

```
entry conditions:
    [0xFFFF9113] == 0                    not in limp mode
    [0xFFFF90E2] <  2
    [0xFFFF90C7] <  5                    selector position (internal code)
    [0xFFFF9182] >  0x819C / 0x819D      pedal above the branch minimum (3 / 8)
    [0xFFFF9200] == 0                    dwell after the previous change expired

table = pair of the current gear [0xFFFF91AE]; second table of the pair if [0xFFFF91CB] == 1
for i = 1 .. [0x8214]−1:
    threshold[i] = table(X = i, Y = [0xFFFF918F] speed km/h)
stage = highest i with threshold[i] <= [0xFFFF9182]; else 1
[0xFFFF91AC] = stage;  [0xFFFF9200] = [0x8E88]
```

Proof that `0xFFFF9182` is the pedal: the same variable is read as the Y input of the shift-point matrices (doc 02 §1). The stage is then converted into the control value `[0xFFFF9216]` (0..255) through the ladder `0x888C`, with ramps:

| Address | Stock | What |
|---|---|---|
| `0x888C…0x888F` | **32 / 96 / 160 / 224** | value per stage 1–4 (12.5 / 37.6 / 62.7 / 87.8 %). The catalog heuristic sees a "table 0x888A 4×1" here — in fact it is the ladder plus 4 bytes of 32 |
| `0x88C0` | 5 | rise per cycle (going up a stage is always slow) |
| `0x88C1` | 3 | fall per cycle |
| `0x889C` | 4×4: 0 / 191 / 129 / 129 … | transition matrix, branch 0: row = new stage, column = old; value < 128 — ramp up at that rate, ≥ 128 — ramp down at 256 − value: one step down 191 → −65, two or three 129 → −127 |
| `0x88B0` | 4×4: 0 / 239 / 223 / 191 … | same, branch 1: −17 / −33 / −65 (softer) |
| `0x8E88` | 5 | dwell after a stage change, cycles |
| `0x819C / 0x819D` | 3 / 8 | pedal minimum per branch |
| `0x82B0 / 0x82B1` | 78 / 1 | "100 %" reference for `0xFFFF9182 = x·100/78` from `0xFFFF8439` / rate-of-change limit (`0xFFFF917A`) |
| `0x8884 / 0x8886` | 65 / 129 / 193 | alternative ladder (fallback branch of the drive) |

**Not proven:** the chain from `[0xFFFF9216]` to a specific PWM channel. The current driver 0x2054C–0x205F4 serves three channels (`input × gain[0xFFFF8CEE/8CF2] / period + offset[0xFFFF8CF0/8CF4]`); TPU registers `0xFFFFFF24 / 0xFFFFFF34` and CTM `0xFFFFF43C` are real, but "which channel = which solenoid" has not been established. So "duty 32/255" is a control value, not a measured EDS current. One third-party reverse read 0x888C as "adaptive program levels" — that does not fit the 0x1DEBC logic, but it has to be mentioned.

## 3. Threshold tables

All 2D8, X = 1..3 (column = threshold to enter stage 2 / 3 / 4), Y = km/h, value = pedal 0..255.

| Gear | Branch 0 | Branch 1 | Y axis (km/h) |
|---|---|---|---|
| 1 | `0x901E` | `0x903E` | 20, 28, 32, 38, 44, 50 |
| 2 | `0x905E` | `0x907E` | 31, 47, 62, 68, 76, 85 |
| 3 | `0x909E` | `0x90BE` | 62, 77, 94, 105, 116, 125 |
| 4 | `0x90DE` | `0x910E` | 63, 88, 113, 125, 138, 147, 156, 166, 181, 188 |
| 5 | `0x913E` | `0x915E` | 31, 63, 94, 125, 156, 188 |
| — | `0x917E` 6×6 | | not decoded (adjacent, read through the same catalog) |

Stock values (columns 1 / 2 / 3):

| Gear | Branch 0 | Branch 1 |
|---|---|---|
| 1 | 153 / 230 / 252 (60 / 90 / 99 %) everywhere | 102 / 166 / 204 (40 / 65 / 80 %) |
| 2 | 153 / 230 / 252 | 64 / 115 / 179 (25 / 45 / 70 %) |
| 3 | 153 / 230 / 252, flat | 64 / 115 / 179 |
| 4 | 128, 129, 132, 134, 137, 139, 144, 151, 172, 191 / 242 / 252 — **rises** with speed | 64 → 88 / 97 → 141 / 128 → 204 |
| 5 | **230** / 242 / 252 (90 %) everywhere | 64 / 115 / 179 |

Consequences in stock: in branch 0 the clutch never leaves stage 1 while cruising in 5th (a 90 % pedal threshold is unreachable); it arrives in 5th already "locked" from 4th and stays as long as the pedal is above 25 % (branch 1) — and only 4th has a speed-dependent threshold, which **rises** with speed. The "lockup limited to 114 km/h" discussed in the community is, on this software, neither a scalar nor a code comparison but the breakpoint of the 4th-gear axis (63 / 88 / **113** / 125 …) together with the first pedal threshold in those rows.

Measured on the reference car (log under load, throttle > 5°): D gears 1–3 at 17–46 km/h — slip 160…736 rpm, not one locked frame; D 4th at 48–65 km/h — up to 704; S 4th — locked in 100 % of frames. ATF heating in town follows directly.

## 4. How it was changed (preset v10/v18, doc 08)

Branch 0: column 1 in rows above 62 km/h (2nd, 3rd), 113 km/h (4th), 94 km/h (5th) → 102 (40 %). Branch 1: column 1 → 26…38 (10–15 %) with a gentler entry in the lowest rows. Ladder `0x888C` → 32 / 128 / 176 / 240, `0x88C0` → 7, `0x88B0` → −10 / −20 / −40. First gear and matrix `0x889C` untouched. Locking the clutch hard below ~1500 rpm on a high-mileage converter causes shudder; hence the gentler threshold at 63 km/h in 4th/5th.

## 5. Myth check: "TCC temperature window 23 / 27 / 90 / 140 °C"

A reading circulated in the community of the constants `0x8F00 = 9000` ("90.0 °C"), `0x8F08 = 2700`, `0x8F0A = 2300` ("27 / 23 °C"), `0x8EFC = 16000` and function `0x26EE0` as "unlock on overheat, DTC 34". Checked against the disassembly — **these are voltages, not temperature**:

- `0x20D78…0x20E6A` is the only place that writes `0xFFFF906C` and `0xFFFF906E`: `raw × 0x62A2 (25250) / 1024` from ADC buffers `0xFFFF89BA / 0xFFFF89BC` (10-bit). A 25.25 V full scale through a divider = **supply voltage, two lines, in mV**; `0xFFFF906A / 0xFFFF9068` are their running averages; a third channel `raw × 2500 / 1024 → 0xFFFF8D84` (0–2.5 V).
- `0x1FB3E`: if `[0xFFFF8626] == 1` and `9000 < [906C] < 16000` → `[8626] = 2`. That is **9.0 V < U < 16.0 V → "supply OK"**.
- `0x2738A–0x273DA` compares `0xFFFF9084 / 0xFFFF9082` (written at `0x20EA6–0x20ED8` as `raw × 5000 / 1024`, 5 V scale) with 2700 / 2300 — a 2.3–2.7 V sensor plausibility check producing a fault code.
- `0x26EE0`: if `[0xFFFF8B88] == 1` and `[906C] − [0x8EFA = 1000] > [906E]` and `[906E] ≤ [0x8EFE = 2500]` → **fault code 0x2D (45)** (second supply line more than 1 V below the first and below 2.5 V). A supply check, not DTC 34.
- The whole scalar block `0x8EE0–0x8F0E` — 2560, 1000, 9000, 11000, 9000, 7000, 500, 9000, 1500, 16000, 9000, 6500, 7000, 1000, 16000, 2500, 9000, 16000, 7000, 7000, 2700, 2300, 2504, 4500 — reads as thresholds in mV. `0x8EE8 / 0x8EEA / 0x8EF0` belong to the same block, see doc 05.

## 6. Where ATF temperature really is

`0x21522`: `a0 = 0xFFFF8435` — raw sensor byte, `0xFF` = invalid. `0x2164C–0x21668`: `[0xFFFF8435] × 3 / 4 → [0xFFFF90D4]` — this byte goes to the diagnostic frame (byte 6 of the "0B 03 frame"). BMW's canonical scale for this generation, `°C = raw × 0.75 − 48`, gives:

> **T(ATF) = frame byte − 48 °C**

The zero point is confirmed indirectly: table `0x9A6E` with axis `83 / 93 / 103 / 113` is read with `0xFFFF90D5` — already degrees. The only use of temperature in the logic is the thermal derate (doc 05 §2). Cold hydraulic corrections are the `0xA2C6` family (doc 01 §5); there are none in the lockup. There is **no** minimum lockup temperature in this software.
