# 14 · The engine link: cruise buttons and the mode through a free byte of the DME2 frame (19x0 and 20C0)

> This document is licensed under [CC BY-NC-SA 4.0](../../LICENSE-docs-nc), unlike the rest of the repository's documents (CC BY-SA 4.0): copy, translate and build on it with credit and under the same licence, but not commercially. It describes the author's own layer on the gearbox side; a finished build for a particular dump is the author's paid work (README, "Custom work").

The engine side is in the MS4X repository, document 05 ("The mode layer", §12): the engine layer writes into the byte of the DME2 frame the factory sends as zero and nobody else reads, byte 2 on the MS42 (buffer 0xEFD9), byte 7 on the MS43 (0xEFDE). Here is what the gearbox does with that byte: how it reaches the lever dispatcher, where the hooks are, how it is protected. It drives two cars: an E39 (GS8.60.0 19D0) and an E46 (GS8.60.4 20C0). No code, no settings layout, no tuned numbers here; code addresses are file offsets, RAM cells absolute addresses `0xFFFFxxxx` as capstone writes them.

## 1. What is sent

| Platform | DME2 byte | Bits | Duration |
|---|---|---|---|
| MS42 → 19x0 | 2 | 2 "up", 3 "down", 4–5 the engine's effective mode, 6 launch, 0–1 and 7 = 0 | a button is held for 8 DME2 frames |
| MS43 → 20C0 | 7 | 0 "+" (up), 1 "−" (down); the mode is not sent | a pulse of 8 frames (80 ms), a new edge cancels the previous one |

The common rule: without a live byte (an engine without the layer, the layer off, a stale frame) the gearbox is factory. The cluster and the ASC see the byte too; the factory sends zeros in it; after the first drive, scan both.

## 2. GS8.60.0 19x0 (E39): reception and mixing into the lever dispatcher

**Reception (DMEX).** Hook 0x2175A in the DME2 frame handler `0x20FAC` (10 ms task): the factory `move.w #0,$ffff8450.l` (8 bytes) is replaced by a `jsr` into own code plus `nop`; the displaced instruction runs inside. Every call: initialisation of the cells by a magic; frame freshness by the flag `0xFFFF8452` (0 on reception, +1 per tick, dead above a threshold); the edges of bits 2 and 3 of byte 2 → "up"/"down" requests (only with a live frame, the switch on and the lever in the S/M gate); bits 4–5 → the mode cell (0xFF when the frame is dead or the switch off); bit 6 → launch; the age of an edge (older than a threshold: reset); the double-tap window; a call of the vector 0x3E7F8, a 10 ms tick for any other code (the author's on-board recorder hangs there). Every register is preserved.

**Mixing into the action (MIX).** Hook 0x25AEA in the manual M branch of the lever dispatcher `0x259DA` (30 ms task): the factory `move.b $ffff9169.l,d0` (the lever contact read) is replaced by a `jsr`; the lever beats the button, and the button goes straight into the body of the "up"/"down" action, not into the contact, so it does not depend on the lever inversion. The "down" body `0x25B34–0x25B4C`: the downshift table `0x122C6` (06 06 02 03 04 06), the request `0xFFFF91BC`, the hold flag `0xFFFF8AFD`, "request pending" `0xFFFF9167`.

**Entry S → M (BTNC).** Hooks 0x230B4 and 0x25BDC: the factory `tst.b $ffff9169.l` followed by `beq` is replaced by a `jsr` that sets Z = 1 when there is neither a lever contact nor a pending button. A button from the S gate switches to M like the first tap of the lever.

**The gate after a self-upshift (GATESET).** Hook 0x25AE0: the factory `move.b $8ece.l,(a2)`: the gate `0xFFFF920C` after a self-upshift in M (× 10 ms) = min(the value from the settings, the factory 100 from `0x8ECE`).

**A double tap "down" = two gears.** A window after the first "down" (the window cell counts down in DMEX every 10 ms); a second "down" inside the window downshifts through one gear by rows 4 and 5 of the M table `0x11888` (the limits of the factory minimum-gear table stay).

**Where it lives.** Code in the free area `0x3E480–0x3E7FF` (`0xFF` there), cells at `0xFFFF98F0…` (the start-up code does not clear them: initialisation by a magic), settings `0x0FE20–0x0FE5F` in the calibration window (under its sum). The hooks lie under the program sum: all three sums are recomputed (document 07 §6).

What the gearbox does with the mode cell (record and matrix packages for Sport+, "D comfort") is the calibration and code of the author's build and is not described here.

## 3. GS8.60.4 20C0 (E46): mixing into the gate pins

**Hook 0x1C432**: the factory write `move.b d0,$ffff9110.l` (6 bytes) in the PF pin polling task (`0x1BC9C`, 10 ms period: PIT 1 ms `0x1198C`, task registration `0x1B156`) is replaced by a `jsr` into own code (6 bytes). On entry d0 = the factory value `[0xFFFF9110]` = (PF3 << 1) | PF1, the "−" and "+" contacts of the gate. When allowed, the code mixes in (DME2 byte 7 & 3) and writes `[0xFFFF9110]` itself.

**Why `[9110]`, not the raw `[910F]`/`[9111]`.** Fault 0x2B "+/− outside the gate" (`0x232EC`) is armed by the raw contacts, while the consumers of the taps (`0x21AC6`, `0x1EAEE`) read `[9110]`. Mixing into `[9110]` only, the layer makes the tap act and can never arm 0x2B.

**The gate.** In the gate only: lever position `[0xFFFF905D]` = 4 and sub-mode `[0xFFFF91A8]` = 2 (in D the position is 4 too, the gate comes from a separate contact: bit 6 of `[0xFFFF8A0A]` → `[0xFFFF8CD4]` → the sub-mode). Both bits at once → 0. A bit held longer than 0.5 s in a row (stuck, engine gone) is ignored until reset. Everything after `[9110]` is factory: the first tap from the S gate → M (`0x70966` = 0xFE), kick-down, ATF, `[9103]`/`[9107]`/`[91AC]`, the tables `0xA512`/`0xA518`, "button released between taps" (`[0xFFFF8B68]`/`[0xFFFF8B69]` at `0x21AC6`).

**Where it lives.** Code in the free `0xFF` zone between the end of bank 1 (`0x258D4`) and the data at `0x40000`, under the program sum `0x6FFFE`; the settings are two free calibration bytes, `0x71D00` (enable) and `0x71D01` (age, × 10 ms), under the calibration sum `0x7FFFE`: edited with a partial, without touching the code.

## 4. Protections common to both sides

- Every protection of the gearbox stays factory: the shift is done by its own logic (kick-down, ATF overheat, rpm after the shift, "button released between presses"); button and lever at once are one shift.
- Freshness: a dead frame means no requests and mode 0xFF; a press in the first instant after the link is lost is lost.
- Two presses within ~80 ms are one; one press never gives two shifts (bench).
- The engine does not check the lever on the 20C0 (it does not see the S gate): the gate is on the gearbox side, which is why it is needed.

## 5. How to prove it

- A bench on a CPU32 emulator with the factory code: the DME2 handler and the lever dispatcher with given frames; invariants: registers, stack, writes only to own cells; "byte zero = factory byte for byte".
- An image verifier: the three sums, code and calibration differ only in the hooks, slots, settings and sums; a rebuild gives the same file.
- The car: a log of the taps (DS2 `0x06`, document 06) and a fault scan before and after: 0x2B must not appear.

## 6. Open question

One byte for both platforms (now 2 and 7), or a "which byte to read" parameter in the gearbox. The author's call.
