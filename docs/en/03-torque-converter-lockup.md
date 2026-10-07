# 03 · Torque converter lockup (WÜK / TCC)

> **Rewritten 25.09.2026.** Until then this document described a "ladder of four stages" (0x1DEBC, 0x888C, `0xFFFF9216`, tables 0x901E-0x915E) as the TCC lockup. On 23.09.2026 the code showed that this is AGS, the adaptive program selection: its points select the shift program and never reach the clutch. That material, with corrected names, moved to §7. The real lockup is described in §1-§4.

## 1. The essentials

- Two levels drive the lockup. The upper one: function 0x29056 computes the request `0xFFFF91F9` every 10 ms: 0 = open, 1 = controlled slip, 2 = locked. The lower one: the clutch state machine 0x32B08 (state `0xFFFF9632`, 0-8) and the task 0x33F66 drive the PWM `0xFFFF95BA` from 0 to 0x1F40 (8000, full scale). The whole chain: 0x29056, table 0x993A with the groups 0x897E, request `0xFFFF91F9`, state machine, regulator, PWM `0xFFFF95BA`, output `0xFFFFFF34`.
- The meaning of request 0 / 1 / 2 is derived from the tables of the lower state machine and from the PWM output: request 0 ends in state 1 (PWM 0), request 1 in state 4 (controlled slip), request 2 in state 7 (PWM 0x1F40). There is no Bosch documentation.
- The thresholds are in **n_out / 32** (`0xFFFF918F`, the same variable as in the shift matrices, doc 02 §3), with the transmission pedal `0xFFFF9182` as the axis. The threshold set (group) depends on the program and the gear. There is no lockup in 1st: the gear mask 0x8978 = 0x3C (2nd-5th).
- ATF temperature does take part. The lower level (0x320DC) keeps the clutch open below raw 70 (about 22 °C), and above raw 160 (about 110 °C) a slip request acts as "open" while full lock stays allowed. With overheated ATF (`0xFFFF90E4`) the programs PC and PD come in with their own threshold groups (§3).
- There is no separate "lockup speed limit" in the upper level: the clutch opens only when n_out falls below the thresholds (§2).
- Checked by code analysis on 23-24.09.2026, by a second independent analysis and by running the lower-level code in an emulator. Where a role comes from a third-party reverse, the text says so.

## 2. Code: upper level (request 0 / 1 / 2)

| Address | What |
|---|---|
| `0x29056` | computes the request `0xFFFF91F9` every 10 ms (function 0x29056-0x29208) |
| `0x290A0` | threshold group: byte `[0x897E + 4 × program + gear - 2]`, program from `0xFFFF91A0` (in code: base 0x897A + 4 + index) |
| `0x290D0` | `movea.l #$9B80`: pointer to the threshold table 0x993A |
| `0x290FC` | `cmp.b $FFFF918F`: threshold compared with n_out / 32 |
| `0x2912E` | direct transition from 0 to 2 during the first ~20 s after power-up |
| `0x291D4` | `move.b $8B4C`: hysteresis |
| `0x32B08`, `0x33F66` | lower level (§4) |

Conditions: the gear `0xFFFF91AF` must be in the mask 0x8978 = 0x3C (2nd-5th), and bit 8 of the fault word `0xFFFF8FA2` disables the lockup (doc 05 §6). Group 0 means "no lockup".

Request transitions (threshold0 / threshold1 / threshold2 come from the group, §3):

- 0 to 1: n_out > threshold1 and `0xFFFF9213` = 0,
- 1 to 2: n_out > threshold2,
- 2 to 1: n_out < threshold2 - [0x8B4C],
- 1 to 0: n_out < threshold0 for longer than [0x8ED7 + gear] ticks.

Stock: 0x8B4C = 3 (n_out / 32 units), dwell [0x8ED7 + gear] = 6 ticks. During the first ~20 s after power-up slip is not allowed (`0xFFFF9213`, 0x15F78), and a direct transition from 0 to 2 is possible (0x2912E). There are no other references to 0x993A, 0x9B80, 0x897E, 0x8978 in the image.

