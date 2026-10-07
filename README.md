<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/wolf4x-dark-400.png">
    <img src="assets/wolf4x-light-400.png" alt="WOLF4X" width="300">
  </picture>
</p>

<h1 align="center">GS8.60.0 / GS8.60.4 · ZF 5HP19</h1>

<p align="center">
  <b>Reverse engineering, TunerPro definitions, ready-made patches and presets<br>for the Bosch GS8.60.0 and GS8.60.4 transmission control units</b><br>
  <i>Реверс, XDF, готовые патчи и пресеты для блоков АКПП Bosch GS8.60.0 и GS8.60.4 (ZF 5HP19)</i>
</p>

<p align="center">
  <a href="https://github.com/therudywolf/gs860-5hp19/releases/latest"><img src="https://img.shields.io/github/v/release/therudywolf/gs860-5hp19?label=release&color=0066B1" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/ECU-Bosch%20GS8.60.0%20%2F%20GS8.60.4-0066B1" alt="ECU">
  <img src="https://img.shields.io/badge/gearbox-ZF%205HP19%20%2F%20A5S%20325Z-1f6feb" alt="Gearbox">
  <img src="https://img.shields.io/badge/XDF%2019D0-843%20tables%20%2B%2061%20constants-2ea44f" alt="XDF 19D0">
  <img src="https://img.shields.io/badge/XDF%2020C0-1069%20tables%20%2B%20710%20constants-2ea44f" alt="XDF 20C0">
  <img src="https://img.shields.io/badge/patches-8%20for%20both%20units-8957e5" alt="Patches">
  <img src="https://img.shields.io/badge/docs-EN%20%7C%20RU-brightgreen" alt="Docs">
  <img src="https://img.shields.io/badge/docs%20%26%20XDF-CC%20BY--SA%204.0-blue" alt="Licence docs">
  <img src="https://img.shields.io/badge/tools-MIT-blue" alt="Licence code">
  <a href="https://boosty.to/therudywolf"><img src="https://img.shields.io/badge/support-Boosty-f15f2c" alt="Support on Boosty"></a>
</p>

<p align="center">
  by <b><a href="https://rudywolf.ru">rudywolf</a></b> | <a href="https://github.com/therudywolf">github.com/therudywolf</a> | <a href="https://boosty.to/therudywolf"><b>support on Boosty</b></a>
</p>

<p align="center">
  <a href="#english"><b>English</b></a> | <a href="#русский"><b>Русский</b></a>
</p>

---

<a name="english"></a>

## English

The **Bosch GS8.60.0** and **GS8.60.4** (ZF 5HP19 / A5S 325Z) are the transmission control units of many BMW E39, E46, E38, E53, Z3 and Z4. There was no public description of what is inside them, and people tuned the gearbox by pouring factory Alpina files into their own dump and hoping. That works until it doesn't.

This repository is the missing description: what each table does **in code**, which ones are safe, which ones are not, ready-made patches for the most wanted changes, and a way to apply them to your own dump that you can repeat and undo. Everything comes from disassembling the firmware (capstone m68k), diffing factory calibrations of BMW and Alpina, and DS2 logs from running cars. No Bosch or ZF documentation was used.

### What's new (07.10.2026)

- **Ready-made patches for both units** ([document 13](docs/en/13-patches.md)): converter lock-up in 1st gear, early lock-up with any pedal, no warm-up program, S without 5th, full-throttle shift rpm by your engine limiter, no kick-down, manual mode that holds the gear, gate S or M. One tool, `tools/egs_patch.py`, checks the image, writes, recomputes the checksums and logs every byte.
- **Presets for GS8.60.4 as well as GS8.60.0** ([document 14](docs/en/14-presets.md)): `sport-daily`, `street-hard`, `track-hard`, built from the patches for your engine, or as ready recipes.
- **Why GS8.60.4 feels faster in stock form** ([document 12 §10](docs/en/12-gs8600-vs-gs8604.md)): four factory calibrations side by side. It is the Alpina calibration, not the unit: BMW's own GS8.60.4 is as calm as the GS8.60.0.
- **20C0 reverse completed where it matters**: D / S / M matrix roles, warm-up program, kick-down source, the lower TCC level gate, all proven by code ([document 11](docs/en/11-gs8604-20c0.md)).
- Corrections: the "ATF thermal derate" was the warm-up program; frame byte 5 is the engine temperature, byte 6 the raw ATF ([document 03 §6](docs/en/03-torque-converter-lockup.md)).

