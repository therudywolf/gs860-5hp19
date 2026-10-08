# 13 · Ready-made patches: TCC in 1st, early lock-up, warm-up, no 5th in S, shift rpm, kick-down, manual mode

The seven most requested edits are implemented by `tools/egs_patch.py` for both programs: GS8.60.0 (19C0 / 19D0, 256 KB image) and GS8.60.4 (20C0, 512 KB image). Each one rests on code: every address below comes with the instruction that reads it. Three presets are built from the patches, document 14.

TCC below is the torque converter clutch (lock-up, document 03).

## In short

| What you want | Patch | 19x0 (256 KB) | 20C0 (512 KB) | § |
|---|---|---|---|---|
| converter locked in 1st gear | `tcc-first` | mask `0x8978`, 52 bytes of code at `0x3E3A0`, group table `0x3E380`, call from `0x290A0`: full flash only | group 12 (`0x71AD0`) and group bytes `0x70970`, calibration only | 1 |
| converter locked early and with any pedal | `tcc-lock` | groups 6-9 of table `0x993A`, bytes `0x897E` | groups 5, 8, 9, 10 of table `0x71996`, bytes `0x70970` | 2 |
| no warm-up program | `no-warmup` | `0x8B48` = 0 | `0x70BAC` = 0 | 3 |
| S without 5th | `s-no5` | matrices k11, k15 (`0x9682`, `0x9842`), `0x887D` | matrices k11, k15 (`0x716DE`, `0x7189E`), `0x70891` | 4 |
| full-throttle shift rpm in S and D | `shift-wot` | matrices k11, k15, k14, k6 | the same k, minus the addition `0x70B98` | 5 |
| no kick-down | `no-kickdown` | `0x8D1A`, `0x8246` | `0x70D6A`, `0x70232` | 6 |
| M does not shift by itself | `manual-hold` | matrices k10, k8, monitor `0x8B44` | matrices k10, k8, monitor `0x70BA8` | 7 |
| a sporty S on the part throttle | `s-sport` | k11, k15 (pedal 60-242) | k11, k15 (pedal 60-242) | 9 |
| hard / gentle shifts by load | `shift-feel` | - | target slip times and on-coming pressure of the records `9824`, `9834`, `0x7B94D` | 10 |
| gate: S first or M at once | `gate` | `0x8975` | `0x70966` | 8 |

```
python3 tools/egs_patch.py list                          # what each patch does, the presets, the reference engines
python3 tools/egs_patch.py show my_dump.bin              # these cells in your image, TCC per program, full-throttle points
python3 tools/egs_patch.py apply my_dump.bin -o build.bin no-warmup tcc-lock manual-hold --cut 6720
python3 tools/egs_patch.py apply my_dump.bin -o build.bin tcc-first:modes=S+M,rpm=1760 s-no5 --spark 6528
python3 tools/egs_patch.py preset sport-daily my_dump.bin -o build.bin --spark 6528 --cut 6720
```

Patch parameters follow a colon: `name:key=value,key=value`. Three patches need the engine limits: `--spark` is the lower limiter (spark or soft cut), `--cut` the highest hard cut. With the converter locked the turbine runs at engine speed, so every threshold below is in turbine rpm.

## 0. How the tool works

1. It recognises the program by the image size and the SHA-256 of the code (19x0: `0x10000–0x40000`, 20C0: `0x08000–0x70000`). Other software, for example BMW GS8.60.4 `15C0`, is refused: its addresses differ.
2. It checks the loader and program checksums of the input. If they do not match, the read is damaged or the program modified: stop.
3. Before writing it checks what the patch relies on: table headers and axes, factory values, free TCC groups, free space for code. Any mismatch stops it with an explanation.
4. It writes only the calibration. The one exception: `tcc-first` on 19x0 adds 52 bytes of code (§1).
5. It recomputes all three checksums, checks that not a byte changed outside the calibration and the declared code, and writes `out.bin` and `out.log`: every changed byte with its reason, old and new checksums, SHA-256. On 19x0 without a code change it also writes the 32K partial (`out_partial32k.bin`). On 20C0 no partial is written: what the flasher reads and writes as a GS8.60.4 Partial is not checked (document 11).
6. `--dry-run` prints the log and writes nothing.

