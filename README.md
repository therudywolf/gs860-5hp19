<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/wolf4x-dark-400.png">
    <img src="assets/wolf4x-light-400.png" alt="WOLF4X" width="300">
  </picture>
</p>

<h1 align="center">GS8.60.0 / GS8.60.4 · ZF 5HP19</h1>

<p align="center">
  <b>Reverse engineering, TunerPro definitions and checking tools<br>for the Bosch GS8.60.0 and GS8.60.4 transmission control units</b><br>
  <i>Реверс, XDF и проверялки для блоков АКПП Bosch GS8.60.0 и GS8.60.4 (ZF 5HP19)</i>
</p>

<p align="center">
  <a href="https://github.com/therudywolf/gs860-5hp19/releases/latest"><img src="https://img.shields.io/github/v/release/therudywolf/gs860-5hp19?label=release&color=0066B1" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/ECU-Bosch%20GS8.60.0%20%2F%20GS8.60.4-0066B1" alt="ECU">
  <img src="https://img.shields.io/badge/gearbox-ZF%205HP19%20%2F%20A5S%20325Z-1f6feb" alt="Gearbox">
  <img src="https://img.shields.io/badge/XDF%2019D0-849%20tables%20%2B%2072%20constants-2ea44f" alt="XDF 19D0">
  <img src="https://img.shields.io/badge/XDF%2020C0-1069%20tables%20%2B%20710%20constants-2ea44f" alt="XDF 20C0">
  <a href="https://github.com/therudywolf/gs860-5hp19/actions/workflows/tests.yml"><img src="https://github.com/therudywolf/gs860-5hp19/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <img src="https://img.shields.io/badge/docs-EN%20%7C%20RU-brightgreen" alt="Docs">
  <img src="https://img.shields.io/badge/docs%20%26%20XDF-CC%20BY--SA%204.0-blue" alt="Licence docs">
  <img src="https://img.shields.io/badge/code-Apache%202.0-blue" alt="Licence code">
  <a href="https://boosty.to/therudywolf"><img src="https://img.shields.io/badge/support-Boosty-f15f2c" alt="Support on Boosty"></a>
</p>

<p align="center">
  by <b><a href="https://rudywolf.ru">rudywolf</a></b> | <a href="https://github.com/therudywolf">github.com/therudywolf</a> | <a href="https://boosty.to/therudywolf"><b>support on Boosty</b></a> | <a href="https://t.me/rudy_wolf">Telegram</a> | <a href="mailto:alonerudywolf@gmail.com">alonerudywolf@gmail.com</a>
</p>

<p align="center">
  <a href="#english"><b>English</b></a> | <a href="#русский"><b>Русский</b></a>
</p>

---

<a name="english"></a>

## English

The **Bosch GS8.60.0** and **GS8.60.4** (ZF 5HP19 / A5S 325Z) are the transmission control units of many BMW E39, E46, E38, E53, Z3 and Z4. There was no public description of what is inside them, and people tuned the gearbox by pouring factory Alpina files into their own dump and hoping. That works until it doesn't.

This repository is the missing description: what each table does **in code**, which ones are safe, which ones are not, and how to check your own edit before it goes into the car. Everything comes from disassembling the firmware (capstone m68k), diffing factory calibrations of BMW and Alpina, and DS2 logs from running cars. No Bosch or ZF documentation was used.

### What's new (29.10.2026)

- **Patches, presets and recipes are withdrawn.** The repository is the reverse engineering, the XDF definitions and the checking tools; ready-made builds are not part of it any more (they are custom work, see below). The releases up to 28.10.2026 are withdrawn with them; the git history keeps the old files.
- **Documents 13 and 14 (29.10, evening):** the eleven most requested edits are back as a description, what to change, where and why, with the reading instruction of every address and the way to check (document 13); and the engine link, how the cruise buttons and the mode reach the lever dispatcher of the 19x0 and the gate pins of the 20C0 through a free byte of the DME2 frame (document 14, CC BY-NC-SA 4.0). No tool, no presets, no code.

