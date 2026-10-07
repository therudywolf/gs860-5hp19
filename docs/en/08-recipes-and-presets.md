# 08 · Recipes and the WOLF4X v18 "Sport daily (8HP-like)" preset

> **07.10.2026: new presets.** For a new build take the presets of document 14 (`sport-daily`, `street-hard`, `track-hard` for 19x0 and 20C0), built from the code-proven patches of document 13 by `egs_patch.py`. The v18-v20 presets below stay for the record: some of their edits rest on disproved readings (§6), and since 06.10.2026 `verify-shift` reports their manual upshift thresholds 58 / 106 / 151 / 212 as errors (above the factory turbine monitor 6720 − 100). 20C0 recipes (512 KB) write the window `0x70000–0x80000` and give a full image only.

> **Revised 23.09.2026.** The shift matrices hold output shaft rpm / 32, not km/h (doc 02 §3). The shift points of all three presets were brought within doc 02 §4 by `egs_tables.py verify-shift --spark 6656 --cut 6784 --fix`, and the recipes moved to schema `gs860-recipe/2`: the calibration checksum at `0xFFFE` is recomputed by `apply_recipe.py` (doc 07 §6). The 16.09 result hashes are kept in each recipe under `history`.

> **Correction 25.09.2026.** Some preset edits were made on readings that turned out wrong on 23.09.2026: the "TCC" groups change AGS (the adaptive program selection), not the lockup, the "sport" matrices 01 / 02 are the `0xFFFF90CD` steps that also act in D, and the manual thresholds 58 / 106 / 151 / 212 are unsafe with a locked converter. The table in §3 is corrected, see §6 for each preset. The preset data (`recipes/*.json`) is unchanged and will be revised separately.

> **Status 27.09.2026.** The presets are not road-tested in their 23.09.2026 form (CHANGELOG, 23.09.2026). Every recipe and its annotations carry a `status` field with the short form of §6: the "TCC" groups change AGS, not the lockup, `torque_reduction` changes the reference slip of the TCC regulator, the manual upshift thresholds are unsafe, in v20 the f24 edit acts in every mode. `apply_recipe.py` prints it.

## 1. What a recipe is

A recipe is a JSON file (`recipes/*.json`, schema `gs860-recipe/2`, the older `/1` is still accepted) describing the **difference** between a stock calibration and a tune:

- for every changed table: address, format (`2D8` / `2D16` / `1D8` / `1D16`), dimensions, **both axes**, old and new data, group and comment;
- for changes outside tables (AGS points `0x888C`, AGS point-decrease step of branch S `0x88B0`, scalars, doc 03 §7): address, width, old and new values.
- base: SHA-256 of the code `0x10000–0x40000`, SHA-256 and label of the stock calibration. Result: SHA-256 of the built file, checksum recomputed. `checksum`: the calibration checksum of stock and result. `history`: earlier result hashes and why they changed.
- never the checksum bytes `0xFFFE–0xFFFF`: they are computed, not edited.

Rules built into `tools/apply_recipe.py`:

1. input — a full 256 KB image only; the code must match the base SHA (otherwise it is different software — stop);
2. **axes are never changed**: if a table axis in your dump differs from the recipe — stop (doc 04 §11 explains why);
3. old values are checked cell by cell; a mismatch = a different base calibration → warning and stop, `--force` writes anyway;
4. only the window `0x8000–0x10000` is written (asserted); output `out.bin`, `out_partial32k.bin`, `out.log`.
5. the loader and program checksums of the input must match (otherwise a damaged read or modified program: stop), and after writing the calibration checksum at `0xFFFE` is recomputed, so the output passes `gs860_crc.py check`.

A recipe is built from two binaries by `tools/make_recipe.py` (stock → tune); it refuses if the tune changes axes or anything outside the window, and leaves the checksum bytes out.

## 2. What the WOLF4X v18 preset was built for

