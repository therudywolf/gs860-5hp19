# Recipes / Рецепты

**[English](#english) · [Русский](#русский)**

<a name="english"></a>
## English

A recipe is a JSON diff between a stock GS8.60.0 calibration and a tune (schema `gs860-recipe/2`, the older `/1` is still accepted; format described in `docs/en/08-recipes-and-presets.md`). It contains addresses, table formats, **both axes**, old and new data and comments — never a firmware dump, and never the checksum bytes `0xFFFE–0xFFFF`: `apply_recipe.py` computes those (`docs/en/07` §6).

**23.09.2026.** All three presets were revised: the shift matrices hold output shaft rpm / 32, not km/h (`docs/en/02` §3), so the 16.09 sport shift points were never reached at full throttle and the box hung at the limiter; the manual programs had no protection on the overrun and a kickdown landing above the spark cut. The shift points were recomputed by `egs_tables.py verify-shift --spark 6656 --cut 6784 --fix`, hydraulics and TCC are as built. The 16.09 result hashes are kept in each recipe under `history`.

### Files

| File | What |
|---|---|
| `wolf4x_v18_sport_daily.json` | full diff of the WOLF4X v18 "Sport daily (8HP-like)" preset against the stock calibration it was built from. 43 tables + 3 byte blocks, 1375 bytes with the checksum. Result full `14e15185…`, partial `e50bdaec…` |
| `wolf4x_v18_sport_daily.annotations.json` | groups, names and comments used by `make_recipe.py` to build the recipe above (kept so the recipe can be regenerated) |
| `wolf4x_v19_street_hard.json` | WOLF4X v19 "Street hard" — v18 taken to the factory Alpina B3 level: shorter target slip time at high torque, on-coming/off-going pressures copied cell by cell from Alpina where the axes match, sport holds a gear longer at part throttle, TCC stages 3–4 from 30–50 % pedal in S/M. 45 tables + 3 byte blocks, 1238 bytes. Result full `3b5c2cab…`, partial `6b740fc5…` |
| `wolf4x_v19_street_hard.annotations.json` | annotations for the recipe above |
| `wolf4x_v20_track_hard.json` | WOLF4X v20 "Track hard" — v19 with a deliberately harder shift in the cells only Sport/Manual reach: shorter target slip time, raised slip-pressure ceiling f24, higher on-coming pressure, stock torque request at 3000 rpm, TCC stages 3–4 earlier in S/M. 47 tables + 7 byte blocks, 1244 bytes. Result full `1106e3eb…`, partial `faad4369…` |
| `wolf4x_v20_track_hard.annotations.json` | annotations for the recipe above |

### Base

| | |
|---|---|
| ECU / software | Bosch GS8.60.0, 256 KB image, program 19C0/19D0 (code SHA-256 `e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546`) |
| Stock calibration | label `B22K4_0419C0KA20` (E39 2.5, stock final drive); SHA-256 of window 0x8000–0x10000 `d3c2c3fdffb943f5bd848f672c6d3750a79986167c59c72dac367d386cbbdf51` |
| Built for | 2.5 l M52TU (M52TUB25) with the fuel cut at 6784 rpm and the spark cut from about 6656; for another limiter run `egs_tables.py verify-shift` (`docs/en/08` §4). The final drive and tyres do not matter for the shift rpm |
| Result (v18) | full `14e1518567722bfe53dda79d04e9fcd88d865643095f94c5656423647fe42a3a`, partial `e50bdaec1c27852ebebec3e3de44e9785f43d3a9fa80020b4d7096c9013767b7`, calibration checksum `0xEA30` |

### How to apply

```
python3 tools/egs_tables.py info my_dump.bin
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
python3 tools/gs860_crc.py check build.bin build_partial32k.bin
python3 tools/egs_tables.py verify-shift build.bin --spark 6656 --cut 6784 --stock my_dump.bin
```

`apply_recipe.py` stops if the code hash differs (different software), if the loader or program checksum of the input does not match (damaged read), if any table axis differs (different calibration — do not force), and warns and stops if old values differ (`--force` to override — read `docs/en/08` §5 first). It recomputes the calibration checksum and writes `build.bin` (256K), `build_partial32k.bin` (32K) and `build.log`. Flash the partial; Reset Adaptation afterwards (`docs/en/07`).

### v17 → v18

v17 raised `0x8EEA` from 7000 to 7300 believing it to be a turbine over-speed limit. Disassembly proves the constant is a supply-voltage threshold in mV (`docs/en/05` §1). v18 is v17 with that byte pair back at stock; nothing else differs. Do not use v17.

### Building your own

```
python3 tools/make_recipe.py stock.bin tuned.bin -o recipes/my_recipe.json -a my_annotations.json
```

`make_recipe.py` refuses when the tune changes any table axis or any byte outside 0x8000–0x10000, and leaves the checksum bytes out. Annotate every changed table (group, name, comment in EN and RU) — unannotated recipes are not accepted into the repository (see CONTRIBUTING). Before a pull request run `python3 -m unittest discover -s tests` with `GS860_STOCK` set and `egs_tables.py verify-shift` for the engine the recipe is meant for.

<a name="русский"></a>
## Русский

Рецепт — JSON-diff между стоковой калибровкой GS8.60.0 и тюном (схема `gs860-recipe/2`, старая `/1` тоже принимается; формат описан в `docs/ru/08-recipes-and-presets.md`). В нём адреса, форматы таблиц, **обе оси**, старые и новые данные и комментарии — и никогда не дамп прошивки и не байты суммы `0xFFFE–0xFFFF`: их считает `apply_recipe.py` (`docs/ru/07` §6).

**23.09.2026.** Все три пресета исправлены: матрицы переключения хранят обороты выходного вала / 32, а не км/ч (`docs/ru/02` §3), поэтому точки спорта 16.09 в пол были недостижимы и коробка висела в отсечке, а у ручных программ не было защиты на накате и кикдаун приводил мотор выше искры. Точки пересчитаны командой `egs_tables.py verify-shift --spark 6656 --cut 6784 --fix`, гидравлика и ГДТ как собраны. Хэши результата от 16.09 сохранены в каждом рецепте в поле `history`.

### Файлы

| Файл | Что |
|---|---|
| `wolf4x_v18_sport_daily.json` | полный diff пресета WOLF4X v18 «Sport daily (8HP-like)» относительно стоковой калибровки, на которой он собран. 43 таблицы + 3 блока байт, 1375 байт с суммой. Результат full `14e15185…`, partial `e50bdaec…` |
| `wolf4x_v18_sport_daily.annotations.json` | группы, имена и комментарии, по которым `make_recipe.py` построил рецепт выше (хранится, чтобы рецепт можно было перегенерировать) |
| `wolf4x_v19_street_hard.json` | WOLF4X v19 «Street hard» — v18, доведённый до заводского уровня Alpina B3: короче целевое время скольжения на высоком моменте, давления включаемого/выключаемого поячеечно из Alpina там, где совпадают оси, спорт дольше держит передачу на частичном газе, ГДТ в S/M выходит на 3–4 ступень с 30–50 % педали. 45 таблиц + 3 блока байт, 1238 байт. Результат full `3b5c2cab…`, partial `6b740fc5…` |
| `wolf4x_v19_street_hard.annotations.json` | аннотации к рецепту выше |
| `wolf4x_v20_track_hard.json` | WOLF4X v20 «Track hard» — v19 с осознанно более жёстким переключением в ячейках, куда попадают только Sport/Manual: короче целевое время скольжения, выше потолок давления f24, выше давление включаемого, запрос момента на 3000 об/мин к стоку, ступени 3–4 ГДТ в S/M раньше. 47 таблиц + 7 блоков байт, 1244 байта. Результат full `1106e3eb…`, partial `faad4369…` |
| `wolf4x_v20_track_hard.annotations.json` | аннотации к рецепту выше |

### База

| | |
|---|---|
| Блок / ПО | Bosch GS8.60.0, образ 256 КБ, программа 19C0/19D0 (SHA-256 кода `e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546`) |
| Стоковая калибровка | метка `B22K4_0419C0KA20` (E39 2.5, стоковая главная пара); SHA-256 окна 0x8000–0x10000 `d3c2c3fdffb943f5bd848f672c6d3750a79986167c59c72dac367d386cbbdf51` |
| Под что собран | 2.5 л M52TU (M52TUB25), топливная отсечка 6784, искра примерно с 6656; под другой ограничитель запустить `egs_tables.py verify-shift` (`docs/ru/08` §4). Главная пара и колёса на обороты переключения не влияют |
| Результат (v18) | full `14e1518567722bfe53dda79d04e9fcd88d865643095f94c5656423647fe42a3a`, partial `e50bdaec1c27852ebebec3e3de44e9785f43d3a9fa80020b4d7096c9013767b7`, сумма калибровки `0xEA30` |

### Как применить

```
python3 tools/egs_tables.py info my_dump.bin
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
python3 tools/gs860_crc.py check build.bin build_partial32k.bin
python3 tools/egs_tables.py verify-shift build.bin --spark 6656 --cut 6784 --stock my_dump.bin
```

`apply_recipe.py` останавливается, если не совпал хэш кода (другое ПО), если у входа не сходится сумма загрузчика или программы (дамп снят с ошибкой), если отличается любая ось таблицы (другая калибровка — не форсировать), и предупреждает и останавливается, если не совпали старые значения (`--force` — только после чтения `docs/ru/08` §5). Пересчитывает сумму калибровки и пишет `build.bin` (256K), `build_partial32k.bin` (32K) и `build.log`. Шить партиал; после — Reset Adaptation (`docs/ru/07`).

### v17 → v18

В v17 `0x8EEA` был поднят с 7000 до 7300 в предположении, что это порог разноса турбины. Дизассемблер доказывает, что константа — порог напряжения питания в мВ (`docs/ru/05` §1). v18 = v17 с этой парой байт, возвращённой к стоку; больше ничего не отличается. v17 не использовать.

### Свой рецепт

```
python3 tools/make_recipe.py stock.bin tuned.bin -o recipes/my_recipe.json -a my_annotations.json
```

`make_recipe.py` откажется, если тюн меняет ось любой таблицы или байты вне 0x8000–0x10000, а байты суммы в рецепт не включает. Аннотируйте каждую изменённую таблицу (группа, имя, комментарий EN и RU) — рецепты без аннотаций в репозиторий не принимаются (см. CONTRIBUTING). Перед pull request запустите `python3 -m unittest discover -s tests` с `GS860_STOCK` и `egs_tables.py verify-shift` под мотор, для которого рецепт.

### v18 vs v19

**v18 "Sport daily"** — conservative: uniform multipliers on top of stock (×0.85 target slip time, ×1.15 pressures). **v19 "Street hard"** — the same levers taken to the factory Alpina B3 data where the axes match, so in some cells v19 is *softer* than v18 (v18 had exceeded Alpina) while the target slip time is shorter. v19 is the recommended preset; v18 stays as the milder option and as a fallback.

### v18 против v19

**v18 «Sport daily»** — осторожный: равномерные множители к стоку (×0.85 целевое время, ×1.15 давления). **v19 «Street hard»** — те же рычаги, доведённые до заводских данных Alpina B3 там, где совпадают оси; поэтому в части ячеек v19 *мягче* v18 (v18 превышал Alpina), а целевое время скольжения короче. Рекомендуемый пресет — v19; v18 остаётся как более мягкий вариант и как откат.
