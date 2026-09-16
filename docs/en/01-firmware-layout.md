# 01 · Firmware layout of GS8.60.0 (19C0 / 19D0)

Everything below applies to the Bosch GS8.60.0 with a **256 KB** image and program **19x0** (label `B22K4_04 19D0` at 0x4322). Verified on two dumps: a stock E39 2.5 (calibration `19C0 KA20`) and an Alpina B3 3.3 E46 (calibration `19D0 620P`). GS8.60.4 dumps (512 KB, e.g. 20C0 from an E46 330i) have a **different layout** — nothing in this document applies to them.

## 1. Hardware and image

| | |
|---|---|
| CPU | Motorola 68k, CPU32 family (MC68336/376: the code uses `muls.l`/`divs.l`, SIM registers at `0xFFFFFAxx`, TPU RAM at `0xFFFF00xx`). Disassembler: capstone `CS_ARCH_M68K`, mode `M68K_040` (otherwise `muls.l` does not decode) |
| Byte order | big-endian |
| Image | 262,144 bytes; reset vector at 0x0000: SP = `0xFFFF828E`, PC = `0x00000400` |
| RAM | `0xFFFF8000–0xFFFF9E00` (declared as DS2 segment 4, see §6). All variables in this documentation are given as 32-bit addresses `0xFFFFxxxx` |
| System tick | 1 ms (PIT: `0x16E6A move.w #$152,$fa22`, `0x16E70 move.w #$108,$fa24`); counter `0xFFFF82A2`. All five main tasks are registered with period 10 (0x16ED4, `moveq #$a,d1`) — a **10 ms task** |

### Memory map

| Range | Contents |
|---|---|
| `0x00000–0x00400` | vector table |
| `0x00400–0x08000` | boot loader, start-up code, DS2 driver (dispatcher 0xC8E–0xF84), identification blocks (`A5 A5 …`): 0x4322 `B22K4_0419D0 1423642 1423642`, 0x5FB6 `B22K4_04 … 0260002429 BX…`; DS2 dispatcher tables 0x3E54 / 0x3E8A (§6) |
| `0x08000–0x10000` | **calibration window** — the only thing that gets edited. Exactly what the flasher calls Partial (32 KB) |
| `0x080D0–0x0E4A2` | table zone inside the window (§2) |
| `0x0E49A–0x0FFCE` | 6964 bytes of `0xFF` (free) |
| `0x0FFCE–0x10000` | calibration label `B22K4_0419C0KA20` ×3 + 2 bytes (0x47DB in stock, 0x1851 in Alpina). These 2 bytes are not reproduced by a simple sum/XOR of the window; edited calibrations with the tail untouched run fine — apparently the ECU does not verify a window checksum (hypothesis) |
| `0x10000–0x13400` | second data area, strings (`BK8D1920BMW51911` @0x131BC), shift-automaton matrices (0x12E30, 0x12F9C, 0x12FAA, 0x12FDC, 0x13012, 0x13034) |
| `0x13784–0x15000` | `0xFF` |
| `0x15000–0x3A800` | main code (including the shift-execution module 0x34000–0x39600) |
| `0x3AA60–0x3ACE0` | descriptor array, 5 records × 32 pointers (stride 0x80), §5 |
| `0x3B372–0x3CBCC` | shift-automaton records (sets kind0..3) and their directories, see doc 04 |
| `0x3CEE0–0x3F77C` | `0xFF` |
| `0x3F77C` | final identification block |

**The code of 19C0 and 19D0 is byte-identical** in `0x10000–0x40000` (SHA-256 of that range: `e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546`). The `0x0000–0x8000` area differs between the two units in 129 bytes: 0x4B78–0x4B97 (`A5A5` markers), 0x5FDB–0x5FE1 (a 12-character string of the form `BX…` — looks like a unit serial number) and 0x6002–0x605B (programming history records — hypothesis). The calibration 0x8000–0x10000 differs in 2547 bytes. Hence: **one XDF for both programs; a full dump carries identifiers of the specific unit.**

## 2. Table format

```
2D8  : [u16 nx][u16 ny][nx bytes X axis][ny bytes Y axis][nx·ny bytes data]   data row by row (Y)
2D16 : same, axes and data 16-bit
1D8  : [u16 n][n bytes axis][n bytes data]
1D16 : [u16 n][2n bytes axis][2n bytes data]
```

