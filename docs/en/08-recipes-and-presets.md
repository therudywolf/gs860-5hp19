# 08 · Recipes and the WOLF4X v18 "Sport daily (8HP-like)" preset

## 1. What a recipe is

A recipe is a JSON file (`recipes/*.json`, schema `gs860-recipe/1`) describing the **difference** between a stock calibration and a tune:

- for every changed table: address, format (`2D8` / `2D16` / `1D8` / `1D16`), dimensions, **both axes**, old and new data, group and comment;
- for changes outside tables (TCC ladder `0x888C`, matrix `0x88B0`, scalars): address, width, old and new values;
- base: SHA-256 of the code `0x10000–0x40000`, SHA-256 and label of the stock calibration; result: SHA-256 of the built file.

Rules built into `tools/apply_recipe.py`:

1. input — a full 256 KB image only; the code must match the base SHA (otherwise it is different software — stop);
2. **axes are never changed**: if a table axis in your dump differs from the recipe — stop (doc 04 §11 explains why);
3. old values are checked cell by cell; a mismatch = a different base calibration → warning and stop, `--force` writes anyway;
4. only the window `0x8000–0x10000` is written (asserted); output `out.bin`, `out_partial32k.bin`, `out.log`.

A recipe is built from two binaries by `tools/make_recipe.py` (stock → tune); it refuses if the tune changes axes or anything outside the window.

## 2. What the WOLF4X v18 preset was built for

- GS8.60.0, program 19x0, stock calibration `B22K4_0419C0KA20` (E39 with the 2.5 l M52TU — M52TUB25, stock final drive).
- An engine with a **6784 rpm rev limit** (the hard engine ceiling in this combination is ~6656 by spark); WOT upshift points in sport ≈ 6520–6570 rpm.
- Character: **"Sport daily"** — in D almost everything is factory (except the 4↔5 hunting fix and earlier converter lockup on the motorway), in S/M short, crisp shifts under throttle, a manual mode that never upshifts by itself. "8HP-like" refers to the hydraulics: shorter target slip time at high torque, higher on-coming clutch pressure only at ≥ 228 Nm, faster release on 3→2 — the principles of doc 04 §12.
- 1389 bytes in total relative to stock, 43 tables + 3 blocks outside tables. Result SHA-256: full `0bfd1d0d10037e020bcbfb16fdf5941bf17d0ec085dd5dd0cdec22c65419812e`, partial `657531fa400e0070f1cc37ebaac497c84d1ef690b1329bfdb3f81726d9ee60e4`. `apply_recipe.py` on the original stock reproduces them byte for byte.
- v18 = v17 with one difference: `0x8EEA` returned to stock (7000). v17 had raised it to 7300 as "turbine protection" — a misreading; it is a supply-voltage threshold (doc 05 §1).

## 3. Table of changes with justification

Confidence: **P** — role proven by code and data; **E** — role proven, magnitude estimated; **H** — hypothesis.

