# Changelog

## 2026-09-23: checksums found, shift-matrix unit corrected, presets recomputed

**EN**

- **Checksums.** The handler of DS2 command `0x0A` (`0x1360`) computes three CRC-16/XMODEM sums with the routine `0x221C` and the table at `0x3EDA`: loader `0x0–0x42FF` at `0x5FFE`, program `0x10000–0x3F77B` at `0x3F7FE`, calibration `0x8000–0xFFCD` at `0xFFFE`. Stock and factory Alpina match on all three. The routine has no other caller, so the ECU checks the sums only when a tester asks: that is why edited calibrations with a stale sum drove. New `tools/gs860_crc.py` (`check` and `fix`, full 256K and 512K images, 32K partials). `apply_recipe.py` checks the loader and program sums of the input and recomputes the calibration sum after writing, `make_recipe.py` leaves `0xFFFE–0xFFFF` out, `egs_tables.py info` prints the sums. Docs 01, 07 §6, 09 rewritten ("do not touch the tail" becomes "the tools recompute the sum").
- **Shift-matrix unit.** The shift matrices and the TCC speed axes hold **output shaft rpm / 32**, not km/h: the decision compares the value with `0xFFFF918F`, written at `0x24F60` as the filtered output shaft rpm shifted right by 5 (doc 02 §3). On the reference car one unit is 1.18 km/h, so every rpm derived from the old km/h reading was 18 % low. Shift rpm does not depend on the final drive or tyres. Docs 02 and 03 rewritten, 06, 08, 10 §7 and the glossary corrected, XDF v2.1 (units and descriptions).
- **Presets recomputed.** With the real unit the 16.09 sport shift points (`66 / 120 / 171` from 63 % pedal) meant 7740 / 7676 / 7699 turbine rpm: never reached under load, the box hung at the limiter in S. The manual programs had `255` in the upshift columns (no overrun protection) and a kickdown landing at 6909…6944 rpm, above the spark cut. New `egs_tables.py verify-shift` checks the 16 matrices against doc 02 §4, `--fix` lowers only the cells that break the rules. v18, v19 and v20 were rebuilt with `verify-shift --spark 6656 --cut 6784 --fix`: sport upshifts at most 47 / 94 / 136 (turbine 5512 / 6013 / 6123 rpm at the command), manual upshift 58 / 106 / 151 / 212 (overrun protection at the fuel cut), every downshift landing at most 6150 rpm. Hydraulics and TCC unchanged. Schema `gs860-recipe/2`, the 16.09 result hashes are kept in each recipe under `history`. Not road-tested yet.
- `tests/test_tools.py`: runs without images. With `GS860_STOCK` it applies every recipe, checks the sums, the reference hashes, the shift rules and a make_recipe round trip.

**RU**