Axes **strictly increase** — that is how tables are detected (`tools/egs_tables.py scan`). In the zone `0x080D0–0x0E4A2` this yields **536 tables** (15,284 bytes). The rest of the zone is scalars, axis-less matrices (0x889C, 0x88B0, 0x8D92), pointer catalogs (0x9ADC) and 1D curves of 2–3 points that the heuristic deliberately skips (about a hundred; they belong to the shift-automaton records). The old note "the zone tiles with no remainder" is wrong.

Table access from code always looks the same:

```
pea.l   <address of the pointer to the table>   ; from a catalog or a record
move.b  <X input>, d0
move.b  <Y input>, d1
clr.w   d2
jsr     <interpolator>
```

Interpolators: `0x1E848` — 2D 8-bit, `0x1EB18` — 2D 16-bit, `0x1E680` / `0x1E710` — 1D; inside the shift module — `0x2CA2A` (2D) and `0x2E462` (lookup − 128, for correction tables with neutral 128).

## 3. Pointer catalog 0x9ADC

48 32-bit pointers to the gear-selection logic tables (followed by `0xFF` up to 0x9BA8):

| Index | Pointer address | Target |
|---|---|---|
| 0 | 0x9ADC | 0x8142 (4×16) |
| 1, 2 | 0x9AE0, 0x9AE4 | **0x81A0, 0x81B2** — gear-selection module threshold vs engine rpm/32 (doc 05) |
| 3, 4 | 0x9AE8, 0x9AEC | 0x8226, 0x824A |
| 5–8 | 0x9AF0–0x9AFC | 0x8EAC, 0x8FF6, 0x9008, 0x9016 |
| 9–19 | **0x9B00–0x9B28** | **11 torque-converter lockup tables** 0x901E … 0x915E, 0x917E (doc 03) |
| 20–35 | **0x9B2C–0x9B68** | **16 shift-point matrices** 0x91B2 + k·0x70 (doc 02) |
| 36–47 | 0x9B6C–0x9B98 | 0x98B2, 0x98C0, 0x98CE, 0x98E0, 0x98F0, 0x993A, 0x9A36, 0x9A50, **0x9A6E** (thermal derate), 0x9A78, 0x9A82, 0x9AA8 |

## 4. Two calibration branches — flag 0xFFFF91CB

The **gear-selection and TCC logic** has two parameter sets. Byte `[0xFFFF91CB]` switches them: 0 — branch 0 ("normal"), 1 — branch 1. Function `0x242F6–0x24370`:

```
[0xFFFF91CB] = 0
if [0xFFFF916C] != 0 and [0x8975] == 254            → 1
else index = (selector − 1)·3 + [0xFFFF91F0]
     if [0xFFFF903A] == 2: byte 0x8D92 + index       else: byte 0x8D78 + index
     if byte == 254                                  → 1
```

Tables of 3 bytes per selector position (verified against the dump):

| Selector | 0x8D92 | 0x8D78 |
|---|---|---|
| 1 | 9, 9, 8 | 9, 9, 8 |
| 2 | 255, **254**, 8 | **254, 254**, 8 |
| 3 | 255, **254**, 8 | **254, 254**, 8 |
| 4 | 255, **254**, 8 | 255, **254**, 8 |
| 5–7 | 0, 0, 0 | 0, 0, 0 |

So from the factory branch 1 is enabled for selector positions 2–4 in sub-mode 1. What exactly "selector 2/3/4" and "sub-mode" mean in terms of S/M/taps is not proven from code; by logs branch 1 coincides with S/M (hypothesis).

How the branches differ (all addresses in the calibration window):

| Parameter | Branch 0 | Branch 1 |
|---|---|---|
| TCC threshold table pairs | 0x901E, 0x905E, 0x909E, 0x90DE, 0x913E | 0x903E, 0x907E, 0x90BE, 0x910E, 0x915E |
| TCC stage release matrix | 0x889C | 0x88B0 |
| minimum pedal for lockup | 0x819C = 3 | 0x819D = 8 |
| 0x81A0 (Y row) | 30 / 30 / 255 / 255 | 15 / 15 / 30 / 30 |
| 0x98CE (Y row) | 0 / 43 / 86 / 128 | 129 / 171 / 213 / 255 |

