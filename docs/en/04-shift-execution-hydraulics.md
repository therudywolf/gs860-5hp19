# 04 · Shift execution: hydraulics, phases, pressures

Reverse of module **0x34000–0x39600** (10 ms task) on the stock 19D0 dump. Anything not confirmed by bytes or code is marked "hypothesis". Units: pressure — raw 0..255 (then `×50` → EDS channel via `0x2E41C` → current/PWM in `0x2E296`); time — ticks of **10 ms**.

## 1. Time units

Δt for the shift timers is computed like this (0x2DBC2):

```
02dbc6  move.w $ffff97ba, d0    ; task time in ms (copy of 0xFFFF82A2)
02dbd2  sub.w  (a4), d0         ; − previous
02dbec  addq.w #5, d0
02dbee  divu.w #10, d0          ; (Δt + 5) / 10
02dbf2  move.w d0, $ffff94d0    ; = number of 10 ms ticks
```

0x340F2 adds `0xFFFF94D0` to the timers `0xFFFF9674` (since start of slip), `0xFFFF969C` (since start of shift), `0xFFFF969E` and to the byte phase timers `0xFFFF973D / 973E / 973F` (saturating at 255). **All times in the tables are in 10 ms ticks.**

## 2. Pointer records: how the module finds its tables

Hydraulic calibrations are not read directly but through **records** of 32-bit pointers. Root `0xFFFF94F8 → 0x3CBCC`; its first word is the directory `0x3CBBA` of four **sets** (kind):

| kind (`0xFFFF971B`) | Directory | Records × fields | Meaning |
|---|---|---|---|
| 0 | `0x3CBA0` | 6 × 34 | Schub-Hoch — upshift without load |
| **1** | `0x3CB3A` | 6 × 78 | **Zug-Hoch — upshift under load** |
| 2 | `0x3CB7A` | 9 × 42 | Schub-Rück — downshift without load |
| **3** | `0x3CB54` | 9 × 73 | **Zug-Rück — downshift under load (kickdown)** |

Directory format: `[u16 n][n × ptr32 to record]`; a record is an array of fields `f00, f01, …`, each a `ptr32` to a table, 1D curve or byte in the calibration window. kind1 records are at `0x3B372, 0x3B4AA, 0x3B5E2, 0x3B71A, 0x3B852` (record 0 = record 1), kind3 at `0x3BF72 … 0x3C76E`, kind2 at `0x3B98A …`, kind0 at `0x3C892 …`.

**Record index = transition type** `0xFFFF971A` from the 7×7 matrix `0x12FDC[from−1][to−1]`:

```
1→2 = 2   2→3 = 3   3→4 = 4   4→5 = 5   2→1 = 2   3→2 = 3   4→3 = 4   5→4 = 5
3→1 = 6   4→2 = 7   5→3 = 8   6(N)↔2 = 1
```

So an address "family" in the catalog is **the same record field for different transitions**: e.g. kind1 f32 = `B6BC (type 0/1), B656 (1↔2), B80A (2↔3), B974 (3↔4), BADE (4↔5)`.

Set selection (0x343B6 → 0x3425E):

- direction `0xFFFF9748` from `0x12FAA` (1 up, 2 down, 3 down skipping a gear);
- class `0xFFFF9722` (0 = Schub, 1 = Zug) from `0x2E4A8`: load `0xFFFF97EA` ≥ threshold (tables of set `0x3CD18` by ATF and n_out) or n_out below a threshold → Zug;
- `kind = 0x13012[class·4 + direction]`: class 0 → up kind0, down kind2; class 1 → up kind1, down kind3.

The module **does not read** the branch flag `0xFFFF91CB`: the hydraulics are the same for D and S/M.

## 3. Module inputs (snapshot every 10 ms, 0x39516–0x397DC)

