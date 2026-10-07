# 09 · What not to touch and why

The list of prohibitions. Every item has cost someone an undriveable box, a limp mode or a week of searching.

## 1. Outside the calibration window

| What | Why |
|---|---|
| `0x0000–0x8000` | boot loader, identification, DS2 driver. Without it the ECU cannot be re-flashed |
| `0x10000–0x40000` | code and record descriptors. Any edit = a code patch. The only code patch in this repository: `tcc-first` on 19x0 (52 bytes in the free area `0x3E3A0`, table `0x3E380`, call from `0x290A0`, byte for byte as the WOLF4X v41-v44 builds, doc 13 §1); after it flash the full image only. No other hooks |
| tail `0x0FFCE–0x10000` | calibration label (leave it) and the calibration checksum at `0xFFFE`: not edited by hand, recomputed by `apply_recipe.py` or `gs860_crc.py fix` (doc 07 §6) |

`apply_recipe.py` physically cannot write outside the calibration window (19x0 `0x8000–0x10000`, 20C0 `0x70000–0x80000`). `egs_patch.py` writes the calibration and, only for `tcc-first` on 19x0, the declared 52 bytes of code, and checks every other byte (doc 13 §0).

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
| `0x8214 = 4` | number of AGS levels, loop size in the AGS function 0x1DEBC (doc 03 §7). Not related to the TCC |
| `0x8D92 / 0x8D78 / 0x8975`, `0x88F2 + k` | calibration-branch selection and program attributes: bit 2 in `0x88F2` does **not** enable branch 1 (it writes 5 to `0xFFFF90C2`, purpose unknown) — already stepped on |
| 1st-gear AGS tables `0x901E / 0x903E` | these are the D / S AGS tables, not TCC thresholds. Editing them will not lock the clutch in 1st: the gear mask 0x8978 = 0x3C (2nd-5th) excludes lockup in 1st (doc 03 §2) |
| minimum-gear table `0x8AE2 + 5 × program` (PB from 0x8B19, PD from 0x8B23) | over-rev protection on manual downshifts (0x1E442, arbiter 0x236C8, doc 02 §5). The downshift columns of the manual matrices only set the automatic downshifts |
| `0x889C` | AGS parameter of branch D, counterpart of 0x88B0 (AGS point-decrease step in S). Not related to TCC release, not traced separately |
| `0x81A0 / 0x81B2` | gear-selection module threshold vs engine rpm/32 (doc 05 §4); meaning of the comparison is a hypothesis. Not "phases" |
| `0xA066 … 0xA20A` (slots 13–15) | purpose not decoded |
| TCC lower level: 950 engine rpm threshold (cell `[0x3B0C2 + 0x6C]`), `0xB0E2` = 1200 | the clutch opens at an engine speed of 950 rpm or less and is allowed again from 1200 (doc 03 §4). The cells are shared by D, S and M |
| hold after a shift `0xB139 … 0xB13C`, closing slope `0xB0FC`, "locked" criterion `0xB0D4 / 0xB12E` | shared by D, S and M and read only through the descriptor 0x3B0C2: an edit changes every mode at once. The hold (1.00 s after an upshift, 0.20 s after a downshift) keeps the clutch from closing right after synchronisation (doc 03 §4) |
| ATF in the TCC lower level (0x320DC) | lower-level protection: below raw 70 (about 22 °C) the clutch is always open, above raw 160 (about 110 °C) no slip (doc 03 §4) |

## 5. Diagnostic scalars

| What | Why |
|---|---|
| `0x8EE0–0x8F0E`, incl. `0x8EE8 / 0x8EEA / 0x8EF0`, `0x8EFC`, `0x8F00`, `0x8F08 / 0x8F0A` | voltage thresholds in mV (doc 03 §5, 05 §1). Not temperature and not turbine rpm (proven by the variable writes in 0x20D78). v17 mistakenly raised 0x8EEA to 7300, v18 restored it. Editing gains nothing and may disable/trigger the supply diagnostics |
| `0x8B44` (u16, stock 6720) | threshold of the turbine monitor 0x26C84: a turbine speed at or above it for about a second sets fault 0x25 and limp mode (doc 05 §6). Raise only together with the engine rev limit. Do not disable the monitor: no other turbine over-speed protection was found in the code |

## 6. Method

- Do not present the inference "a constant of 7000 must be rpm" as fact without a code reference **and** the write site of the variable (doc 10).
- Do not combine in one build steps that cannot later be separated in a log (doc 10 §5).
- Do not flash without comparing the SHA-256 of the built file with the build log, and never without Reset Adaptation afterwards.
- Do not post full dumps (doc 07 §5).