| Group | Addresses | Stock → v18 | Why | Conf. |
|---|---|---|---|---|
| Shift points: sport 01/02/11/15 | 0x9222, 0x9292, 0x9682, 0x9842 | WOT upshifts 45–47 / 93 / 134 / 200 → **66 / 120 / 171 / 231** (≈ 6570 / 6520 / 6550 / 6260 rpm); part-throttle rows bridged (rows 83/121 → 30/78/126 and 42/92/135), 4→5 at light pedal 200 (stock), 218–231 under throttle; 5→4 = 190–191 at part throttle (stock 157–189 depending on program), 213–215 at WOT; WOT downshifts 46 / 86 / 122 | a four-speed sport mode up to ~220 km/h, shifting at the limiter without hitting it, no steps in the lines (doc 02 §4) | P |
| Shift points: manual 08/09/10 | 0x9532, 0x95A2, 0x9612 | upshifts 49/95/137/200 → **255** (never); downshifts in rows 0…254 = stock (0/10/25/69, 0/0/25/39, 0/10/19/28); kickdown downshifts → 59 / 108 / 154 / 217 (≈ 5880 rpm in the lower gear) | honest manual: holds to the limiter; protective downshift lines untouched | P |
| Shift points: D 03/04/07 | 0x9302, 0x9372, 0x94C2 | 4→5 in pedal rows 0/10/46: 64 → **75** km/h | 4↔5 hunting on the overrun: hysteresis 8 → 19 km/h, 5th at 1508 instead of 1286 rpm | P |
| TCC, branch 0 | 0x905E, 0x909E, 0x90DE, 0x913E | column 1: 153 → **102** from 62 km/h (2nd, 3rd); 128…191 → 128/128, **102** from 113 km/h (4th); 230 → **102** from 94 km/h (5th) | lockup in D from 40 % pedal instead of 60/50/90 %: less slip and heat on the motorway; a gentler threshold kept at 63–88 km/h in 4th (shudder below ~1500 rpm) | P (role) / E |
| TCC, branch 1 | 0x907E, 0x90BE, 0x910E, 0x915E | column 1: 64 → 64/64/31/28/26/26 (2nd), 31/28/26/26/26/26 (3rd), 64…88 → 38/31/26… (4th), 64 → 64/64/31/26/26/26 (5th) | in S/M leaving stage 1 from 10–15 % pedal | P / E |
| TCC, scalars | 0x888C, 0x88C0, 0x88B0 | ladder 32/96/160/224 → **32/128/176/240**; rise ramp 5 → **7**; branch-1 release matrix −17/−33/−65 → **−10/−20/−40** | stages 2–4 hold harder; softer release on lift-off in S/M. Stage 1 and the branch-0 matrix untouched | E (physical channel unproven, doc 03 §2) |
| Torque reduction | 0xAB0C, 0xABB0, 0xAC54, 0xACF8, 0xAD9C, 0xAE40 | columns 3000/4000/6000 rpm in all non-zero-load rows → **15 %** (stock 25–40) | less torque in the slip phase = less shock with a short target time. Requires a DME that actually honours a deep request | P (map meaning) / E |
| Hydraulics: target slip time, upshifts | 0xBF9C, 0xBFEC, 0xC028, 0xC064 (kind1 f45, 3×3) | row Y=85 (240 Nm) **×0.85**, row Y=55 (120 Nm) ×0.92 (C064 — Y85 only); low-torque row = stock. E.g. BFEC: [50,63,75] / [44,56,66] / [36,43,53] → [50,63,75] / [40,52,61] / [31,37,45] | the main "sport" lever: controller 0x364A2 raises the pressure gradient (doc 04 §6). Alpina at 280 Nm: 30/36/26 | P / E |
| Hydraulics: target time, downshifts | 0xC0B4, 0xBFD8 (1↔2); 0xC08C (4↔5); 0xC0C8 (2↔3, 3→1, 4→2) | C0B4/BFD8: Alpina data (65 → 57, 55 → 47, same axes); C08C rows Y75/Y100 ×0.85 → [23,31,45] / [20,28,36]; C0C8 rows Y63/Y100 ×0.85 → [23,30,36] / [22,26,33] | crisper 2→1, 5→4, 3→2 under throttle; Alpina data not copied for C0C8/C08C — other axes there | P / E |
| Hydraulics: on-coming pressure, upshifts | 0xB80A (2↔3), 0xB974 (3↔4) (kind1 f32) | B80A: rows Y ≥ 82 (≥ 228 Nm) **×1.08**, lower rows stock; B974: rows Y ≥ 66 ×1.15 (from v10), rows Y ≤ 58 (≤ 132 Nm) **returned to stock** | faster torque transfer under throttle, town comfort as stock (Alpina: higher at ≥ 200 Nm, lower at low torque). B656 (1→2) and BADE (4→5) untouched | P / E |
| Hydraulics: off-going pressure, upshifts | 0xBCAE, 0xBD14 (kind1 f53) | ×1.15 everywhere (≈ Alpina +8…+10; clipped by f47 = 82/104) | less sag during overlap | P |
| Hydraulics: off-going pressure, downshifts | 0xB90E (2↔3, kind3 f45) | **Alpina data whole** (identical axes): Y85 [60,59,57,58,54,46,40,37] → [60,59,52,46,42,38,22,20]; Y110 [102,77,70,69,67,61,53,48] → [102,77,70,63,60,52,36,28] | 3→2 under throttle: releases faster, shorter "hole" | P (role, axes) / E |
| Hydraulics inherited from v10 | 0xB73E, 0xB7A4, 0xBD7A ×0.85; 0xBA78, 0xBE46, 0xBEAC ×1.15 | uniform over the whole map | B73E/B7A4 — off-going pressure 2→1 / N↔2 (direction as Alpina ×0.78); BD7A — on-coming N↔2; BE46/BEAC — on-coming on downshifts (Alpina higher at high torque). **BA78 ×1.15 goes the wrong way** (slower 4→3 release): candidate for reverting to stock in the next version | P / E; BA78 — doubtful |

What v18 did **not** touch and why — doc 09. Returned to stock compared with v10: the branch-1 row of `0x81A0` (v10 set 10/10/20/20 on the mistaken "phases" reading).

## 4. For another engine / rev limit / final drive

Must be recalculated:

1. **Shift points** of the sport programs and the manual kickdown row — for your own spark cut and your own rpm-per-km/h factor (doc 02 §3–4). Formula: `v = (n_limit − 150 − margin) / k_g`. A different final drive or tyre size changes k_g for every gear — all matrices.
2. **The Y axis of the pressure maps is engine torque**: 8×10 maps are read by actual torque (Nm/4 + 25). For a torquier engine the "high-torque rows" are the same rows Y ≥ 82, they are simply used more often; there is no extrapolation beyond 400 Nm (axis up to 125 = 400 Nm). The Alpina data in B90E was designed for 335 Nm — on a weaker engine those cells are just visited less.
3. **The X axis of the maps — turbine/32** up to 188 (6000) or 203 (6500): with a rev limit above 6500 the top cell extrapolates as a constant — for such an engine the X axis would need extending, as Alpina did (219 = 7000), but that is an axis change with all its risks; recipes do not do it.
4. Torque reduction 15 % — only if the DME actually honours the request; otherwise keep stock.

Not engine-dependent: TCC thresholds (pedal × km/h — but km/h depend on the final drive!), TCC scalars, target times (turbine rpm × torque).

## 5. How to apply

```
python3 tools/egs_tables.py info my_dump.bin                 # code e151733e…, 536 tables
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
```

If your calibration is not `19C0KA20` but, say, `19D0620P` (Alpina), the tool stops already on the axes: Alpina has different axes in some 3×3 tables (Y 85 → 95) and in C0C8. That is not a tool error — the recipe is not applicable to that base as a whole; take only the groups whose axes match and recalculate the rest. If the axes match but the old values do not (another revision of the 19x0 calibration) — compare `egs_tables.py diff` of your dump against the `old` values in the recipe and decide per group; `--force` only after that.
