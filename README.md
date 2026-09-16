# GS8.60.0 · ZF 5HP19 · Bosch EGS reverse-engineering notes

**[English](#english) · [Русский](#русский)**

---

<a name="english"></a>
## English

Community documentation of the calibration and shift logic of the **Bosch GS8.60.0** transmission control unit (ZF 5HP19 / A5S 325Z, BMW E39 / E46 and other models with this gearbox), software **19C0 / 19D0**, 256 KB image, Motorola 68k (CPU32). Written in the style of the [MS4X wiki](https://www.ms4x.net): dry, with addresses, axes and units, and an explicit line between what is proven and what is a hypothesis.

Author of the project: **rudywolf (WOLF4X)**. Everything here was obtained by disassembling firmware dumps (capstone m68k), by diffing a stock calibration against the Alpina B3 factory calibration on the same software, and by DS2 logs on a real car. Nothing is taken from Bosch/ZF documentation — there is none available.

### Who this is for

- People who tune or diagnose a 5HP19 with the GS8.60.0 and want to know **what a given table does in code**, not "what it might be".
- People who want to apply a ready preset to their own dump in a reproducible way (recipes + tools), or build their own.
- People who log the EGS and want the RAM addresses that matter.

### What is covered / not covered

| | |
|---|---|
| **Covered** | GS8.60.0, 256 KB, program 19x0. Two dumps verified: stock 2.5 (M52TU) (calibration `19C0 KA20`) and Alpina B3 3.3 (`19D0 620P`). The program code 0x10000–0x40000 is byte-identical in both (SHA-256 `e151733e…`), so **one XDF fits both**; the calibrations differ in 2547 bytes |
| **Not covered** | **GS8.60.4** (512 KB image, e.g. 20C0 from the E46 330i / Alpina B3S): different memory layout — the XDF, addresses and recipes here **do not apply**. Also not covered: the engine ECU (MS42/MS43 — see the MS4X wiki), immobiliser, CAN wiring |
| **Not published** | firmware dumps (they carry unit identifiers and possibly the VIN), code patches, anything about EWS |

### Quick start

```
python3 tools/egs_tables.py info my_dump.bin          # size, SHA-256, code hash (must be e151733e…), 536 tables
python3 tools/egs_tables.py shift my_dump.bin         # the 16 shift-point matrices
python3 tools/egs_tables.py dump my_dump.bin 0xBF9C   # any table by address
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
```

Then read `docs/en/07-reading-and-flashing.md` before flashing anything. Open `xdf/GS8600_19D0_Full256K.xdf` in TunerPro with a 256 KB dump, or `xdf/GS8600_19x0_Partial32K.xdf` with a 32 KB partial.

### Documents

| File | Contents |
|---|---|
| [docs/en/01-firmware-layout.md](docs/en/01-firmware-layout.md) | memory map, table format, 536 tables, pointer catalog, the two calibration branches, 16 programs, DS2 dispatcher |
| [docs/en/02-shift-points.md](docs/en/02-shift-points.md) | 16 matrices 0x91B2 + k·0x70, pedal rows, km/h ↔ rpm, rules for computing a point |
| [docs/en/03-torque-converter-lockup.md](docs/en/03-torque-converter-lockup.md) | function 0x1DEBC, 4-stage ladder, threshold tables 0x901E…0x915E, the "temperature window" myth, where ATF temperature really is |
| [docs/en/04-shift-execution-hydraulics.md](docs/en/04-shift-execution-hydraulics.md) | the shift-execution module: record sets kind0..3, transition types, phases, slip-time controller, pressures, axes, table families, stock vs Alpina, why v5 died |
| [docs/en/05-protections.md](docs/en/05-protections.md) | function 0x265F4 = supply-voltage monitor (the "turbine 7000" reading and how it was corrected), thermal derate, limp mode, 0x81A0 |
| [docs/en/06-logging-ds2.md](docs/en/06-logging-ds2.md) | DS2 at 9600, RAM read via 0x06 segment 4, status frame bytes, RAM addresses for A/B |
| [docs/en/07-reading-and-flashing.md](docs/en/07-reading-and-flashing.md) | full 256K vs partial 32K, order, Reset Adaptation, what a dump contains |
| [docs/en/08-recipes-and-presets.md](docs/en/08-recipes-and-presets.md) | recipe format, the WOLF4X v18 preset with every change justified, what to recalculate for another engine |
| [docs/en/09-what-not-to-touch.md](docs/en/09-what-not-to-touch.md) | the prohibitions and why |
| [docs/en/10-methodology.md](docs/en/10-methodology.md) | how the reverse was done, what counts as proven, open questions |
| [docs/en/glossary.md](docs/en/glossary.md) | terms |

Russian versions of every document are in `docs/ru/`.

### Repository layout

```
docs/en, docs/ru     documentation (identical set of files)
xdf/                 TunerPro definitions: full 256K and partial 32K
tools/               egs_tables.py (scan/dump/diff/shift), make_recipe.py, apply_recipe.py — Python 3, no dependencies
recipes/             JSON recipes (stock → tune) and their annotations
```

### Disclaimer

This is reverse-engineering of a safety-relevant control unit by hobbyists. Everything here may be incomplete or wrong; several earlier readings were wrong and are listed as refuted in `docs/en/10-methodology.md`. A wrong calibration can damage the transmission, put the ECU into limp mode or leave the car immobile. You flash at your own risk, only with your own full dump saved, and you are responsible for compliance with the laws of your country.

### Licence

Documentation and XDF files: **CC BY-SA 4.0** (`LICENSE-docs`). Scripts in `tools/`: **MIT** (`LICENSE-code`). Recipes in `recipes/` are data and follow CC BY-SA 4.0.

### Credits

- The [MS4X wiki](https://www.ms4x.net) — the reference for the engine side (MS42/MS43), the flashing tool and the source of the Alpina reference files.
- Everyone who sent logs, dumps for comparison and questions — the "114 km/h" and "minimum temperature" questions from other tuners forced the TCC module to be read to the end.
- Disassembly and text assistance: AI tools were used for parts of the disassembly, cross-checking and writing; every number was verified against the binaries.

---

<a name="русский"></a>
## Русский

Документация сообщества по калибровке и логике переключений блока управления АКПП **Bosch GS8.60.0** (ZF 5HP19 / A5S 325Z, BMW E39 / E46 и другие модели с этой коробкой), софт **19C0 / 19D0**, образ 256 КБ, Motorola 68k (CPU32). Стиль — как у [wiki MS4X](https://www.ms4x.net): сухо, адреса, оси, единицы, и явная граница между доказанным и гипотезой.

Автор проекта: **rudywolf (WOLF4X)**. Всё получено дизассемблированием дампов (capstone m68k), сравнением стоковой калибровки с заводской калибровкой Alpina B3 на том же ПО и логами DS2 на реальной машине. Документации Bosch/ZF в открытом доступе нет, ничего из неё не использовано.

### Для кого

- Для тех, кто настраивает или диагностирует 5HP19 с GS8.60.0 и хочет знать, **что таблица делает в коде**, а не «чем она могла бы быть».
- Для тех, кто хочет воспроизводимо применить готовый пресет к своему дампу (рецепты + инструменты) или собрать свой.
- Для тех, кто логирует EGS и хочет знать адреса RAM, которые имеют смысл.

### Что покрыто / не покрыто

| | |
|---|---|
| **Покрыто** | GS8.60.0, 256 КБ, программа 19x0. Проверено на двух дампах: сток 2.5 (M52TU) (калибровка `19C0 KA20`) и Alpina B3 3.3 (`19D0 620P`). Код 0x10000–0x40000 у обоих совпадает байт-в-байт (SHA-256 `e151733e…`), поэтому **один XDF подходит обоим**; калибровки различаются в 2547 байтах |
| **Не покрыто** | **GS8.60.4** (образ 512 КБ, например 20C0 с E46 330i / Alpina B3S): другая раскладка памяти — XDF, адреса и рецепты отсюда **не подходят**. Также не покрыто: блок ДВС (MS42/MS43 — см. wiki MS4X), иммобилайзер, разводка CAN |
| **Не публикуется** | дампы прошивок (в них идентификаторы блока и, возможно, VIN), патчи кода, что-либо про EWS |

### Быстрый старт

```
python3 tools/egs_tables.py info my_dump.bin          # размер, SHA-256, хэш кода (должен быть e151733e…), 536 таблиц
python3 tools/egs_tables.py shift my_dump.bin         # 16 матриц точек переключения
python3 tools/egs_tables.py dump my_dump.bin 0xBF9C   # любая таблица по адресу
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
```

Перед прошивкой — `docs/ru/07-reading-and-flashing.md`. XDF: `xdf/GS8600_19D0_Full256K.xdf` для дампа 256 КБ, `xdf/GS8600_19x0_Partial32K.xdf` для партиала 32 КБ (TunerPro).

### Документы

| Файл | Содержание |
|---|---|
| [docs/ru/01-firmware-layout.md](docs/ru/01-firmware-layout.md) | карта памяти, формат таблиц, 536 таблиц, каталог указателей, две ветки калибровки, 16 программ, диспетчер DS2 |
| [docs/ru/02-shift-points.md](docs/ru/02-shift-points.md) | 16 матриц 0x91B2 + k·0x70, строки педали, км/ч ↔ об/мин, правила расчёта точки |
| [docs/ru/03-torque-converter-lockup.md](docs/ru/03-torque-converter-lockup.md) | функция 0x1DEBC, лесенка из 4 ступеней, таблицы порогов 0x901E…0x915E, миф о «температурном окне», где на самом деле температура ATF |
| [docs/ru/04-shift-execution-hydraulics.md](docs/ru/04-shift-execution-hydraulics.md) | модуль исполнения переключения: наборы записей kind0..3, типы переходов, фазы, регулятор времени скольжения, давления, оси, семейства таблиц, сток vs Alpina, почему умерла v5 |
| [docs/ru/05-protections.md](docs/ru/05-protections.md) | функция 0x265F4 = монитор напряжения питания (трактовка «турбина 7000» и её исправление), термодерейт, аварийный режим, 0x81A0 |
| [docs/ru/06-logging-ds2.md](docs/ru/06-logging-ds2.md) | DS2 на 9600, чтение RAM через 0x06 сегмент 4, байты статусного кадра, адреса RAM для A/B |
| [docs/ru/07-reading-and-flashing.md](docs/ru/07-reading-and-flashing.md) | full 256K vs partial 32K, порядок, Reset Adaptation, что содержит дамп |
| [docs/ru/08-recipes-and-presets.md](docs/ru/08-recipes-and-presets.md) | формат рецепта, пресет WOLF4X v18 с обоснованием каждого изменения, что пересчитать под другой мотор |
| [docs/ru/09-what-not-to-touch.md](docs/ru/09-what-not-to-touch.md) | запреты и почему |
| [docs/ru/10-methodology.md](docs/ru/10-methodology.md) | как делался реверс, что считается доказанным, открытые вопросы |
| [docs/ru/glossary.md](docs/ru/glossary.md) | термины |

Английские версии всех документов — в `docs/en/`.

### Структура репозитория

```
docs/en, docs/ru     документация (одинаковый набор файлов)
xdf/                 определения TunerPro: полный 256K и партиал 32K
tools/               egs_tables.py (scan/dump/diff/shift), make_recipe.py, apply_recipe.py — Python 3, без зависимостей
recipes/             JSON-рецепты (сток → тюн) и их аннотации
```

### Ответственность

Это любительский реверс блока, влияющего на безопасность. Всё здесь может быть неполным или ошибочным; несколько ранних трактовок оказались неверны и перечислены как опровергнутые в `docs/ru/10-methodology.md`. Неверная калибровка может повредить коробку, отправить блок в аварийный режим или обездвижить машину. Вы прошиваете на свой риск, только имея собственный полный дамп, и сами отвечаете за соответствие законам своей страны.

### Лицензия

Документация и XDF: **CC BY-SA 4.0** (`LICENSE-docs`). Скрипты в `tools/`: **MIT** (`LICENSE-code`). Рецепты в `recipes/` — данные, распространяются на условиях CC BY-SA 4.0.

### Благодарности

- [Wiki MS4X](https://www.ms4x.net) — источник по моторной части (MS42/MS43), по флешеру и эталонных файлов Alpina.
- Всем, кто присылал логи, дампы для сравнения и вопросы — вопросы других тюнеров про «114 км/ч» и «минимальную температуру» заставили дочитать модуль ГДТ до конца.
- Помощь в дизассемблировании и тексте: для части дизассемблирования, перепроверки и написания использовались AI-инструменты; каждое число проверено по бинарникам.