## 3. Threshold table 0x993A and groups 0x897E

Table 0x993A (pointer 0x9B80), 2D8 30 × 7: `[u16 30][u16 7]`, X axis 30 bytes (threshold number 0…29), Y axis 7 bytes (transmission pedal `0xFFFF9182`, stock 0 / 5 / 46 / 59 / 72 / 97 / 122), 210 data bytes from 0x9963, rows of 30 bytes. Group g uses columns 3g-3 (threshold0, "open below"), 3g-2 (threshold1, "slip above") and 3g-1 (threshold2, "locked above"). Values in n_out / 32, turbine rpm at a threshold = value × 32 × i (2nd-5th: 1.999 / 1.407 / 1.000 / 0.742).

Group = byte `[0x897E + 4 × program + gear - 2]`, 16 programs × 4 bytes (gears 2-5). Factory:

| Program | Groups for 2nd / 3rd / 4th / 5th |
|---|---|
| P0, P1 (D), P2, P3 (S) | 4 / 1 / 2 / 3 |
| PB (M) | 0 / 8 / 9 / 9 |
| PD (M with overheated ATF) | 0 / 7 / 6 / 0 |
| PC (D with overheated ATF) | 0 / 0 / 0 / 0, no lockup |
| P4-P6, PA, PE, PF | factory values not listed here |

The factory uses groups 0-4 and 6-9, groups 5 and 10 are free, groups 6-9 belong to PB and PD only.

Factory thresholds in turbine rpm (threshold0 / threshold1 / threshold2):

| Gear | D and S, light pedal | D and S, pedal from 122 | M (PB) |
|---|---|---|---|
| 2 | 3966 / 4542 / 5757 | 3966 / 4542 / 5757 | no lockup |
| 3 | 900 / 990 / 4052 | 2791 / 3196 / 4052 | 2611 / 3016 / 4592, WOT 3466 / 3737 / 4592 |
| 4 | 960 / 1152 / 2880 | 1984 / 2272 / 2880 | 1984 / 2176 / 3584 |
| 5 | 1187 / 1234 / 1543 | 1686 / 1923 / 2137 | 1472 / 1615 / 2659 |

D and S use the same groups (4 / 1 / 2 / 3), the thresholds rise with pedal. At WOT in D the factory groups lock the converter in 2nd from 5757 and in 3rd from 4052 turbine rpm: at the limiter the engine equals the turbine. In M (PB) the clutch locks in 3rd, 4th and 5th from 4592 / 3584 / 2659 turbine rpm. This matters for manual upshift thresholds (doc 02 §5).

Measured on the reference car (log under load, throttle above 5°): D, gears 1-3 at 17-46 km/h, slip 160…736 rpm, not one locked frame. D, 4th at 48-65 km/h, slip up to 704 rpm. S, 4th, locked in 100 % of frames. ATF heating in town follows. Until 23.09.2026 this measurement was explained by the "ladder" (§7), in fact the clutch is driven by the thresholds 0x993A and the lower level (§4).

## 4. Lower level: clutch state machine, PWM and protections

State machine 0x32B08 (tables 0x12EEC-0x12F9B), state `0xFFFF9632`:

| State | What |
|---|---|
| 0 | reset, PWM 0 |
| 1 | open |
| 2, 3 | start of engagement |
| 4 | controlled slip |
| 5 | role not named in the analysis |
| 6 | closing, PWM rising |
| 7 | locked: handler 0x33DE4 sets PWM 0x1F40 (maximum) |
| 8 | leaving lock |

The way up is 1, 2, 3, 4, 6, 7, the way back goes through 8 and 5. Request 0 ends in state 1 (PWM `0xFFFF95BA` = 0), request 1 in state 4, request 2 in state 7. Checked by running the code in an emulator.

