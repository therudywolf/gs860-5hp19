# Glossary

| Term | Meaning in this repository |
|---|---|
| **GS8.60.0 / GS8.60.4** | generations of the Bosch transmission ECU for the ZF 5HP19 in BMWs. GS8.60.0 — 256 KB image (programs 19C0/19D0 and others), GS8.60.4 — 512 KB (e.g. 20C0), different layout (document 11) |
| **19C0 / 19D0** | software/calibration labels in the image. In both dumps studied the program (code 0x10000–0x40000) is labelled 19D0 and is byte-identical; the calibration label in the window tail (`0x0FFCE`) is `19C0 KA20` on the stock E39 2.5 and `19D0 620P` on the Alpina B3 |
| **Calibration window / Partial** | image area `0x8000–0x10000`; as a separate 32 KB file, offset = address − 0x8000 |
| **Stock** | the stock calibration the recipes are relative to (label `19C0KA20`) |
| **Recipe** | a JSON diff stock → tune: addresses, axes, old and new data; axes never change (doc 08) |
| **Branch 0 / branch 1** | D / S. Switched by the S flag `0xFFFF91CB` (doc 01 §4): 1 in the gate before a +/- tap. The branch is read by the AGS functions and by table 0x81A0, it has nothing to do with the TCC or the hydraulics. M is a separate flag `0xFFFF91F3`. Early notes called them "normal" / "aggressive" |
| **Program (P0…PF)** | one of the 16 shift programs, the active one is held in `0xFFFF91A0`. The matrix for it is chosen by the table in function 0x24BA4: P0 = k14, P1 = k6, P2 = k11, P3 = k15, P4 = k0, P5 = k1, P6 = k2, P7 = k13, P8 = k9, P9 = k12, PA = k5, PB = k10, PC = k7, PD = k8, PE = k4, PF = k3. `0xFFFF91B0` is the forced program (0 / 4 / 5), doc 01 §5 |
| **Zug / Schub** | German "pull" / "coast": shift under load (class 1) or without load (class 0), flag `0xFFFF9722` |
| **Hochschaltung / Rückschaltung** | upshift / downshift |
| **kind (0…3)** | record set of the execution automaton: 0 Schub-Hoch, 1 Zug-Hoch, 2 Schub-Rück, 3 Zug-Rück; `0xFFFF971B` |
| **Transition type (1…8)** | record index inside a set from the matrix `0x12FDC`[from-1][to-1] (`0xFFFF971A`). Kind 1: 2 1-2, 3 2-3, 4 3-4, 5 4-5, 6 3-1, 7 4-2, 8 5-3, confirmed. Kind 2 (checked in code on 25.09.2026): 0 is 1 to 6, 1 is 2 to 6, 2 is 2 to 1, 3 is 3 to 2. Gear code 6 is not neutral but 1st with one extra shift element (0x12D31), the old label N-2 is wrong (doc 04 §2) |
| **Record / field fNN** | an array of 32-bit pointers to the calibrations of one transition; field fNN is the pointer at offset 4·NN |
| **Phase** | a step of the pressure sequence (`0xFFFF9735`), table `0x13034`: 1 pause, 2 fast fill, 3 separating tick, 4 approach, 9 open-loop slip pressure, 10 controlled slip, 11 squeeze, 12 end of downshift |
| **Schnellfüllung / fill time** | phase 2: fast fill of the on-coming clutch; time f10(ATF) + corrections, pressure f13(ATF) |
| **Füllausgleich** | phase 4: equalisation / approach to the kiss point, duration f27 |
| **Schleifdruck / slip pressure** | on-coming clutch pressure in phases 9–11 (kind1/kind3 f32), `0xFFFF9720` |
| **Überschneidung / overlap** | simultaneous action of off-going and on-coming clutches on an upshift; off-going pressure — kind1 f53, `0xFFFF9783` |
| **Target slip time** | 3×3 tables (kind1 f45, kind3 f33/f69): how many 10 ms ticks the slip phase should take; controller 0x364A2 picks the pressure gradient |
| **On-coming / off-going clutch** | the pack that builds pressure and the pack that is released |
| **EDS** | Elektronischer Drucksteller, proportional pressure solenoid (several channels in the 5HP19, the converter clutch has its own). For the converter clutch the PWM `0xFFFF95BA` goes to the output `0xFFFFFF34` (third-party reverse, accepted on 23.09.2026). For the other channels the PWM-to-solenoid mapping is not proven |
| **MV** | Magnetventil — on/off shift solenoid MV1…MV3; their pattern per gear is table `0x12E30` |
| **WÜK / TCC** | Wandlerüberbrückungskupplung, torque converter lock-up clutch. The upper level 0x29056 computes the request `0xFFFF91F9` every 10 ms: 0 open, 1 controlled slip, 2 locked (thresholds 0x993A, groups 0x897E). The lower state machine 0x32B08 / 0x33F66 (states 0-8) drives the PWM `0xFFFF95BA` up to 0x1F40 (doc 03) |
| **TCC stage** | an obsolete term of this repository. The "ladder" `0x888C` (32/96/160/224 stock) holds the "home" points of the AGS levels, not clutch stages (doc 03 §7). The clutch has the request 0 / 1 / 2 and the states 0-8 |
| **Turbine** | speed of the converter turbine = transmission input shaft (`0xFFFF97B4`); equals engine speed with the clutch locked |
| **n_out** | output shaft speed (`0xFFFF97B2`), 27.11 rpm per km/h on the reference car. The shift matrices, the speed axes of the AGS tables and the TCC thresholds 0x993A hold n_out / 32 (`0xFFFF918F`), doc 02 §3 |
| **Torque** | `0xFFFF97A0`: turbine torque, Nm, 97A4 × 97F4 / 100 (0x2DFBA). Map Y axis `0xFFFF97DF` = 97A0/4 + 25 |
| **ATF** | transmission fluid; raw sensor byte `0xFFFF8435`; in the frame °C = byte − 48 |
| **Thermal derate** | limitation of the effective pedal by ATF temperature (table `0x9A6E`, doc 05 §2) |
| **Torque reduction** | request to the DME to cut torque during a shift. One channel: byte 3 of the EGS1 frame, `0xFFFF90C0` from `0xFFFF918D` = max(`0xFFFF958D`, `0xFFFF97E1`), 958D is written only by 0x2E3C6 (doc 04 §9). The maps `0xAB0C…0xAE40` are the reference slip of the TCC regulator, not torque reduction |
| **Tick (10 ms)** | unit of all times in the shift-execution tables |
| **Kickdown** | pedal row 255 of the shift matrices, the full-travel switch. Kickdown flag `0xFFFF9113`: with it the manual branch is off (doc 02 §5) |
| **Limp mode** | Notlauf: 4th gear, pressure regulators off. Flag `0xFFFF90C1`, set by 0x222A2 from bit 3 of the mask word `0xFFFF8FA2`. In the 0B 03 frame it is bit 0 of byte 18, it also shows in bytes 12/14/17/20. `0xFFFF9113` is kickdown, not limp mode (doc 05 §3, §6) |
| **DS2** | BMW diagnostic protocol over K-line; GS8.60.0 address 0x32, 9600 baud, RAM read with command 0x06 |
| **Segment 4** | in the DS2 segment table `0x3E8A` — RAM `0xFF8000–0xFF9E00` |
| **XDF** | TunerPro definition; `xdf/GS8600_19D0_Full256K.xdf` (256 KB) and `xdf/GS8600_19x0_Partial32K.xdf` (32 KB, addresses − 0x8000) |
| **Alpina (reference)** | the Alpina B3 3.3 E46 calibration on the same software (19D0 620P); used as the factory example of a "fast" calibration, but its axes are not copied |
| **AGS** | adaptive program selection: the points `0xFFFF9216` (0..255) give a level 1-4, and the level selects the program (D: P0 / P1, S: P2 / P3). Functions 0x1DEBC, 0x1Fxxx, tables 0x901E-0x915E, parameters 0x888C-0x88C1. Until 23.09.2026 this repository wrongly described AGS as the TCC lockup (doc 03 §7) |
| **S flag / M flag** | `0xFFFF91CB` = 1 in the gate before a +/- tap (S), `0xFFFF91F3` = 1 after a +/- tap with program code 0x0B / 0x0D (M), doc 01 §4 |
| **Step 0xFFFF90CD** | 1 / 2 / 3 switch to programs P4 / P5 / P6 (matrices k0 / k1 / k2) with priority above D and S. That these are hill steps is a hypothesis, not proven |
| **Minimum gear** | table `0x8AE2 + 5 × program` (0x1E442, `0xFFFF91B4`, arbiter 0x236C8): keeps a manual downshift from landing the engine above the threshold, never shifts up by itself (doc 02 §5) |
| **Turbine monitor** | 0x26C84, 50 ms task: a turbine speed `0xFFFF8DE2` at or above [0x8B44] (stock 6720) for about a second sets fault 0x25 and limp mode (doc 05 §6) |
| **EGS1 / DME1 / DME2** | CAN frames. EGS1 (0x43F) is sent by the box: byte 0 bits 0-2 target gear, byte 3 torque reduction. From DME1 the box takes the engine speed, from DME2 the brake (byte 6 bit 0, `0xFFFF97F5`). The pedal arrives as CAN byte `0xFFFF8439`, apparently byte 5 of DME2 (an inference, not checked). DME2 byte 2 is not read by the stock software (doc 04 §15) |
