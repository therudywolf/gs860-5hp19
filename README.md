<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/wolf4x-dark-400.png">
    <img src="assets/wolf4x-light-400.png" alt="WOLF4X" width="300">
  </picture>
</p>

<h1 align="center">GS8.60.0 / GS8.60.4 · ZF 5HP19</h1>

<p align="center">
  <b>Reverse-engineering notes, TunerPro definitions and reproducible presets<br>for the Bosch GS8.60.0 transmission control unit (and, partially, the GS8.60.4)</b><br>
  <i>Реверс, XDF и воспроизводимые пресеты для блока АКПП Bosch GS8.60.0 (ZF 5HP19), частично для GS8.60.4</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/ECU-Bosch%20GS8.60.0%20%2F%20GS8.60.4-0066B1" alt="ECU">
  <img src="https://img.shields.io/badge/gearbox-ZF%205HP19%20%2F%20A5S%20325Z-1f6feb" alt="Gearbox">
  <img src="https://img.shields.io/badge/XDF%2019D0-842%20tables%20%2B%2057%20constants-2ea44f" alt="XDF 19D0">
  <img src="https://img.shields.io/badge/XDF%2020C0-1067%20tables%20%2B%20705%20constants-2ea44f" alt="XDF 20C0">
  <img src="https://img.shields.io/badge/docs-EN%20%7C%20RU-brightgreen" alt="Docs">
  <img src="https://img.shields.io/badge/docs%20%26%20XDF-CC%20BY--SA%204.0-blue" alt="Licence docs">
  <img src="https://img.shields.io/badge/tools-MIT-blue" alt="Licence code">
  <a href="https://boosty.to/therudywolf"><img src="https://img.shields.io/badge/support-Boosty-f15f2c" alt="Support"></a>
</p>

<p align="center">
  by <b><a href="https://rudywolf.ru">rudywolf</a></b> | <a href="https://github.com/therudywolf">github.com/therudywolf</a>
</p>

<p align="center">
  <a href="#english"><b>English</b></a> | <a href="#русский"><b>Русский</b></a>
</p>

---

<a name="english"></a>

## English

The **Bosch GS8.60.0** (ZF 5HP19 / A5S 325Z) is the transmission control unit behind a lot of BMW E39, E46, E38, E53, Z3 and Z4 cars, and until now there was no public description of what is actually inside it. People tune this gearbox by copying factory Alpina files into their own dump and hoping. That works until it doesn't.

This repository is the missing description: what each table does **in code**, which ones are safe, which ones are not, and how to apply a change to your own dump in a way you can repeat and undo.

Everything here comes from disassembling the firmware (capstone m68k), diffing a stock calibration against a factory Alpina calibration on the same software, and DS2 logs from a running car. There is no Bosch or ZF documentation in the public domain, and none was used.

### Who this is for

- You tune or diagnose a 5HP19 with the GS8.60.0 and want to know **what a table does**, not what it might do.
- You want to apply a ready preset to your own dump reproducibly, or build your own preset.
- You log the gearbox and need the RAM addresses that actually mean something.

### What is covered