- GS8.60.0, program 19x0, stock calibration `B22K4_0419C0KA20` (E39 with the 2.5 l M52TU — M52TUB25, stock final drive).
- An engine with a **6784 rpm fuel cut and the spark cut from about 6656**. WOT upshifts in sport at most 47 / 94 / 136 = turbine 5512 / 6013 / 6123 rpm at the command: the engine reaches the spark cut as the shift completes (doc 02 §4). The shift points depend only on the engine limiter, not on the final drive or tyres (doc 02 §3).
- Character: **"Sport daily"**. In D almost everything is factory, except the 4-5 hunting fix (the edit sits in matrices 03 / 04 / 07, the D replacement programs, §6) and an edit that was built as earlier converter lockup on the motorway. In fact that edit changes AGS (doc 03 §7): at 40-60 % pedal D holds level 2 longer, i.e. program P1 (matrix 06), without 5th. It does not touch the clutch. In S/M short, crisp shifts under throttle. The manual mode was meant to hold the gear to the limiter under load and to shift up by itself only on the overrun at the fuel cut. That idea was refuted on 23.09.2026 (doc 02 §5): a manual threshold at the 6784 cut is above the factory turbine monitor threshold 6720 (0x8B44), and with a locked converter it upshifts by itself on the limiter plateau. "8HP-like" refers to the hydraulics: shorter target slip time at high torque, higher on-coming clutch pressure only at ≥ 228 Nm, faster release on 3-2, the principles of doc 04 §12.
- 1375 bytes in total relative to stock (checksum included), 43 tables + 3 blocks outside tables. Result SHA-256: full `14e1518567722bfe53dda79d04e9fcd88d865643095f94c5656423647fe42a3a`, partial `e50bdaec1c27852ebebec3e3de44e9785f43d3a9fa80020b4d7096c9013767b7`, checksum `0xEA30`. `apply_recipe.py` on the original stock reproduces them byte for byte. The 16.09 build (`0bfd1d0d…`, stale checksum, km/h shift points) is in `history`.
- v18 = v17 with one difference: `0x8EEA` returned to stock (7000). v17 had raised it to 7300 as "turbine protection" — a misreading; it is a supply-voltage threshold (doc 05 §1).

## 3. Table of changes with justification

Confidence: **P** — role proven by code and data; **E** — role proven, magnitude estimated; **H** — hypothesis.

Since 25.09.2026 the "Conf." column can also say **role refuted**: the edit was made for a role that turned out to be different (see "Why").

