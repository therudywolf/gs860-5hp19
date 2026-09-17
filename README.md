<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/wolf4x-dark-400.png">
    <img src="assets/wolf4x-light-400.png" alt="WOLF4X" width="300">
  </picture>
</p>

<h1 align="center">GS8.60.0 · ZF 5HP19</h1>

<p align="center">
  <b>Reverse-engineering notes, TunerPro definitions and reproducible presets<br>for the Bosch GS8.60.0 transmission control unit</b><br>
  <i>Реверс, XDF и воспроизводимые пресеты для блока АКПП Bosch GS8.60.0 (ZF 5HP19)</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/ECU-Bosch%20GS8.60.0-0066B1" alt="ECU">
  <img src="https://img.shields.io/badge/gearbox-ZF%205HP19%20%2F%20A5S%20325Z-1f6feb" alt="Gearbox">
  <img src="https://img.shields.io/badge/XDF-850%20tables-2ea44f" alt="XDF">
  <img src="https://img.shields.io/badge/docs-EN%20%7C%20RU-brightgreen" alt="Docs">
  <img src="https://img.shields.io/badge/docs%20%26%20XDF-CC%20BY--SA%204.0-blue" alt="Licence docs">
  <img src="https://img.shields.io/badge/tools-MIT-blue" alt="Licence code">
  <a href="https://boosty.to/therudywolf"><img src="https://img.shields.io/badge/support-Boosty-f15f2c" alt="Support"></a>
</p>

<p align="center">
  by <b><a href="https://rudywolf.ru">rudywolf</a></b> · <a href="https://github.com/therudywolf">github.com/therudywolf</a>
</p>

<p align="center">
  <a href="#english"><b>English</b></a> · <a href="#русский"><b>Русский</b></a>
</p>

---

<a name="english"></a>

## English

The **Bosch GS8.60.0** (ZF 5HP19 / A5S 325Z) is the transmission control unit behind a lot of BMW E39, E46, E38, E53, Z3 and Z4 cars — and until now there was no public description of what is actually inside it. People tune this gearbox by copying factory Alpina files into their own dump and hoping. That works until it doesn't.

This repository is the missing description: what each table does **in code**, which ones are safe, which ones are not, and how to apply a change to your own dump in a way you can repeat and undo.

Everything here comes from disassembling the firmware (capstone m68k), diffing a stock calibration against a factory Alpina calibration on the same software, and DS2 logs from a running car. There is no Bosch or ZF documentation in the public domain, and none was used.

### Who this is for

- You tune or diagnose a 5HP19 with the GS8.60.0 and want to know **what a table does**, not what it might do.
- You want to apply a ready preset to your own dump reproducibly — or build your own preset.
- You log the gearbox and need the RAM addresses that actually mean something.

### What is covered

