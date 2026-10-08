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

**Disputed, not re-checked in code.** The analysis of 23.09.2026 states that the calibrations with the value 7000 at 0x8EEA, 0x8EF8, 0x8F04, 0x8F06 are compared with values received over CAN. The listing above (analysis of 16.09.2026) shows 0x8EEA compared with `0xFFFF906E`, the supply voltage in mV written at 0x20D78. Both readings agree on one point: this is not turbine speed. What 0x8EF8 / 0x8F04 / 0x8F06 are compared with is not spelled out in either analysis.

What remains open:

- **Closed on 23.09.2026.** The cause of limp mode at the limiter is found: the turbine monitor 0x26C84 with the threshold [0x8B44] = 6720 (§6). The 6613 peak is below the threshold, hitting the limiter at about 7008 is above it, limp mode after 1.3 s. The constants 0x8EE8 / 0x8EEA / 0x8EF0 have nothing to do with it.
- fault code 0x95 (149) in the EGS memory — no mapping table from internal fault numbers to DS2 codes has been found; its link to the event is unproven.
- That the DS2 code 0x95 is the internal fault 0x25 of the turbine monitor was a hypothesis. **Refuted by the 20C0 code (08.10.2026):** in the DS2 table of 20C0 (`0x707A0`) the internal fault 0x25 gives the DS2 code 0x21 (P0716 overspeed / P0715 no signal), and 0x95 belongs to the fault 0x24 (wheel speeds from CAN invalid); in 19D0 the same pairs sit at `0x87A8` / `0x87B0`. Why 0x95 was stored next to the limiter event in the 19D0 log is not explained by the code.

## 2. Warm-up program (until 06.10.2026 this section said "thermal derate by ATF")

> **Corrected 06.10.2026.** The former text called the table `0x9A6E` an ATF thermal derate: "the hotter the fluid, the smaller the time budget for full pedal, at 113 °C it is zero". The code disproves it. The table input `[0xFFFF90D5]` is the **engine** temperature at power-on: `0x15F92` copies `[0xFFFF90D3]` into it, and that is byte 1 of the DME2 frame × 3 / 4 (`0x21696`, °C + 48; when CAN is lost ATF + 8 is substituted, `0x21682–0x2168A`, document 03 §6). The axis 83 / 93 / 103 / 113 is 35 / 45 / 55 / 65 °C of the engine. The function `0x28D50` does not cap the pedal from above, it raises it from below: this is the warm-up program. Analysis with addresses in document 13 §3.

| Address | What |
|---|---|
| `0x28D50` | warm-up program. The flag `[0xFFFF90EE]` = 1 is set at power-on by `0x15F82` (function `0x15F78`), states 1-4 |
| `0x8142` | 2D8 4×16, slot 0 of the catalog `0x9ADC`: pedal for the matrices by engine temperature `[0xFFFF90D3]` and program `[0xFFFF91A0]`. P0, P1, P7 = 102 (40 %) up to 55 °C, 0 from 65 °C; read at `0x28DF6`, `0x28E10`, `0x28E62` |
| `0x9A6E` | 1D8, slot 44 (`0x9B8C`): counter by engine temperature at power-on, 35 / 45 / 55 / 65 °C → 170 / 90 / 55 / 0 → `[0xFFFF920F]` (`0x28DCA`). In state 4 a zero counter ends the warm-up |
| `0x9A78`, `0x81CC`, `0x8141` | second branch: counter (zeros) → `[0xFFFF9210]`, pedal floor by program (zeros), engine temperature 113 = 65 °C that switches the branch off |
| `0x25E54–0x25E6C` | both counters count down by 1 on a timer (function `0x25C40`) |
| `0x8B48` = 48 | end by speed: n_out / 32 at or above the byte (`0x28D6E`), 1536 output rpm. 0 = no warm-up |
| `0x24B66–0x24B76` | while the flag is set the shift matrices see `[0xFFFF9184]` = max(pedal `[0xFFFF9182]`, `0x8142`, `0x81CC`) instead of the pedal |
| `0x231F8` | while the flag is set the program arbiter gets request 8 (P0) |