| Group | Addresses | Stock → v18 | Why | Conf. |
|---|---|---|---|---|
| Shift points: matrices 01/02/11/15 ("sport" in the preset) | 0x9222, 0x9292, 0x9682, 0x9842 | values in output shaft rpm / 32. From pedal row 160 up: upshifts **47 / 94 / 136** (stock WOT 45-47 / 93 / 134) = turbine 5512 / 6013 / 6123 rpm at the command. Part-throttle rows bridged (rows 83 / 121: 30/78/126 and 42/92/135). 4>5 200 (stock) at light pedal, 218-231 under throttle (4th to top speed). Downshifts 2>1 = 41 from row 160, WOT 41 / 86 / 122 / 192, kickdown 41 / 88 / 125 / 192 (at most 6144 rpm after the downshift) | meant as a four-speed sport mode, upshifting so that the engine meets the spark cut as the shift completes, no steps in the lines (doc 02 §4). The 16.09 values 66 / 120 / 171 meant 7740 / 7676 / 7699 turbine rpm: never reached, the box hung at the limiter. Correction 25.09.2026: S is only matrices 11 and 15 (P2 and P3). Matrices 01 and 02 are the `0xFFFF90CD` steps (P5 and P6), they also act in D on a gradient, so editing them as "sport" changes D (doc 01 §5) | P (values), role of 01 / 02 refuted |
| Shift points: matrices 08/09/10 ("manual" in the preset) | 0x9532, 0x95A2, 0x9612 | upshifts 49/95/137/200 replaced by **58 / 106 / 151 / 212** in every row (turbine 6781…6802 rpm, the fuel cut). Downshifts in rows 0…254 = stock (0/10/25/69, 0/0/25/39, 0/10/19/28). Kickdown downshifts **52 / 96 / 136 / 192** (at most 6144 rpm in the lower gear) | meant as an "honest manual": under load the engine stops at the spark cut and the box holds the gear, on the overrun it shifts up before the wheels drive the engine past the cut. Refuted on 23.09.2026 (doc 02 §5). M is matrices 10 (PB) and 08 (PD), matrix 09 is P8, not M. With a locked converter the 6781-6802 thresholds upshift by themselves on the limiter plateau, and a turbine speed from 6720 (0x8B44) for about a second sets fault 0x25 and limp mode. The over-rev protection on manual downshifts is table 0x8AE2, not these columns | role refuted |
| Shift points: matrices 03/04/07 ("D" in the preset) | 0x9302, 0x9372, 0x94C2 | 4>5 in pedal rows 0/10/46: 64 replaced by **75** | against 4-5 hunting on the overrun: the gap to 5>4 becomes 19 units instead of 8 (22 km/h instead of 9 on the reference car), 5th at turbine 1781 instead of 1520 rpm. Correction 25.09.2026: these are programs PF / PE / PC, the D replacements. The main D (matrices 14 and 06, P0 and P1) is untouched and the edit does not act on it | P (values), role clarified |
| AGS, branch D ("TCC, branch 0" in the preset) | 0x905E, 0x909E, 0x90DE, 0x913E | column 1: 153 replaced by **102** from speed row 62 (2nd, 3rd), 128…191 by 128/128 and **102** from row 113 (4th), 230 by **102** from row 94 (5th). Rows are output shaft rpm / 32: 62 / 113 / 94 = 73 / 133 / 111 km/h on the reference car | meant as converter lockup in D from 40 % pedal. In fact these are AGS tables (doc 03 §7): at 40-60 % pedal D holds level 2 longer (program P1, matrix 06) without 5th. The edit does not touch the converter clutch, whose thresholds are 0x993A / 0x897E (doc 03 §3) | role refuted |
| AGS, branch S ("TCC, branch 1" in the preset) | 0x907E, 0x90BE, 0x910E, 0x915E | column 1: 64 replaced by 64/64/31/28/26/26 (2nd), 31/28/26/26/26/26 (3rd), 64…88 by 38/31/26… (4th), 64 by 64/64/31/26/26/26 (5th) | meant as leaving TCC stage 1 in S/M from 10-15 % pedal. In fact these are the AGS tables of branch S: the pedal threshold vs speed for the target AGS level in S, i.e. the choice between P2 and P3 (matrices 11 and 15). The edit does not touch the converter clutch | role refuted |
| AGS, scalars ("TCC, scalars" in the preset) | 0x888C, 0x88C0, 0x88B0 | "home" points 32/96/160/224 replaced by **32/128/176/240**, point growth 5 by **7**, point-decrease step in S −17/−33/−65 by **−10/−20/−40** | meant as "stages 2-4 hold harder, softer release". In fact AGS: level 2 in D is pulled towards 128 instead of 96, the S levels towards 176 / 240 instead of 160 / 224, the points grow faster, S holds level 4 longer and drops from it more slowly (doc 03 §7). The edit does not touch the converter clutch | role refuted |
| Maps 0xAB0C… ("torque reduction" in the preset) | 0xAB0C, 0xABB0, 0xAC54, 0xACF8, 0xAD9C, 0xAE40 | columns 3000/4000/6000 rpm in all non-zero-load rows: **15** (stock 25-40) | meant as less torque in the slip phase. By the third-party reverse accepted on 23.09.2026 these maps are the reference slip of the TCC regulator (`0xFFFF95A6`, doc 03 §4): the edit changes the reference of the clutch regulator, not torque reduction. Its effect on the clutch is not checked. Torque reduction goes through one channel, EGS1 byte 3 (doc 04 §9) | role refuted |
| Hydraulics: target slip time, upshifts | 0xBF9C, 0xBFEC, 0xC028, 0xC064 (kind1 f45, 3×3) | row Y=85 (240 Nm) **×0.85**, row Y=55 (120 Nm) ×0.92 (C064 — Y85 only); low-torque row = stock. E.g. BFEC: [50,63,75] / [44,56,66] / [36,43,53] → [50,63,75] / [40,52,61] / [31,37,45] | the main "sport" lever: controller 0x364A2 raises the pressure gradient (doc 04 §6). Alpina at 280 Nm: 30/36/26 | P / E |
| Hydraulics: target time, downshifts | 0xC0B4, 0xBFD8 (1↔2); 0xC08C (4↔5); 0xC0C8 (2↔3, 3→1, 4→2) | C0B4/BFD8: Alpina data (65 → 57, 55 → 47, same axes); C08C rows Y75/Y100 ×0.85 → [23,31,45] / [20,28,36]; C0C8 rows Y63/Y100 ×0.85 → [23,30,36] / [22,26,33] | crisper 2→1, 5→4, 3→2 under throttle; Alpina data not copied for C0C8/C08C — other axes there | P / E |
| Hydraulics: on-coming pressure, upshifts | 0xB80A (2↔3), 0xB974 (3↔4) (kind1 f32) | B80A: rows Y ≥ 82 (≥ 228 Nm) **×1.08**, lower rows stock; B974: rows Y ≥ 66 ×1.15 (from v10), rows Y ≤ 58 (≤ 132 Nm) **returned to stock** | faster torque transfer under throttle, town comfort as stock (Alpina: higher at ≥ 200 Nm, lower at low torque). B656 (1→2) and BADE (4→5) untouched | P / E |
| Hydraulics: off-going pressure, upshifts | 0xBCAE, 0xBD14 (kind1 f53) | ×1.15 everywhere (≈ Alpina +8…+10; clipped by f47 = 82/104) | less sag during overlap | P |
| Hydraulics: off-going pressure, downshifts | 0xB90E (2↔3, kind3 f45) | **Alpina data whole** (identical axes): Y85 [60,59,57,58,54,46,40,37] → [60,59,52,46,42,38,22,20]; Y110 [102,77,70,69,67,61,53,48] → [102,77,70,63,60,52,36,28] | 3→2 under throttle: releases faster, shorter "hole" | P (role, axes) / E |
| Hydraulics inherited from v10 | 0xB73E, 0xB7A4, 0xBD7A ×0.85; 0xBA78, 0xBE46, 0xBEAC ×1.15 | uniform over the whole map | B73E/B7A4 — off-going pressure 2→1 / N↔2 (direction as Alpina ×0.78); BD7A — on-coming N↔2; BE46/BEAC — on-coming on downshifts (Alpina higher at high torque). **BA78 ×1.15 goes the wrong way** (slower 4→3 release): candidate for reverting to stock in the next version | P / E; BA78 — doubtful |

