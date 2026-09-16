# 05 · Protections, limp mode, voltage monitor

## 1. Function 0x265F4 and constants 0x8EE8 / 0x8EEA / 0x8EF0 — supply-voltage monitor (proven)

Variables `0xFFFF906C` and `0xFFFF906E` are written **only** in function `0x20D78…0x20E6A`:

```
020d8e  movea.l #$ffff89bc, a1      ; ADC buffer, channel B (16-bit: high/low byte)
020dac  muls.l  #$62a2, d0          ; × 25250
020dba  divs.l  d5, d0              ; / 1024   (d5 = 0x400)
020dbe  move.w  d0, $ffff906e       ; = U_B, mV  (0xFFFF906A — running average ×4/5)
020de4  movea.l #$ffff89ba, a1      ; channel A
020dfc  muls.l  #$62a2, d0
020e08  move.w  d0, $ffff906c       ; = U_A, mV  (0xFFFF9068 — average)
020e46  muls.l  #$9c4, d0           ; third channel: × 2500 / 1024 → 0xFFFF8D84 (2.5 V scale)
```

10-bit ADC × 25250 / 1024 = a full scale of **25.25 V through a divider**: two supply-voltage measurements in mV. Engine and turbine speeds live in other variables (`0xFFFF97B0` from `0xFFFF8DB2`, CAN × 40/256; `0xFFFF97B4` from `0xFFFF8DE2`, doc 04 §3).

Who reads these variables:

| Code | What it does |
|---|---|
| `0x1FB3E` | if `[0xFFFF8626] == 1` and `0x8F00 (9000) < [906C] < 0x8EFC (16000)` → `[0xFFFF8626] = 2` — "supply 9…16 V OK" |
| `0x265F4` | three flags (listing below): `|[906C] − [906E]| > 0x8EF0 (1500)` — channels more than 1.5 V apart, check skipped; `[906E] ≥ 0x8EE8 (9000)` — flag −4(a6); else `[906E] ≥ 0x8EEA (7000)` — flag −6(a6). Then an ATF-dependent threshold `([0xFFFF90D0] − 45) × 38 + 10000`, × `[0x8B60]` / 10000 + `[0x8B62]` → `0xFFFF8FB2`, a loop over three items at `0x1263C` with `0xFFFF8D80`; flag consumer `0x266B2` — actuator-circuit diagnostics with voltage-dependent thresholds |
| `0x21DAE` | `cmpi.w #10000, [906E]` — 10.0 V threshold |
| `0x26EE0` | if `[0xFFFF8B88] == 1` and `[906C] − 0x8EFA (1000) > [906E]` and `[906E] ≤ 0x8EFE (2500)` → fault code `0x2D` (45): channel B more than 1 V below channel A and below 2.5 V |

```
02660e  move.w  $ffff906c, d0
026614  movea.l #$ffff906e, a3
02661a..026632                    ; d0 = |[906C] − [906E]|
026636  cmp.w   $8ef0, d0         ; 1500 mV
02663c  bhi     $2665e            ; too far apart — skip the check
02663e  move.w  (a3), d0          ; [906E]
026640  cmp.w   $8ee8, d0         ; 9000 mV
026646  bcs     $26650
026648  move.w  #1, -4(a6)        ; U_B ≥ 9.0 V
02664e  bra     $2665e
026650  cmp.w   $8eea, d0         ; 7000 mV
026656  bcs     $2665e
026658  move.w  #1, -6(a6)        ; 7.0 V ≤ U_B < 9.0 V
```

The whole scalar block `0x8EE0–0x8F0E` (2560, 1000, 9000, 11000, 9000, **7000**, 500, 9000, **1500**, 16000, 9000, 6500, 7000, 1000, 16000, 2500, 9000, 16000, 7000, 7000, 2700, 2300, 2504, 4500) holds thresholds in mV; the "temperature" myth of doc 03 §5 belongs to the same block.

**History of the mistake.** In September 2026, based on an experiment (a series of revs in neutral: peak 6613 — fine, hitting the limiter at ~7008 → limp mode after 1.3 s and code 0x95 stored), the round constants 7000/9000/1500 in `0x265F4` were read as "turbine / engine rpm" and the function as "turbine over-speed protection". The write sites of the variables were not checked. On that basis preset **v17** raised `0x8EEA` to 7300 — i.e. it moved a 7.0 V threshold to 7.3 V, with no relation to rpm. **Fixed in v18: 0x8EEA = 7000 (stock).** Leave all three constants stock.