| RAM | Source | Meaning |
|---|---|---|
| `0xFFFF97B4` | filter of `0xFFFF8DE2` | turbine speed; `0xFFFF97E2` = /32 (byte) |
| `0xFFFF97B2` | filter of `0xFFFF8DA8` | output shaft speed n_out; `0xFFFF97E4` = /32 |
| `0xFFFF97A0 / 97A4` | `0xFFFF8D96` via 0x2DFBA / 0x2DFE0 | engine torque, Nm; `0xFFFF97DF = 97A0/4 + 25`, `0xFFFF97E0 = 97A4/4 + 25` — **Y axis of the maps** |
| `0xFFFF97E5` | `0xFFFF90D0` | ATF, raw (axis of many 1D curves, 10…170) |
| `0xFFFF97E9` | `0xFFFF9182` | pedal |
| `0xFFFF97E8 / 97EA` | `0xFFFF9173` → 0x2E082 | load (Zug/Schub class) |
| `0xFFFF9595 / 0xFFFF9716` | — | actual / target gear (7 = undefined, 6 = N/R) |
| `0xFFFF9725` | snapshot of `0xFFFF97E2` at start (0x3446C) | turbine/32 at shift start — **X axis of the pressure maps** |

**Axes of all 8×10 / 3×3 / 4×4 maps: X = turbine speed / 32** (snapshot at start or current), **Y = engine torque / 4 + 25** (Y = 85 → 240 Nm, Y = 125 → 400 Nm). Tables with neutral 128 are signed corrections (`lookup − 128`, 0x2E462).

## 4. Shift start

0x39238 → 0x3911E → 0x343B6 / 0x35114:

```
039296  move.b (a3), d0          ; target 0xFFFF9716
039298  move.b (a5), d1          ; actual 0xFFFF9595
03929a  jsr $34b00               ; permission
039312  jsr $39086               ; delay from root [$80/$84/$88] against 0xFFFF969C
03932a  jsr $3911e               ; START
039186  move.b d6, $ffff9717     ; = 1 "shift in progress"
03918c  move.b d6, $ffff9718     ; = 1 "pressure sequence in progress"
```

Record times are computed immediately: `0xFFFF9684 = f02(ATF)` (total time), `0xFFFF9688 = 9684 − f03`, `0xFFFF9692 / 9694 = f05 / f06(ATF)` (gear-recognition timeouts), `0xFFFF9686 = f04(ATF)`; for upshifts (0x35494, **always from kind1**): `0xFFFF968E = f10(ATF) + f08 + (f12(n_out) − 128)` = **fill time**, `0xFFFF9690 = 968E + f43(n_out) + root[$7C] + f27`.

## 5. Phases

Phase driver 0x36340 (every 10 ms): while 0x3565A ("phase complete") = 1 → step `0xFFFF976B`++ → new phase from **`0x13034[step·5 + kind]`** → 0x35978 (entry: duration `0xFFFF96A8`, pressure base `0xFFFF96AC`) → phase timer `0xFFFF973D` reset; then 0x35DBE computes the on-coming clutch pressure → `0xFFFF9720`.

Table `0x13034` (rows = step, columns = kind0..3 + special):

```
step0: 0 0 0 0 0    step1: 1 1 1 1 1    step2: 2 2 2 2 2    step3: 3 3 3 3 3
step4: 6 4 5 8 0    step5: 6 9 9 8 0    step6: 6 10 10 8 7  step7: 13 11 11 12 13   step8: 255…
```

kind1 (load upshift): **0 → 1 → 2 → 3 → 4 → 9 → 10 → 11**. kind3: 0→1→2→3→8→8→8→12. kind2: 0→1→2→3→5→9→10→11. kind0: 0→1→2→3→6→6→6→13.