- **Full-lock permission** `0xFFFF9634` (0x32150, by gear, speed and load). Entry into state 7 depends on it, and it selects the 95FA entry. Without it the clutch stays in slip (table 0x12F08). There is also a minimum slip time `0xFFFF9655`. The conditions of 0x32150 are not fully traced.
- **Closing** (state 6, 0x33D32). The PWM rises by [0xB0FC] × 100 per second at a full scale of 8000 (integrator 0x2C684, step read at 0x33DB0, rise computed by 0x3237A). The clutch counts as locked when a slip below [0xB0D4] rpm holds for [0xB12E] × 10 ms, or when the PWM reaches 8000. Minimum slip time before closing 0xB140 = 30 ms. Stock: 0xB0FC = 10 (1000 PWM units per second), 0xB0D4 = 10 rpm, 0xB12E = 20 (0.2 s).
- **Shift phase for the TCC** `0xFFFF964B` (0x32270): 2 = new gear command, 3 = waiting, 4 = shift in progress (flag `0xFFFF9718`), 5 = after flag `0xFFFF9730` and until 9718 clears, then 1. Flag 9730 is set at synchronisation (0x3487A). In phases 3 and 4 a locked clutch goes to controlled slip (states 7, 8, 4, table 0x12F24). The shift type for the TCC `0xFFFF9650` comes from table 0x12FAA by the pair (current, target): 1 = upshift by one, 2 = downshift by one, 3 = downshift skipping one (3-1, 4-2, 5-3).
- **Hold after a shift.** In phase 5 function 0x32A38 (called from 0x32B48) does not let the state machine go from slip to closing (4 to 6) or from open to the start of engagement (1 to 2) while the counter `0xFFFF9658` (10 ms step, reset outside phase 5) is below a threshold. The threshold is chosen by shift type through the pointer `0xFFFF962E` (array 0x3B0B4, entries 0x3B026 / 0x3B032 / 0x3B03E): after an upshift 0xB13B, 0xB139, after downshifts 0xB13C, 0xB13A. Stock: 0xB139 = 100, 0xB13A = 20, 0xB13B = 100, 0xB13C = 20 (× 10 ms: 1.00 s after an upshift, 0.20 s after a downshift). The hold starts after the ratio change. The cells are shared by D, S and M.
- **Descriptor 0x3B0C2.** Both data sets point to it (array 0x3B1F2), and every lower-level cell is read only through it: +0x08 array of type entries 0x3B0B4, +0x58 0xB0FC, +0x6C threshold 950, +0x78 0xB0D4, +0x98 0xB12E. Editing these cells changes D, S and M at once.
- **Reset on brake and engine speed.** 0x33F66 (every 10 ms) calls the check 0x33024 at 0x33F74. Reset when the state `0xFFFF9632` is neither 0 nor 1, the engine speed `0xFFFF97B0` is below [descriptor 0x3B0C2 + 0x6C] = 950, `0xFFFF97F5` = 1 (brake, DME2 frame byte 6 bit 0) and `0xFFFF9634` = 0. The conditions are joint: pressing the brake alone does not open the clutch. The reset path is 0x33F9C: 9632 = 0, 9635 = 1, 95D0 = 0, 963E = 0 (PWM 0 in the same tick, then state 1).
- **Engine speed.** By the lower-level analysis of 23.09.2026, at an engine speed of 950 rpm or less the clutch is forced open and allowed again from 1200 (0xB0E2 = 1200, 0xAAC6 = 250). The box takes the engine speed from the DME1 frame (`0xFFFF8DB2`).
- **ATF** (0x320DC): below raw 70 (about 22 °C) the clutch is always open, above raw 160 (about 110 °C) a slip request acts as "open" and full lock is allowed. The conversion of the raw values to °C is approximate.
- **Slip power** is monitored by 0x32986 (lower-level protection).
- **Reference slip of the regulator** (`0xFFFF95A6`) comes from six 8×8 maps in 0xAB0C-0xAEE3 (0xAB0C, 0xABB0, 0xAC54, 0xACF8, 0xAD9C, 0xAE40). This role comes from a third-party reverse and was accepted on 23.09.2026, the repository has no own code analysis of these maps yet. The earlier reading "torque-reduction maps" (doc 04 §9) is withdrawn.
- **Output.** The current driver 0x2054C-0x205F4 serves three channels (`input × gain[0xFFFF8CEE/8CF2] / period + offset[0xFFFF8CF0/8CF4]`), TPU registers `0xFFFFFF24 / 0xFFFFFF34` and CTM `0xFFFFF43C`. The clutch PWM `0xFFFF95BA` goes to the output `0xFFFFFF34`. This also comes from the third-party reverse, accepted on 23.09.2026, and part of the chain (0x29056, 0x993A, 0x897E, `0xFFFF91F9`) was checked by own analysis. For the other channels "which channel = which solenoid" is not established.

