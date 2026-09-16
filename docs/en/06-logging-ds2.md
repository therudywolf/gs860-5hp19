# 06 · DS2 and logging

## 1. Physical layer

K-line, ECU address **0x32**, **9600 baud only** — GS8.60.0 does not answer at the raised speeds some patched DMEs support; a logger that talks to both ECUs must stay at 9600 or switch speed per request. The ECU does not answer unless a pause is kept after another ECU's reply (the reference logger used 150 ms plus one retry; after optimisation 40 ms of bus silence and a 250 ms timeout, ≈8–10 frames/s when polling only the EGS).

Frame: `<address> <length> <data…> <XOR>`; the length counts the whole frame including itself and the checksum; the checksum is the XOR of all preceding bytes. Reply: `<address> <length> <A0 | B0 | A1 | A2> …` (A0 — OK, B0 — command rejected, A1 — busy/error, A2 — no data).

## 2. Commands that exist in the firmware

Dispatcher (doc 01 §6): `0x00` identification, **`0x06` memory read**, `0x07` write, `0x0A` checksum, `0x0D`, `0x90/0x91` flash, `0x9E/0x9F`. Anything else → `0xFF`. Commands `0x04` (faults), `0x05` (clear), `0x0B 0x03` (status) are **absent** from table 0x3E54: what testers show as the "0B 03 frame" (24-byte body) is a tester job that gathers values by reading RAM through 0x06. So "bytes 12 / 17 / 20" are bytes of a RAM block whose address the job defines; the ROM has no such layout.

RAM read: command `0x06`, **segment 4**, range `0xFF8000–0xFF9E00` (table `0x3E8A`). The exact argument format of `0x06` (segment, address, length) is not documented in these notes — capture it from a factory tester (INPA/DIS) running the status jobs and replay; the reply format is the RAM bytes themselves.

## 3. Body of the "0B 03 frame" (24 bytes) — what logs have decoded

| Byte | What | Scale / status |
|---|---|---|
| 0 | engine rpm | × 32 |
| 1 | turbine rpm | × 32 |
| 2 | output shaft rpm | × 32; speed = byte × 32 / k (reference car k = 27.11 rpm per km/h) |
| 3 | pedal | ≈ × 3.6 (0…255 → %); full throttle without kickdown ≈ 229 |
| 4 | rpm gradient | signed |
| 6 | ATF temperature | **°C = byte − 48** (`[0xFFFF90D4] = [0xFFFF8435] × 3/4`, doc 03 §6) |
| 7 | battery voltage | × 0.0813 V (by correlation) |
| 12 | **255 = shift in progress** | proven by log (every 255 frame is adjacent to a change of byte 20). No 0xFF write in ROM — hypothesis: the job outputs flag `0xFFFF9717/9718` |
| 17 | solenoid picture MV1/MV2/MV3 (bits 7/6/5): 1st/2nd → 192, 3rd → 64, 4th → 0/64, 5th → 160 | matches table `0x12E30` (doc 04 §13) |
| 18 | lever: 220 = P, 140 = R, 236 = N, 44 = D, 46 = D in S/M, 172 = transition | by log |
| 20 | **gear × 32** (32 … 160) | proven by log; intermediate values only during a shift |
| 21 | flags: 192 = shifting; bit 0 = M; bits 4/5 — taps | incomplete |
| 22 | program: 0 = D, 34 = S, 178 = M | by log |

Converter slip = byte 0 − byte 1 (× 32) — evaluate **under load only** (throttle > 5°, air mass > ~90 kg/h): on the overrun slip collapses to zero regardless of the clutch, and any "locked N %" statistic without a load filter is garbage.

Limitation of the status frame: when alternating with DME polling the EGS frame updates once per ~1.3 s, a shift lasts 0.3–0.8 s — shift duration cannot be measured with this frame. Measurements need an "EGS only" mode reading RAM.

## 4. What to read from RAM for hydraulic A/B

Command 0x06, segment 4, period 10–20 ms. Addresses and meaning from the execution-module reverse (doc 04):

| RAM | What | Metric |
|---|---|---|
| `0xFFFF9717` / `0xFFFF9718` | shift in progress / pressure sequence in progress | duration (equivalent of byte 12 = 255) |
| `0xFFFF9735`, `0xFFFF973D` | phase number, phase timer (× 10 ms) | duration of phases 2, 4, 9, 10 |
| `0xFFFF966C` (s16) | slip to target sync, rpm | time from start of phase 9 until \|966C\| ≤ 100 — this is the "slip time"; flare / sag |
| `0xFFFF97B4`, `0xFFFF97B2` (u16) | turbine, n_out | turbine sag on upshift / overshoot on downshift |
| `0xFFFF9720`, `0xFFFF9783` | on-coming / off-going pressure (0..255) | ramp shape; hitting f24 (116/138) = target time too short |
| `0xFFFF96AE`, `0xFFFF9666` | controller correction, slip-time deviation | if 96AE is constantly large — the target is unrealistic |
| `0xFFFF965E`, `0xFFFF9668`, `0xFFFF9480/9482/9484` | adaptations | drift after flashing |
| `0xFFFF958C` | EDS1 pressure (/50) | output check |
| `0xFFFF97A0` (u16) | engine torque, Nm | link to the Y axis of the maps (Y = Nm/4 + 25) |
| `0xFFFF9725` | turbine/32 at start | X axis of the pressure maps |
| `0xFFFF971A`, `0xFFFF971B` | transition type, kind | which record was active |
| `0xFFFF9182`, `0xFFFF918F`, `0xFFFF91B0`, `0xFFFF91CB` | pedal, speed km/h, program, branch | gear selection and TCC |
| `0xFFFF91AC`, `0xFFFF9216` | TCC stage, TCC control value | lockup |

"Better" for hydraulics means: a shorter phase 10 at the same torque, no rise in the peak d(turbine)/dt after sync, `0xFFFF9720` not hitting f24, no turbine overshoot on downshifts above ~150 rpm over the new gear's synchronous speed, and `0xFFFF96AE` not growing shift after shift (otherwise the adaptation is fighting the calibration).

## 5. Pitfalls

1. Do not kill the logger hard: the DME may stay at the raised speed and the next session will not find it — terminate cleanly.
2. Two processes on one port fight ("multiple access on port"); stop the background one first.
3. Always check the frame length when parsing: the last byte is the XOR, not data.
4. Rpm peaks between polls are lost — do not judge maxima from a sparse frame.