| Phase | Duration `0xFFFF96A8` | Exit (0x3565A) | On-coming pressure (0x35DBE) | Physics |
|---|---|---|---|---|
| 1 | f08 (byte; 1→2: 0, 2→3: 6) | timer ≥ duration | 0x30248(from) if `0x9756 == 1`, else 0 | pause / preparation |
| 2 | kind1: `0xFFFF968E − f08` = fill time; kind3: f31 / f12(n_out) + f10(ATF) + adaptation f11 | timer ≥ duration | `0xFFFF96AC` (= **f13(ATF)** fast-fill pressure) + `0xFFFF968C` | **fast fill (Schnellfüllung)** |
| 3 | root[$7C] = 1 tick | timer ≥ and `0x9756` | 0 | separating tick |
| 4 | **f27** (byte: 1→2 12, 2→3 11, 3→4 15, 4→5 12 → 110–150 ms) | timer ≥ **or** flag `0xFFFF96A6` | (f28(load) − 128) + **f14(t)** + `0xFFFF96AC` (= f15(ATF) + adaptation 0x2AC6A + `0xFFFF9480`) | **approach to the kiss point (Füllausgleich)** |
| 9 | **f43(n_out/32)** (1→2: 15–28; 3→4 / 4→5: 20 → 150–280 ms) | timer ≥ duration | **f32(turbine at start, torque)** + (f33(t) − 128) + `0xFFFF96AC` (= f29(ATF) + `0xFFFF9668`), ramped from the previous value over `0xFFFF96A8`, clamped to f23..f24 | **start of slip — open-loop pressure** |
| 10 | f31 (if root[$9C]) | \|slip\| ≤ **f44** (u16 = 100 rpm) → synchronised | as 9 + `0xFFFF96AE` (slip-time controller) + `0xFFFF968C`, clamped to f23..f24 | **controlled slip to sync** |
| 11 | — | timer ≥ duration | f32 + (f33(t + `0xFFFF96AA`) − 128) + **f30(t)** (0 / 10 / 255) + bases | **squeeze to full pressure** |
| 12 (kind3) | f46 | timer ≥ duration | f00 or 255 | end of downshift |

End of shift (0x3504C → 0x34ECC → 0x34FA8): `0xFFFF969C ≥ 0xFFFF9684` (f02) or the actual gear (by ratio, `0xFFFF9747`) became the target and timeouts f05 / f06 elapsed → `0xFFFF9717 = 0`, `0xFFFF9716 = target`; `0xFFFF9718` clears when the pressure sequence finishes.

## 6. Slip-time controller (0x347DE, 0x364A2, 0x36612, 0x36678)

```
0347fe  move.w $ffff97b2, d0    ; n_out
034804  muls.l d1, d0           ; × i(target) from 0x12F9C (×1000)
034808  divs.l #1000, d0
034812  move.w $ffff97b4, d1    ; − turbine
034828  move.w d0, (a1)         ; 0xFFFF966C = slip to target sync, rpm
```

0x364A2: fraction of remaining slip `d7 = (turb·1000 − n_out·i_target) / (n_out·(i_from − i_target))` (0…1000); then:

```
036564  move.l $b4(a0), -(a7)   ; kind1: f45 = 3×3 (BFB0 / BF9C / BFEC / C028 / C064)
036568  move.b (a4), d0         ; X = 0xFFFF97E2 turbine/32
03656a  move.b (a2), d1         ; Y = 0xFFFF97DF torque/4+25
03656c  jsr $2ca2a              ; 2D lookup
0365c4  muls.l d7, d0           ; × remainder/1000
0365da  move.b d0, (a5)         ; 0xFFFF9737 = target remaining time
0365e6..0365fe                  ; 0xFFFF96B6 = 0xFFFF966C·100 / 0xFFFF9737 — required gradient
```

kind3: f33 (`0x84`) when `0xFFFF972C ∈ {3, 4}`, else f69 (`0x114`); kind2: f41 — 1D by turbine. 0x36678: deviation (estimated remaining time 0x36612 − target) outside dead band f16 → coefficients f17 / f18 → gradient correction → `0xFFFF9670` → pressure increment `0xFFFF96AE`.

**Conclusion: the 3×3 tables are the target slip-phase time.** Unit — same as the timers, 10 ms (hypothesis by dimension: 40–80 → 400–800 ms at low torque, 26–40 in 5th and on downshifts — consistent with a real 5HP19). A smaller value → the controller demands a steeper pressure gradient → quicker and firmer.

## 7. Off-going clutch pressure (0x37664 → 0x37728…0x38218)