## 5. Myth check: "TCC temperature window 23 / 27 / 90 / 140 °C"

A reading circulated in the community of the constants `0x8F00 = 9000` ("90.0 °C"), `0x8F08 = 2700`, `0x8F0A = 2300` ("27 / 23 °C"), `0x8EFC = 16000` and function `0x26EE0` as "unlock on overheat, DTC 34". Checked against the disassembly — **these are voltages, not temperature**:

- `0x20D78…0x20E6A` is the only place that writes `0xFFFF906C` and `0xFFFF906E`: `raw × 0x62A2 (25250) / 1024` from ADC buffers `0xFFFF89BA / 0xFFFF89BC` (10-bit). A 25.25 V full scale through a divider = **supply voltage, two lines, in mV**; `0xFFFF906A / 0xFFFF9068` are their running averages; a third channel `raw × 2500 / 1024 → 0xFFFF8D84` (0–2.5 V).
- `0x1FB3E`: if `[0xFFFF8626] == 1` and `9000 < [906C] < 16000` → `[8626] = 2`. That is **9.0 V < U < 16.0 V → "supply OK"**.
- `0x2738A–0x273DA` compares `0xFFFF9084 / 0xFFFF9082` (written at `0x20EA6–0x20ED8` as `raw × 5000 / 1024`, 5 V scale) with 2700 / 2300 — a 2.3–2.7 V sensor plausibility check producing a fault code.
- `0x26EE0`: if `[0xFFFF8B88] == 1` and `[906C] − [0x8EFA = 1000] > [906E]` and `[906E] ≤ [0x8EFE = 2500]` → **fault code 0x2D (45)** (second supply line more than 1 V below the first and below 2.5 V). A supply check, not DTC 34.
- The whole scalar block `0x8EE0–0x8F0E` — 2560, 1000, 9000, 11000, 9000, 7000, 500, 9000, 1500, 16000, 9000, 6500, 7000, 1000, 16000, 2500, 9000, 16000, 7000, 7000, 2700, 2300, 2504, 4500 — reads as thresholds in mV. `0x8EE8 / 0x8EEA / 0x8EF0` belong to the same block, see doc 05.

## 6. Where ATF temperature really is

> **Corrected 07.10.2026.** Until this date this section said "`0xFFFF8435` is the raw byte of the ATF sensor" with the conclusion "T(ATF) = frame byte 6 − 48 °C", and on 25.09.2026 "needs checking" was added to it. The check is done: `0xFFFF8435` is the **engine coolant** temperature, and it goes into the `0B 03` frame as **byte 5**, not 6. Byte 6 is the raw ATF + 15.

