# Recipes / Рецепты

**[English](#english) · [Русский](#русский)**

<a name="english"></a>
## English

A recipe is a JSON diff between a stock GS8.60.0 calibration and a tune (schema `gs860-recipe/1`, format described in `docs/en/08-recipes-and-presets.md`). It contains addresses, table formats, **both axes**, old and new data and comments — never a firmware dump.

### Files

| File | What |
|---|---|
| `wolf4x_v18_sport_daily.json` | full diff of the WOLF4X v18 "Sport daily (8HP-like)" preset against the stock calibration it was built from. 43 tables + 3 byte blocks, 1389 bytes |
| `wolf4x_v18_sport_daily.annotations.json` | groups, names and comments used by `make_recipe.py` to build the recipe above (kept so the recipe can be regenerated) |

### Base

| | |
|---|---|
| ECU / software | Bosch GS8.60.0, 256 KB image, program 19C0/19D0 (code SHA-256 `e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546`) |
| Stock calibration | label `B22K4_0419C0KA20` (E39 2.5, stock final drive); SHA-256 of window 0x8000–0x10000 `d3c2c3fdffb943f5bd848f672c6d3750a79986167c59c72dac367d386cbbdf51` |
| Built for | 2.5 l M52TU (M52TUB25) with a 6784 rpm rev limit; see `docs/en/08` §4 for what to recalculate otherwise |
| Result | full `0bfd1d0d10037e020bcbfb16fdf5941bf17d0ec085dd5dd0cdec22c65419812e`, partial `657531fa400e0070f1cc37ebaac497c84d1ef690b1329bfdb3f81726d9ee60e4` |

### How to apply

```
python3 tools/egs_tables.py info my_dump.bin
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
```

`apply_recipe.py` stops if the code hash differs (different software), if any table axis differs (different calibration — do not force), and warns and stops if old values differ (`--force` to override — read `docs/en/08` §5 first). It writes `build.bin` (256K), `build_partial32k.bin` (32K) and `build.log`. Flash the partial; Reset Adaptation afterwards (`docs/en/07`).

### v17 → v18

v17 raised `0x8EEA` from 7000 to 7300 believing it to be a turbine over-speed limit. Disassembly proves the constant is a supply-voltage threshold in mV (`docs/en/05` §1). v18 is v17 with that byte pair back at stock; nothing else differs. Do not use v17.

### Building your own

```
python3 tools/make_recipe.py stock.bin tuned.bin -o recipes/my_recipe.json -a my_annotations.json
```

`make_recipe.py` refuses when the tune changes any table axis or any byte outside 0x8000–0x10000. Annotate every changed table (group, name, comment in EN and RU) — unannotated recipes are not accepted into the repository (see CONTRIBUTING).

<a name="русский"></a>
## Русский

Рецепт — JSON-diff между стоковой калибровкой GS8.60.0 и тюном (схема `gs860-recipe/1`, формат описан в `docs/ru/08-recipes-and-presets.md`). В нём адреса, форматы таблиц, **обе оси**, старые и новые данные и комментарии — и никогда не дамп прошивки.

### Файлы

| Файл | Что |
|---|---|
| `wolf4x_v18_sport_daily.json` | полный diff пресета WOLF4X v18 «Sport daily (8HP-like)» относительно стоковой калибровки, на которой он собран. 43 таблицы + 3 блока байт, 1389 байт |
| `wolf4x_v18_sport_daily.annotations.json` | группы, имена и комментарии, по которым `make_recipe.py` построил рецепт выше (хранится, чтобы рецепт можно было перегенерировать) |

### База

| | |
|---|---|
| Блок / ПО | Bosch GS8.60.0, образ 256 КБ, программа 19C0/19D0 (SHA-256 кода `e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546`) |
| Стоковая калибровка | метка `B22K4_0419C0KA20` (E39 2.5, стоковая главная пара); SHA-256 окна 0x8000–0x10000 `d3c2c3fdffb943f5bd848f672c6d3750a79986167c59c72dac367d386cbbdf51` |
| Под что собран | 2.5 л M52TU (M52TUB25) с отсечкой 6784; что пересчитывать под другое — `docs/ru/08` §4 |
| Результат | full `0bfd1d0d10037e020bcbfb16fdf5941bf17d0ec085dd5dd0cdec22c65419812e`, partial `657531fa400e0070f1cc37ebaac497c84d1ef690b1329bfdb3f81726d9ee60e4` |

### Как применить

```
python3 tools/egs_tables.py info my_dump.bin
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
```

`apply_recipe.py` останавливается, если не совпал хэш кода (другое ПО), если отличается любая ось таблицы (другая калибровка — не форсировать), и предупреждает и останавливается, если не совпали старые значения (`--force` — только после чтения `docs/ru/08` §5). Пишет `build.bin` (256K), `build_partial32k.bin` (32K) и `build.log`. Шить партиал; после — Reset Adaptation (`docs/ru/07`).

### v17 → v18

В v17 `0x8EEA` был поднят с 7000 до 7300 в предположении, что это порог разноса турбины. Дизассемблер доказывает, что константа — порог напряжения питания в мВ (`docs/ru/05` §1). v18 = v17 с этой парой байт, возвращённой к стоку; больше ничего не отличается. v17 не использовать.

### Свой рецепт

```
python3 tools/make_recipe.py stock.bin tuned.bin -o recipes/my_recipe.json -a my_annotations.json
```

`make_recipe.py` откажется, если тюн меняет ось любой таблицы или байты вне 0x8000–0x10000. Аннотируйте каждую изменённую таблицу (группа, имя, комментарий EN и RU) — рецепты без аннотаций в репозиторий не принимаются (см. CONTRIBUTING).