```
037b2e  move.l $d4(a0), -(a7)   ; kind1 f53 = BCAE / BD14 (3↔4)
037b34  move.b $ffff97df, d1    ; Y = torque
037b3a  jsr $2ca2a
037b5c  cmp.w d7, d0            ; ≤ f47 (0xBC; max 82 / 104)
037b78  move.b d0, $ffff9783    ; off-going pressure
```
```
038168  movea.l $b4(a0), a0     ; kind3 f45 = B73E / B7A4 / B90E / BA78 / BBE2 / B88C / B9F6 / BB60
03816e  move.b $ffff9725, d0    ; X = turbine/32 at start
0381a4  movea.l $c0(a0), a0     ; + (f48(t) − 128)
```

Output: 0x353F6 / 0x37664 → EDS channel by `0xFFFF9756 / 9757 / 9758` (0x34DD6 picks EDS 3/4 by MV2 for 5th) → 0x38F68 (lower bound `0xFFFF9763` + f34(torque)) → 0x2E41C (channel, value × 50) → 0x2E296 / 0x2E3CE (current/PWM; for EDS1 a /50 copy in `0xFFFF958C`).

## 8. Table families — what they are physically

| Addresses (transition type) | Set / field | What | Axes | Alpina B3 vs stock |
|---|---|---|---|---|
| B6BC (0/1), **B656** 1↔2, **B80A** 2↔3, **B974** 3↔4, **BADE** 4↔5 | kind1 f32 | on-coming clutch pressure in phases 9–11 on load upshifts (Schleifdruck) | X turbine/32 31…188 (1000…6000), Y 30…125 (20…400 Nm) | X extended to 219 (7000); higher at ≥ 200 Nm (B974 at 300 Nm: 80 → 90…116), lower at ≤ 100 Nm (29 → 24); B656 at 400 Nm lower (102 → 88) |
| **BCAE** (all but 3↔4), **BD14** 3↔4 | kind1 f53 | off-going clutch pressure on upshifts (overlap, Überschneidung), ≤ f47 | same | **+8…+10 everywhere** (≈ ×1.11–1.25) |
| BC48 | kind1 f39 | 8×10, 16/30/45/46 — no read found in code | — | identical |
| BFB0 (0/1), **BF9C** 1↔2, **BFEC** 2↔3, **C028** 3↔4, **C064** 4↔5 | kind1 f45 | **target slip-phase time**, 3×3 | X 25/113/200 (800/3600/6400), Y 35/55/85 (BFEC: 25/55/85) | Y axis 85 → **95** (280 Nm); high-torque row −5…−15 %, BFEC/C028 at 6400: 53 → 26, 40 → 26 |
| B42A, B40E, B4AE, B532, B5B6 | kind1 f70 | 4×4 — semantics not found | — | strongly (×0.3–7) with other axes — **do not copy** |
| BDE0 (0/2), **BD7A** N↔2, **BE46** 2↔3 / 3→1 / 4→2, **BEAC** 3↔4, **BF12** 4↔5 / 5→3 | kind3 f32 | on-coming pressure on load downshifts | X 31…172, Y 25…175 | BE46/BEAC higher in high-torque cells (up to ×1.7 / 2.1); BD7A lower ×0.78 |
| **B7A4** (0/2 = 1↔2), **B73E** N↔2, **B90E** 2↔3, **BA78** 3↔4, **BBE2** 4↔5, B88C 3→1, B9F6 4→2, BB60 5→3 | kind3 f45 | **off-going clutch pressure on load downshifts** (release) | X 8…203 / 16…172 / 31…172, Y 25…175 (0…600 Nm) | B73E/B7A4 ×0.78, B90E down to ×0.54 (**same axes**); BA78/BBE2 — other axes; B88C/B9F6/BB60 identical |
| C0A0 (N), C0B4 (1↔2), C0C8 (2↔3, 3→1, 4→2), C0DC (3↔4), C0F0 (4↔5) | kind3 f33 | target slip time on downshifts (variant `0xFFFF972C ∈ {3,4}`) | X 0/25/94 or 25/75/125, Y 38…100 | C0B4/C0A0: 65 → 57, 55 → 47; C0C8 ×0.6 with **other axes** |
| BFC4 (N), BFD8 (1↔2), C014 (2↔3), C050 (3↔4), C08C (4↔5), C000 / C03C / C078 (skip-shifts) | kind3 f69 | target slip time on downshifts | 3×3 | C08C rows 75/100 → 25/23 (×0.5–0.7, same axes); C014/C050 other axes |
| B446, B47A, B4FE, B582, B606, B4CA, B54E, B5D2 | kind3 f65 | 6×6 — semantics not found | — | B4FE/B606 ×1.2–1.7, B582 other axes |
| B63A, B722, **B8F2** (2↔3), **BA5C** (3↔4), **BBC6** (4↔5), B870, B9DA, BB44 | kind2 f32 | on-coming pressure on no-load downshifts, 4×4 | X turbine/32, Y torque | +4…+20 % in the upper cells |
| **D6C2 / D6E2** (1↔2), **D722** (2↔3), **D782** (3↔4), **D7E2** (4↔5) | kind1 f10 | **fill time vs ATF** (7 points; 1↔2: 110 at ATF 10 → 13 at 150; × 10 ms) | X ATF raw | almost identical |
| D01E / D03E, D07E, D0DE, D13E | kind1 f13 | fast-fill pressure vs ATF (90 cold → 36–40) | X ATF | almost identical |
| D372 / D356, D3AA, D3FE, D452 | kind1 f12 | fill-time correction vs n_out (128 = 0) | X n_out/32 | identical |
| C82C / C81C, C84C, C87C, C8AC | kind1 f14 | phase-4 pressure ramp vs time (16 → 22 over 15 ticks) | X ticks | identical |
| CB96 / CB76, CBD6, CC36, CC96 | kind1 f15 | phase-4/5 pressure correction vs ATF (128 = 0; cold +16…+30) | X ATF | ≈ |
| C9F6 / C9E6, CA36, CA86, CAD6 | kind1 f29 | phase-9–11 pressure correction vs ATF (128 = 0) | X ATF | ≈ |
| D67A / D670, D684, D68E, D698 | kind1 f43 | phase-9 duration vs n_out (15…28 / 30…22 / 20 / 20 ticks) | X n_out/32 | **longer**: D670 ×1.0–1.33, D698 20 → 35 |
| E092 / E091, E094, E097, E09A (bytes) | kind1 f27 | phase-4 duration: 12 / 12 / 11 / 15 / 12 ticks | — | 1↔2: 12 → **15** |
| DF06…DF14 / DEC5…DED3 (bytes) | kind1 f23 / f24 | min / max slip pressure (20, 16, 12, 16 / 116, 138, 138, 87) | — | identical |
| DED8 / DED9 | kind1 f47 | max off-going pressure: 82 / 104 (3↔4) | — | — |
| DE5C (u16 = 100) | kind1 f44 | slip threshold ending phase 10, rpm | — | identical |
| DF34 (u16 = 20) | root $78 | slip-start threshold, rpm | — | identical |
| E113 (= 1) | root $7C | phase-3 duration | — | — |
| C206, C90C | kind3 f38 / kind2 f39 | 1D tables 5×1 / 4×1 (zeros) — **not structures**, as previously assumed | — | — |