**Engine temperature.** `0xFFFF8434` is the start of the receive buffer of the DME2 frame `0x329` (byte 0), so `0xFFFF8435` is its byte 1, the engine temperature in the DME2 layout (°C = byte × 0.75 − 48). The code computes exactly that: `0x2164C–0x21668` `[0xFFFF8435] × 3 / 4 → [0xFFFF90D4]`, the same value in `[0xFFFF90D3]` (`0x21696`). With the byte `0xFF` (invalid) `[0xFFFF8D28]` = 1 is set (`0x21520–0x21534`), and `[0xFFFF90D3]` is replaced by ATF + 8 (`[0xFFFF90D0] + 8`, `0x21682–0x2168A`) or, with an ATF sensor fault, by the constant `0x813F`. The warm-up program uses it (document 05 §2). The frame builder `0x19B4A` writes `[0xFFFF90D4]` as the fifth data byte (`0x19B82`). An E39 log confirms it: byte 5 − 48 equals the DME coolant temperature, mean difference 0.1-0.2 °C in four runs (8700 frames), −1.4 °C in a fifth short one (125 frames).

**ATF.** Sensor: mV `[0xFFFF9080]` → table `0x9A82` (slot `0x9B94`, `0x20EEE–0x20F02`) → `[0xFFFF8D1A]`, its low byte `[0xFFFF8D1B]` → the raw ATF of the shift module and the TCC lower level `[0xFFFF90D0]` (`0x20F50`; with a sensor fault `[0xFFFF90D3]` − 8 or the constant `0x8135`, `0x20F14–0x20F36`). The frame carries **byte 6 = `[0xFFFF8D1A]` + 15** (`0x19B88–0x19B92`). 20C0 is built the same way: byte 5 = `[0xFFFF906B]` = `[0xFFFF83DF]` × 3 / 4 (`0x1CE12`, DME2 buffer from `0xFFFF83DE`), byte 6 = `[0xFFFF8C8C]` + 15 (document 11 §10).

> **Byte 5 of the `0B 03` frame = engine temperature, °C = byte − 48. Byte 6 = raw ATF + 15.**

The conversion of the raw ATF into degrees is not established by code. The former formula "byte 6 − 48" rested on a wrong attribution to `[0xFFFF90D4]`. The code's substitutions (ATF = coolant − 8 and coolant = ATF + 8 in raw units) speak for the scale "raw = °C + 40", then ATF °C = byte 6 − 55, but this is an inference from the substitution logic, not a proof. A cold-start log after a night's parking checks it: in the first frames ATF and coolant both equal the air temperature. The degree estimates below and in documents 01, 05 (raw 70 "about 22 °C", 170 "about 120 °C") were made on the old scale and are only as good as it.

ATF temperature acts in the logic in two places: the TCC lower level (0x320DC, §4) and the program selection on overheating (`0xFFFF90E4`, raw `0xFFFF90D0` from 170: programs PC and PD with their own lockup groups, §3). The table `0x9A6E`, formerly called an "ATF thermal derate", is read by the engine temperature and belongs to the warm-up program (doc 05 §2). Cold hydraulic corrections are the `0xA2C6` family (doc 01 §5). The earlier statement "there is no minimum lockup temperature" is refuted: below raw ATF 70 the clutch does not lock.

## 7. AGS: adaptive program selection (not the lockup)

> **The reading before 23.09.2026 was wrong.** The earlier §1-§4 of this document described the functions below as the TCC lockup: a "ladder of four stages" of a control value `0xFFFF9216`, the thresholds 0x901E-0x915E, the "duty" 0x888C. On 23.09.2026 an analysis of every access to `0xFFFF9216` showed that it never reaches an output: it is read only by ramps, minima and comparisons in the program arbitration (0x23156-0x231CE) and in the level ladder 0x8886 (0x1DD18). This is AGS, the adaptive selection of the shift program. These functions and tables do not touch the converter clutch. The third-party reverse that called 0x888C "adaptive program levels" was right.

AGS accumulates points `0xFFFF9216` (0..255), the points give a level 1-4, and the level selects the program. In D levels 1-2 give P0 / P1 (matrices 14 / 06), in S levels 3-4 give P2 / P3 (matrices 11 / 15), doc 01 §5.