### What is covered

| | |
|---|---|
| **GS8.60.0, program 19x0** (256 KB) | Addresses fully, roles partially. Verified on two factory dumps, BMW `19C0 KA20` (E39 2.5) and Alpina B3 3.3 `19D0 620P`, with byte-identical code: **one XDF fits both**. `catalog/gs8600_19d0.json`: 904 entries, 843 tables + 61 constants, every table the scanner finds; 84 roles proven by code, 636 carried over from XDF v2.1, 182 shape only, 2 hypotheses. |
| **GS8.60.4, program 20C0** (512 KB) | `catalog/gs8604_20c0.json`: 1779 entries, 1069 tables + 710 constants, **1565 roles proven by the 20C0 code**, 18 by structure, 195 shape only, 1 hypothesis. Image map and checksums, the 16 shift matrices with their roles, TCC lock-up (upper level, 1st gear, lower-level gate), AGS and gate, warm-up and kick-down, protections, the record fields of the shift automaton traced to the pressure channels and the CAN frame. Russian and English XDF. |
| **Not covered** | Other GS8.60.4 software builds (BMW `15C0` is mapped for comparison only), the engine ECU (see the [MS4X wiki](https://www.ms4x.net)). |

### Quick start

```bash
python3 tools/egs_tables.py info my_dump.bin               # software, code hash, labels, the three checksums
python3 tools/egs_patch.py  show my_dump.bin               # gate, warm-up, kick-down, TCC per program, full-throttle points
python3 tools/egs_patch.py  apply my_dump.bin -o build.bin no-warmup tcc-lock s-no5 --spark 6528
python3 tools/egs_patch.py  preset sport-daily my_dump.bin -o build.bin --spark 6528 --cut 6720
python3 tools/egs_tables.py verify-shift build.bin --spark 6528 --cut 6720 --stock my_dump.bin
python3 tools/gs860_crc.py  check build.bin                # checksums (egs_patch already recomputed them)
```

The XDF files open in TunerPro: `xdf/GS8600_19D0_Full256K.xdf` for a 256 KB dump, `xdf/GS8600_19x0_Partial32K.xdf` for a 32 KB partial, `xdf/GS8604_20C0_Full512K.xdf` (Russian) and `xdf/GS8604_20C0_Full512K_EN.xdf` (English) for a 512 KB GS8.60.4 dump. After editing in TunerPro run `gs860_crc.py fix edited.bin fixed.bin`. **Read [document 07](docs/en/07-reading-and-flashing.md) before you flash anything.**

**Download:** the [latest release](https://github.com/therudywolf/gs860-5hp19/releases/latest): the XDF files, the tools, the recipes and the documents in one archive.

### Patches

`python3 tools/egs_patch.py list` prints them all. Details, addresses and the code behind each: [document 13](docs/en/13-patches.md).

| Patch | What it does | 19x0 | 20C0 |
|---|---|---|---|
| `tcc-first` | converter locked in 1st gear under throttle (S and M, optionally D) | adds 52 bytes of code, full flash only | calibration only |
| `tcc-lock` | converter locked from 1600 turbine rpm in 2nd-5th, with any pedal | groups 6-9 | groups 5, 8, 9, 10 |
| `no-warmup` | no warm-up program after a cold start | `0x8B48` = 0 | `0x70BAC` = 0 |
| `s-no5` | S never shifts into 5th, AGS held on level 4 | k11, k15 | k11, k15 |
| `shift-wot` | full-throttle upshifts right under your engine limiter | k11, k15 (+ k14, k6) | the same, minus the lock-up addition |
| `no-kickdown` | kick-down off (or only in M) | `0x8D1A`, `0x8246` | `0x70D6A`, `0x70232` |
| `manual-hold` | M holds the gear on the limiter, upshifts only on the overrun | k10, k8, monitor | k10, k8 |
| `gate` | left gate: S first (BMW) or M at once (Alpina) | `0x8975` | `0x70966` |

### Presets

| Preset | Character | 19x0 | 20C0 |
|---|---|---|---|
| `sport-daily` | factory D; S without 5th, full-throttle shifts at the limiter, converter locked from 1600; M holds the gear | recipe + `preset` | recipe + `preset` |
| `street-hard` | sport-daily + converter in 1st, no kick-down, no warm-up | `preset` (code change) | recipe + `preset` |
| `track-hard` | street-hard + the same for D | `preset` (code change) | recipe + `preset` |

Build a preset for your own engine: `egs_patch.py preset NAME dump.bin -o out.bin --spark RPM --cut RPM`. The recipes in `recipes/` are built for the reference engines (M52TUB25 and M54B30 with factory limiters). None of the presets is road-tested as a whole yet; their 19x0 counterparts are flashed on the reference E39, the converter lock-up in 1st is not confirmed by a log yet (document 14 §5). The older v18-v20 presets stay in `recipes/` for the record and are not recommended (document 08).

### Tools

Python 3, standard library only. Every script prints its usage with `--help`.

| Script | Commands | What it does |
|---|---|---|
| `tools/egs_patch.py` | `list`, `show`, `apply`, `preset`, `recipe` | the patches and presets of documents 13 and 14 for 256 KB 19x0 and 512 KB 20C0 images |
| `tools/egs_tables.py` | `info`, `scan`, `dump`, `cell`, `shift`, `programs`, `diff`, `ids`, `verify-shift` | table scanner and dumper; `verify-shift` checks the shift points against your engine limiter by the matrix roles from code |
| `tools/gs860_crc.py` | `check`, `fix` | the three CRC-16 checksums: check, or write a new file with them recomputed |
| `tools/apply_recipe.py` | `recipe.json stock.bin -o out.bin` | applies a recipe (JSON diff) to your 256 KB or 512 KB dump, writes only the calibration window |
| `tools/make_recipe.py` | `stock.bin tuned.bin -o recipe.json` | builds a recipe from two images |
| `tools/make_xdf.py` | `check`, `build`, `import` | checks a catalog and generates the XDF from it |

How to rebuild the XDF and run the tests: [CONTRIBUTING.md](CONTRIBUTING.md).

### Documentation

| | |
|---|---|
| [01 · Firmware layout](docs/en/01-firmware-layout.md) | memory map, table format, the 536 tables, pointer catalogue, the two calibration branches, the 16 programs, DS2 dispatcher |
| [02 · Shift points](docs/en/02-shift-points.md) | the 16 matrices, their unit (output shaft rpm / 32), how to check a point against your engine limiter |
| [03 · Torque converter lockup](docs/en/03-torque-converter-lockup.md) | the real lockup (request 0/1/2, thresholds, clutch automaton), AGS, where the temperatures really are |
| [04 · Shift execution and hydraulics](docs/en/04-shift-execution-hydraulics.md) | record sets, phases, the slip-time controller, clutch pressures, stock vs Alpina |
| [05 · Protections](docs/en/05-protections.md) | voltage monitor `0x265F4`, warm-up program (not a thermal derate), limp mode, turbine monitor `0x26C84` |
| [06 · Logging over DS2](docs/en/06-logging-ds2.md) | 9600 baud, reading RAM, status-frame bytes, addresses worth logging |
| [07 · Reading and flashing](docs/en/07-reading-and-flashing.md) | full vs partial, order of operations, Reset Adaptation, the three checksums |
| [08 · Recipes and presets](docs/en/08-recipes-and-presets.md) | the recipe format and the legacy v18-v20 presets, what they really change |
| [09 · What not to touch](docs/en/09-what-not-to-touch.md) | the prohibitions, each with the reason |
| [10 · Methodology](docs/en/10-methodology.md) | how the reverse was done, what counts as proven, refuted readings |
| [11 · GS8.60.4 (20C0)](docs/en/11-gs8604-20c0.md) | the 512 KB image: map, checksums, matrices and roles, lockup, AGS, warm-up, kick-down, record roots, the `0B 03` frame |
| [12 · GS8.60.0 and GS8.60.4](docs/en/12-gs8600-vs-gs8604.md) | the two programs side by side, and stock against stock: why GS8.60.4 feels faster (§10) |
| [13 · Patches](docs/en/13-patches.md) | TCC in 1st, early lockup, warm-up, no 5th in S, shift rpm, kick-down, manual mode, gate |
| [14 · Presets](docs/en/14-presets.md) | sport-daily, street-hard, track-hard for both units |
| [Glossary](docs/en/glossary.md) | terms |

Every document also exists in Russian under `docs/ru/`, with the same structure and facts.

### Repository layout

```
docs/en, docs/ru     documentation, identical set of files, index in README.md of each folder
catalog/             the source of the XDF files: gs8600_19d0.json (19x0, 256K) and gs8604_20c0.json (20C0, 512K)
xdf/                 TunerPro definitions generated from the catalogs: 19D0 full 256K, 19x0 partial 32K, 20C0 full 512K (RU and EN)
tools/               egs_patch.py, egs_tables.py, apply_recipe.py, make_recipe.py, gs860_crc.py, make_xdf.py
recipes/             presets as JSON diffs: gs8600_19x0_*, gs8604_20c0_* (and the legacy wolf4x_v18-v20)
tests/               python3 tests/test_tools.py (GS860_STOCK=stock19x0.bin GS8604_STOCK=stock20c0.bin for the full set)
assets/              logo
.github/             issue and pull request templates, funding link
```

### Disclaimer

This is hobby reverse engineering of a safety-relevant control unit. It may be incomplete or wrong: several earlier readings **were** wrong and are listed as refuted in [document 10](docs/en/10-methodology.md) and in the corrections inside the documents. A bad calibration can damage the gearbox, drop the unit into limp mode or leave the car immobile. You flash at your own risk, only with your own full dump saved first, and you are responsible for compliance with the law where you live.

### Licence

Documentation and XDF: **CC BY-SA 4.0** (`LICENSE-docs`). Scripts in `tools/`: **MIT** (`LICENSE-code`). Recipes are data and follow CC BY-SA 4.0. Attribution to **rudywolf** stays in forks and derivatives.

### Credits

The [MS4X wiki](https://www.ms4x.net): the reference for the engine side and the source of the factory reference files. [TunerPro RT](https://www.tunerpro.net): the calibration editor and the XDF format. Everyone who asked awkward questions and shared dumps: they forced the lockup module, the gate and the warm-up program to be read to the end.

AI tools were used for parts of the disassembly, cross-checking and writing. Every number in these documents was verified against the binaries.

### Support the work

Unpaid hobby research: dumps read by hand, code disassembled instruction by instruction, every finding checked against the code and, wherever possible, on a real car, including the mistakes, which are documented too. Everything here stays free and open. If it saved you time, money or a gearbox, support it on **[Boosty: boosty.to/therudywolf](https://boosty.to/therudywolf)**.

---

<a name="русский"></a>

## Русский

**Bosch GS8.60.0** и **GS8.60.4** (ZF 5HP19 / A5S 325Z) это блоки управления АКПП множества BMW E39, E46, E38, E53, Z3 и Z4. Публичного описания того, что у них внутри, не было, и коробку настраивали, заливая в свой дамп заводские файлы Alpina и надеясь на лучшее. Работает до первого раза, когда не сработало.

Здесь то самое описание: что каждая таблица делает **в коде**, какие трогать можно, какие нельзя, готовые патчи для самых нужных правок и способ внести их в свой дамп так, чтобы это можно было повторить и откатить. Всё получено дизассемблированием прошивки (capstone m68k), сравнением заводских калибровок BMW и Alpina и логами DS2 с живых машин. Документация Bosch и ZF не использовалась.

### Что нового (07.10.2026)

- **Готовые патчи для обоих блоков** ([документ 13](docs/ru/13-patches.md)): ГДТ на 1-й передаче, ранняя блокировка ГДТ при любой педали, без режима прогрева, S без 5-й, обороты переключения в пол под ограничитель вашего мотора, без кикдауна, ручной режим, который держит передачу, кулиса S или сразу M. Один инструмент `tools/egs_patch.py` проверяет образ, пишет, пересчитывает суммы и записывает в журнал каждый байт.
- **Пресеты для GS8.60.4, как и для GS8.60.0** ([документ 14](docs/ru/14-presets.md)): `sport-daily`, `street-hard`, `track-hard`, собранные из патчей под ваш мотор или готовыми рецептами.
- **Почему GS8.60.4 в стоке кажется быстрее** ([документ 12 §10](docs/ru/12-gs8600-vs-gs8604.md)): четыре заводских калибровки рядом. Дело в калибровке Alpina, а не в блоке: собственная GS8.60.4 от BMW такая же спокойная, как GS8.60.0.
- **Реверс 20C0 доведён там, где это важно**: роли матриц D / S / M, программа прогрева, источник кикдауна, ворота нижнего уровня ГДТ, всё доказано кодом ([документ 11](docs/ru/11-gs8604-20c0.md)).
- Поправки: «термодерейт по ATF» оказался программой прогрева; байт 5 кадра это температура мотора, байт 6 сырая ATF ([документ 03 §6](docs/ru/03-torque-converter-lockup.md)).

### Что покрыто

| | |
|---|---|
| **GS8.60.0, программа 19x0** (256 КБ) | Адреса полностью, роли частично. Проверено на двух заводских дампах, BMW `19C0 KA20` (E39 2.5) и Alpina B3 3.3 `19D0 620P`, код байт в байт одинаковый: **один XDF подходит обоим**. `catalog/gs8600_19d0.json`: 904 записи, 843 таблицы + 61 константа, все таблицы, которые находит сканер; 84 роли доказаны кодом, 636 перенесены из XDF v2.1, 182 только форма, 2 гипотезы. |
| **GS8.60.4, программа 20C0** (512 КБ) | `catalog/gs8604_20c0.json`: 1779 записей, 1069 таблиц + 710 констант, **1565 ролей доказаны кодом 20C0**, 18 по структуре, 195 только форма, 1 гипотеза. Карта образа и суммы, 16 матриц с ролями, блокировка ГДТ (верхний уровень, 1-я передача, ворота нижнего уровня), AGS и кулиса, прогрев и кикдаун, защиты, поля записей автомата переключения с путём до каналов давления и кадра CAN. XDF на русском и английском. |
| **Не покрыто** | Другие сборки ПО GS8.60.4 (BMW `15C0` сопоставлен только для сравнения), блок двигателя (смотрите [wiki MS4X](https://www.ms4x.net)). |

### Быстрый старт

```bash
python3 tools/egs_tables.py info my_dump.bin               # ПО, хэш кода, метки, три контрольные суммы
python3 tools/egs_patch.py  show my_dump.bin               # кулиса, прогрев, кикдаун, ГДТ по программам, точки в пол
python3 tools/egs_patch.py  apply my_dump.bin -o build.bin no-warmup tcc-lock s-no5 --spark 6528
python3 tools/egs_patch.py  preset sport-daily my_dump.bin -o build.bin --spark 6528 --cut 6720
python3 tools/egs_tables.py verify-shift build.bin --spark 6528 --cut 6720 --stock my_dump.bin
python3 tools/gs860_crc.py  check build.bin                # суммы (egs_patch их уже пересчитал)
```

XDF открывается в TunerPro: `xdf/GS8600_19D0_Full256K.xdf` для дампа 256 КБ, `xdf/GS8600_19x0_Partial32K.xdf` для партиала 32 КБ, `xdf/GS8604_20C0_Full512K.xdf` (русский) и `xdf/GS8604_20C0_Full512K_EN.xdf` (английский) для дампа GS8.60.4 на 512 КБ. После правки в TunerPro запустите `gs860_crc.py fix edited.bin fixed.bin`. **Перед любой прошивкой прочитайте [документ 07](docs/ru/07-reading-and-flashing.md).**

**Скачать:** [последний релиз](https://github.com/therudywolf/gs860-5hp19/releases/latest): XDF, инструменты, рецепты и документы одним архивом.

### Патчи

`python3 tools/egs_patch.py list` печатает все. Подробности, адреса и код за каждым: [документ 13](docs/ru/13-patches.md).

| Патч | Что делает | 19x0 | 20C0 |
|---|---|---|---|
| `tcc-first` | ГДТ замкнута на 1-й под газом (S и M, по желанию D) | добавляет 52 байта кода, только полная прошивка | только калибровка |
| `tcc-lock` | ГДТ замкнута с 1600 об/мин турбины во 2-5-й при любой педали | группы 6-9 | группы 5, 8, 9, 10 |
| `no-warmup` | без режима прогрева после холодного пуска | `0x8B48` = 0 | `0x70BAC` = 0 |
| `s-no5` | S никогда не включает 5-ю, AGS держит уровень 4 | k11, k15 | k11, k15 |
| `shift-wot` | повышения в пол сразу под ограничитель вашего мотора | k11, k15 (+ k14, k6) | то же, с вычетом прибавки при замкнутой ГДТ |
| `no-kickdown` | кикдаун выключен (или только в M) | `0x8D1A`, `0x8246` | `0x70D6A`, `0x70232` |
| `manual-hold` | M держит передачу на отсечке, повышает только на накате | k10, k8, монитор | k10, k8 |
| `gate` | левая кулиса: сначала S (BMW) или сразу M (Alpina) | `0x8975` | `0x70966` |

### Пресеты

| Пресет | Характер | 19x0 | 20C0 |
|---|---|---|---|
| `sport-daily` | D заводской; S без 5-й, повышения в пол у ограничителя, ГДТ замкнута с 1600; M держит передачу | рецепт + `preset` | рецепт + `preset` |
| `street-hard` | sport-daily + ГДТ на 1-й, без кикдауна, без прогрева | `preset` (правка кода) | рецепт + `preset` |
| `track-hard` | street-hard + то же для D | `preset` (правка кода) | рецепт + `preset` |

Собрать пресет под свой мотор: `egs_patch.py preset ИМЯ dump.bin -o out.bin --spark ОБ/МИН --cut ОБ/МИН`. Рецепты в `recipes/` собраны под эталонные моторы (M52TUB25 и M54B30 с заводскими ограничителями). Целиком ни один пресет на машине пока не проверен; их аналоги для 19x0 стоят на референсной E39, замыкание ГДТ на 1-й логом пока не подтверждено (документ 14 §5). Прежние пресеты v18-v20 лежат в `recipes/` для истории и не рекомендуются (документ 08).

### Инструменты

Python 3, только стандартная библиотека. Каждый скрипт печатает справку по `--help`.

| Скрипт | Команды | Что делает |
|---|---|---|
| `tools/egs_patch.py` | `list`, `show`, `apply`, `preset`, `recipe` | патчи и пресеты документов 13 и 14 для образов 19x0 на 256 КБ и 20C0 на 512 КБ |
| `tools/egs_tables.py` | `info`, `scan`, `dump`, `cell`, `shift`, `programs`, `diff`, `ids`, `verify-shift` | сканер и распечатка таблиц; `verify-shift` проверяет точки под ограничитель мотора по ролям матриц из кода |
| `tools/gs860_crc.py` | `check`, `fix` | три контрольные суммы CRC-16: проверить или записать новый файл с пересчитанными суммами |
| `tools/apply_recipe.py` | `recipe.json stock.bin -o out.bin` | применяет рецепт (JSON-diff) к вашему дампу на 256 или 512 КБ, пишет только окно калибровки |
| `tools/make_recipe.py` | `stock.bin tuned.bin -o recipe.json` | собирает рецепт из двух образов |
| `tools/make_xdf.py` | `check`, `build`, `import` | проверяет каталог и собирает из него XDF |

Как пересобрать XDF и запустить тесты: [CONTRIBUTING.md](CONTRIBUTING.md).

### Документация

| | |
|---|---|
| [01 · Устройство прошивки](docs/ru/01-firmware-layout.md) | карта памяти, формат таблиц, 536 таблиц, каталог указателей, две ветки калибровки, 16 программ, диспетчер DS2 |
| [02 · Точки переключения](docs/ru/02-shift-points.md) | 16 матриц, их единица (обороты выходного вала / 32), как проверить точку под ограничитель мотора |
| [03 · Блокировка гидротрансформатора](docs/ru/03-torque-converter-lockup.md) | настоящая блокировка (запрос 0/1/2, пороги, автомат муфты), AGS, где на самом деле температуры |
| [04 · Исполнение переключения и гидравлика](docs/ru/04-shift-execution-hydraulics.md) | наборы записей, фазы, регулятор времени скольжения, давления сцеплений, сток против Alpina |
| [05 · Защиты](docs/ru/05-protections.md) | монитор напряжения `0x265F4`, программа прогрева (не термодерейт), аварийный режим, монитор турбины `0x26C84` |
| [06 · Логирование по DS2](docs/ru/06-logging-ds2.md) | 9600 бод, чтение RAM, байты статусного кадра, адреса, которые стоит писать |
| [07 · Чтение и прошивка](docs/ru/07-reading-and-flashing.md) | полный образ против партиала, порядок действий, сброс адаптаций, три суммы |
| [08 · Рецепты и пресеты](docs/ru/08-recipes-and-presets.md) | формат рецепта и прежние пресеты v18-v20, что они меняют на деле |
| [09 · Что не трогать](docs/ru/09-what-not-to-touch.md) | запреты, у каждого своя причина |
| [10 · Методика](docs/ru/10-methodology.md) | как делался реверс, что считается доказанным, опровергнутые трактовки |
| [11 · GS8.60.4 (20C0)](docs/ru/11-gs8604-20c0.md) | образ 512 КБ: карта, суммы, матрицы и роли, блокировка, AGS, прогрев, кикдаун, корни записей, кадр `0B 03` |
| [12 · GS8.60.0 и GS8.60.4](docs/ru/12-gs8600-vs-gs8604.md) | две программы рядом и сток против стока: почему GS8.60.4 кажется быстрее (§10) |
| [13 · Патчи](docs/ru/13-patches.md) | ГДТ на 1-й, ранняя блокировка, прогрев, S без 5-й, обороты, кикдаун, ручной режим, кулиса |
| [14 · Пресеты](docs/ru/14-presets.md) | sport-daily, street-hard, track-hard для обоих блоков |
| [Глоссарий](docs/ru/glossary.md) | термины |

Английские версии всех документов лежат в `docs/en/`, структура и факты те же.

### Структура репозитория

```
docs/en, docs/ru     документация, одинаковый набор файлов, оглавление в README.md каждой папки
catalog/             источник XDF: gs8600_19d0.json (19x0, 256K) и gs8604_20c0.json (20C0, 512K)
xdf/                 определения TunerPro, собранные из каталогов: 19D0 полный 256K, 19x0 партиал 32K, 20C0 полный 512K (RU и EN)
tools/               egs_patch.py, egs_tables.py, apply_recipe.py, make_recipe.py, gs860_crc.py, make_xdf.py
recipes/             пресеты как JSON-diff: gs8600_19x0_*, gs8604_20c0_* (и прежние wolf4x_v18-v20)
tests/               python3 tests/test_tools.py (GS860_STOCK=stock19x0.bin GS8604_STOCK=stock20c0.bin для полного набора)
assets/              логотип
.github/             шаблоны issue и pull request, ссылка на поддержку
```

### Ответственность

Это любительский реверс блока, отвечающего за безопасность. Он может быть неполным или ошибочным: несколько прежних трактовок **оказались неверными** и перечислены как опровергнутые в [документе 10](docs/ru/10-methodology.md) и в поправках внутри документов. Неудачная калибровка может повредить коробку, отправить блок в аварийный режим или оставить машину без хода. Вы прошиваете на свой риск, только сохранив собственный полный дамп, и сами отвечаете за соблюдение законов своей страны.

### Лицензия

Документация и XDF: **CC BY-SA 4.0** (`LICENSE-docs`). Скрипты в `tools/`: **MIT** (`LICENSE-code`). Рецепты это данные, на них распространяется CC BY-SA 4.0. Указание авторства **rudywolf** сохраняется в форках и производных работах.

### Благодарности

[Wiki MS4X](https://www.ms4x.net): источник по моторной части и заводским эталонным файлам. [TunerPro RT](https://www.tunerpro.net): редактор калибровок и формат XDF. Все, кто задавал неудобные вопросы и делился дампами: они заставили дочитать до конца модуль блокировки, кулису и программу прогрева.

Часть дизассемблирования, перекрёстных проверок и текста сделана с помощью ИИ-инструментов. Каждое число в этих документах проверено по бинарникам.

### Поддержать

Это хобби-исследование без бюджета: дампы читаются руками, код разбирается инструкция за инструкцией, каждая находка проверяется по коду и, где можно, на живой машине, включая ошибки, которые тоже документируются. Всё здесь остаётся бесплатным и открытым. Если это сэкономило вам время, деньги или коробку, поддержите на **[Boosty: boosty.to/therudywolf](https://boosty.to/therudywolf)**.
