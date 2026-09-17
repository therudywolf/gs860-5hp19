# Contributing / Как участвовать

**[English](#english) · [Русский](#русский)**

<a name="english"></a>
## English

### What is welcome

- Corrections with evidence: a disassembly excerpt, a table dump, a log — anything that lets somebody else re-check it. "I think X is Y" without a code reference goes into an issue as a hypothesis, not into the docs.
- Logs of shifts (RAM read via DS2 0x06, doc 06 §4) before/after a recipe, with the recipe named.
- Recipes for other engines / final drives, with annotations (group, name, EN+RU comment for every table) and the base calibration label.
- Information about **other 19x0 calibration revisions** (different `B22K4_04xxxx` label at 0x0FFCE): which tables differ from the `19C0KA20` base.
- Translations and wording fixes.

### What is not accepted

- **Firmware dumps in issues or pull requests, in any form** (full 256K, partial 32K, hex pastes). A full dump carries the unit serial and history; the EEPROM carries the VIN. If a comparison needs your dump, post the output of `tools/egs_tables.py info` and `tools/egs_tables.py diff <your dump> <reference>` — that is enough to see what differs — or agree on a private exchange with the maintainer directly. Issues that contain dumps are deleted.
- Anything about GS8.60.4 / 512 KB images as if it applied here (open a separate discussion; the layout is different).
- Anything about the engine ECU or vehicle anti-theft systems — this repository is about the gearbox only.
- Copies of third-party AI-generated "findings" without verification against the binary. Several such lists have already been refuted (doc 10 §6).

### How to send a log or a calibration difference

1. `python3 tools/egs_tables.py info dump.bin` → paste the output (size, hashes, label, table count). No bytes of the dump itself.
2. `python3 tools/egs_tables.py diff reference.bin dump.bin --all` against a stock of the same label if you have one → paste the changed cells.
3. For a log: CSV with a time column and the RAM addresses read (doc 06 §4), plus the recipe/build SHA-256 it was recorded with, engine, final drive, tyre size.
4. Say what the car did (symptom) and what you expected.

### Style

Same as the docs: addresses in hex with `0x`, RAM as `0xFFFFxxxx`, units for every number, and a confidence label (proven / estimated / hypothesis) for every claim about semantics. Russian and English versions of a document must say the same thing — if you change one, change the other or mark it `TODO translate`.

<a name="русский"></a>
## Русский

### Что приветствуется

- Исправления с доказательством: фрагмент дизассемблера, распечатка таблицы, лог — то, что позволит другому перепроверить. «Я думаю, что X — это Y» без ссылки на код идёт в issue как гипотеза, а не в документацию.
- Логи переключений (чтение RAM через DS2 0x06, документ 06 §4) до/после рецепта с указанием рецепта.
- Рецепты под другие моторы / главные пары с аннотациями (группа, имя, комментарий EN+RU для каждой таблицы) и меткой базовой калибровки.
- Сведения о **других ревизиях калибровки 19x0** (другая метка `B22K4_04xxxx` по 0x0FFCE): какие таблицы отличаются от базы `19C0KA20`.
- Переводы и правки формулировок.

### Что не принимается

- **Дампы прошивок в issues и pull request'ах в любом виде** (полный 256K, партиал 32K, hex-вставки). Полный дамп содержит серийный номер блока и историю; EEPROM — VIN. Если для сравнения нужен ваш дамп — присылайте вывод `tools/egs_tables.py info` и `tools/egs_tables.py diff <ваш дамп> <эталон>` — этого достаточно, чтобы увидеть отличия, — либо договаривайтесь о приватном обмене с мейнтейнером напрямую. Issues с дампами удаляются.
- Что-либо про GS8.60.4 / образы 512 КБ в предположении, что это применимо здесь (отдельное обсуждение; раскладка другая).
- Что-либо про блок двигателя и штатные противоугонные системы — этот репозиторий только про коробку.
- Копии чужих «находок», сгенерированных AI, без проверки по бинарнику. Несколько таких списков уже опровергнуты (документ 10 §6).

### Как прислать лог или отличия калибровки

1. `python3 tools/egs_tables.py info dump.bin` → вывод целиком (размер, хэши, метка, число таблиц). Байтов самого дампа — нет.
2. `python3 tools/egs_tables.py diff reference.bin dump.bin --all` против стока с той же меткой, если он у вас есть → изменённые ячейки.
3. Для лога: CSV с колонкой времени и прочитанными адресами RAM (документ 06 §4), плюс SHA-256 рецепта/сборки, с которой он записан, мотор, главная пара, размер колёс.
4. Что делала машина (симптом) и что ожидалось.

### Стиль

Как в документах: адреса в hex с `0x`, RAM как `0xFFFFxxxx`, единицы у каждого числа и метка уверенности (доказано / оценочно / гипотеза) у каждого утверждения о смысле. Русская и английская версии документа должны говорить одно и то же — меняете одну, меняйте другую или ставьте `TODO translate`.