What remains open:

- the observation "engine hitting the ~7000 rpm limiter → limp mode, 6613 → no" is real and reproducible, but its cause has **not been found**. Candidates (hypotheses): a ratio-monitoring / turbine-vs-engine plausibility check in another module; a condition in the CAN handling while the DME limiter is active. To be located with the method of doc 10;
- fault code 0x95 (149) in the EGS memory — no mapping table from internal fault numbers to DS2 codes has been found; its link to the event is unproven.

## 2. Thermal derate by ATF

The only use of ATF temperature in the logic (doc 03 §6):

| Address | What |
|---|---|
| `0x9A6E` | 1D8, axis `83 / 93 / 103 / 113` °C → values `170 / 90 / 55 / 0`; read with `0xFFFF90D5` (0x28DCA), result → counter `0xFFFF920F` |
| `0x9A78` | second table (zeros) → `0xFFFF9210` |
| `0x25E54–0x25E6C` | counters decrement every cycle |
| `0x28D50` | when `[0xFFFF920F] == 0` it clamps the **effective pedal** `0xFFFF9184` (itself capped by the real pedal `0xFFFF9182`) |

Meaning: the hotter the fluid, the smaller the "time budget" for full pedal; at 113 °C it is zero. This is a **maximum**-temperature protection. Through the pedal it indirectly affects shift points and TCC thresholds (both are in pedal). There is no minimum temperature below which anything is inhibited in this chain. Cold hydraulic behaviour comes from the `0xA2C6…0xA3FC` family (2D16 4×5, axis 140 / 150 / 180 / 255 raw units ≈ 57 / 65 / 87 / 143 °C, values −80 or 0), slot 12 of the descriptors `0x3AA60`.

## 3. Limp mode — how it looks in the frame

Observation from a log (not reverse): on entering limp mode five bytes of the "0B 03 frame" body change at once — byte 12 `0x1E → 0xFF`, byte 14 `0x08 → 0xFF`, byte 17 `0xC2 → 0x02`, byte 18 `0xDC → 0xDD`, byte 20 `0x20 → 0x80`. An engine restart clears the mode; the fault stays in memory. The limp-mode flag in RAM is `0xFFFF9113` (checked in 0x1DEBC as a lockup entry condition). Third-party lists of "12 triggers of the inhibit vector 0xFFFF8FA2" are not confirmed by code and are not reproduced here.

## 4. 0x81A0 / 0x81B2 — neither hydraulics nor "solenoid phases"

Two 2D8 4×2 tables (`X = 0 / 166 / 167 / 194`, `Y = 0 / 1`), stock `0x81A0`: `30 30 255 255 / 15 15 30 30`; `0x81B2`: `15 × 8`. Early notes called them "shift phase durations" / "solenoid phases". The 16 Sep reverse: they are read through list `0x9AE0[2] / [3]` by `0x1E848(0x9AE0, X = 0xFFFF9197, Y = 0xFFFF91CB)` from the gear-selection module `0x1F4xx` and compared with `0xFFFF9176`. `0xFFFF9197` = **engine rpm / 32** (`0xFFFF8DB2` = CAN `0xFFFF842E` × 40/256, /32): X axis = 0 / 5312 / 5344 / 6208 rpm; Y = calibration branch. The meaning of the comparison is a hypothesis (holding/inhibiting the shift decision at high rpm; 255 = condition never met). It has nothing to do with shift execution; v10 changed the branch-1 row to 10/10/20/20 — v17 restored stock.

## 5. Limits that must not be touched

| Address | Stock | Why |
|---|---|---|
| `0x8214` | 4 | number of TCC stages — loop size in 0x1DEBC |
| `0xDF06…DF14 / 0xDEC5…DED3` | 20/16/12/16 … 116/138/138/87 | min/max slip pressure (f23/f24); f24 is the shock fuse |
| `0xDED8 / 0xDED9` | 82 / 104 | max off-going pressure (f47) |
| `0xDE5C` | 100 rpm | end-of-phase-10 threshold |
| `0xDF34` | 20 rpm | slip-start threshold |
| `0x8EE0–0x8F0E` | — | voltage diagnostic thresholds |
| downshift columns of the manual programs | — | over-rev protection (doc 02 §5) |