Read document 07 before flashing. Reset the adaptations after flashing.

## 1. Converter locked in first gear (`tcc-first`)

**Factory behaviour.**

- 19x0: the clutch never locks in 1st. The upper lock-up level `0x29056` lets a gear through only when its bit is set in the mask `[0x8978]` = `0x003C` (2nd-5th, `0x29066-0x29078`). The threshold group byte is `[0x897E + 4 × program + gear − 2]` (`0x29088-0x290A8`); for 1st this is the 5th-gear byte of the previous program, so the mask alone cannot enable 1st.
- 20C0: mask `[0x7096E]` = `0x007E` (gear codes 1-6, `0x25494`), group bytes `[0x70970 + 6 × program + code − 1]` (`0x255F6`). D and S use group 11 in 1st (`0x71AD0`): threshold 202 (never) at pedal 0-224, and open 10, slip 11, lock 12 (n_out / 32) at 230 / 240 / 255. So with the pedal near the floor the clutch locks in 1st from 1407 turbine rpm, never at part throttle. BMW 15C0 locks there only in the kick-down row, from 1994.

**What the patch does.** It sets its own 1st-gear thresholds: lock from `rpm` turbine rpm on a light pedal, later with more pedal (the steps of the WOLF4X v41-v44 builds the owner's E39 runs on). With the pedal released (pedal rows 0 and 5) it does not lock, so braking in 1st opens the clutch at once (`coast=1` turns that off).

| Parameter | Default | What |
|---|---|---|
| `modes` | `S+M` | `M`, `S+M` or `D+S+M` |
| `rpm` | 1760 | lock turbine rpm in S and M on a light pedal |
| `rpm_d` | `rpm` + 350 = 2110 | the same for D |
| `coast` | 0 | 1: lock with the pedal released too |

Thresholds in the pedal axis rows (open / slip / lock, turbine rpm in 1st, 1 unit = 117 rpm). The pedal axis is 0 / 5 / 46 / 59 / 72 / 97 / 122 on 19x0 and 0 / 5 / 46 / 59 / 72 / 224 / 230 / 240 / 255 on 20C0:

| Pedal row | S and M (rpm 1760) | D (rpm_d 2110) |
|---|---|---|
| 0, 5 | never | never |
| 46 | 1290 / 1525 / 1759 | 1407 / 1759 / 2111 |
| 59 | 1407 / 1642 / 1876 | 1525 / 1876 / 2228 |
| 72 | 1525 / 1759 / 2111 | 1642 / 1994 / 2463 |
| 97 (19x0) | 1642 / 1994 / 2346 | 1759 / 2111 / 2580 |
| 122 (19x0), 224 (20C0) | 1759 / 2111 / 2463 | 1876 / 2228 / 2697 |
| 230, 240, 255 (20C0) | factory 1173 / 1290 / 1407 | factory 1173 / 1290 / 1407 |

- **20C0**: calibration only. S and M (P2, P3, PB, PD) are moved to group 12, which no factory program uses; its rows are written from the table above, the near-floor rows (230+) never later than the factory group 11. With `D` the rows of group 11 are rewritten for D, the near-floor rows stay factory. The patch refuses if group 12 is already in use.
- **19x0**: mask `0x003C` → `0x007E`, one free factory group for S/M and one for D (5 and 10 are free in the factory calibration), a "1st-gear group per program" table at `0x3E380` and 52 bytes of code in `0x3E380–0x3E3FF` (filled with `0xFF` there). At `0x290A0` three factory instructions become `jsr 0x3E3A0` and three `nop`: the code does what the factory instructions did and takes the group from the table for 1st (and code 6). These are the bytes of the WOLF4X v41-v44 builds (checked byte by byte). The code changes, so **flash the full image only**: a 32K partial would carry the mask without the code and 1st would read a wrong group. The tool writes no partial in this case.

The lower level still keeps the clutch open when the clutch automaton says so: on 19D0 with cold ATF (below raw 70, about 22 °C, document 03 §4), on 20C0 with engine speed not above field f24 of root `0xFFFF9808` (1000 or 820 rpm by record, `0x4A766`, document 11 §6).

## 2. Converter locked early and with any pedal (`tcc-lock`)

**Factory behaviour.** The upper level compares n_out / 32 with the three thresholds of a group (document 03 §2-3): below "open" the clutch opens, above "slip" it slips under control, above "lock" it is locked. Each program and gear has its group, and the thresholds rise with the pedal. The factory D of the E39 locks 3rd from 4052 turbine rpm and 2nd from 5757; M has no lock-up in 2nd at all (document 03 §3, the table in document 12).

**What the patch does.** In 2nd-5th it sets thresholds flat over the pedal: lock from `rpm` (1600 turbine rpm by default), slip from `rpm` − 385, open below `rpm` − 512 (the WOLF4X v25 values). Pressing the pedal does not open the clutch. The lock threshold is never later than the factory one of S (P3) and M (PB) at any pedal.

| Parameter | Default | What |
|---|---|---|
| `modes` | `S+M` | `M`, `S+M`, `D+S+M` |
| `rpm` | 1600 | lock turbine rpm, 1300-3500 |
| `d_gears` | `3-5` | for D: `3-5` or `2-5` |

Groups the patch writes: 6, 7, 8, 9 on 19x0 (only PB and PD use them in the factory calibration), 5, 8, 9, 10 on 20C0 (only PB). If another program uses them in your calibration, the patch refuses.

Result on the reference images (turbine rpm, open / slip / lock): 2nd 1087 / 1215 / 1599, 3rd 1081 / 1216 / 1621, 4th 1088 / 1216 / 1600, 5th 1092 / 1211 / 1543 (19x0, capped by the factory S) or 1591 (20C0).

What it gives: in S and M the car drives "direct", without converter slip, and the ATF runs cooler (document 03 §3: in town the E39 D almost never locks). The price: at low rpm under load the engine vibration comes through. On 20C0 the addition `0x70B98` to the upshift threshold acts while the converter is locked (§5); manual shift points must allow for it.

## 3. Warm-up program (`no-warmup`)

**What it is (proven by code on 06.10.2026).** After power-on the ECU runs a warm-up program: 19x0 `0x28D50`, flag `[0xFFFF90EE]` (set at `0x15F82`); 20C0 `0x25182`, flag `[0xFFFF9088]` (set at `0x10994`). While the flag is set:

- the shift matrices see max(pedal, table) instead of the pedal (19x0 `0x24B66`, 20C0 `0x2072A`). The table `0x8142` / `0x7013A` is indexed by engine temperature and program: P0, P1 and P7 = 102 (40 % pedal) up to 55 °C, 0 from 65 °C. So on a cold engine D upshifts as if the pedal were at 40 %, that is later;
- on 19x0 the program arbiter gets request 8, program P0 (`0x231F8`); in M the program code has a higher priority and the request does not act. AGS reads the flag too (`0x1DC1E`).

The engine temperature comes from the DME over CAN (byte × 3 / 4 = °C + 48: 19x0 `0x21696`, 20C0 `0x1CE44`). The warm-up ends when n_out / 32 reaches `[0x8B48]` / `[0x70BAC]` = 48 (1536 output rpm, about 57 km/h on an E39 523i), on a DME signal over CAN, when a counter set by the temperature at power-on runs out (`0x9A6E` / `0x71B52`: 170 / 90 / 55 / 0 at 35 / 45 / 55 / 65 °C), or when the table gives 0. The data are the same on 19x0 and 20C0.

Until 06.10.2026 the table `0x9A6E` was called an "ATF thermal derate" in document 05 and in the catalogs. That is wrong: its temperature is the engine temperature at power-on, and the table is the counter of the warm-up program.

**What the patch does.** `[end]` = 0: the condition "n_out / 32 not below 0" holds at once and the program ends in the first cycle. One byte: 19x0 `0x8B48`, 20C0 `0x70BAC` (each has one reference in code: `0x28D6E`, `0x251A0`). The patch refuses unless the byte is the factory 48 (`force=1` writes anyway).

Why BMW runs the warm-up program is not established by code: it depends only on the engine temperature and ends by 65 °C. Without it a cold engine gets earlier upshifts.

## 4. S without 5th gear (`s-no5`)

S is programs P2 and P3 (matrices k11 and k15); the AGS level picks between them (documents 01 §5, 11 §5).

**What the patch does.**

1. 4>5 = 255 in every row of k11 and k15: S never shifts into 5th.
2. 5>4 = the threshold at which a downshift from 5th lands 4th at least 500 rpm under the spark cut (`--spark`). Moving the lever from D to S in 5th drops to 4th at once if n_out is below the threshold. On the reference engines the threshold is 5984 (M52TUB25, spark 6496) and 6016 (M54B30, spark 6528) turbine rpm in 4th.
3. `pin=1` (default): the lower AGS points bound in S `0x887D` / `0x70891` 129 → 193. S stays on level 4 (P3, k15), and neither the D replacement PF nor the hill step 2 acts in S (document 01 §5). `pin=0` leaves AGS factory.

## 5. Shift rpm in S, D and other maps (`shift-wot` and by hand)

**Unit.** A matrix value is n_out / 32 (document 02 §3). Turbine rpm at the threshold = value × 32 × ratio (1st 3.665, 2nd 1.999, 3rd 1.407, 4th 1.000, 5th 0.742). Backwards: value = turbine rpm / (32 × ratio), rounded down. The final drive and the wheels do not enter.

| Mode | Programs and matrices | 19x0 | 20C0 |
|---|---|---|---|
| D | P0 = k14, P1 = k6 | `0x97D2`, `0x9452` | `0x7182E`, `0x714AE` |
| S | P2 = k11, P3 = k15 | `0x9682`, `0x9842` | `0x716DE`, `0x7189E` |
| M | PB = k10, PD = k8 at overheat | `0x9612`, `0x9532` | `0x7166E`, `0x7158E` |

Matrix k lives at `0x91B2 + k × 0x70` on 19x0 and `0x7120E + k × 0x70` on 20C0. Columns 1-4 are the upshifts 1>2…4>5, 5-8 the downshifts 2>1…5>4. Rows are the gearbox pedal, D and S axis 0 / 46 / 83 / 121 / 160 / 198 / 203 / 243 / 244 / 254 / 255, row 255 is kick-down. The XDF of both units carry the role in the matrix titles.

**Rules (document 02 §4).** The upshift command comes 1120 / 610 / 490 / 400 rpm before the spark cut for 1>2 / 2>3 / 3>4 / 4>5: the engine keeps revving while the shift runs. A downshift lands at least 500 rpm under the spark cut and at least 6 units under the upshift. On 20C0 with the converter locked the upshift threshold gets `0x70B98` = 4 / 2 / 2 / 5 units for 1>2…4>5 (1-2 later by 469 turbine rpm, 2-3 by 128, 3-4 by 90, 4-5 by 160; document 11 §5).

**The patch `shift-wot`** writes the pedal rows 243-255 of the chosen mode's matrices by these rules, keeps the rows below 243 from rising above the new points, and keeps the downshifts under the upshifts and under the spark cut. On 20C0 the addition is subtracted: with the converter locked the command comes exactly by the rule, with it open earlier by the addition.

| Parameter | Default | What |
|---|---|---|
| `modes` | `S` | `S`, `D`, `D+S` (M is set by §7) |
| `rpm` | by the rule | `a/b/c`: command turbine rpm of 1>2 / 2>3 / 3>4 directly, at least 200 under the spark cut |

Result on the reference engines, turbine rpm at the command for 1>2 / 2>3 / 3>4: M52TUB25 (spark 6496) 5278 / 5885 / 5988; M54B30 (spark 6528) 5395 / 5885 / 6033 with the converter locked, 4926 / 5757 / 5943 with it open.

**By hand.** Open the matrix in TunerPro (XDF from `xdf/`), compute the value by the formula above, then check:

```
python3 tools/egs_tables.py shift build.bin --turbine        # all 16 matrices in turbine rpm
python3 tools/egs_tables.py verify-shift build.bin --spark 6528 --cut 6720 --stock my_dump.bin
python3 tools/gs860_crc.py fix build.bin build_fixed.bin     # after editing in TunerPro
```

`verify-shift` checks D, S and M by the roles from code (on 20C0 with the locked addition) and with `--fix out.bin` lowers whatever breaks the rules.

## 6. No kick-down (`no-kickdown`)

**Factory behaviour.** Kick-down is a flag (19x0 `[0xFFFF9113]`, function `0x205FC`; 20C0 `[0xFFFF90B7]`, `0x1BC9C`). A byte selects its source:

- 19x0 `[0x8D1A]`, 0 on the E39: the switch under the pedal (bit 7 of port `0xFFFF89BE`, active low) and gearbox pedal above `[0x8246]` = 230; not 0: the DME bit over CAN.
- 20C0 `[0x70D6A]`, 1 in the Alpina B3S file: the DME bit over CAN (`[0xFFFF90BA]`); 0: the switch and pedal above `[0x70232]` = 230.

With the flag the matrices use row 255 (19x0 `0x24B34`, 20C0 `0x206F8`), AGS is not updated (19x0 `0x1DEC4`, 20C0 `0x1908C`) and the manual M branch is skipped (19x0 `0x2492C`, 20C0 `0x2047E`): in M the +/- buttons do not work with the pedal on the floor.

**What the patch does.**

- `scope=all` (default): source = 0 (switch), threshold = 255. The gearbox pedal never exceeds 254, so the flag is never set. With the pedal floored row 254 applies, and the M buttons work with the pedal floored. Two bytes.
- `scope=M`: the flag stays, but in the M matrices row 255 becomes equal to row 254, so kick-down does not downshift in M. The M buttons still do not work with the pedal floored.

## 7. M without automatic shifts (`manual-hold`)

**Factory behaviour.** M is PB (k10), PD (k8) at overheat. In M the matrix still acts: the up columns give automatic upshifts, the down columns automatic downshifts, row 255 kick-down (document 02 §5). The factory M of the E39 upshifts by itself from 5747 / 6077 / 6168 turbine rpm, i.e. before the M52TU limiter. The Alpina 20C0 from 5160 / 6525 / 6799 / 6752. Protection from over-revving on a manual downshift comes from the minimum-gear table (19x0 `0x8AE2`, 20C0 `0x70B3C`), not from the matrix, and the patch does not touch it.

**What the patch does.** The M upshift thresholds go at least 150 rpm above the hard cut `--cut`: under power the engine hits the cut and the box holds the gear. Upshifts remain only on the overrun, when the wheels drive the turbine above the cut. The thresholds stay at least 100 rpm under the turbine monitor (document 05 §6: turbine at or above it for about a second gives fault 0x25 and limp mode). On 20C0 the addition `0x70B98` is counted where M can hold the clutch locked with the pedal released. The kick-down row does not downshift in M (`kd=0`).

| Parameter | Default | What |
|---|---|---|
| `monitor` | factory | `auto`: raise the monitor just enough for the thresholds to sit above the cut; a number: your own, at most 7232 (the factory value of Alpina 19x0 and 20C0) |
| `up` | `guard` | `never`: 255, no overrun protection (the wheels can drive the engine past the cut) |
| `kd` | 0 | 1: kick-down downshifts in M as in the factory |

Result on the references, turbine rpm of the automatic upshift 1>2 / 2>3 / 3>4 / 4>5: M52TUB25 (cut 6592) 6802 / 6781 / 6754 / 6752, monitor `0x8B44` 6720 → 6912; M54B30 (cut 6720) 6920 / 6909 / 6889 / 6880, the 20C0 monitor 7232 unchanged.

A trap right here: take the **highest** hard cut (on the M54 it depends on the gear). If a threshold lands under the real cut, M upshifts by itself on the limiter.

## 8. Gate: S or M at once (`gate`)

The program byte of the left gate before the first +/- tap: 19x0 `0x8975` (`0x230D8`), 20C0 `0x70966` (`0x1EB88`, `0x1EBE4`).

- `0xFE` (BMW 19C0 and BMW 15C0): the gate gives S first (P2 / P3 by AGS level), the first +/- tap switches to M.
- `0x0B` (Alpina 19D0 620P and 20C0): M (PB) at once.

`gate:mode=S` writes `0xFE`, `gate:mode=M` writes `0x0B`. 20C0 has a second byte, `0x70967` = 3 (P3), used when `[0xFFFF918C]` = 2 (bits 0-1 of byte 2 of CAN `0x338`, meaning of the value not established); the patch leaves it.

## 9. A sporty S (`s-sport`)

**Why.** In the Alpina 20C0 file the matrices of S (P2 = k11, P3 = k15) are almost the same as D (k14, k6): the same points at pedal 83-203. The Alpina gate gives M at once (`0x0B`), so the file never needed a sport program. After `gate:mode=S` the S level would only differ from D by the patches `s-no5` and `shift-wot`, which touch the full-throttle rows. `s-sport` makes S sporty also on the part throttle.

**What it does.** For pedal 60-242 the upshift points of the S matrices move from the factory point toward the full-throttle point of the same matrix (the row of pedal 243, which `shift-wot` has put under the limiter): 20 % of the way at pedal 83, 35 % at 121, 50 % at 160, 65 % at 198, 67 % at 203, interpolated between. The downshift points move toward the full-throttle downshifts by `down=0.35` of that way and stay at least 6 units under their upshift (no hunting). The rows 0-46 (cruising) and 243-255 are not touched, the 4>5 column stays 255 after `s-no5`. `strength=` (default 1) scales the weights.

Order in a chain: after `shift-wot` and `s-no5`. Works on both platforms. On a file whose S is already sporty (BMW factory) it would shift S even higher: lower `strength`.

Example on the 20C0 file of Alpina B3S (turbine rpm, converter open): pedal 160, 1>2 / 2>3 / 3>4 = 2228 / 2751 / 2927 in D, 3518 / 4286 / 4412 in S.

## 10. Shift hardness by load (`shift-feel`, 20C0)

**What decides the hardness.** The hydraulic records (pressure, times, slip controller) are chosen by the shift type and the load class; the selector `0x41842` does not read the program D / S / M, and the variant byte `[0xFFFF93C0]` comes from the shift state, not from the program (document 11 §9). So "hard M, sporty S, gentle D" cannot be made by separate tables; the same tables apply to every program. What differs is the load: D shifts at light load, S and M near the limiter at full throttle. The patch makes the tables follow the load.

**What it does.** 20C0 only.

- The target slip time of the shifts under load (5 tables of the upshifts, 13 of the downshifts, 3 rows of turbine torque, ticks of 10 ms) is scaled by the row: the light row `up_soft` / `dn_soft` (default 1.20 / 1.15, longer = gentler), the middle row 1, the heavy row `up_hard` / `dn_hard` (0.80 / 0.85, shorter = crisper), not below `up_min` / `dn_min` (28 / 15 ticks). The garage shifts (N to D, type 0>2) and the downshifts 2>1 are not touched.
- The pressure of the on-coming element in the slip phases of the upshifts under load (4 tables 8x10 of the types 1>2 to 4>5) rises by `press` (default 0.10) on the upper torque rows, linearly from row `ramp` (3) to the last; the first three rows stay as they are.
- The upper bound of that pressure (13 bytes `0x7B94D`-`0x7B960`) is raised by `bound` (1.10), otherwise the slip controller would stay under the old cap.

**What is proven and what is not.** The tables and the axes are proven by the code (document 11 §9); the slip time is the target of the controller, so a shorter target makes it raise the pressure by itself. The pressure units are not established; that "a larger byte is a higher pressure" follows from the tables rising with the torque. Whether the packs of a given box take the change is not known: the first drive needs a log (ATF, turbine, gear, converter state).

## 11. What the patches do not do

- They do not touch the hydraulics (except `shift-feel` on 20C0, section 10), table axes, the loader or the identification. The list of don'ts is document 09.
- They do not raise the turbine monitor above 7232 and do not touch the voltage monitor (`0x8EE8…`, `0x70F32…`: those are millivolts, document 05 §1).
- They do not work on other software (15C0 and the rest): other addresses, the tool refuses.
- The presets as a whole are not road-tested (document 14). On 19x0 the counterparts of `tcc-lock`, `tcc-first`, `s-no5` and `manual-hold` are flashed on the reference E39 (WOLF4X builds v24-v44), the converter lock-up in 1st is not confirmed by a log yet. Check with a log (document 06).
