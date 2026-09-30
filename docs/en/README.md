# Documents

Documents 01–10 are about the GS8.60.0 (program 19C0 / 19D0, 256 KB image), document 11 is about the GS8.60.4 (program 20C0, 512 KB image). The Russian versions are in [`../ru/`](../ru/README.md), with the same structure and facts.

| Document | In one line |
|---|---|
| [01 · Firmware layout](01-firmware-layout.md) | memory map, table format, the 536 tables of the zone, pointer catalog `0x9ADC`, the two calibration branches, the 16 programs, DS2 dispatcher |
| [02 · Shift points](02-shift-points.md) | the 16 matrices, their unit (output shaft rpm / 32) and how to check a point against the engine limiter |
| [03 · Torque converter lockup](03-torque-converter-lockup.md) | the real lockup (request 0 / 1 / 2, thresholds `0x993A`, clutch state machine) and AGS, which was taken for it |
| [04 · Shift execution and hydraulics](04-shift-execution-hydraulics.md) | record sets, phases, slip-time controller, clutch pressures, table families, CAN |
| [05 · Protections](05-protections.md) | voltage monitor `0x265F4`, thermal derate, limp mode, turbine monitor `0x26C84` |
| [06 · Logging over DS2](06-logging-ds2.md) | physical layer, commands, bytes of the `0B 03` frame, RAM addresses for A/B |
| [07 · Reading and flashing](07-reading-and-flashing.md) | full 256K and partial 32K, order of operations, roll-back, the three checksums |
| [08 · Recipes and presets](08-recipes-and-presets.md) | recipe format, the v18 changes table by table, what the presets really change (§6) |
| [09 · What not to touch](09-what-not-to-touch.md) | the prohibitions, each with the reason |
| [10 · Methodology](10-methodology.md) | tools, what counts as proven, confidence scale, refuted readings, open questions |
| [11 · GS8.60.4 (20C0)](11-gs8604-20c0.md) | the 512 KB image: map, checksums, matrices, lockup, AGS, protections, the 20 record roots and the field roles proven by code, execution-module RAM, `0B 03` frame, what is proven and what is not |
| [Glossary](glossary.md) | terms and abbreviations |