28.10.2026:

- **Licence with attribution**: use, share and build on everything here, commercially too, on one condition: credit the author. Code under Apache-2.0 with [`NOTICE`](NOTICE), documents, catalogs and XDF under CC BY-SA 4.0; every XDF carries the licence and the credit in its header ([Licence](#licence)).
- **Repository guard**: a test keeps firmware images, dumps and anything that looks like a VIN out of the tree; [`SECURITY.md`](SECURITY.md) says how to report a dangerous error privately.
- **English axis labels**: the English 20C0 XDF labels every axis in English (132 labels were Russian), and the 19D0 catalog carries them too. The `labels_en` field came from Jason King.

14.10.2026:

- **19D0 catalog v3.3**: readers found for 36 objects marked "no reader", nine scanner "tables" remodelled as the arrays and threshold lists the code really indexes, 17 objects added, among them the converter ratio `0xE38E` ([document 10 §9](docs/en/10-methodology.md)).
- **DS2 corrected** ([document 06 §2](docs/en/06-logging-ds2.md)): the running 19D0 program does answer `0B 03` (its own dispatcher `0x10E58`); the `0x06` memory-read format comes from the code; a real status exchange is decoded byte by byte.
- **Every pull request is tested** by GitHub Actions, `main` is protected ([CONTRIBUTING](CONTRIBUTING.md)).
- 07.10.2026: why the GS8.60.4 feels faster in stock form (document 12 §10), the 20C0 reverse (document 11). All changes: [CHANGELOG](CHANGELOG.md).

### What is covered

| | |
|---|---|
| **GS8.60.0, program 19x0** (256 KB) | Addresses fully, roles partially. Verified on two factory dumps, BMW `19C0 KA20` (E39 2.5) and Alpina B3 3.3 `19D0 620P`, with byte-identical code: **one XDF fits both**. `catalog/gs8600_19d0.json`: 921 entries, 849 tables + 72 constants, every object the scanner finds (nine of them turned out to be arrays or threshold lists and are described from code); 87 roles proven by code, 636 carried over from XDF v2.1, 196 shape only, 2 hypotheses. |
| **GS8.60.4, program 20C0** (512 KB) | `catalog/gs8604_20c0.json`: 1779 entries, 1069 tables + 710 constants, **1743 roles proven by the 20C0 code**, 36 shape only, none by structure. Image map and checksums, the 16 shift matrices with their roles, TCC lock-up (upper level, 1st gear, lower-level gate), AGS and gate, warm-up and kick-down, protections, the record fields of the shift automaton traced to the pressure channels and the CAN frame. Russian and English XDF. |
| **Not covered** | Other GS8.60.4 software builds (BMW `15C0` is mapped for comparison only; BMW `22C0` has its own matrix and constant addresses, document 12 §11), the engine ECU (see the [MS4X wiki](https://www.ms4x.net)). |

### Quick start

```bash
python3 tools/egs_tables.py info my_dump.bin               # software, code hash, labels, the three checksums
python3 tools/egs_tables.py shift my_dump.bin --turbine    # the 16 shift matrices in turbine rpm
python3 tools/gs860_crc.py  fix edited.bin build.bin       # after an edit in TunerPro: recompute the checksums
python3 tools/egs_tables.py verify-shift build.bin --spark 6528 --cut 6720 --stock my_dump.bin
python3 tools/egs_tables.py diff my_dump.bin build.bin     # what changed, table by table
```

The XDF files open in TunerPro: `xdf/GS8600_19D0_Full256K.xdf` for a 256 KB dump, `xdf/GS8600_19x0_Partial32K.xdf` for a 32 KB partial, `xdf/GS8604_20C0_Full512K.xdf` (Russian) and `xdf/GS8604_20C0_Full512K_EN.xdf` (English) for a 512 KB GS8.60.4 dump. After editing in TunerPro run `gs860_crc.py fix edited.bin fixed.bin`. **Read [document 07](docs/en/07-reading-and-flashing.md) before you flash anything.**

**Download:** the [latest release](https://github.com/therudywolf/gs860-5hp19/releases/latest): the XDF files, the tools and the documents in one archive.

### Tools

Python 3, standard library only. Every script prints its usage with `--help`.

| Script | Commands | What it does |
|---|---|---|
| `tools/egs_tables.py` | `info`, `scan`, `dump`, `cell`, `shift`, `programs`, `diff`, `ids`, `verify-shift` | table scanner and dumper; `verify-shift` checks the shift points against your engine limiter by the matrix roles from code |
| `tools/gs860_crc.py` | `check`, `fix` | the three CRC-16 checksums: check, or write a new file with them recomputed |
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
| [09 · What not to touch](docs/en/09-what-not-to-touch.md) | the prohibitions, each with the reason |
| [10 · Methodology](docs/en/10-methodology.md) | how the reverse was done, what counts as proven, refuted readings |
| [11 · GS8.60.4 (20C0)](docs/en/11-gs8604-20c0.md) | the 512 KB image: map, checksums, matrices and roles, lockup, AGS, warm-up, kick-down, record roots, the `0B 03` frame |
| [12 · GS8.60.0 and GS8.60.4](docs/en/12-gs8600-vs-gs8604.md) | the two programs side by side, and stock against stock: why GS8.60.4 feels faster (§10) |
| [13 · What to change, and where](docs/en/13-what-to-change.md) | TCC in 1st, early lock-up, warm-up, no 5th in S, shift rpm, kick-down, manual mode, gate, sporty S, shift feel, converter curve: addresses, reading instructions, factory values, how to check |
| [14 · The engine link](docs/en/14-engine-link.md) | cruise buttons and the mode through a free byte of DME2: reception, lever dispatcher and gate pins on the 19x0 and 20C0, protections (CC BY-NC-SA 4.0) |
| [Glossary](docs/en/glossary.md) | terms |

Every document also exists in Russian under `docs/ru/`, with the same structure and facts.

### Repository layout

```
docs/en, docs/ru     documentation, identical set of files, index in README.md of each folder
catalog/             the source of the XDF files: gs8600_19d0.json (19x0, 256K) and gs8604_20c0.json (20C0, 512K)
xdf/                 TunerPro definitions generated from the catalogs: 19D0 full 256K, 19x0 partial 32K, 20C0 full 512K (RU and EN)
tools/               egs_tables.py, gs860_crc.py, make_xdf.py
tests/               python3 tests/test_tools.py (GS860_STOCK=stock19x0.bin GS8604_STOCK=stock20c0.bin for the full set)
assets/              logo
.github/             issue and pull request templates, funding link
LICENSE, LICENSE-docs Apache-2.0 for the code, CC BY-SA 4.0 for documents, catalogs and XDF
NOTICE, CITATION.cff  the credit to keep, a ready citation
SECURITY.md          how to report a dangerous error privately
```

### Disclaimer

This is hobby reverse engineering of a safety-relevant control unit. It may be incomplete or wrong: several earlier readings **were** wrong and are listed as refuted in [document 10](docs/en/10-methodology.md) and in the corrections inside the documents. A bad calibration can damage the gearbox, drop the unit into limp mode or leave the car immobile. You flash at your own risk, only with your own full dump saved first, and you are responsible for compliance with the law where you live. Bosch, ZF, Siemens, BMW and Alpina are trademarks of their owners; this project is not affiliated with them.

### Licence

Use, share and build on everything here, commercially too, **on one condition: credit the author**:

> **rudywolf, https://github.com/therudywolf/gs860-5hp19**

| What | Licence | What the credit means in practice |
|---|---|---|
| Code: `tools/`, `tests/` | [Apache License 2.0](LICENSE) | copies and derived tools keep [`NOTICE`](NOTICE) with the credit and say what was changed |
| Documents, catalogs (`catalog/`), XDF (`xdf/`) | [CC BY-SA 4.0](LICENSE-docs) | copies and adaptations credit the author, link the licence, say what was changed and stay under CC BY-SA 4.0; every XDF carries the licence and the credit in its header: keep them |
| Documents about the author's own layer: `docs/*/14-*` and those that say so in their header | [CC BY-NC-SA 4.0](LICENSE-docs-nc) | as above, and not commercially: no builds or services sold on the strength of these documents; a finished build for a dump is the author's work |

The documents about the author's own layer are the one exception to "commercially too": CC BY-NC-SA 4.0. The WOLF4X name and logo are not licensed for reuse; firmware of Bosch, ZF, Siemens and BMW is not part of this repository ([`NOTICE`](NOTICE)). GitHub offers a ready citation under "Cite this repository" ([`CITATION.cff`](CITATION.cff)). Releases up to v2026.10.14 shipped the tools under MIT; the code is Apache-2.0 from 28.10.2026.

### Credits

The [MS4X wiki](https://www.ms4x.net): the reference for the engine side and the source of the factory reference files. [TunerPro RT](https://www.tunerpro.net): the calibration editor and the XDF format. Everyone who asked awkward questions and shared dumps: they forced the lockup module, the gate and the warm-up program to be read to the end.

Jason King (KingAI, [@KingAiCodeForge](https://github.com/KingAiCodeForge)): his questions about the 19D0 axes and the RAM writers led to a mis-modelled object, wrong "no reader" notes and the converter torque ratio (19D0 catalog v3.3, document 10 §9); the hashes of his own Alpina B3 19C0 and SP-Daten 19C0 KA20 images confirmed the reference files independently; the field-placement part of his catalog guard became `test_english_field_placement`; his pull request added `labels_en`, the English labels of table axes.

AI tools were used for parts of the disassembly, cross-checking and writing. Every number in these documents was verified against the binaries.

### Support the work

Unpaid hobby research: dumps read by hand, code disassembled instruction by instruction, every finding checked against the code and, wherever possible, on a real car, including the mistakes, which are documented too. Everything here stays free and open. If it saved you time, money or a gearbox, support it on **[Boosty: boosty.to/therudywolf](https://boosty.to/therudywolf)**.

### Custom work

Want a custom tune for **MS42 / MS43**, a custom tune of the **5HP19** gearbox (GS8.60), or a custom logger for your car? Write to me, I take paid work: Telegram **[t.me/rudy_wolf](https://t.me/rudy_wolf)**, e-mail **[alonerudywolf@gmail.com](mailto:alonerudywolf@gmail.com)**.

---

<a name="русский"></a>

## Русский

**Bosch GS8.60.0** и **GS8.60.4** (ZF 5HP19 / A5S 325Z) это блоки управления АКПП множества BMW E39, E46, E38, E53, Z3 и Z4. Публичного описания того, что у них внутри, не было, и коробку настраивали, заливая в свой дамп заводские файлы Alpina и надеясь на лучшее. Работает до первого раза, когда не сработало.

Здесь то самое описание: что каждая таблица делает **в коде**, какие трогать можно, какие нельзя, и как проверить свою правку до того, как она попадёт в машину. Всё получено дизассемблированием прошивки (capstone m68k), сравнением заводских калибровок BMW и Alpina и логами DS2 с живых машин. Документация Bosch и ZF не использовалась.

### Что нового (29.10.2026)

- **Патчи, пресеты и рецепты убраны.** Репозиторий — это реверс, определения XDF и проверялки; готовых сборок в нём больше нет (это работа на заказ, см. ниже). Вместе с ними сняты релизы по 28.10.2026; история git хранит старые файлы.
- **Документы 13 и 14 (29.10, вечер):** одиннадцать самых нужных правок вернулись описанием — что, где и зачем менять, с инструкцией-читателем каждого адреса и способом проверки (документ 13); и связь с мотором — как кнопки круиза и режим доходят до диспетчера рычага 19x0 и ножек кулисы 20C0 через свободный байт кадра DME2 (документ 14, CC BY-NC-SA 4.0). Без инструмента, пресетов и кода.

28.10.2026:

- **Лицензия с указанием автора**: всё здесь можно использовать, распространять и дорабатывать, в том числе в коммерческих целях, при одном условии — указывать автора. Код под Apache-2.0 с [`NOTICE`](NOTICE), документы, каталоги и XDF под CC BY-SA 4.0; в заголовке каждого XDF записаны лицензия и автор ([Лицензия](#лицензия)).
- **Защита репозитория**: тест не пускает в дерево образы прошивок, дампы и всё, что похоже на VIN; [`SECURITY.md`](SECURITY.md) описывает, как лично сообщить об опасной ошибке.
- **Английские подписи осей**: английский XDF 20C0 подписывает все оси по-английски (132 подписи были русскими), в каталоге 19D0 они тоже есть. Поле `labels_en` предложил Jason King.

14.10.2026:

- **Каталог 19D0 v3.3**: найдены читатели у 36 объектов с пометкой «читателей нет», девять «таблиц» сканера переописаны как массивы и списки порогов, которые на самом деле индексирует код, добавлено 17 объектов, среди них коэффициент ГДТ `0xE38E` ([документ 10 §9](docs/ru/10-methodology.md)).
- **Исправлено по DS2** ([документ 06 §2](docs/ru/06-logging-ds2.md)): работающая программа 19D0 отвечает на `0B 03` (свой диспетчер `0x10E58`); формат чтения памяти `0x06` взят из кода; настоящий обмен статусом разобран по байтам.
- **Каждый pull request проверяется** GitHub Actions, `main` защищён ([CONTRIBUTING](CONTRIBUTING.md)).
- 07.10.2026: почему GS8.60.4 в стоке кажется быстрее (документ 12 §10), реверс 20C0 (документ 11). Все изменения: [CHANGELOG](CHANGELOG.md).

### Что покрыто

| | |
|---|---|
| **GS8.60.0, программа 19x0** (256 КБ) | Адреса полностью, роли частично. Проверено на двух заводских дампах, BMW `19C0 KA20` (E39 2.5) и Alpina B3 3.3 `19D0 620P`, код байт в байт одинаковый: **один XDF подходит обоим**. `catalog/gs8600_19d0.json`: 921 запись, 849 таблиц + 72 константы, все объекты, которые находит сканер (девять оказались массивами или списками порогов и описаны по коду); 87 ролей доказаны кодом, 636 перенесены из XDF v2.1, 196 только форма, 2 гипотезы. |
| **GS8.60.4, программа 20C0** (512 КБ) | `catalog/gs8604_20c0.json`: 1779 записей, 1069 таблиц + 710 констант, **1743 роли доказаны кодом 20C0**, 36 только форма, по структуре нет. Карта образа и суммы, 16 матриц с ролями, блокировка ГДТ (верхний уровень, 1-я передача, ворота нижнего уровня), AGS и кулиса, прогрев и кикдаун, защиты, поля записей автомата переключения с путём до каналов давления и кадра CAN. XDF на русском и английском. |
| **Не покрыто** | Другие сборки ПО GS8.60.4 (BMW `22C0` с другими адресами матриц и констант, документ 12 §11; BMW `15C0` сопоставлен только для сравнения), блок двигателя (смотрите [wiki MS4X](https://www.ms4x.net)). |

### Быстрый старт

```bash
python3 tools/egs_tables.py info my_dump.bin               # ПО, хэш кода, метки, три контрольные суммы
python3 tools/egs_tables.py shift my_dump.bin --turbine    # 16 матриц переключения в оборотах турбины
python3 tools/gs860_crc.py  fix edited.bin build.bin       # после правки в TunerPro: пересчитать суммы
python3 tools/egs_tables.py verify-shift build.bin --spark 6528 --cut 6720 --stock my_dump.bin
python3 tools/egs_tables.py diff my_dump.bin build.bin     # что изменилось, таблица за таблицей
```

XDF открывается в TunerPro: `xdf/GS8600_19D0_Full256K.xdf` для дампа 256 КБ, `xdf/GS8600_19x0_Partial32K.xdf` для партиала 32 КБ, `xdf/GS8604_20C0_Full512K.xdf` (русский) и `xdf/GS8604_20C0_Full512K_EN.xdf` (английский) для дампа GS8.60.4 на 512 КБ. После правки в TunerPro запустите `gs860_crc.py fix edited.bin fixed.bin`. **Перед любой прошивкой прочитайте [документ 07](docs/ru/07-reading-and-flashing.md).**

**Скачать:** [последний релиз](https://github.com/therudywolf/gs860-5hp19/releases/latest): XDF, инструменты и документы одним архивом.

### Инструменты

Python 3, только стандартная библиотека. Каждый скрипт печатает справку по `--help`.

| Скрипт | Команды | Что делает |
|---|---|---|
| `tools/egs_tables.py` | `info`, `scan`, `dump`, `cell`, `shift`, `programs`, `diff`, `ids`, `verify-shift` | сканер и распечатка таблиц; `verify-shift` проверяет точки под ограничитель мотора по ролям матриц из кода |
| `tools/gs860_crc.py` | `check`, `fix` | три контрольные суммы CRC-16: проверить или записать новый файл с пересчитанными суммами |
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
| [09 · Что не трогать](docs/ru/09-what-not-to-touch.md) | запреты, у каждого своя причина |
| [10 · Методика](docs/ru/10-methodology.md) | как делался реверс, что считается доказанным, опровергнутые трактовки |
| [11 · GS8.60.4 (20C0)](docs/ru/11-gs8604-20c0.md) | образ 512 КБ: карта, суммы, матрицы и роли, блокировка, AGS, прогрев, кикдаун, корни записей, кадр `0B 03` |
| [12 · GS8.60.0 и GS8.60.4](docs/ru/12-gs8600-vs-gs8604.md) | две программы рядом и сток против стока: почему GS8.60.4 кажется быстрее (§10) |
| [13 · Что и где менять](docs/ru/13-what-to-change.md) | ГДТ на 1-й, ранняя блокировка, прогрев, S без 5-й, обороты, кикдаун, ручной режим, кулиса, спортивная S, жёсткость, кривая ГДТ: адреса, инструкции-читатели, заводские значения, как проверить |
| [14 · Связь с мотором](docs/ru/14-engine-link.md) | кнопки круиза и режим через свободный байт DME2: приём, диспетчер рычага и ножки кулисы на 19x0 и 20C0, защиты (CC BY-NC-SA 4.0) |
| [Глоссарий](docs/ru/glossary.md) | термины |

Английские версии всех документов лежат в `docs/en/`, структура и факты те же.

### Структура репозитория

```
docs/en, docs/ru     документация, одинаковый набор файлов, оглавление в README.md каждой папки
catalog/             источник XDF: gs8600_19d0.json (19x0, 256K) и gs8604_20c0.json (20C0, 512K)
xdf/                 определения TunerPro, собранные из каталогов: 19D0 полный 256K, 19x0 партиал 32K, 20C0 полный 512K (RU и EN)
tools/               egs_tables.py, gs860_crc.py, make_xdf.py
tests/               python3 tests/test_tools.py (GS860_STOCK=stock19x0.bin GS8604_STOCK=stock20c0.bin для полного набора)
assets/              логотип
.github/             шаблоны issue и pull request, ссылка на поддержку
LICENSE, LICENSE-docs Apache-2.0 на код, CC BY-SA 4.0 на документы, каталоги и XDF
NOTICE, CITATION.cff  указание автора, которое нужно сохранять, готовая ссылка для цитирования
SECURITY.md          как лично сообщить об опасной ошибке
```

### Ответственность

Это любительский реверс блока, отвечающего за безопасность. Он может быть неполным или ошибочным: несколько прежних трактовок **оказались неверными** и перечислены как опровергнутые в [документе 10](docs/ru/10-methodology.md) и в поправках внутри документов. Неудачная калибровка может повредить коробку, отправить блок в аварийный режим или оставить машину без хода. Вы прошиваете на свой риск, только сохранив собственный полный дамп, и сами отвечаете за соблюдение законов своей страны. Bosch, ZF, Siemens, BMW и Alpina — товарные знаки их владельцев, проект с ними не связан.

### Лицензия

Всё здесь можно использовать, распространять и дорабатывать, в том числе в коммерческих целях, **при одном условии: указывать автора**:

> **rudywolf, https://github.com/therudywolf/gs860-5hp19**

| Что | Лицензия | Что значит указание автора на деле |
|---|---|---|
| Код: `tools/`, `tests/` | [Apache License 2.0](LICENSE) | копии и производные инструменты сохраняют [`NOTICE`](NOTICE) с указанием автора и сообщают, что изменено |
| Документы, каталоги (`catalog/`), XDF (`xdf/`) | [CC BY-SA 4.0](LICENSE-docs) | копии и переработки указывают автора, дают ссылку на лицензию, сообщают, что изменено, и выходят под CC BY-SA 4.0; в заголовке каждого XDF записаны лицензия и автор, их не удалять |
| Документы о собственном слое автора: `docs/*/14-*` и те, что так помечены в шапке | [CC BY-NC-SA 4.0](LICENSE-docs-nc) | как выше, и не в коммерческих целях: по этим документам не продают сборки и услуги; готовая сборка под дамп — работа автора |

Документы о собственном слое автора — единственное исключение из «в том числе в коммерческих целях»: CC BY-NC-SA 4.0. Имя и логотип WOLF4X для повторного использования не лицензируются; прошивок Bosch, ZF, Siemens и BMW в репозитории нет ([`NOTICE`](NOTICE)). Готовая ссылка для цитирования — кнопка «Cite this repository» на GitHub ([`CITATION.cff`](CITATION.cff)). Релизы до v2026.10.14 выходили с инструментами под MIT, с 28.10.2026 код под Apache-2.0.

### Благодарности

[Wiki MS4X](https://www.ms4x.net): источник по моторной части и заводским эталонным файлам. [TunerPro RT](https://www.tunerpro.net): редактор калибровок и формат XDF. Все, кто задавал неудобные вопросы и делился дампами: они заставили дочитать до конца модуль блокировки, кулису и программу прогрева.

Jason King (KingAI, [@KingAiCodeForge](https://github.com/KingAiCodeForge)): его вопросы об осях 19D0 и о том, кто пишет ячейки RAM, привели к неверно описанному объекту, ошибочным пометкам «читателей нет» и коэффициенту трансформации ГДТ (каталог 19D0 v3.3, документ 10 §9); хэши его собственных образов Alpina B3 19C0 и SP-Daten 19C0 KA20 независимо подтвердили эталонные файлы; проверка размещения полей из его сторожа каталога стала тестом `test_english_field_placement`; его pull request добавил `labels_en`, английские подписи осей таблиц.

Часть дизассемблирования, перекрёстных проверок и текста сделана с помощью ИИ-инструментов. Каждое число в этих документах проверено по бинарникам.

### Поддержать

Это хобби-исследование без бюджета: дампы читаются руками, код разбирается инструкция за инструкцией, каждая находка проверяется по коду и, где можно, на живой машине, включая ошибки, которые тоже документируются. Всё здесь остаётся бесплатным и открытым. Если это сэкономило вам время, деньги или коробку, поддержите на **[Boosty: boosty.to/therudywolf](https://boosty.to/therudywolf)**.

### Работа на заказ

Нужен кастомный тюн **MS42 / MS43**, кастомный тюн коробки **5HP19** (GS8.60) или свой логгер под машину? Напишите мне, готов взять работу платно: Telegram **[t.me/rudy_wolf](https://t.me/rudy_wolf)**, почта **[alonerudywolf@gmail.com](mailto:alonerudywolf@gmail.com)**.
