# 09 · What not to touch and why

The list of prohibitions. Every item has cost someone an undriveable box, a limp mode or a week of searching.

## 1. Outside the calibration window

| What | Why |
|---|---|
| `0x0000–0x8000` | boot loader, identification, DS2 driver. Without it the ECU cannot be re-flashed |
| `0x10000–0x40000` | code and record descriptors. Any edit = a code patch; this repository contains no such patches and publishes no hooks |
| tail `0x0FFCE–0x10000` | calibration label and 2 bytes of unknown purpose (doc 07 §6) |

`apply_recipe.py` physically cannot write outside `0x8000–0x10000`.

## 2. Table axes — never

The axes (`X`, `Y`) of all tables are never changed in recipes. Reason — doc 04 §11: a build that gave 118 tables the axes of another calibration with extrapolated data produced harsh 2→3 / 3→4, rpm flares on downshifts and random behaviour vs temperature. The code reads a cell through the axes; a shifted axis = shifted physics in every phase at once, and in a log this cannot be separated from "just bad data". Copying somebody else's table whole is allowed only when its axes match stock **byte for byte** (example — `0xB90E` from Alpina).

## 3. Hydraulics (doc 04 §12)

| Field / addresses | What | Why not |
|---|---|---|
| kind1 f10: `D6C2 / D6E2, D722, D782, D7E2` | fast-fill time vs ATF | under-fill = delay and bump; over-fill = shock at the start of phase 4. Alpina leaves it alone |
| kind1 f13: `D01E / D03E, D07E, D0DE, D13E` | fast-fill pressure | same |
| kind1 f27: `E091 … E09A`, f43: `D670 … D698` | phase-4 and phase-9 durations | shortening = shock at the start of slip; Alpina makes phase 9 **longer** |
| kind1 f15 / f29 / f41 / f42, `A2C6 …` | ATF corrections, cold corrections | to be edited only from cold-box measurements |
| kind1 f23 / f24: `DF05 … DF14`, `DEC4 … DED3`; f47 `DED8 / DED9` | min / max pressures | f24 is the shock fuse; "raise the maximum so the controller stops hitting it" = move the shock into the clutch |
| kind1 f70: `B40E, B42A, B4AE, B532, B5B6` (4×4); kind3 f65: `B446 … B5D2` (6×6) | semantics not proven from code | Alpina changes them ×0.3–7 with other axes — all the more reason not to copy |
| f11 (`D538`), adaptations in RAM | fill-time adaptation | after flashing — Reset Adaptation, not "fix it with a constant" |
| `C206, C90C, C1FA …` | 1D tables 5×1 / 4×1 of fields f38 / f39 (zeros) | not structures; copying bytes into them "blind" is pointless |
| kind3 f45 `BA78` upwards | off-going pressure on 4→3 | raising it = slower release; v10/v18 have ×1.15 there and that is the wrong direction |

Also: the low-torque rows (Y ≤ 58, ≤ 132 Nm) of the pressure maps are town comfort; change Y ≥ 82 only.

## 4. Gear selection and TCC

| What | Why |
|---|---|
| `0x8214 = 4` | number of TCC stages — loop size in code |
| `0x8D92 / 0x8D78 / 0x8975`, `0x88F2 + k` | calibration-branch selection and program attributes: bit 2 in `0x88F2` does **not** enable branch 1 (it writes 5 to `0xFFFF90C2`, purpose unknown) — already stepped on |
| 1st-gear TCC thresholds `0x901E / 0x903E` | lockup in 1st — vibration and heat, no gain |
| downshift columns of manual programs 08/09/10 in rows 0…254 | over-rev protection |
| branch-0 release matrix `0x889C` | unlock in D on lift-off — the factory behaviour everyone is used to |
| `0x81A0 / 0x81B2` | gear-selection module threshold vs engine rpm/32 (doc 05 §4); meaning of the comparison is a hypothesis. Not "phases" |
| `0xA066 … 0xA20A` (slots 13–15) | purpose not decoded |

## 5. Diagnostic scalars

| What | Why |
|---|---|
| `0x8EE0–0x8F0E`, incl. `0x8EE8 / 0x8EEA / 0x8EF0`, `0x8EFC`, `0x8F00`, `0x8F08 / 0x8F0A` | voltage thresholds in mV (doc 03 §5, 05 §1). Not temperature and not turbine rpm (proven by the variable writes in 0x20D78). v17 mistakenly raised 0x8EEA to 7300, v18 restored it. Editing gains nothing and may disable/trigger the supply diagnostics |

## 6. Method

- Do not present the inference "a constant of 7000 must be rpm" as fact without a code reference **and** the write site of the variable (doc 10).
- Do not combine in one build steps that cannot later be separated in a log (doc 10 §5).
- Do not flash without comparing the SHA-256 of the built file with the build log, and never without Reset Adaptation afterwards.
- Do not post full dumps (doc 07 §5).
