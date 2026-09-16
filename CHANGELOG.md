# Changelog

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