| | |
|---|---|
| **GS8.60.0, program 19x0: addresses fully, roles partially** | 256 KB image. Verified against two factory dumps: a stock 2.5 calibration (`19C0 KA20`) and the Alpina B3 3.3 calibration (`19D0 620P`). The program code `0x10000–0x40000` is byte-identical in both, so **one XDF fits both**. The calibrations differ in 2547 bytes. `catalog/gs8600_19d0.json` and the XDF generated from it hold 899 entries, 842 tables + 57 constants, and every one of the 536 tables the scanner finds in the table zone. Roles: 76 entries proven by code (instruction address in `proof`), 637 carried over from XDF v2.1 without a re-check, 184 shape only, 2 hypotheses. The shapes of some carried record fields are still open (CHANGELOG, 27.09.2026). |
| **GS8.60.4, program 20C0: partially** | 512 KB image, since 27.09.2026: [document 11](docs/en/11-gs8604-20c0.md), [document 12](docs/en/12-gs8600-vs-gs8604.md) (how it differs from 19D0), `catalog/gs8604_20c0.json`, `xdf/GS8604_20C0_Full512K.xdf` and the English `xdf/GS8604_20C0_Full512K_EN.xdf` (since 30.09.2026: 1772 entries, 1067 tables + 705 constants: 1551 proven by code, 19 by structure, 201 shape only, 1 hypothesis). `egs_tables.py` and `gs860_crc.py` understand the image. Proven from the code: the image map and the three checksums, the 16 shift matrices with their unit and program mapping, the TCC lockup upper level, the turbine monitor (7232 rpm), the voltage monitor, AGS and gate constants, the `0B 03` frame, and since 30.09.2026 the roles of the shift-automaton record fields (on-coming and off-going element phases and pressures, slip controller, torque reduction, drive engagement on a selector change) traced to the pressure channels and the CAN frame. **Not proven**: which matrix is the manual program (a road log contradicts the naive reading), the roles of 180 tables of the other record roots, the lower TCC level. The 19D0 addresses, recipes and RAM cells **do not apply to it**, and the other way round. |
| **Not covered** | The engine ECU (MS42 / MS43). For that, see the [MS4X wiki](https://www.ms4x.net). |

### Quick start

```bash
python3 tools/egs_tables.py info  my_dump.bin          # size, SHA-256, code hash, table count, checksums
python3 tools/egs_tables.py shift my_dump.bin --turbine    # the 16 shift-point matrices in turbine rpm
python3 tools/egs_tables.py dump  my_dump.bin 0xBF9C   # any table by address
python3 tools/apply_recipe.py recipes/wolf4x_v20_track_hard.json my_dump.bin -o build.bin
python3 tools/gs860_crc.py check build.bin             # the three CRC-16 checksums
python3 tools/egs_tables.py verify-shift build.bin --spark 6656 --cut 6784 --stock my_dump.bin
```

`apply_recipe.py` recomputes the calibration checksum. After editing an image in TunerPro run `gs860_crc.py fix edited.bin fixed.bin`.

Open `xdf/GS8600_19D0_Full256K.xdf` in TunerPro with a 256 KB dump, or `xdf/GS8600_19x0_Partial32K.xdf` with a 32 KB partial. `xdf/GS8604_20C0_Full512K.xdf` (Russian) and `xdf/GS8604_20C0_Full512K_EN.xdf` (English) are for a 512 KB GS8.60.4 dump (document 11). The XDF files are generated from `catalog/*.json` by `tools/make_xdf.py` and are not edited by hand. **Read `docs/en/07-reading-and-flashing.md` before you flash anything.**

### Tools

Python 3, standard library only. Every script prints its usage with `--help`.

| Script | Commands | What it does |
|---|---|---|
| `tools/egs_tables.py` | `info`, `scan`, `dump`, `cell`, `shift`, `programs`, `diff`, `ids`, `verify-shift` | table scanner and dumper for 256 KB and 32 KB images of 19x0 and 512 KB images of 20C0 (the layout is chosen by the file size) |
| `tools/gs860_crc.py` | `check`, `fix` | the three CRC-16 checksums: check, or write a new file with them recomputed |
| `tools/apply_recipe.py` | `recipe.json stock.bin -o out.bin [--force] [--dry-run]` | applies a recipe to your 256 KB 19x0 dump, recomputes the calibration checksum |
| `tools/make_recipe.py` | `stock.bin tuned.bin -o recipe.json [-a annotations.json]` | builds a recipe from two 256 KB 19x0 images |
| `tools/make_xdf.py` | `check`, `build`, `import` | checks a catalog and generates the XDF from it |

How to rebuild the XDF and run the tests: [CONTRIBUTING.md](CONTRIBUTING.md).

### Documentation

One line per document: [docs/en/README.md](docs/en/README.md).

| | |
|---|---|
| [01 · Firmware layout](docs/en/01-firmware-layout.md) | memory map, table format, the 536 tables, pointer catalogue, the two calibration branches, the 16 programs, DS2 dispatcher |
| [02 · Shift points](docs/en/02-shift-points.md) | the 16 matrices, pedal rows, the unit (output shaft rpm / 32), how to check a point against your engine's limiter |
| [03 · Torque converter lockup](docs/en/03-torque-converter-lockup.md) | the real lockup (request 0/1/2, thresholds `0x993A`, state machine 0-8), AGS (the old "4-stage ladder" reading), the "temperature window" myth, where ATF temperature really is |
| [04 · Shift execution and hydraulics](docs/en/04-shift-execution-hydraulics.md) | the shift automaton: record sets, transition types, phases, the slip-time controller, clutch pressures, table families, stock vs Alpina, and why copying Alpina data blindly destroys a shift |
| [05 · Protections](docs/en/05-protections.md) | function `0x265F4` is a supply-voltage monitor (and how the "turbine 7000 rpm" reading was disproved), thermal derate, limp mode |
| [06 · Logging over DS2](docs/en/06-logging-ds2.md) | 9600 baud, reading RAM, status-frame bytes, the addresses worth logging for A/B |
| [07 · Reading and flashing](docs/en/07-reading-and-flashing.md) | full 256K vs partial 32K, order of operations, Reset Adaptation, what a dump contains, the three checksums |
| [08 · Recipes and presets](docs/en/08-recipes-and-presets.md) | the recipe format, every preset change justified table by table, what the presets really change (§6) |
| [09 · What not to touch](docs/en/09-what-not-to-touch.md) | the prohibitions, each with the reason |
| [10 · Methodology](docs/en/10-methodology.md) | how the reverse was done, what counts as proven, refuted readings, open questions |
| [11 · GS8.60.4 (20C0)](docs/en/11-gs8604-20c0.md) | the 512 KB image: map, checksums, catalog of 43 slots, the 16 matrices and their unit, TCC lockup with two checks, AGS and gate, protections and the voltage block (`0x70F40` is 7.0 V, not a turbine limit), record sets, the 33-byte `0B 03` frame, what is proven and what is not |
| [12 · GS8.60.0 and GS8.60.4](docs/en/12-gs8600-vs-gs8604.md) | how 19D0 and 20C0 differ, side by side with addresses in both images: image and checksums, catalog, matrices and gears, lockup, AGS and gate, protections, record sets, DS2 and CAN |
| [Glossary](docs/en/glossary.md) | terms |

Every document also exists in Russian under `docs/ru/`, with the same structure and facts.

### Presets

A preset here is a **recipe**, a JSON diff against the stock calibration, not a firmware file. `apply_recipe.py` applies it to *your* dump and refuses to run if the software differs, if any table axis differs, or if the old values don't match.

| Preset | Character |
|---|---|
| `wolf4x_v18_sport_daily` | conservative: uniform correction on top of stock |
| `wolf4x_v19_street_hard` | factory Alpina B3 level where the axes match |
| `wolf4x_v20_track_hard` | short slip time, raised pressure ceiling, and AGS edits that were meant as early lockup in Sport/Manual (doc 08 §6) |

All three are built for a 2.5 M52TU with the spark cut from about 6656 rpm and the fuel cut at 6784. Their shift points were recomputed on 23.09.2026 after the matrix unit was proven to be output shaft rpm / 32, not km/h (CHANGELOG). Shift points depend only on the engine limiter, not on the final drive or tyres: check them against yours with `egs_tables.py verify-shift` (`docs/en/08` §4).

**Status.** The presets are not road-tested in their 23.09.2026 form. Their "TCC" groups change AGS, the adaptive program selection, not the converter lockup, and the manual upshift thresholds are unsafe with a locked converter (doc 08 §6). The presets will be revised separately. Each recipe file carries this note in its `status` field.

### Repository layout

```
docs/en, docs/ru     documentation, identical set of files, index in README.md of each folder
catalog/             the source of the XDF files: gs8600_19d0.json (19x0, 256K) and gs8604_20c0.json (20C0, 512K), every entry with a confidence level
xdf/                 TunerPro definitions generated from the catalogs: 19D0 full 256K, 19x0 partial 32K, 20C0 full 512K (RU and EN)
tools/               egs_tables.py, make_recipe.py, apply_recipe.py, gs860_crc.py, make_xdf.py (Python 3, no dependencies)
recipes/             presets as JSON diffs, with annotations (19x0 only)
tests/               self-tests: python3 tests/test_tools.py (GS860_STOCK=stock.bin and GS8604_STOCK=stock20c0.bin for the full set)
assets/              logo
.github/             issue and pull request templates, funding link
```

### Disclaimer

This is hobby reverse-engineering of a safety-relevant control unit. It may be incomplete or wrong: several earlier readings **were** wrong and are listed as refuted in `docs/en/10-methodology.md`. A bad calibration can damage the gearbox, drop the unit into limp mode or leave the car immobile. You flash at your own risk, only with your own full dump saved first, and you are responsible for compliance with the law where you live.

### Licence

Documentation and XDF: **CC BY-SA 4.0** (`LICENSE-docs`). Scripts in `tools/`: **MIT** (`LICENSE-code`). Recipes are data and follow CC BY-SA 4.0. Attribution to **rudywolf** stays in forks and derivatives.

### Credits

The [MS4X wiki](https://www.ms4x.net): the reference for the engine side and the source of the factory reference files. [TunerPro RT](https://www.tunerpro.net): the calibration editor and the XDF format. Everyone who asked awkward questions: the "114 km/h" and "minimum temperature" arguments are what forced the lockup module to be read to the end.

AI tools were used for parts of the disassembly, cross-checking and writing. Every number in these documents was verified against the binaries.

### Support the work

Unpaid hobby research: dumps read by hand, code disassembled instruction by instruction, every finding checked on a real car, including the mistakes, which are documented too. Everything here stays free and open. If it saved you time, money or a gearbox: **[boosty.to/therudywolf](https://boosty.to/therudywolf)**.

---

<a name="русский"></a>

## Русский

**Bosch GS8.60.0** (ZF 5HP19 / A5S 325Z) это блок управления АКПП, который стоит на множестве BMW E39, E46, E38, E53, Z3 и Z4. Публичного описания того, что у него внутри, до сих пор не было. Эту коробку настраивают, заливая в свой дамп заводские файлы Alpina и надеясь на лучшее. Работает до первого раза, когда не сработало.

Здесь то самое описание: что каждая таблица делает **в коде**, какие трогать можно, какие нельзя, и как внести правку в свой дамп так, чтобы её можно было повторить и откатить.

Всё получено дизассемблированием прошивки (capstone m68k), сравнением стоковой калибровки с заводской калибровкой Alpina на том же ПО и логами DS2 с живой машины. Документации Bosch и ZF в открытом доступе нет, и ничего из неё не использовано.

### Для кого

- Вы настраиваете или диагностируете 5HP19 с GS8.60.0 и хотите знать, **что таблица делает**, а не чем она могла бы быть.
- Вы хотите воспроизводимо применить готовый пресет к своему дампу или собрать свой.
- Вы логируете коробку и вам нужны адреса RAM, которые действительно что-то значат.

### Что покрыто

| | |
|---|---|
| **GS8.60.0, программа 19x0: адреса полностью, роли частично** | Образ 256 КБ. Проверено на двух заводских дампах: стоковая калибровка 2.5 (`19C0 KA20`) и калибровка Alpina B3 3.3 (`19D0 620P`). Код программы `0x10000–0x40000` у обоих совпадает байт в байт, поэтому **один XDF подходит обоим**. Калибровки различаются в 2547 байтах. В `catalog/gs8600_19d0.json` и собранном из него XDF 899 записей, 842 таблицы + 57 констант, в том числе все 536 таблиц, которые сканер находит в зоне таблиц. Роли: 76 записей доказаны кодом (адрес инструкции в `proof`), 637 перенесены из XDF v2.1 без перепроверки, 184 только форма, 2 гипотезы. Форма части перенесённых полей записей ещё не выяснена (CHANGELOG, 27.09.2026). |
| **GS8.60.4, программа 20C0: частично** | Образ 512 КБ, с 27.09.2026: [документ 11](docs/ru/11-gs8604-20c0.md), [документ 12](docs/ru/12-gs8600-vs-gs8604.md) (чем отличается от 19D0), `catalog/gs8604_20c0.json`, `xdf/GS8604_20C0_Full512K.xdf` и английский `xdf/GS8604_20C0_Full512K_EN.xdf` (с 30.09.2026: 1772 записи, 1067 таблиц + 705 констант: 1551 доказаны кодом, 19 по структуре, 201 только форма, 1 гипотеза). `egs_tables.py` и `gs860_crc.py` понимают образ. Доказано кодом: карта образа и три контрольные суммы, 16 матриц точек с единицей и привязкой к программам, верхний уровень блокировки ГДТ, монитор турбины (7232 об/мин), монитор напряжения, константы AGS и кулисы, кадр `0B 03`, а с 30.09.2026 роли полей записей автомата переключения (фазы и давления включаемого и выключаемого элементов, регулятор скольжения, снижение момента, включение привода при смене селектора) с путём до каналов давления и кадра CAN. **Не доказано**: какая матрица у ручного режима (лог заезда противоречит наивному прочтению), роли 180 таблиц остальных корней записей, нижний уровень ГДТ. Адреса, рецепты и RAM 19D0 **к нему не подходят**, и наоборот. |
| **Не покрыто** | Блок двигателя (MS42 / MS43). По нему смотрите [wiki MS4X](https://www.ms4x.net). |

### Быстрый старт

```bash
python3 tools/egs_tables.py info  my_dump.bin          # размер, SHA-256, хэш кода, число таблиц, контрольные суммы
python3 tools/egs_tables.py shift my_dump.bin --turbine    # 16 матриц точек переключения в оборотах турбины
python3 tools/egs_tables.py dump  my_dump.bin 0xBF9C   # любая таблица по адресу
python3 tools/apply_recipe.py recipes/wolf4x_v20_track_hard.json my_dump.bin -o build.bin
python3 tools/gs860_crc.py check build.bin             # три контрольные суммы CRC-16
python3 tools/egs_tables.py verify-shift build.bin --spark 6656 --cut 6784 --stock my_dump.bin
```

`apply_recipe.py` сам пересчитывает контрольную сумму калибровки. После правки образа в TunerPro запустите `gs860_crc.py fix edited.bin fixed.bin`.

XDF открывается в TunerPro: `xdf/GS8600_19D0_Full256K.xdf` для дампа 256 КБ, `xdf/GS8600_19x0_Partial32K.xdf` для партиала 32 КБ, `xdf/GS8604_20C0_Full512K.xdf` (русский) и `xdf/GS8604_20C0_Full512K_EN.xdf` (английский) для дампа GS8.60.4 на 512 КБ (документ 11). Файлы XDF генерируются из `catalog/*.json` скриптом `tools/make_xdf.py` и руками не правятся. **Перед любой прошивкой прочитайте `docs/ru/07-reading-and-flashing.md`.**

### Инструменты

Python 3, только стандартная библиотека. Каждый скрипт печатает справку по `--help`.

| Скрипт | Команды | Что делает |
|---|---|---|
| `tools/egs_tables.py` | `info`, `scan`, `dump`, `cell`, `shift`, `programs`, `diff`, `ids`, `verify-shift` | сканер и распечатка таблиц для образов 19x0 на 256 КБ и 32 КБ и образов 20C0 на 512 КБ (раскладка выбирается по размеру файла) |
| `tools/gs860_crc.py` | `check`, `fix` | три контрольные суммы CRC-16: проверить или записать новый файл с пересчитанными суммами |
| `tools/apply_recipe.py` | `recipe.json stock.bin -o out.bin [--force] [--dry-run]` | применяет рецепт к вашему дампу 19x0 на 256 КБ, пересчитывает сумму калибровки |
| `tools/make_recipe.py` | `stock.bin tuned.bin -o recipe.json [-a annotations.json]` | собирает рецепт из двух образов 19x0 на 256 КБ |
| `tools/make_xdf.py` | `check`, `build`, `import` | проверяет каталог и собирает из него XDF |

Как пересобрать XDF и запустить тесты: [CONTRIBUTING.md](CONTRIBUTING.md).

### Документация

По одной строке на документ: [docs/ru/README.md](docs/ru/README.md).

| | |
|---|---|
| [01 · Устройство прошивки](docs/ru/01-firmware-layout.md) | карта памяти, формат таблиц, 536 таблиц, каталог указателей, две ветки калибровки, 16 программ, диспетчер DS2 |
| [02 · Точки переключения](docs/ru/02-shift-points.md) | 16 матриц, строки педали, единица (обороты выходного вала / 32), как проверить точку под ограничитель своего мотора |
| [03 · Блокировка гидротрансформатора](docs/ru/03-torque-converter-lockup.md) | настоящая блокировка (запрос 0/1/2, пороги `0x993A`, автомат состояний 0-8), AGS (прежнее прочтение «лесенка из 4 ступеней»), миф о «температурном окне», где на самом деле температура ATF |
| [04 · Исполнение переключения и гидравлика](docs/ru/04-shift-execution-hydraulics.md) | автомат переключения: наборы записей, типы переходов, фазы, регулятор времени скольжения, давления сцеплений, семейства таблиц, сток против Alpina, и почему слепое копирование данных Alpina убивает переключение |
| [05 · Защиты](docs/ru/05-protections.md) | функция `0x265F4` это монитор напряжения бортсети (и как была опровергнута трактовка «турбина 7000»), термодерейт, аварийный режим |
| [06 · Логирование по DS2](docs/ru/06-logging-ds2.md) | 9600 бод, чтение RAM, байты статусного кадра, адреса, которые стоит писать для сравнения «до/после» |
| [07 · Чтение и прошивка](docs/ru/07-reading-and-flashing.md) | полный 256K против партиала 32K, порядок действий, сброс адаптаций, что содержит дамп, три контрольные суммы |
| [08 · Рецепты и пресеты](docs/ru/08-recipes-and-presets.md) | формат рецепта, обоснование каждой правки пресета таблица за таблицей, что пресеты меняют на деле (§6) |
| [09 · Что не трогать](docs/ru/09-what-not-to-touch.md) | запреты, у каждого своя причина |
| [10 · Методика](docs/ru/10-methodology.md) | как делался реверс, что считается доказанным, опровергнутые трактовки, открытые вопросы |
| [11 · GS8.60.4 (20C0)](docs/ru/11-gs8604-20c0.md) | образ 512 КБ: карта, суммы, каталог из 43 слотов, 16 матриц и их единица, блокировка ГДТ с двумя проверками, AGS и кулиса, защиты и блок напряжений (`0x70F40` это 7.0 В, а не порог турбины), наборы записей, кадр `0B 03` из 33 байт, что доказано и что нет |
| [12 · GS8.60.0 и GS8.60.4](docs/ru/12-gs8600-vs-gs8604.md) | чем отличаются 19D0 и 20C0, рядом с адресами обоих образов: образ и суммы, каталог, матрицы и передачи, блокировка, AGS и кулиса, защиты, наборы записей, DS2 и CAN |
| [Глоссарий](docs/ru/glossary.md) | термины |

Английские версии всех документов лежат в `docs/en/`, структура и факты те же.

### Пресеты

Пресет здесь это **рецепт**, то есть JSON-diff относительно стоковой калибровки, а не файл прошивки. `apply_recipe.py` применяет его к *вашему* дампу и отказывается работать, если ПО другое, если хоть одна ось таблицы отличается или если не совпали старые значения.

| Пресет | Характер |
|---|---|
| `wolf4x_v18_sport_daily` | осторожный: равномерная поправка поверх стока |
| `wolf4x_v19_street_hard` | уровень заводской Alpina B3 там, где совпадают оси |
| `wolf4x_v20_track_hard` | короткое время скольжения, поднятый потолок давления и правки AGS, задуманные как ранняя блокировка в Sport/Manual (документ 08 §6) |

Все три собраны под мотор 2.5 M52TU с искрой примерно с 6656 и топливной отсечкой 6784. Точки переключения пересчитаны 23.09.2026, когда доказано, что единица матриц это обороты выходного вала / 32, а не км/ч (CHANGELOG). Точки зависят только от ограничителя мотора, не от главной пары и колёс: проверьте их под свой командой `egs_tables.py verify-shift` (`docs/ru/08` §4).

**Статус.** В виде от 23.09.2026 пресеты на машине не проверены. Их группы «ГДТ» меняют AGS, адаптивный выбор программы, а не блокировку гидротрансформатора, а ручные пороги вверх небезопасны при замкнутой ГДТ (документ 08 §6). Пресеты будут пересмотрены отдельно. Эта пометка есть в каждом файле рецепта, в поле `status`.

### Структура репозитория

```
docs/en, docs/ru     документация, одинаковый набор файлов, оглавление в README.md каждой папки
catalog/             источник XDF: gs8600_19d0.json (19x0, 256K) и gs8604_20c0.json (20C0, 512K), у каждой записи уровень уверенности
xdf/                 определения TunerPro, собранные из каталогов: 19D0 полный 256K, 19x0 партиал 32K, 20C0 полный 512K (RU и EN)
tools/               egs_tables.py, make_recipe.py, apply_recipe.py, gs860_crc.py, make_xdf.py (Python 3, без зависимостей)
recipes/             пресеты как JSON-diff, с аннотациями (только 19x0)
tests/               самопроверка: python3 tests/test_tools.py (GS860_STOCK=stock.bin и GS8604_STOCK=stock20c0.bin для полного набора)
assets/              логотип
.github/             шаблоны issue и pull request, ссылка на поддержку
```

### Ответственность

Это любительский реверс блока, отвечающего за безопасность. Он может быть неполным или ошибочным: несколько прежних трактовок **оказались неверными** и перечислены как опровергнутые в `docs/ru/10-methodology.md`. Неудачная калибровка может повредить коробку, отправить блок в аварийный режим или оставить машину без хода. Вы прошиваете на свой риск, только сохранив собственный полный дамп, и сами отвечаете за соблюдение законов своей страны.

### Лицензия

Документация и XDF: **CC BY-SA 4.0** (`LICENSE-docs`). Скрипты в `tools/`: **MIT** (`LICENSE-code`). Рецепты это данные, на них распространяется CC BY-SA 4.0. Указание авторства **rudywolf** сохраняется в форках и производных работах.

### Благодарности

[Wiki MS4X](https://www.ms4x.net): источник по моторной части и заводским эталонным файлам. [TunerPro RT](https://www.tunerpro.net): редактор калибровок и формат XDF. И все, кто задавал неудобные вопросы: споры про «114 км/ч» и «минимальную температуру» заставили дочитать модуль блокировки до конца.

Часть дизассемблирования, перекрёстных проверок и текста сделана с помощью ИИ-инструментов. Каждое число в этих документах проверено по бинарникам.

### Поддержать

Это хобби-исследование без бюджета: дампы читаются руками, код разбирается инструкция за инструкцией, каждая находка проверяется на живой машине, включая ошибки, которые тоже документируются. Всё здесь остаётся бесплатным и открытым. Если это сэкономило вам время, деньги или коробку: **[boosty.to/therudywolf](https://boosty.to/therudywolf)**.