What v18 did **not** touch and why — doc 09. Returned to stock compared with v10: the branch-1 row of `0x81A0` (v10 set 10/10/20/20 on the mistaken "phases" reading).

## 4. For another engine / rev limit / final drive

Must be recalculated:

1. **Shift points** of the sport programs, the manual upshift guard and the kickdown rows, for your own spark cut and fuel cut (doc 02 §4): `python3 tools/egs_tables.py verify-shift build.bin --spark <rpm> --cut <rpm> --stock stock.bin`, and `--fix out.bin` to lower what breaks the rules. The matrices hold output shaft rpm / 32, so a different final drive or tyre size does not change the shift rpm (doc 02 §3). A manual upshift threshold at the cut is unsafe with a locked converter (doc 02 §5): check it separately against the turbine monitor threshold 0x8B44 (doc 05 §6).
2. **The Y axis of the pressure maps is engine torque**: 8×10 maps are read by actual torque (Nm/4 + 25). For a torquier engine the "high-torque rows" are the same rows Y ≥ 82, they are simply used more often; there is no extrapolation beyond 400 Nm (axis up to 125 = 400 Nm). The Alpina data in B90E was designed for 335 Nm — on a weaker engine those cells are just visited less.
3. **The X axis of the maps — turbine/32** up to 188 (6000) or 203 (6500): with a rev limit above 6500 the top cell extrapolates as a constant — for such an engine the X axis would need extending, as Alpina did (219 = 7000), but that is an axis change with all its risks; recipes do not do it.
4. The 0xAB0C… maps were edited in the presets as "torque reduction 15 %". They are the reference slip of the TCC regulator (doc 04 §9) and have no link to the DME. The effect of the edit on the clutch is not checked.

Not engine-dependent: the AGS tables and scalars 0x901E-0x915E, 0x888C, 0x88C0, 0x88B0 (formerly called TCC thresholds and scalars, doc 03 §7), target times (turbine rpm × torque). The real TCC thresholds (0x993A) and the lower level of the clutch (open below 950 engine rpm) are tied to the engine (doc 03 §3, §4).

## 5. How to apply

```
python3 tools/egs_tables.py info my_dump.bin                 # code e151733e…, 536 tables, three checksums ok
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
python3 tools/gs860_crc.py check build.bin build_partial32k.bin
python3 tools/egs_tables.py verify-shift build.bin --spark 6656 --cut 6784 --stock my_dump.bin
```

If your calibration is not `19C0KA20` but, say, `19D0620P` (Alpina), the tool stops already on the axes: Alpina has different axes in some 3×3 tables (Y 85 → 95) and in C0C8. That is not a tool error — the recipe is not applicable to that base as a whole; take only the groups whose axes match and recalculate the rest. If the axes match but the old values do not (another revision of the 19x0 calibration) — compare `egs_tables.py diff` of your dump against the `old` values in the recipe and decide per group; `--force` only after that.

## 6. Correction 25.09.2026: what the presets really change

The data of the preset files `recipes/wolf4x_v18_sport_daily.json`, `wolf4x_v19_street_hard.json`, `wolf4x_v20_track_hard.json` is unchanged (on 27.09.2026 each got the `status` field, see the note at the top). They are not road-tested in their 23.09.2026 form. Some of their edits were made on readings that turned out wrong on 23.09.2026. The presets will be revised separately, until then read them with the corrections below.