| | |
|---|---|
| **Covered** | GS8.60.0, 256 KB image, program 19x0. Verified against two factory dumps: a stock 2.5 calibration (`19C0 KA20`) and the Alpina B3 3.3 calibration (`19D0 620P`). The program code `0x10000–0x40000` is byte-identical in both, so **one XDF fits both**; the calibrations differ in 2547 bytes. |
| **Not covered** | **GS8.60.4** — the 512 KB image (for example `20C0`). Different memory layout: the XDF, the addresses and the recipes here **do not apply to it**. The engine ECU (MS42 / MS43) is out of scope too — for that, see the [MS4X wiki](https://www.ms4x.net). |

### Quick start

```bash
python3 tools/egs_tables.py info  my_dump.bin          # size, SHA-256, code hash, table count
python3 tools/egs_tables.py shift my_dump.bin          # the 16 shift-point matrices
python3 tools/egs_tables.py dump  my_dump.bin 0xBF9C   # any table by address
python3 tools/apply_recipe.py recipes/wolf4x_v20_track_hard.json my_dump.bin -o build.bin
```

Open `xdf/GS8600_19D0_Full256K.xdf` in TunerPro with a 256 KB dump, or `xdf/GS8600_19x0_Partial32K.xdf` with a 32 KB partial. **Read `docs/en/07-reading-and-flashing.md` before you flash anything.**

### Documentation

| | |
|---|---|
| [01 · Firmware layout](docs/en/01-firmware-layout.md) | memory map, table format, the 536 tables, pointer catalogue, the two calibration branches, the 16 programs, DS2 dispatcher |
| [02 · Shift points](docs/en/02-shift-points.md) | the 16 matrices, pedal rows, km/h ↔ rpm, how to compute a point for your engine |
| [03 · Torque converter lockup](docs/en/03-torque-converter-lockup.md) | the 4-stage ladder, threshold tables, the "temperature window" myth, where ATF temperature really is |
| [04 · Shift execution and hydraulics](docs/en/04-shift-execution-hydraulics.md) | the shift automaton: record sets, transition types, phases, the slip-time controller, clutch pressures, table families, stock vs Alpina — and why copying Alpina data blindly destroys a shift |
| [05 · Protections](docs/en/05-protections.md) | function `0x265F4` is a supply-voltage monitor (and how the "turbine 7000 rpm" reading was disproved), thermal derate, limp mode |
| [06 · Logging over DS2](docs/en/06-logging-ds2.md) | 9600 baud, reading RAM, status-frame bytes, the addresses worth logging for A/B |
| [07 · Reading and flashing](docs/en/07-reading-and-flashing.md) | full 256K vs partial 32K, order of operations, Reset Adaptation, what a dump contains |
| [08 · Recipes and presets](docs/en/08-recipes-and-presets.md) | the recipe format and every preset change justified table by table |
| [09 · What not to touch](docs/en/09-what-not-to-touch.md) | the prohibitions, each with the reason |
| [10 · Methodology](docs/en/10-methodology.md) | how the reverse was done, what counts as proven, refuted readings, open questions |
| [Glossary](docs/en/glossary.md) | terms |

Every document also exists in Russian under `docs/ru/`.

### Presets

A preset here is a **recipe** — a JSON diff against the stock calibration, not a firmware file. `apply_recipe.py` applies it to *your* dump and refuses to run if the software differs, if any table axis differs, or if the old values don't match.

| Preset | Character |
|---|---|
| `wolf4x_v18_sport_daily` | conservative: uniform correction on top of stock |
| `wolf4x_v19_street_hard` | factory Alpina B3 level where the axes match |
| `wolf4x_v20_track_hard` | short slip time, raised pressure ceiling, early lockup in Sport/Manual |

All three were built for a 2.5 M52TU with a stock final drive — `docs/en/08` §4 explains what to recalculate for a different engine, rev limit or final drive.

### Repository layout

```
docs/en, docs/ru     documentation, identical set of files
xdf/                 TunerPro definitions: full 256K and partial 32K
tools/               egs_tables.py, make_recipe.py, apply_recipe.py — Python 3, no dependencies
recipes/             presets as JSON diffs, with annotations
```

### Disclaimer

This is hobby reverse-engineering of a safety-relevant control unit. It may be incomplete or wrong — several earlier readings **were** wrong and are listed as refuted in `docs/en/10-methodology.md`. A bad calibration can damage the gearbox, drop the unit into limp mode or leave the car immobile. You flash at your own risk, only with your own full dump saved first, and you are responsible for compliance with the law where you live.

### Licence

Documentation and XDF: **CC BY-SA 4.0** (`LICENSE-docs`). Scripts in `tools/`: **MIT** (`LICENSE-code`). Recipes are data and follow CC BY-SA 4.0. Attribution to **rudywolf** stays in forks and derivatives.

### Credits

The [MS4X wiki](https://www.ms4x.net) — the reference for the engine side and the source of the factory reference files. [TunerPro RT](https://www.tunerpro.net) — the calibration editor and the XDF format. Everyone who asked awkward questions: the "114 km/h" and "minimum temperature" arguments are what forced the lockup module to be read to the end.

AI tools were used for parts of the disassembly, cross-checking and writing. Every number in these documents was verified against the binaries.

### Support the work

Unpaid hobby research: dumps read by hand, code disassembled instruction by instruction, every finding checked on a real car — including the mistakes, which are documented too. Everything here stays free and open. If it saved you time, money or a gearbox: **[boosty.to/therudywolf](https://boosty.to/therudywolf)**.

---

<a name="русский"></a>

## Русский

**Bosch GS8.60.0** (ZF 5HP19 / A5S 325Z) — блок управления АКПП, который стоит на множестве BMW E39, E46, E38, E53, Z3 и Z4. Публичного описания того, что у него внутри, до сих пор не было. Эту коробку настраивают, заливая в свой дамп заводские файлы Alpina и надеясь на лучшее. Работает до первого раза, когда не сработало.

Здесь — то самое описание: что каждая таблица делает **в коде**, какие трогать можно, какие нельзя, и как внести правку в свой дамп так, чтобы её можно было повторить и откатить.

Всё получено дизассемблированием прошивки (capstone m68k), сравнением стоковой калибровки с заводской калибровкой Alpina на том же ПО и логами DS2 с живой машины. Документации Bosch и ZF в открытом доступе нет, и ничего из неё не использовано.

### Для кого

- Вы настраиваете или диагностируете 5HP19 с GS8.60.0 и хотите знать, **что таблица делает**, а не чем она могла бы быть.
- Вы хотите воспроизводимо применить готовый пресет к своему дампу — или собрать свой.
- Вы логируете коробку и вам нужны адреса RAM, которые действительно что-то значат.

### Что покрыто

| | |
|---|---|
| **Покрыто** | GS8.60.0, образ 256 КБ, программа 19x0. Проверено на двух заводских дампах: стоковая калибровка 2.5 (`19C0 KA20`) и калибровка Alpina B3 3.3 (`19D0 620P`). Код программы `0x10000–0x40000` у обоих совпадает байт в байт, поэтому **один XDF подходит обоим**; калибровки различаются в 2547 байтах. |
| **Не покрыто** | **GS8.60.4** — образ 512 КБ (например `20C0`). Другая раскладка памяти: XDF, адреса и рецепты отсюда **к нему не подходят**. Блок двигателя (MS42 / MS43) тоже вне темы — по нему смотрите [wiki MS4X](https://www.ms4x.net). |

### Быстрый старт

```bash
python3 tools/egs_tables.py info  my_dump.bin          # размер, SHA-256, хэш кода, число таблиц
python3 tools/egs_tables.py shift my_dump.bin          # 16 матриц точек переключения
python3 tools/egs_tables.py dump  my_dump.bin 0xBF9C   # любая таблица по адресу
python3 tools/apply_recipe.py recipes/wolf4x_v20_track_hard.json my_dump.bin -o build.bin
```

XDF открывается в TunerPro: `xdf/GS8600_19D0_Full256K.xdf` — для дампа 256 КБ, `xdf/GS8600_19x0_Partial32K.xdf` — для партиала 32 КБ. **Перед любой прошивкой прочитайте `docs/ru/07-reading-and-flashing.md`.**

### Документация

| | |
|---|---|
| [01 · Устройство прошивки](docs/ru/01-firmware-layout.md) | карта памяти, формат таблиц, 536 таблиц, каталог указателей, две ветки калибровки, 16 программ, диспетчер DS2 |
| [02 · Точки переключения](docs/ru/02-shift-points.md) | 16 матриц, строки педали, км/ч ↔ об/мин, как посчитать точку под свой мотор |
| [03 · Блокировка гидротрансформатора](docs/ru/03-torque-converter-lockup.md) | лесенка из 4 ступеней, таблицы порогов, миф о «температурном окне», где на самом деле температура ATF |
| [04 · Исполнение переключения и гидравлика](docs/ru/04-shift-execution-hydraulics.md) | автомат переключения: наборы записей, типы переходов, фазы, регулятор времени скольжения, давления сцеплений, семейства таблиц, сток против Alpina — и почему слепое копирование данных Alpina убивает переключение |
| [05 · Защиты](docs/ru/05-protections.md) | функция `0x265F4` — монитор напряжения бортсети (и как была опровергнута трактовка «турбина 7000»), термодерейт, аварийный режим |
| [06 · Логирование по DS2](docs/ru/06-logging-ds2.md) | 9600 бод, чтение RAM, байты статусного кадра, адреса, которые стоит писать для сравнения «до/после» |
| [07 · Чтение и прошивка](docs/ru/07-reading-and-flashing.md) | полный 256K против партиала 32K, порядок действий, сброс адаптаций, что содержит дамп |
| [08 · Рецепты и пресеты](docs/ru/08-recipes-and-presets.md) | формат рецепта и обоснование каждой правки пресета, таблица за таблицей |
| [09 · Что не трогать](docs/ru/09-what-not-to-touch.md) | запреты, у каждого — причина |
| [10 · Методика](docs/ru/10-methodology.md) | как делался реверс, что считается доказанным, опровергнутые трактовки, открытые вопросы |
| [Глоссарий](docs/ru/glossary.md) | термины |

Английские версии всех документов — в `docs/en/`.

### Пресеты

Пресет здесь — это **рецепт**, то есть JSON-diff относительно стоковой калибровки, а не файл прошивки. `apply_recipe.py` применяет его к *вашему* дампу и отказывается работать, если ПО другое, если хоть одна ось таблицы отличается или если не совпали старые значения.

| Пресет | Характер |
|---|---|
| `wolf4x_v18_sport_daily` | осторожный: равномерная поправка поверх стока |
| `wolf4x_v19_street_hard` | уровень заводской Alpina B3 там, где совпадают оси |
| `wolf4x_v20_track_hard` | короткое время скольжения, поднятый потолок давления, ранняя блокировка в Sport/Manual |

Все три собраны под мотор 2.5 M52TU с заводской главной парой. Что пересчитать под другой мотор, отсечку или главную пару — в `docs/ru/08`, раздел 4.

### Структура репозитория

```
docs/en, docs/ru     документация, одинаковый набор файлов
xdf/                 определения TunerPro: полный 256K и партиал 32K
tools/               egs_tables.py, make_recipe.py, apply_recipe.py — Python 3, без зависимостей
recipes/             пресеты как JSON-diff, с аннотациями
```

### Ответственность

Это любительский реверс блока, отвечающего за безопасность. Он может быть неполным или ошибочным — несколько прежних трактовок **оказались неверными** и перечислены как опровергнутые в `docs/ru/10-methodology.md`. Неудачная калибровка может повредить коробку, отправить блок в аварийный режим или оставить машину без хода. Вы прошиваете на свой риск, только сохранив собственный полный дамп, и сами отвечаете за соблюдение законов своей страны.

### Лицензия

Документация и XDF: **CC BY-SA 4.0** (`LICENSE-docs`). Скрипты в `tools/`: **MIT** (`LICENSE-code`). Рецепты — данные, на них распространяется CC BY-SA 4.0. Указание авторства **rudywolf** сохраняется в форках и производных работах.

### Благодарности

[Wiki MS4X](https://www.ms4x.net) — источник по моторной части и заводским эталонным файлам. [TunerPro RT](https://www.tunerpro.net) — редактор калибровок и формат XDF. И все, кто задавал неудобные вопросы: споры про «114 км/ч» и «минимальную температуру» — именно то, что заставило дочитать модуль блокировки до конца.

Часть дизассемблирования, перекрёстных проверок и текста сделана с помощью ИИ-инструментов. Каждое число в этих документах проверено по бинарникам.

### Поддержать

Это хобби-исследование без бюджета: дампы читаются руками, код разбирается инструкция за инструкцией, каждая находка проверяется на живой машине — включая ошибки, которые тоже документируются. Всё здесь остаётся бесплатным и открытым. Если это сэкономило вам время, деньги или коробку — **[boosty.to/therudywolf](https://boosty.to/therudywolf)**.