| Address | What |
|---|---|
| `0x1DEBC`, functions `0x1Fxxx` | adaptive program selection, read the D / S branch `0xFFFF91CB` |
| `0x1F14A` | writes the points `0xFFFF9216`, raises them with tables 0x88D8 / 0x88E8 |
| `0x1DF6C` | picks the D / S pair of tables from 0x901E-0x915E by `0xFFFF91CB` |
| `0x1E11E-0x1E230` | drives the points: ramps to the "home" points and the decrease (the three rows below) |
| `0x1E12A-0x1E19C` | pulls the points towards the "home" points 0x888C-0x888F |
| `0x1E1A2` | lowers the points in branch S (step 0x88B0) |
| `0x1E220` | exit when the pedal is below the threshold 0x819C / 0x819D |
| `0x1DCB2`, `0x1DBA4` | point clamp `[0x887C + 91CB, 0x8878 + 91CB]` |
| `0x1DD18` | level ladder 0x8886 |
| `0x23156-0x231CE` | program arbitration by points |
| `0x1E848` | 2D interpolator |
| `0x9B00-0x9B28` | pointer catalog of the tables 0x901E-0x917E (doc 01 §3) |

Algorithm of `0x1DEBC` from the earlier disassembly, names corrected:

```
entry conditions:
    [0xFFFF9113] == 0                    no kickdown
    [0xFFFF90E2] <  2
    [0xFFFF90C7] <  5                    selector position (internal code)
    [0xFFFF9182] >  0x819C / 0x819D      pedal above the branch threshold (3 / 8)
    [0xFFFF9200] == 0                    dwell after the previous change expired

table = pair of the current gear [0xFFFF91AE], second table of the pair if [0xFFFF91CB] == 1
for i = 1 .. [0x8214]-1:
    threshold[i] = table(X = i, Y = [0xFFFF918F] output shaft rpm / 32)
level = highest i with threshold[i] <= [0xFFFF9182], else 1
[0xFFFF91AC] = level
[0xFFFF9200] = [0x8E88]
```

Parameters (all belong to AGS, none to the clutch):

| Address | Stock | What |
|---|---|---|
| `0x888C…0x888F` | 32 / 96 / 160 / 224 | "home" points of levels 1-4, `0xFFFF9216` is pulled towards them (0x1E12A-0x1E19C). The catalog heuristic sees a "table 0x888A 4×1" here |
| `0x88C0` | 5 | rate at which the points grow towards "home" |
| `0x88C1` | 3 | lies in the AGS parameter block, role not traced separately |
| `0x88B0` | 4×4: 0 / 239 / 223 / 191 … | step of the point decrease in branch S (0x1E1A2). A value from 128 up means a decrease of 256 minus the value: -17 / -33 / -65 |
| `0x889C` | 4×4: 0 / 191 / 129 / 129 … | branch-D counterpart of 0x88B0, not traced separately |
| `0x8E88` | 5 | dwell after a level change, cycles (from the earlier analysis of the 0x1DEBC loop) |
| `0x819C / 0x819D` | 3 / 8 | pedal threshold for branches D / S: below it the function exits through 0x1E220 and the level is frozen, not reset. Zeroing it would have the opposite effect. Do not touch |
| `0x8214` | 4 | number of AGS levels, loop size in 0x1DEBC |
| `0x887C / 0x887D` | 32 / 129 | lower point limit for D / S |
| `0x8878 / 0x8879` | 128 / 255 | upper point limit for D / S |
| `0x8884 / 0x8886` | 65 / 129 / 193 | 0x8886: level ladder (accesses to `0xFFFF9216` at 0x1DD18) |
| `0x82B0 / 0x82B1` | 78 / 1 | an input, not an AGS parameter: divisor of the transmission pedal (`0xFFFF9182` = min(254, `0xFFFF8439` × 100 / 78), code 0x215DE-0x2163C) and its rate-of-change limit (`0xFFFF917A`) |