**Which matrices are really used** (doc 01 §5). D runs on matrices 14 (P0) and 06 (P1), the D replacements are 04 (PE), 03 (PF) and 07 (PC with overheated ATF). S runs on 11 (P2) and 15 (P3). M runs on 10 (PB), with overheated ATF on 08 (PD). 09 is P8 (gate without Steptronic logic). 00 / 01 / 02 are the `0xFFFF90CD` steps (P4 / P5 / P6), they override D and S.

**Common to v18, v19 and v20:**

- The groups `tcc_thresholds_branch0`, `tcc_thresholds_branch1`, `tcc_scalars` ("TCC") change AGS, not the lockup: these are tables 0x905E, 0x909E, 0x90DE, 0x913E (branch D), 0x907E, 0x90BE, 0x910E, 0x915E (branch S) and bytes 0x888C, 0x88C0, 0x88B0. They affect which program AGS selects: P0 or P1 in D, P2 or P3 in S. No preset touches the real clutch thresholds 0x993A and groups 0x897E, so the presets do not give the earlier converter lockup these edits were made for.
- The group `torque_reduction` (0xAB0C…0xAE40) changes the reference slip of the TCC regulator, not the torque-reduction request (§3). Its effect on the clutch is not checked.
- The group `shift_points_sport` edits matrices 11 and 15 (S) and matrices 01 and 02. 01 and 02 are the `0xFFFF90CD` steps, which also act in D on a gradient, so the preset changes D on a gradient too.
- The group `shift_points_drive_45` edits matrices 03, 04, 07. These are the D replacement programs (PF, PE, PC). The main D (14 and 06) is untouched, so the presets do not change 4>5 in normal D.
- The group `shift_points_manual` edits matrices 08, 09, 10: M is 10 (PB) and 08 (PD), 09 is P8, not M. The upshift thresholds 58 / 106 / 151 / 212 (turbine 6781-6802) are unsafe. The factory M locks the clutch in 3rd, 4th and 5th (from 4592 / 3584 / 2659 turbine rpm), and then the turbine equals the engine. Under throttle M may shift up by itself on the limiter plateau, and in 3rd-5th holding the gear at the limiter keeps the turbine at about 6656-6784, i.e. at and above the 6720 turbine monitor threshold (0x8B44). On the overrun, for M to shift up by itself the wheels must drive the engine and turbine to 6781-6802, above the 6720 threshold. About a second at such speeds sets fault 0x25 and limp mode (4th gear, doc 05 §6). The over-rev protection on manual downshifts is table 0x8AE2, and the presets do not touch it.

**v18 "Sport daily".** Everything common above. AGS groups: column 1 lowered to 102 in D and to 26-38 in S, "home" points 32/128/176/240, growth 7, decrease step in S −10/−20/−40. Result: at 40-60 % pedal D holds level 2 longer without 5th, S holds level 4 longer and drops from it more slowly. Maps 0xAB0C…: 15 in the 3000 / 4000 / 6000 columns.

**v19 "Street hard".** As v18, plus columns 2 and 3 of branch S lowered to 77 / 128. The preset description calls this "TCC stages 3/4 in S/M from 30-50 % pedal". In fact these are lower pedal thresholds for the target AGS levels 3 and 4 in S: the target level 4 (P3, matrix 15) is reached at less pedal. It does not touch the clutch. The edit of matrices 01 / 02 ("sport holds a gear longer at part throttle") also changes D on a gradient.

**v20 "Track hard".** As v19, plus:

- the level 3 / 4 thresholds of branch S are lowered further (to 38-48 / 68-90 transmission-pedal units), and the point-decrease step in S becomes −6 / −10 / −16. S holds level 4 even longer. The preset description calls this "TCC stages 3-4 earlier in S/M", in fact it is AGS and does not touch the clutch.
- Bytes 0xDEC4 / 0xDEC9 / 0xDECE / 0xDED3 are raised from 116 / 138 / 138 / 87 to 138 / 160 / 160 / 104. This is f24, the slip-pressure ceiling of load upshifts (doc 04 §14), and the preset has the right addresses. The hydraulics are the same for D and S/M (the execution module does not read `0xFFFF91CB`), so this edit acts in every mode, D included, not only in S/M cells.
- Maps 0xAB0C…: the 3000 column back to stock, at least 35 in the 4000 / 6000 columns. These are the reference slip of the TCC regulator, not torque reduction.