Meaning: with a cold engine D upshifts as if the pedal were at 40 % or more, i.e. later, until the engine reaches 55-65 °C, the car reaches n_out / 32 = 48 or the counter runs out. There is no gearbox protection by oil temperature here.

ATF temperature acts elsewhere: the TCC lower level (`0x320DC`: open below raw 70, no slip above raw 160, document 03 §4) and the overheat programs (`0xFFFF90E4`: programs PC and PD, document 01 §5). The cold behaviour of the hydraulics is set by the family `0xA2C6…0xA3FC` (2D16 4×5, axis 140 / 150 / 180 / 255 raw units, values −80 or 0), slot 12 of the descriptors `0x3AA60`.

## 3. Limp mode — how it looks in the frame

Observation from a log (not reverse): on entering limp mode five bytes of the "0B 03 frame" body change at once: byte 12 from `0x1E` to `0xFF`, byte 14 from `0x08` to `0xFF`, byte 17 from `0xC2` to `0x02`, byte 18 from `0xDC` to `0xDD`, byte 20 from `0x20` to `0x80` (4th gear in bits 7-5, doc 06 §3). An engine restart clears the mode, the fault stays in memory. The limp-mode flag in RAM is `0xFFFF90C1`: 0x222A2 sets it from bit 3 of the mask word `0xFFFF8FA2`, and in the 0B 03 frame it is bit 0 of byte 18 (hence 0xDC and 0xDD). `0xFFFF9113`, which this section used to call the limp-mode flag, is the kickdown flag, and 0x1DEBC, where it is checked, is an AGS function (doc 03 §7). `0xFFFF8FA2` is the word of fault-reaction masks: 0x1A71A builds it from table 0x8366, bit 3 = limp mode, bit 8 = TCC lockup inhibit (§6). Third-party lists of "12 triggers of the inhibit vector 0xFFFF8FA2" are not confirmed by code and are not reproduced here.

## 4. 0x81A0 / 0x81B2 — neither hydraulics nor "solenoid phases"

Two 2D8 4×2 tables (`X = 0 / 166 / 167 / 194`, `Y = 0 / 1`), stock `0x81A0`: `30 30 255 255 / 15 15 30 30`; `0x81B2`: `15 × 8`. Early notes called them "shift phase durations" / "solenoid phases". The 16 Sep reverse: they are read through list `0x9AE0[2] / [3]` by `0x1E848(0x9AE0, X = 0xFFFF9197, Y = 0xFFFF91CB)` from the gear-selection module `0x1F4xx` and compared with `0xFFFF9176`. `0xFFFF9197` = **engine rpm / 32** (`0xFFFF8DB2` = CAN `0xFFFF842E` × 40/256, /32): X axis = 0 / 5312 / 5344 / 6208 rpm; Y = calibration branch. The meaning of the comparison is a hypothesis (holding/inhibiting the shift decision at high rpm; 255 = condition never met). It has nothing to do with shift execution; v10 changed the branch-1 row to 10/10/20/20 — v17 restored stock.

## 5. Limits that must not be touched

