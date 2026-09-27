# Contributing / Как участвовать

**[English](#english) | [Русский](#русский)**

<a name="english"></a>
## English

### What is welcome

- Corrections with evidence: a disassembly excerpt, a table dump, a log, anything that lets somebody else re-check it. "I think X is Y" without a code reference goes into an issue as a hypothesis, not into the docs.
- Logs of shifts (RAM read via DS2 0x06, doc 06 §4) before/after a recipe, with the recipe named.
- Recipes for other engines / final drives, with annotations (group, name, EN+RU comment for every table) and the base calibration label.
- Information about **other 19x0 calibration revisions** (different `B22K4_04xxxx` label at 0x0FFCE): which tables differ from the `19C0KA20` base.
- Translations and wording fixes.

### What is not accepted

- **Firmware dumps in issues or pull requests, in any form** (full 256K or 512K, partial 32K, hex pastes). A full dump carries the unit serial and history, the EEPROM carries the VIN. If a comparison needs your dump, post the output of `tools/egs_tables.py info` and `tools/egs_tables.py diff <your dump> <reference>`, that is enough to see what differs, or agree on a private exchange with the maintainer directly. Issues that contain dumps are deleted.
- **VIN, unit serial numbers and owner names** anywhere: in text, logs, screenshots and file names. Dump files are often named after the VIN, rename them before you paste a command line or its output. `egs_tables.py ids` prints the identification strings of the unit, do not post its output.
- Anything that mixes GS8.60.0 and GS8.60.4 addresses. The 512 KB images (20C0) have their own catalog, XDF and document (doc 11). A 19x0 address, recipe or RAM cell does not apply to them, and the other way round.
- Anything about the engine ECU or vehicle anti-theft systems. This repository is about the gearbox only.
- Copies of third-party AI-generated "findings" without verification against the binary. Several such lists have already been refuted (doc 10 §6).

### How to send a log or a calibration difference

1. `python3 tools/egs_tables.py info dump.bin`: paste the output (size, hashes, label, table count). No bytes of the dump itself.
2. `python3 tools/egs_tables.py diff reference.bin dump.bin --all` against a stock of the same label if you have one: paste the changed cells.
3. For a log: CSV with a time column and the RAM addresses read (doc 06 §4), plus the recipe/build SHA-256 it was recorded with, engine, final drive, tyre size.
4. Say what the car did (symptom) and what you expected.

### Tests

```bash
python3 tests/test_tools.py
GS860_STOCK=stock19x0.bin GS8604_STOCK=stock20c0.bin python3 tests/test_tools.py
```

Without images the tests check the tools, both catalogs and the XDF files (the image tests are skipped and say so). `GS860_STOCK` is a stock 256 KB 19x0 image, `GS8604_STOCK` a factory 512 KB 20C0 image. With them the recipes are applied and checked (when the image is the stock calibration they were built from), and the catalog tables are read from the image. Run both before a pull request that touches `tools/`, `catalog/`, `xdf/` or `recipes/`.

### XDF from the catalog

The XDF files are generated, never edited by hand. Change `catalog/*.json`, then:

```bash
python3 tools/make_xdf.py check catalog/gs8600_19d0.json
python3 tools/make_xdf.py build catalog/gs8600_19d0.json xdf/GS8600_19D0_Full256K.xdf --partial xdf/GS8600_19x0_Partial32K.xdf
python3 tools/make_xdf.py check catalog/gs8604_20c0.json
python3 tools/make_xdf.py build catalog/gs8604_20c0.json xdf/GS8604_20C0_Full512K.xdf
```

`check` refuses a byte span outside the image, two entries reading the same byte, a repeated uid, an unknown category and an empty unit. `build` runs `check` first. The tests compare every XDF file with what its catalog renders. No partial XDF for 20C0 is published until it is known what the flasher reads as a Partial on the GS8.60.4 (doc 11 §13). Every entry carries a `confidence` level, and `proven` entries name the instruction in `proof`.

### Style

Same as the docs: addresses in hex with `0x`, RAM as `0xFFFFxxxx`, units for every number, and a confidence label for every claim about semantics (doc 10 §6 in the documents, the `confidence` levels in the catalogs). What is not established is called not established. Russian and English versions of a document must say the same thing: if you change one, change the other or mark it `TODO translate`.

<a name="русский"></a>
## Русский

### Что приветствуется

- Исправления с доказательством: фрагмент дизассемблера, распечатка таблицы, лог, то, что позволит другому перепроверить. «Я думаю, что X это Y» без ссылки на код идёт в issue как гипотеза, а не в документацию.
- Логи переключений (чтение RAM через DS2 0x06, документ 06 §4) до/после рецепта с указанием рецепта.
- Рецепты под другие моторы / главные пары с аннотациями (группа, имя, комментарий EN+RU для каждой таблицы) и меткой базовой калибровки.
- Сведения о **других ревизиях калибровки 19x0** (другая метка `B22K4_04xxxx` по 0x0FFCE): какие таблицы отличаются от базы `19C0KA20`.
- Переводы и правки формулировок.

### Что не принимается

- **Дампы прошивок в issues и pull request'ах в любом виде** (полный 256K или 512K, партиал 32K, hex-вставки). Полный дамп содержит серийный номер блока и историю, EEPROM содержит VIN. Если для сравнения нужен ваш дамп, присылайте вывод `tools/egs_tables.py info` и `tools/egs_tables.py diff <ваш дамп> <эталон>`, этого достаточно, чтобы увидеть отличия, либо договаривайтесь о приватном обмене с мейнтейнером напрямую. Issues с дампами удаляются.
- **VIN, серийные номера блоков и имена владельцев** нигде: ни в тексте, ни в логах, ни на снимках экрана, ни в именах файлов. Файлы дампов часто названы по VIN, переименуйте их, прежде чем вставлять командную строку или её вывод. `egs_tables.py ids` печатает идентификационные строки блока, его вывод не публикуйте.
- Что-либо, где смешаны адреса GS8.60.0 и GS8.60.4. У образов 512 КБ (20C0) свой каталог, XDF и документ (документ 11). Адрес, рецепт или ячейка RAM 19x0 к ним не применимы, и наоборот.
- Что-либо про блок двигателя и штатные противоугонные системы. Этот репозиторий только про коробку.
- Копии чужих «находок», сгенерированных AI, без проверки по бинарнику. Несколько таких списков уже опровергнуты (документ 10 §6).

### Как прислать лог или отличия калибровки

1. `python3 tools/egs_tables.py info dump.bin`: вывод целиком (размер, хэши, метка, число таблиц). Байтов самого дампа не нужно.
2. `python3 tools/egs_tables.py diff reference.bin dump.bin --all` против стока с той же меткой, если он у вас есть: изменённые ячейки.
3. Для лога: CSV с колонкой времени и прочитанными адресами RAM (документ 06 §4), плюс SHA-256 рецепта/сборки, с которой он записан, мотор, главная пара, размер колёс.
4. Что делала машина (симптом) и что ожидалось.

### Тесты

```bash
python3 tests/test_tools.py
GS860_STOCK=stock19x0.bin GS8604_STOCK=stock20c0.bin python3 tests/test_tools.py
```

Без образов тесты проверяют инструменты, оба каталога и файлы XDF (тесты по образам пропускаются и пишут почему). `GS860_STOCK` это стоковый образ 19x0 на 256 КБ, `GS8604_STOCK` заводской образ 20C0 на 512 КБ. С ними рецепты применяются и проверяются (если образ это та стоковая калибровка, на которой они собраны), а таблицы каталога читаются по образу. Перед pull request, который трогает `tools/`, `catalog/`, `xdf/` или `recipes/`, запустите оба варианта.

### XDF из каталога

Файлы XDF генерируются и руками не правятся. Меняете `catalog/*.json`, затем:

```bash
python3 tools/make_xdf.py check catalog/gs8600_19d0.json
python3 tools/make_xdf.py build catalog/gs8600_19d0.json xdf/GS8600_19D0_Full256K.xdf --partial xdf/GS8600_19x0_Partial32K.xdf
python3 tools/make_xdf.py check catalog/gs8604_20c0.json
python3 tools/make_xdf.py build catalog/gs8604_20c0.json xdf/GS8604_20C0_Full512K.xdf
```

`check` не пропускает байты вне образа, две записи на одном байте, повтор uid, неизвестную категорию и пустую единицу. `build` сначала запускает `check`. Тесты сравнивают каждый файл XDF с тем, что рендерит его каталог. Частичного XDF для 20C0 нет, пока не известно, что флешер читает как Partial у GS8.60.4 (документ 11 §13). У каждой записи есть уровень `confidence`, у записей `proven` в `proof` указана инструкция.

### Стиль

Как в документах: адреса в hex с `0x`, RAM как `0xFFFFxxxx`, единицы у каждого числа и метка уверенности у каждого утверждения о смысле (в документах по документу 10 §6, в каталогах уровни `confidence`). Неустановленное называется неустановленным. Русская и английская версии документа должны говорить одно и то же: меняете одну, меняйте другую или ставьте `TODO translate`.
