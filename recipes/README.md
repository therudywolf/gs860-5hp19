# Recipes / Рецепты

**[English](#english) | [Русский](#русский)**

<a name="english"></a>
## English

A recipe is a JSON diff between a factory calibration and a build (schema `gs860-recipe/2`, the older `/1` is still accepted, format described in `docs/en/08-recipes-and-presets.md`). It contains addresses, table formats, **both axes**, old and new data and comments. It never contains a firmware dump or the checksum bytes: `apply_recipe.py` computes those (`docs/en/07` §6). Since 07.10.2026 recipes exist for GS8.60.0 19x0 (256 KB) and GS8.60.4 20C0 (512 KB).

### Presets of document 14 (07.10.2026)

Built by `tools/egs_patch.py recipe` from the patches of document 13 for the reference engine of each platform; `built_with` in each file names the chain and the engine limits. For another engine build the preset on your dump instead: `egs_patch.py preset NAME dump.bin -o out.bin --spark RPM --cut RPM` (`docs/en/14-presets.md`).

| File | Base calibration | Reference engine | Result |
|---|---|---|---|
| `gs8600_19x0_sport_daily.json` | GS8.60.0 `B22K4_0419C0KA20` (E39 2.5) | M52TUB25, spark 6496, cut 6592 | full `d3fda1b5…`, partial `af1b7003…`, 268 bytes |
| `gs8604_20c0_sport_daily.json` | GS8.60.4 20C0 `B223K_0520C06440` (the Alpina B3S file) | M54B30, spark 6528, cut 6720 | full `2a7701dd…`, 294 bytes |
| `gs8604_20c0_street_hard.json` | the same | the same | full `73039a98…`, 332 bytes |
| `gs8604_20c0_track_hard.json` | the same | the same | full `166de54b…`, 382 bytes |

`street-hard` and `track-hard` for 19x0 change program code (`tcc-first`, `docs/en/13` §1) and therefore exist only as `egs_patch.py preset`, not as recipes. Status: not road-tested as whole presets; the 19x0 counterparts of their patches run on the reference E39 (`docs/en/14` §5).

```
python3 tools/apply_recipe.py recipes/gs8604_20c0_sport_daily.json my_20c0.bin -o build.bin
python3 tools/egs_tables.py verify-shift build.bin --spark 6528 --cut 6720 --stock my_20c0.bin
```

### Legacy presets v18-v20 (19x0)

Not recommended for a new build: some of their edits rest on disproved readings, and `verify-shift` reports their manual upshift thresholds (`docs/en/08` §6). Kept for the record.

#### Status

**Not road-tested in their 23.09.2026 form.** On 25.09.2026 some edits turned out to rest on wrong readings (`docs/en/08` §6): the "TCC" groups (`tcc_thresholds_branch0`, `tcc_thresholds_branch1`, `tcc_scalars`) change AGS, the adaptive program selection, not the converter lockup, and do not give the earlier lockup they were made for. The group `torque_reduction` changes the reference slip of the TCC regulator, its effect on the clutch is not checked. The manual upshift thresholds 58 / 106 / 151 / 212 are unsafe with a locked converter. In v20 the f24 edit acts in every mode, D included. The recipe data is unchanged and will be revised separately. Each recipe and its annotations carry this note in `status`, and `apply_recipe.py` prints it.

**23.09.2026.** All three presets were revised: the shift matrices hold output shaft rpm / 32, not km/h (`docs/en/02` §3), so the 16.09 sport shift points were never reached at full throttle and the box hung at the limiter. The manual programs had no protection on the overrun and a kickdown landing above the spark cut. The shift points were recomputed by `egs_tables.py verify-shift --spark 6656 --cut 6784 --fix`, hydraulics and TCC are as built. The 16.09 result hashes are kept in each recipe under `history`.

#### Files

| File | What |
|---|---|
| `wolf4x_v18_sport_daily.json` | full diff of the WOLF4X v18 "Sport daily (8HP-like)" preset against the stock calibration it was built from. 43 tables + 3 byte blocks, 1375 bytes with the checksum. Result full `14e15185…`, partial `e50bdaec…` |
| `wolf4x_v18_sport_daily.annotations.json` | groups, names, comments and status used by `make_recipe.py` to build the recipe above (kept so the recipe can be regenerated) |
| `wolf4x_v19_street_hard.json` | WOLF4X v19 "Street hard", v18 taken to the factory Alpina B3 level: shorter target slip time at high torque, on-coming/off-going pressures copied cell by cell from Alpina where the axes match, sport holds a gear longer at part throttle, "TCC stages 3–4 from 30–50 % pedal in S/M" (AGS in fact, see Status). 45 tables + 3 byte blocks, 1238 bytes. Result full `3b5c2cab…`, partial `6b740fc5…` |
| `wolf4x_v19_street_hard.annotations.json` | annotations for the recipe above |
| `wolf4x_v20_track_hard.json` | WOLF4X v20 "Track hard", v19 with a deliberately harder shift in the cells only Sport/Manual reach: shorter target slip time, raised slip-pressure ceiling f24, higher on-coming pressure, stock torque request at 3000 rpm, "TCC stages 3–4 earlier in S/M" (AGS in fact, see Status). 47 tables + 7 byte blocks, 1244 bytes. Result full `1106e3eb…`, partial `faad4369…` |
| `wolf4x_v20_track_hard.annotations.json` | annotations for the recipe above |

#### Base

| | |
|---|---|
| ECU / software | Bosch GS8.60.0, 256 KB image, program 19C0/19D0 (code SHA-256 `e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546`) |
| Stock calibration | label `B22K4_0419C0KA20` (E39 2.5, stock final drive); SHA-256 of window 0x8000–0x10000 `d3c2c3fdffb943f5bd848f672c6d3750a79986167c59c72dac367d386cbbdf51` |
| Built for | 2.5 l M52TU (M52TUB25) with the fuel cut at 6784 rpm and the spark cut from about 6656; for another limiter run `egs_tables.py verify-shift` (`docs/en/08` §4). The final drive and tyres do not matter for the shift rpm |
| Result (v18) | full `14e1518567722bfe53dda79d04e9fcd88d865643095f94c5656423647fe42a3a`, partial `e50bdaec1c27852ebebec3e3de44e9785f43d3a9fa80020b4d7096c9013767b7`, calibration checksum `0xEA30` |

#### How to apply

```
python3 tools/egs_tables.py info my_dump.bin
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
python3 tools/gs860_crc.py check build.bin build_partial32k.bin
python3 tools/egs_tables.py verify-shift build.bin --spark 6656 --cut 6784 --stock my_dump.bin
```

`apply_recipe.py` stops if the code hash differs (different software), if the loader or program checksum of the input does not match (damaged read), if any table axis differs (different calibration, do not force), and warns and stops if old values differ (`--force` to override, read `docs/en/08` §5 first). It recomputes the calibration checksum and writes `build.bin` (256K), `build_partial32k.bin` (32K) and `build.log`. Flash the partial, then Reset Adaptation (`docs/en/07`).

#### v17 to v18

v17 raised `0x8EEA` from 7000 to 7300 believing it to be a turbine over-speed limit. Disassembly proves the constant is a supply-voltage threshold in mV (`docs/en/05` §1). v18 is v17 with that byte pair back at stock, nothing else differs. Do not use v17.

#### v18 vs v19

**v18 "Sport daily"** is conservative: uniform multipliers on top of stock (×0.85 target slip time, ×1.15 pressures). **v19 "Street hard"** takes the same levers to the factory Alpina B3 data where the axes match, so in some cells v19 is *softer* than v18 (v18 had exceeded Alpina) while the target slip time is shorter. Until the presets are revised against the 25.09 findings (see Status), none of them is recommended: v19 was the recommended preset before that, v18 the milder fallback.

### Building your own

```
python3 tools/make_recipe.py stock.bin tuned.bin -o recipes/my_recipe.json -a my_annotations.json
```

`make_recipe.py` refuses when the tune changes any table axis or any byte outside 0x8000–0x10000, and leaves the checksum bytes out. Annotate every changed table (group, name, comment in EN and RU), unannotated recipes are not accepted into the repository (see CONTRIBUTING). If something in the preset is known to be wrong or unchecked, say so in `meta.status` of the annotations. Before a pull request run `python3 tests/test_tools.py` with `GS860_STOCK` set and `egs_tables.py verify-shift` for the engine the recipe is meant for.

<a name="русский"></a>
## Русский

Рецепт это JSON-diff между заводской калибровкой и сборкой (схема `gs860-recipe/2`, старая `/1` тоже принимается, формат описан в `docs/ru/08-recipes-and-presets.md`). В нём адреса, форматы таблиц, **обе оси**, старые и новые данные и комментарии. Дампа прошивки и байтов суммы в нём нет никогда: их считает `apply_recipe.py` (`docs/ru/07` §6). С 07.10.2026 рецепты есть для GS8.60.0 19x0 (256 КБ) и GS8.60.4 20C0 (512 КБ).

### Пресеты документа 14 (07.10.2026)

Собраны командой `tools/egs_patch.py recipe` из патчей документа 13 под эталонный мотор каждой платформы; в поле `built_with` каждого файла цепочка и обороты мотора. Под другой мотор соберите пресет на своём дампе: `egs_patch.py preset ИМЯ dump.bin -o out.bin --spark ОБ/МИН --cut ОБ/МИН` (`docs/ru/14-presets.md`).

| Файл | Базовая калибровка | Эталонный мотор | Результат |
|---|---|---|---|
| `gs8600_19x0_sport_daily.json` | GS8.60.0 `B22K4_0419C0KA20` (E39 2.5) | M52TUB25, искра 6496, отсечка 6592 | full `d3fda1b5…`, partial `af1b7003…`, 268 байт |
| `gs8604_20c0_sport_daily.json` | GS8.60.4 20C0 `B223K_0520C06440` (файл Alpina B3S) | M54B30, искра 6528, отсечка 6720 | full `2a7701dd…`, 294 байта |
| `gs8604_20c0_street_hard.json` | та же | тот же | full `73039a98…`, 332 байта |
| `gs8604_20c0_track_hard.json` | та же | тот же | full `166de54b…`, 382 байта |

`street-hard` и `track-hard` для 19x0 меняют код программы (`tcc-first`, `docs/ru/13` §1), поэтому есть только как `egs_patch.py preset`, рецептами их нет. Статус: целиком на машине не проверены; аналоги их патчей на 19x0 ездят на референсной E39 (`docs/ru/14` §5).

```
python3 tools/apply_recipe.py recipes/gs8604_20c0_sport_daily.json my_20c0.bin -o build.bin
python3 tools/egs_tables.py verify-shift build.bin --spark 6528 --cut 6720 --stock my_20c0.bin
```

### Прежние пресеты v18-v20 (19x0)

Для новой сборки не рекомендуются: часть их правок сделана по опровергнутым прочтениям, а `verify-shift` отмечает их ручные пороги вверх (`docs/ru/08` §6). Оставлены для истории.

#### Статус

**В виде от 23.09.2026 на машине не проверены.** 25.09.2026 выяснилось, что часть правок сделана по неверным прочтениям (`docs/ru/08` §6): группы «ГДТ» (`tcc_thresholds_branch0`, `tcc_thresholds_branch1`, `tcc_scalars`) меняют AGS, адаптивный выбор программы, а не блокировку гидротрансформатора, и раннего замыкания, ради которого делались, не дают. Группа `torque_reduction` меняет опорное скольжение регулятора ГДТ, как это действует на муфту, не проверено. Ручные пороги вверх 58 / 106 / 151 / 212 небезопасны при замкнутой ГДТ. В v20 правка f24 действует во всех режимах, включая D. Данные рецептов не менялись и будут пересмотрены отдельно. Эта пометка есть в каждом рецепте и его аннотациях в поле `status`, `apply_recipe.py` её печатает.

**23.09.2026.** Все три пресета исправлены: матрицы переключения хранят обороты выходного вала / 32, а не км/ч (`docs/ru/02` §3), поэтому точки спорта 16.09 в пол были недостижимы и коробка висела в отсечке. У ручных программ не было защиты на накате, и кикдаун приводил мотор выше искры. Точки пересчитаны командой `egs_tables.py verify-shift --spark 6656 --cut 6784 --fix`, гидравлика и ГДТ как собраны. Хэши результата от 16.09 сохранены в каждом рецепте в поле `history`.

#### Файлы

| Файл | Что |
|---|---|
| `wolf4x_v18_sport_daily.json` | полный diff пресета WOLF4X v18 «Sport daily (8HP-like)» относительно стоковой калибровки, на которой он собран. 43 таблицы + 3 блока байт, 1375 байт с суммой. Результат full `14e15185…`, partial `e50bdaec…` |
| `wolf4x_v18_sport_daily.annotations.json` | группы, имена, комментарии и статус, по которым `make_recipe.py` построил рецепт выше (хранится, чтобы рецепт можно было перегенерировать) |
| `wolf4x_v19_street_hard.json` | WOLF4X v19 «Street hard», v18, доведённый до заводского уровня Alpina B3: короче целевое время скольжения на высоком моменте, давления включаемого/выключаемого поячеечно из Alpina там, где совпадают оси, спорт дольше держит передачу на частичном газе, «ГДТ в S/M выходит на 3–4 ступень с 30–50 % педали» (на деле AGS, см. «Статус»). 45 таблиц + 3 блока байт, 1238 байт. Результат full `3b5c2cab…`, partial `6b740fc5…` |
| `wolf4x_v19_street_hard.annotations.json` | аннотации к рецепту выше |
| `wolf4x_v20_track_hard.json` | WOLF4X v20 «Track hard», v19 с осознанно более жёстким переключением в ячейках, куда попадают только Sport/Manual: короче целевое время скольжения, выше потолок давления f24, выше давление включаемого, запрос момента на 3000 об/мин к стоку, «ступени 3–4 ГДТ в S/M раньше» (на деле AGS, см. «Статус»). 47 таблиц + 7 блоков байт, 1244 байта. Результат full `1106e3eb…`, partial `faad4369…` |
| `wolf4x_v20_track_hard.annotations.json` | аннотации к рецепту выше |

#### База

| | |
|---|---|
| Блок / ПО | Bosch GS8.60.0, образ 256 КБ, программа 19C0/19D0 (SHA-256 кода `e151733e1cc1a779975680a48722e26ac43c5b3674150576a38fb0b9e57c2546`) |
| Стоковая калибровка | метка `B22K4_0419C0KA20` (E39 2.5, стоковая главная пара); SHA-256 окна 0x8000–0x10000 `d3c2c3fdffb943f5bd848f672c6d3750a79986167c59c72dac367d386cbbdf51` |
| Под что собран | 2.5 л M52TU (M52TUB25), топливная отсечка 6784, искра примерно с 6656; под другой ограничитель запустить `egs_tables.py verify-shift` (`docs/ru/08` §4). Главная пара и колёса на обороты переключения не влияют |
| Результат (v18) | full `14e1518567722bfe53dda79d04e9fcd88d865643095f94c5656423647fe42a3a`, partial `e50bdaec1c27852ebebec3e3de44e9785f43d3a9fa80020b4d7096c9013767b7`, сумма калибровки `0xEA30` |

#### Как применить

```
python3 tools/egs_tables.py info my_dump.bin
python3 tools/apply_recipe.py recipes/wolf4x_v18_sport_daily.json my_dump.bin -o build.bin
python3 tools/gs860_crc.py check build.bin build_partial32k.bin
python3 tools/egs_tables.py verify-shift build.bin --spark 6656 --cut 6784 --stock my_dump.bin
```

`apply_recipe.py` останавливается, если не совпал хэш кода (другое ПО), если у входа не сходится сумма загрузчика или программы (дамп снят с ошибкой), если отличается любая ось таблицы (другая калибровка, не форсировать), и предупреждает и останавливается, если не совпали старые значения (`--force` только после чтения `docs/ru/08` §5). Пересчитывает сумму калибровки и пишет `build.bin` (256K), `build_partial32k.bin` (32K) и `build.log`. Шить партиал, после него Reset Adaptation (`docs/ru/07`).

#### От v17 к v18

В v17 `0x8EEA` был поднят с 7000 до 7300 в предположении, что это порог разноса турбины. Дизассемблер доказывает, что константа это порог напряжения питания в мВ (`docs/ru/05` §1). v18 = v17 с этой парой байт, возвращённой к стоку, больше ничего не отличается. v17 не использовать.

#### v18 против v19

**v18 «Sport daily»** осторожный: равномерные множители к стоку (×0.85 целевое время, ×1.15 давления). **v19 «Street hard»** доводит те же рычаги до заводских данных Alpina B3 там, где совпадают оси, поэтому в части ячеек v19 *мягче* v18 (v18 превышал Alpina), а целевое время скольжения короче. Пока пресеты не пересмотрены по находкам 25.09 (см. «Статус»), ни один не рекомендуется: до них рекомендуемым был v19, v18 более мягкий откат.

### Свой рецепт

```
python3 tools/make_recipe.py stock.bin tuned.bin -o recipes/my_recipe.json -a my_annotations.json
```

`make_recipe.py` откажется, если тюн меняет ось любой таблицы или байты вне 0x8000–0x10000, а байты суммы в рецепт не включает. Аннотируйте каждую изменённую таблицу (группа, имя, комментарий EN и RU), рецепты без аннотаций в репозиторий не принимаются (см. CONTRIBUTING). Если что-то в пресете известно как неверное или не проверенное, напишите это в `meta.status` аннотаций. Перед pull request запустите `python3 tests/test_tools.py` с `GS860_STOCK` и `egs_tables.py verify-shift` под мотор, для которого рецепт.