The points `0xFFFF9216` are clamped to `[0x887C + 91CB, 0x8878 + 91CB]` (0x1DCB2, also 0x1DBA4). In D (branch 0) that is 32…128, levels 1-2 (programs P0 / P1), in S (branch 1) 129…255, levels 3-4 (P2 / P3). So in S levels 1 and 2 cannot be told apart.

Tables 0x901E-0x915E: D / S pairs, the pair is chosen at 0x1DF6C by `0xFFFF91CB`. The value is a transmission-pedal threshold (0..254) for the target AGS level, the rows are speed in n_out / 32. All 2D8, X = 1..3 (column = threshold of level 2 / 3 / 4). On the reference car the rows 31 / 62 / 94 / 125 / 156 / 188 are 37 / 73 / 111 / 148 / 184 / 222 km/h. The percentages in brackets below are value / 255 of the transmission pedal, not pedal travel.

| Gear | Branch 0 (D) | Branch 1 (S) | Y axis (n_out / 32) |
|---|---|---|---|
| 1 | `0x901E` | `0x903E` | 20, 28, 32, 38, 44, 50 |
| 2 | `0x905E` | `0x907E` | 31, 47, 62, 68, 76, 85 |
| 3 | `0x909E` | `0x90BE` | 62, 77, 94, 105, 116, 125 |
| 4 | `0x90DE` | `0x910E` | 63, 88, 113, 125, 138, 147, 156, 166, 181, 188 |
| 5 | `0x913E` | `0x915E` | 31, 63, 94, 125, 156, 188 |
| none | `0x917E` 6×6 | | role not traced (adjacent, read through the same catalog) |

Stock values (columns 1 / 2 / 3):

| Gear | Branch 0 (D) | Branch 1 (S) |
|---|---|---|
| 1 | 153 / 230 / 252 (60 / 90 / 99 %) everywhere | 102 / 166 / 204 (40 / 65 / 80 %) |
| 2 | 153 / 230 / 252 | 64 / 115 / 179 (25 / 45 / 70 %) |
| 3 | 153 / 230 / 252, flat | 64 / 115 / 179 |
| 4 | 128, 129, 132, 134, 137, 139, 144, 151, 172, 191 / 242 / 252, **rises** with speed | 64…88 / 97…141 / 128…204 |
| 5 | **230** / 242 / 252 (90 %) everywhere | 64 / 115 / 179 |

The earlier conclusions about the clutch drawn from these tables are withdrawn: "while cruising in 5th the clutch never leaves stage 1" and "the lockup limit at 114 km/h is the breakpoint of the 4th-gear axis" described AGS, not the lockup. The clutch thresholds are in 0x993A (§3).

**How the presets changed it (v10, v18-v20, doc 08).** Branch 0: column 1 lowered to 102 (40 %) from speed row 62 (2nd, 3rd), 113 (4th), 94 (5th). Branch 1: column 1 lowered to 26…38 (10-15 %) with a gentler entry in the lowest rows. The "home" points 0x888C became 32 / 128 / 176 / 240, the growth rate 0x88C0 became 7, the decrease step 0x88B0 -10 / -20 / -40. This was meant as an earlier and firmer clutch lock. In fact the edits change AGS: level 2 in D is pulled towards 128 instead of 96, the S levels towards 176 / 240 instead of 160 / 224, the points grow at 7 instead of 5. D at 40-60 % pedal holds level 2 (P1) longer and without 5th, S holds level 4 longer and drops from it more slowly. These edits do not touch the converter clutch.

The measurement from the earlier §1 (manual mode, 3rd gear, pedal 225/255, 100-142 km/h: slip 128, 256, 160, 128, 96, 64, 0, 0 rpm "with the stage unchanged") shows the work of the real clutch (§2-§4), not an AGS level.