| Address | Stock | Why |
|---|---|---|
| `0x8214` | 4 | number of AGS levels, loop size in the AGS function 0x1DEBC (doc 03 §7). Not related to the TCC |
| `0xDF06…DF14` / `0xDEC4, 0xDEC9, 0xDECE, 0xDED3` | 20/16/12/16 … 116/138/138/87 | min/max slip pressure (f23/f24). f24 for 1-2 / 2-3 / 3-4 / 4-5 is the ceiling the controller runs into and the shock fuse (doc 04 §14) |
| `0xDED8 / 0xDED9` | 82 / 104 | max off-going pressure (f47) |
| `0xDE5C` | 100 rpm | end-of-phase-10 threshold |
| `0xDF34` | 20 rpm | slip-start threshold |
| `0x8EE0–0x8F0E` | — | voltage diagnostic thresholds |
| `0x8AE2 + 5 × program` (PB from 0x8B19, PD from 0x8B23) | PB, PD: 0 / 41 / 86 / 129 / 189 | minimum gear on a manual downshift (0x1E442, arbiter 0x236C8): landing at most 4808 / 5501 / 5808 / 6048 turbine rpm. This is the over-rev protection on manual downshifts, the downshift columns of the manual matrices only set the automatic downshifts (doc 02 §5) |
| `0x8B44` (u16) | 6720 | threshold of the turbine monitor 0x26C84: a turbine speed at or above it for about a second sets fault 0x25 and limp mode (§6). Raise only together with the engine rev limit |
| `0x8366` (4 bytes per fault) | for 0x25 (entry 0x8366 + 4 × 36): 0x30000009 | fault-reaction masks (§6): bit 3 = limp mode. Bit 8 of the collected word `0xFFFF8FA2` = TCC lockup inhibit |

## 6. Turbine monitor 0x26C84 (the cause of limp mode at the limiter)

Found on 23.09.2026. The 50 ms task (task list 0x121DE) calls 0x26C84: if the turbine speed `0xFFFF8DE2` (raw channel 1) is at or above [0x8B44], fault 0x25 (sub-code 7) is set through 0x1A3FA. There are no other conditions: neither the gear, nor P/N, nor road speed is needed. It takes about a second to reach limp mode, a short excursion above the threshold passes without consequences.

| Address | Instruction | What |
|---|---|---|
| `0x26C8E` | `movea.l #$FFFF8DE2,a4` | turbine speed, raw channel 1 |
| `0x26C96` | `cmp.w $8B44.l,d0` | comparison with the threshold |
| `0x26D14` | `moveq #$25,d0` | fault number 0x25 |

Threshold `0x8B44` (u16): stock 6720 turbine rpm, one reference to 0x8B44 in the code (the whole image was searched). Confirmed by a second independent analysis.

The reaction is set by the mask table 0x8366, 4 bytes per fault: for 0x25 the entry 0x8366 + 4 × 36 = 0x30000009, bit 3 = limp mode. 0x1A71A collects the masks into the word `0xFFFF8FA2`, and 0x222A2 sets the limp-mode flag `0xFFFF90C1` from bit 3: 4th gear, pressure regulators off. In the 0B 03 frame this is bit 0 of byte 18 (`0xFFFF91BE`, doc 06 §3). Bit 8 of the word `0xFFFF8FA2` disables the TCC lockup (doc 03 §2).

This explains the observation of §1: the 6613 peak is below the threshold, hitting the limiter at about 7008 is above it, limp mode after 1.3 s. The constants 0x8EE8 / 0x8EEA / 0x8EF0 have nothing to do with it. The code has no other comparisons of the turbine speed near 7000 except 0x2AD9C (7000 / 7001 from 0xB19C), and that one splits ranges for a table choice, it is not a protection.

Consequence for tuning: the factory threshold of 6720 is below the rev limit of many engines. If the turbine stays above 6720 at the limiter (with the converter locked the turbine equals the engine), the box goes into limp mode after about a second. Raise 0x8B44 only together with the engine rev limit. Better not to disable the monitor itself: no other turbine over-speed protection was found in the code.

Hypothesis, not proven: the counter 0x14 = 20 in the fault record 0x8464 counts 50 ms ticks, hence about a second to limp mode. It is also not proven that the DS2 code 0x95 is the internal fault 0x25.

A related protection: fault 0x21 is set when the output shaft reads 0 while the CAN road speed is above [0x8B32] (0x26AD6, stock 400). Mask 0x800, no limp mode.