The full field → table mapping for all records is reproduced by a script (doc 10 §4) and is baked into the XDF (categories "Hydraulics" / "Shift phases").

## 9. Torque reduction

Six 2D16 8×8 maps `0xAB0C / 0xABB0 / 0xAC54 / 0xACF8 / 0xAD9C / 0xAE40`: X = rpm 700 … 6000, Y = load 0 … 100, value = **percentage of engine torque left** during the shift (stock 25–70 %; the zero-load row is 100 or 40–60). The request goes to the DME over CAN; how deeply the DME honours it is a DME calibration matter (outside this repository). These maps are not "TCC target-slip maps", as one third-party report claimed.

## 10. Where Alpina is quicker and how

Proven from the table data and their role in code:

1. Shorter target slip time at high torque (3×3 kind1 and kind3) — the controller raises the pressure gradient → faster synchronisation.
2. Higher on-coming clutch pressure at ≥ 200 Nm (B974 / BE46 / BEAC) and **lower** at low torque — sharper under throttle, softer in town.
3. Higher off-going pressure on upshifts (BCAE / BD14 +8…10) — less sag during overlap.
4. Lower off-going pressure on load downshifts (B73E / B7A4 / B90E) — releases faster.
5. Fill time and fill pressure **untouched** (only the X axis of the pressure maps extended to 7000 for the Alpina engine).
6. Phase 9 is **longer** on Alpina — speed comes from pressure and target time, not from cutting phases.