- **Контрольные суммы.** Обработчик команды DS2 `0x0A` (`0x1360`) считает три суммы CRC-16/XMODEM функцией `0x221C` по таблице `0x3EDA`: загрузчик `0x0–0x42FF` в `0x5FFE`, программа `0x10000–0x3F77B` в `0x3F7FE`, калибровка `0x8000–0xFFCD` в `0xFFFE`. Сток и заводская Alpina сходятся по всем трём. Других вызовов у функции нет, значит, блок проверяет суммы только по запросу тестера: поэтому правленые калибровки со старой суммой ездили. Новый `tools/gs860_crc.py` (`check` и `fix`, полные образы 256K и 512K, партиалы 32K). `apply_recipe.py` проверяет суммы загрузчика и программы на входе и пересчитывает сумму калибровки после записи, `make_recipe.py` не берёт в рецепт `0xFFFE–0xFFFF`, `egs_tables.py info` печатает суммы. Документы 01, 07 §6, 09 переписаны («хвост не трогать» стало «сумму пересчитывают инструменты»).
- **Единица матриц переключения.** Матрицы переключения и оси скорости таблиц ГДТ хранят **обороты выходного вала / 32**, а не км/ч: решение сравнивает значение с `0xFFFF918F`, который пишется в `0x24F60` как отфильтрованные обороты выходного вала, сдвинутые вправо на 5 (документ 02 §3). На референсной машине единица равна 1.18 км/ч, поэтому все обороты по старому прочтению занижены на 18 %. Обороты переключения не зависят от главной пары и колёс. Документы 02 и 03 переписаны, 06, 08, 10 §7 и глоссарий исправлены, XDF v2.1 (единицы и описания).
- **Пресеты пересчитаны.** В настоящих единицах точки спорта 16.09 (`66 / 120 / 171` с 63 % педали) означали 7740 / 7676 / 7699 об/мин турбины: под нагрузкой недостижимо, в S коробка висела в отсечке. У ручных программ в столбцах вверх стояло `255` (без защиты на накате), а кикдаун приводил мотор на 6909…6944 об/мин, выше искры. Новая команда `egs_tables.py verify-shift` проверяет 16 матриц по правилам документа 02 §4, `--fix` опускает только нарушающие ячейки. v18, v19 и v20 пересобраны командой `verify-shift --spark 6656 --cut 6784 --fix`: спорт вверх не выше 47 / 94 / 136 (5512 / 6013 / 6123 об/мин турбины в момент команды), ручные вверх 58 / 106 / 151 / 212 (защита на накате на топливной отсечке), после любого понижения не выше 6150 об/мин. Гидравлика и ГДТ не менялись. Схема `gs860-recipe/2`, хэши результата от 16.09 сохранены в каждом рецепте в поле `history`. На машине ещё не проверено.
- `tests/test_tools.py`: работает без образов. С `GS860_STOCK` применяет каждый рецепт и проверяет суммы, эталонные хэши, правила точек и обратную сборку make_recipe.

## 2026-09-16 — preset v19 "Street hard" added

- `recipes/wolf4x_v19_street_hard.json` (+ annotations): 45 tables + 3 byte blocks, 1252 bytes vs stock. Target slip time at high torque down to the Alpina B3 level; on-coming/off-going clutch pressures taken cell by cell from Alpina where the axes match (BCAE/BD14, B73E/B7A4/BA78, BE46/BEAC/BD7A) and interpolated onto the stock axes where Alpina's are wider (B80A/B974); sport programs hold a gear longer at part throttle and drop down earlier; TCC branch 1 (S/M) reaches stages 3–4 from 30–50 % pedal. D and manual untouched. Axes untouched everywhere; `0x8EE0–0x8F0E` = stock. Verified: `apply_recipe.py` on stock reproduces `5ee8d309…` byte for byte.
- В части ячеек v19 мягче v18: v18 применял ×1.15 поверх стока и в ряде мест превышал заводскую Alpina; v19 возвращает эти ячейки на данные Alpina. Рекомендуемый пресет — v19.


## 2026-09-16 — preset v17 → v18 (fix)

**EN.** The v17 preset raised `0x8EEA` from 7000 to 7300 as a "turbine over-speed limit". Disassembly of the write sites (0x20D78: `ADC × 25250 / 1024` → `0xFFFF906C/906E`) proves the function 0x265F4 is a supply-voltage monitor (7.0 / 9.0 V thresholds, 1.5 V channel spread), so the change had moved a 7.0 V threshold to 7.3 V. v18 = v17 with `0x8EEA` back at stock; the recipe `wolf4x_v18_sport_daily.json` replaces the v17 recipe (SHA-256 of the result `0bfd1d0d10037e020bcbfb16fdf5941bf17d0ec085dd5dd0cdec22c65419812e`). Docs 05, 08, 09, 10 and the XDF constant titles updated.

**RU.** В пресете v17 `0x8EEA` был поднят с 7000 до 7300 как «порог разноса турбины». Дизассемблер записей переменных (0x20D78: `АЦП × 25250 / 1024` → `0xFFFF906C/906E`) доказывает, что функция 0x265F4 — монитор напряжения питания (пороги 7.0 / 9.0 В, разбег каналов 1.5 В), то есть правка сдвигала порог 7.0 В на 7.3 В. v18 = v17 с `0x8EEA`, возвращённым к стоку; рецепт `wolf4x_v18_sport_daily.json` заменяет рецепт v17 (SHA-256 результата `0bfd1d0d10037e020bcbfb16fdf5941bf17d0ec085dd5dd0cdec22c65419812e`). Обновлены документы 05, 08, 09, 10 и заголовки констант в XDF.


