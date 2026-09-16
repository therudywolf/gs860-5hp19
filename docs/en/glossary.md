# Glossary

| Term | Meaning in this repository |
|---|---|
| **GS8.60.0 / GS8.60.4** | generations of the Bosch transmission ECU for the ZF 5HP19 in BMWs. GS8.60.0 — 256 KB image (programs 19C0/19D0 and others), GS8.60.4 — 512 KB (e.g. 20C0), different layout |
| **19C0 / 19D0** | software/calibration labels in the image. In both dumps studied the program (code 0x10000–0x40000) is labelled 19D0 and is byte-identical; the calibration label in the window tail (`0x0FFCE`) is `19C0 KA20` on the stock E39 2.5 and `19D0 620P` on the Alpina B3 |
| **Calibration window / Partial** | image area `0x8000–0x10000`; as a separate 32 KB file, offset = address − 0x8000 |
| **Stock** | the stock calibration the recipes are relative to (label `19C0KA20`) |
| **Recipe** | a JSON diff stock → tune: addresses, axes, old and new data; axes never change (doc 08) |
| **Branch 0 / branch 1** | the two parameter sets of gear selection and TCC, flag `0xFFFF91CB` (doc 01 §4). Early notes called them "normal" / "aggressive" |
| **Program (0…15)** | one of the 16 shift-point matrices, number in `0xFFFF91B0` |
| **Zug / Schub** | German "pull" / "coast": shift under load (class 1) or without load (class 0), flag `0xFFFF9722` |
| **Hochschaltung / Rückschaltung** | upshift / downshift |
| **kind (0…3)** | record set of the execution automaton: 0 Schub-Hoch, 1 Zug-Hoch, 2 Schub-Rück, 3 Zug-Rück; `0xFFFF971B` |
| **Transition type (1…8)** | record index inside a set: 1 N↔2, 2 1↔2, 3 2↔3, 4 3↔4, 5 4↔5, 6 3→1, 7 4→2, 8 5→3; `0xFFFF971A`, matrix `0x12FDC` |
| **Record / field fNN** | an array of 32-bit pointers to the calibrations of one transition; field fNN is the pointer at offset 4·NN |
| **Phase** | a step of the pressure sequence (`0xFFFF9735`), table `0x13034`: 1 pause, 2 fast fill, 3 separating tick, 4 approach, 9 open-loop slip pressure, 10 controlled slip, 11 squeeze, 12 end of downshift |
| **Schnellfüllung / fill time** | phase 2: fast fill of the on-coming clutch; time f10(ATF) + corrections, pressure f13(ATF) |
| **Füllausgleich** | phase 4: equalisation / approach to the kiss point, duration f27 |
| **Schleifdruck / slip pressure** | on-coming clutch pressure in phases 9–11 (kind1/kind3 f32), `0xFFFF9720` |
| **Überschneidung / overlap** | simultaneous action of off-going and on-coming clutches on an upshift; off-going pressure — kind1 f53, `0xFFFF9783` |
| **Target slip time** | 3×3 tables (kind1 f45, kind3 f33/f69): how many 10 ms ticks the slip phase should take; controller 0x364A2 picks the pressure gradient |
| **On-coming / off-going clutch** | the pack that builds pressure and the pack that is released |
| **EDS** | Elektronischer Drucksteller — proportional pressure solenoid (several channels in the 5HP19; the converter clutch has its own). Which PWM channel drives which solenoid is not proven for this software |
| **MV** | Magnetventil — on/off shift solenoid MV1…MV3; their pattern per gear is table `0x12E30` |
| **WÜK / TCC** | Wandlerüberbrückungskupplung — torque converter lock-up clutch. In GS8.60.0 a four-stage ladder of a control value (doc 03) |
| **TCC stage** | one of the 4 ladder values `0x888C` (32/96/160/224 stock); chosen by pedal and speed |
| **Turbine** | speed of the converter turbine = transmission input shaft (`0xFFFF97B4`); equals engine speed with the clutch locked |
| **n_out** | output shaft speed (`0xFFFF97B2`); 27.11 rpm per km/h on the reference car |
| **Torque** | engine torque from CAN, Nm (`0xFFFF97A0`); map Y axis = Nm/4 + 25 |
| **ATF** | transmission fluid; raw sensor byte `0xFFFF8435`; in the frame °C = byte − 48 |
| **Thermal derate** | limitation of the effective pedal by ATF temperature (table `0x9A6E`, doc 05 §2) |
| **Torque reduction** | request to the DME to cut torque during a shift; maps `0xAB0C…0xAE40`, value = % of torque left |
| **Tick (10 ms)** | unit of all times in the shift-execution tables |
| **Kickdown** | pedal row 255 of the shift matrices — the full-travel switch |
| **Limp mode** | Notlauf: the ECU holds one gear, `0xFFFF9113 != 0`; visible in the status frame by bytes 12/14/17/18/20 |
| **DS2** | BMW diagnostic protocol over K-line; GS8.60.0 address 0x32, 9600 baud, RAM read with command 0x06 |
| **Segment 4** | in the DS2 segment table `0x3E8A` — RAM `0xFF8000–0xFF9E00` |
| **XDF** | TunerPro definition; `xdf/GS8600_19D0_Full256K.xdf` (256 KB) and `xdf/GS8600_19x0_Partial32K.xdf` (32 KB, addresses − 0x8000) |
| **Alpina (reference)** | the Alpina B3 3.3 E46 calibration on the same software (19D0 620P); used as the factory example of a "fast" calibration, but its axes are not copied |