**Important:** the shift-execution module (hydraulics, 0x34000+) **does not read** flag `0xFFFF91CB`. Pressures and times are the same for D and S/M. There is no separate "sport hydraulics" branch in this software.

A mistake already made here once: bit 2 in the program attribute table `0x88F2 + k` does **not** enable branch 1 — function 0x222D4 writes 5 to `0xFFFF90C2`, whose purpose is unknown.

## 5. The 16 shift programs and descriptors

The active program number is `0xFFFF91B0`. Shift-point matrices: 0x91B2 + k·0x70 (doc 02). Program roles:

| k | Address | Role | Basis |
|---|---|---|---|
| 00 | 0x91B2 | D-like | shape |
| 01, 02 | 0x9222, 0x9292 | sport | shape; in stock they differ from D only at part throttle |
| **03, 04, 07** | 0x9302, 0x9372, 0x94C2 | **D** | 13 of 14 shift events in a log matched these matrices |
| 05 | 0x93E2 | hold (upshift 250 everywhere) | shape |
| 06, 14 | 0x9452, 0x97D2 | D-like (economy) | shape |
| **08, 09, 10** | 0x9532, 0x95A2, 0x9612 | **manual**: rows do not depend on pedal; downshift columns are protection lines | shape; by log, manual mode = program 178 in byte 22 of the status frame |
| 11, 15 | 0x9682, 0x9842 | sport (11 — early shifts) | shape |
| 12 | 0x96F2 | only 1→2 (30 km/h), never above 2nd | shape |
| 13 | 0x9762 | start in 2nd (1→2 = 0) — winter | shape |

Everything "by shape" is a hypothesis: the mapping of program number to button/selector lives in code (0x2300C → 0x23110 → 0x23230 → `0xFFFF91A0`) and is not fully traced.

Descriptors `0x3AA60`: 5 records × 32 pointers (stride 0x80). Slot 12 → six 2D16 4×5 maps `0xA2C6 / 0xA304 / 0xA342 / 0xA380 / 0xA3BE / 0xA3FC` (X axis 140/150/180/255 raw temperature units, values −80 or 0) — cold corrections. Slots 13–15 → 16 tables 4×4 in `0xA066–0xA20A` — purpose not decoded (these are **not** TCC thresholds, as one third-party report claimed).

## 6. DS2 dispatcher

Dispatcher 0xC8E–0xF84, command table `0x3E54` — 9 entries `[cmd][pad][ptr32]`:

| Command | Handler | What |
|---|---|---|
| 0x00 | 0x0F8A | identification |
| 0x06 | 0x1088 | **memory read** by segment |
| 0x07 | 0x112E | memory write |
| 0x0A | 0x1360 | checksum |
| 0x0D | 0x152E | block 0x3E0E |
| 0x90 / 0x91 | 0x1598 / 0x1708 | flash |
| 0x9E / 0x9F | 0x17D2 / 0x17F2 | — |

Unknown command → reply `0xFF` (0xCFC). **There is no command 0x0B in this software** — the "frame 0B 03" that INPA/loggers read is a tester job that internally uses memory read 0x06.

Segment table `0x3E8A`, 8 entries `[type][pad][start32][end32]`:

| Type | Range | What |
|---|---|---|
| 0, 2, 6, 15 | 0x000000–0x040000 | ROM |
| 3 | 0x000000–0x000100 | EEPROM (via I²C, 0x1D58) |
| **4** | **0xFF8000–0xFF9E00** | **RAM** |
| 1, 5 | empty | — |

How to use this for logging — doc 06.

## 7. What "stock" means in this repository

The stock calibration all recipes are relative to: program 19D0, calibration label `B22K4_0419C0KA20`, SHA-256 of window 0x8000–0x10000 `d3c2c3fdffb943f5bd848f672c6d3750a79986167c59c72dac367d386cbbdf51`. The dump itself is not published — it contains unit identifiers and, in EEPROM, may contain the VIN. You need **your own** dump; `tools/egs_tables.py info` shows whether the code and the label match.