## 2026-09-16 — first public version

**EN**

- Documentation `docs/en`, `docs/ru` (01–10 + glossary) for GS8.60.0, program 19C0/19D0, 256 KB.
- XDF v2 for the full 256K image and the 32K partial (850 tables and 20 constants; shift-execution tables named by record set / field / transition after the 16.09 reverse).
- Tools: `egs_tables.py` (scan / dump / cell / shift / programs / diff / ids / info), `make_recipe.py`, `apply_recipe.py`.
- Recipe `wolf4x_v18_sport_daily.json` — full diff of the v18 preset against stock; verified byte-exact round trip (SHA-256 `0bfd1d0d…`).
- Corrections relative to earlier project notes (refuted):
  - `0x81A0 / 0x81B2` are not "shift phases / solenoid phases" but a gear-selection module threshold vs engine rpm/32;
  - the `B73E / B7A4 / B90E / …` family (kind3 f45) is off-going clutch pressure on load downshifts, not "fill time"; real fill time is the 1D curves `D6C2 / D722 / D782 / D7E2` (kind1 f10);
  - `0x8F00 / 0x8F08 / 0x8F0A / 0x8EFC` and `0xFFFF906C / 906E` are voltages in mV, not TCC temperatures;
  - `0x265F4` with `0x8EE8 / 0x8EEA / 0x8EF0` (9000 / 7000 / 1500) compares the same voltage variables (written at 0x20D78 as ADC × 25250 / 1024) — the "turbine 7000 rpm protection" reading is refuted; the cause of limp mode at the rev limiter is an open question;
  - `0xAB0C…0xAE40` are torque-reduction request maps, not TCC slip maps; `0xA066…0xA20A` are not TCC thresholds;
  - "the table zone tiles with no remainder" — wrong; 536 tables cover 15,284 of the zone's bytes, the rest are scalars, matrices and short curves.

**RU**

- Документация `docs/en`, `docs/ru` (01–10 + глоссарий) по GS8.60.0, программа 19C0/19D0, 256 КБ.
- XDF v2 для полного образа 256K и партиала 32K (850 таблиц и 20 констант; таблицы исполнения переключения названы по набору записей / полю / переходу по реверсу 16.09).
- Инструменты: `egs_tables.py` (scan / dump / cell / shift / programs / diff / ids / info), `make_recipe.py`, `apply_recipe.py`.
- Рецепт `wolf4x_v18_sport_daily.json` — полный diff пресета v18 относительно стока; проверено байт-в-байт (SHA-256 `0bfd1d0d…`).
- Исправления относительно ранних заметок проекта (опровергнуто или спорно):
  - `0x81A0 / 0x81B2` — не «фазы переключения / фазы соленоидов», а порог модуля выбора передачи по оборотам ДВС/32;
  - семейство `B73E / B7A4 / B90E / …` (kind3 f45) — давление выключаемого сцепления при понижении под нагрузкой, не «время наполнения»; настоящее время наполнения — 1D-кривые `D6C2 / D722 / D782 / D7E2` (kind1 f10);
  - `0x8F00 / 0x8F08 / 0x8F0A / 0x8EFC` и `0xFFFF906C / 906E` — напряжения в мВ, не температуры ГДТ;
  - `0x265F4` с `0x8EE8 / 0x8EEA / 0x8EF0` (9000 / 7000 / 1500) сравнивает те же переменные напряжения (пишутся в 0x20D78 как АЦП × 25250 / 1024) — трактовка «защита турбины 7000» опровергнута; причина аварийного режима на отсечке — открытый вопрос;
  - `0xAB0C…0xAE40` — карты запроса снятия момента, не карты скольжения ГДТ; `0xA066…0xA20A` — не пороги ГДТ;
  - «зона таблиц замощается без остатка» — неверно; 536 таблиц покрывают 15 284 байта зоны, остальное — скаляры, матрицы и короткие кривые.
