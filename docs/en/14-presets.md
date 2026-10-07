# 14 · Presets sport-daily, street-hard, track-hard for GS8.60.0 and GS8.60.4

A preset here is a chain of the patches of document 13 plus the engine limiter. The same three presets exist for both programs: GS8.60.0 (19C0 / 19D0, 256 KB) and GS8.60.4 (20C0, 512 KB). There are two ways to build one:

- on your own dump: `egs_patch.py preset NAME my_dump.bin -o build.bin --spark RPM --cut RPM`. The tool checks the image, applies the patches for your engine and recomputes the checksums. This is the main way;
- with a ready recipe from `recipes/` (JSON diff, document 08 §1) and `apply_recipe.py`. A recipe is built on one factory calibration for the reference engine of the platform; on another calibration it stops.

The older presets v18-v20 (document 08) stay in the repository for the record. They were built on readings some of which were disproved (document 08 §6), and since 06.10.2026 `verify-shift` reports their manual upshift thresholds as errors: 6781-6802 turbine rpm is above the factory monitor 6720 − 100. For a new build use the presets of this document.

## 1. What is in each preset

| Preset | D | S | M | Chain |
|---|---|---|---|---|
| `sport-daily` | factory | the gate gives S, no 5th, full-throttle upshifts under the limiter, converter locked from 1600 rpm in 2nd-5th | converter from 1600 in 2nd-5th, holds the gear on the limiter, kick-down does not downshift in M | `gate:mode=S` `s-no5` `shift-wot:modes=S` `tcc-lock:modes=S+M` `manual-hold:monitor=auto` |
| `street-hard` | factory, but no warm-up and no kick-down | as sport-daily, plus the converter locked in 1st under throttle from 1760 | as sport-daily, plus the converter in 1st, the buttons work with the pedal floored | sport-daily + `tcc-first:modes=S+M` `no-kickdown` `no-warmup` |
| `track-hard` | full-throttle upshifts under the limiter, converter from 1600 in 3rd-5th and in 1st under throttle from 2110 | as street-hard | as street-hard | `shift-wot:modes=D+S` `tcc-lock:modes=D+S+M` `tcc-first:modes=D+S+M` instead of the S variants |

Common to all three: the gate gives S first (code `0xFE`, as the factory BMW), the first +/- tap switches to M. What each patch does and which addresses it writes is in document 13.

## 2. Engine limiter

A preset needs two numbers: `--spark` (the lower limiter; the full-throttle upshifts and the 5>4 downshift in S are set from it) and `--cut` (the highest hard cut; the M thresholds are set from it). Without them the reference engine of the platform is used:

| Platform | Reference engine | `--spark` | `--cut` |
|---|---|---|---|
| 19x0 | M52TUB25, factory MS42 0110C6 limiter for the automatic, 6496-6592 | 6496 | 6592 |
| 20C0 | M54B30, factory MS43 limiter: soft 6528-6624, hard 6624-6720 by gear | 6528 | 6720 |

For another engine rebuild the preset with its numbers. The final drive and the wheels do not change the shift rpm (document 02 §3).

## 3. Result on the reference calibrations

Turbine rpm. In S the full-throttle upshifts, in M the automatic upshift only on the overrun (above the cut), 4>5 in S never.

| | 19x0 `19C0 KA20`, M52TUB25 | 20C0 `0520C06440`, M54B30 |
|---|---|---|
| S full throttle, 1>2 / 2>3 / 3>4 | 5278 / 5885 / 5988 | 5395 / 5885 / 6033 with the converter locked (4926 / 5757 / 5943 open) |
| S, the 5>4 downshift lands 4th | at most 5984 | at most 6016 |
| M, automatic upshift 1>2 / 2>3 / 3>4 / 4>5 | 6802 / 6781 / 6754 / 6752 | 6920 / 6909 / 6889 / 6880 |
| turbine monitor | 6720 → 6912 (`monitor=auto`) | 7232, unchanged |
| converter in S and M, 2nd-5th (lock) | 1599 / 1621 / 1600 / 1543 | 1599 / 1621 / 1600 / 1591 |
| converter in 1st (street-hard, track-hard) | S/M from 1759 on a light pedal, D from 2111 (track-hard) | the same, near the floor the factory 1407 |
| bytes changed (with checksums): sport-daily / street-hard / track-hard | 268 / 369 / 420 | 294 / 332 / 382 |

On 19x0 `street-hard` and `track-hard` contain `tcc-first`, which changes code on 19x0 (document 13 §1). Flash such builds as a full image only, and there is no recipe for them: a recipe cannot carry code. Build them with `egs_patch.py preset`.

## 4. Recipes in `recipes/`

| File | Base | Result (SHA-256 of the full image) |
|---|---|---|
| `gs8600_19x0_sport_daily.json` | GS8.60.0, calibration `B22K4_0419C0KA20` (E39 2.5) | `d3fda1b5…`, partial `af1b7003…` |
| `gs8604_20c0_sport_daily.json` | GS8.60.4 20C0, calibration `B223K_0520C06440` (the Alpina B3S file) | `2a7701dd…` |
| `gs8604_20c0_street_hard.json` | the same | `73039a98…` |
| `gs8604_20c0_track_hard.json` | the same | `166de54b…` |

Every recipe records the tool, preset, chain and engine limits in `built_with`. With `GS860_STOCK` and `GS8604_STOCK` set, `tests/test_tools.py` applies every recipe to the factory image and checks the SHA-256 of the result, the checksums and the shift-point rules (document 02 §4), and builds every preset both with `egs_patch.py preset` and from its recipe and compares them byte for byte.

```
python3 tools/apply_recipe.py recipes/gs8604_20c0_sport_daily.json my_20c0.bin -o build.bin
python3 tools/gs860_crc.py check build.bin
python3 tools/egs_tables.py verify-shift build.bin --spark 6528 --cut 6720 --stock my_20c0.bin
```

Flash the full 512 KB image on 20C0. On 19x0 sport-daily may go as the 32K partial (`build_partial32k.bin`); reset the adaptations after flashing (document 07).

## 5. Status

No preset as a whole has been road-tested. Every patch in them is proven by code (document 13). On 19x0 the counterparts of `tcc-lock`, `tcc-first`, `s-no5` and `manual-hold` are flashed on the reference E39 (WOLF4X builds v24-v44, `tcc-first` byte for byte as v41-v44), but the converter lock-up in 1st is not confirmed by a log yet, only by code analysis and emulation. No 20C0 build has been tested on a car. Before trusting one, take a log (document 06): program, gear, turbine and engine rpm, TCC clutch state.

## 6. What the presets are not

- They do not touch the hydraulics (pressures, slip times). They do not make the shift itself "faster", only "locked earlier" and "upshifting later" (what "faster" means on the Alpina 20C0 is in document 12 §9).
- They do not touch AGS (adaptive program selection), except the lower bound of the S points in `s-no5`.
- They are not a transfer of the Alpina calibration to BMW or back: table axes are never changed (document 09 §2).