## 11. Why the early build "v5" was undriveable

118 tables were written with **Alpina axes** and data **stock + 2 × (Alpina − stock)** (extrapolation). Consequences per code:

| What | Stock → v5 | What the code does | Symptom |
|---|---|---|---|
| 3×3 target time BFEC / C028 / C0C8 / C08C | ×0.30–0.68 at high torque, Y axis 85 → 95 | controller demands a 1.5–3× steeper gradient, pressure runs to f24 (max) | harsh 2→3 / 3→4 under throttle, jerk on 4→3 / 5→4 |
| off-going pressure on downshifts B73E / B7A4 / B90E | ×0.19–0.47 | clutch releases almost immediately | rpm flare / hang, then engagement shock |
| fill time D6C2 (1↔2) | ×0.55–1.31 per cell, other axes | under-fill → delay and bump; over-fill → shock at start of phase 4 | rough 1→2 / 2→1 |
| fill pressure D01E, corrections CB76 / C9E6 / D2FA / D30A, phase-9 duration D670 / D684 / D698 (×2.45), 4×4 B42A… (×0.2–10), 6×6 B582 (×2.4) | distorted with foreign axes | values read on shifted axes — effectively random | unpredictable vs temperature / speed |
| TCC thresholds 0x901E–0x915E, shift points 0x9222…0x9842 | Alpina axes | shifted thresholds | superimposed |

Hence rule no. 1 of the repository: **never change axes** (doc 09).

## 12. What to touch and what not — per code

Touch (high-torque rows only, axes = stock):

- **target slip time 3×3** — the main "sport" lever; the controller picks the pressure within f23..f24;
- **on-coming pressure in the slip phase (kind1 f32)** — rows ≥ 228 Nm only (Y ≥ 82); rows ≤ 100 Nm stay stock (comfort);
- **off-going pressure on upshifts (BCAE / BD14)** — up to +8…10 (Alpina level);
- **off-going pressure on downshifts (B73E / B7A4 / B90E)** — down; B90E shares axes with Alpina, so its data can be taken whole. Raising BA78 goes the wrong way (slower 4→3).

Do not touch: fill time f10, fill pressure f13, phase-4 (f27) and phase-9 (f43) durations — Alpina does not shorten them, and errors here = shock/flare (that is v5); ATF corrections (f15 / f29 / f41 / f42); min/max f23 / f24 (f24 is the shock fuse); 4×4 kind1 f70 and 6×6 kind3 f65 (semantics unproven); adaptations f11.

## 13. Diagnostic frame: bytes 12 / 17 / 20

Proven from RAM:

- **byte 17** ("clutch picture" 192 / 64 / 0 / 160) = solenoid states MV1 / MV2 / MV3 in bits 7 / 6 / 5 — matches table `0x12E30` (3 MV × 7 gears × 2 modes, read by 0x30312 → 0x2E372 → RAM `0xFFFF9518…951A`): 1st = 1,1,0 → 192; 3rd = 0,1,0 → 64; 4th = 0,0/1,0 → 0/64; 5th = 1,0,1 → 160;
- **byte 20 = gear × 32** — no code packing into bits 7..5 found; hypothesis: the tester formats it;
- **byte 12 = 255 during a shift** — no write of constant 0xFF in the module; hypothesis: the tester shows the "Schaltung aktiv" flag (`0xFFFF9717 / 0xFFFF9718`) as 255. For a logger, read `0xFFFF9717`, `0xFFFF9735`, `0xFFFF973D` directly (doc 06).
