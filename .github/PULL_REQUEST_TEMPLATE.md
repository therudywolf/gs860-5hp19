<!-- EN | RU. Do not attach dumps, do not paste VIN or unit serials. / Дамп не прикладывать, VIN и серийные номера не вставлять. -->

**Unit and software / Блок и ПО:** GS8.60.0 19x0 (256K) | GS8.60.4 20C0 (512K), calibration label / метка калибровки:

**What was changed / Что меняли:**
<!-- docs, catalog, XDF, tools, recipes, addresses and tables / документы, каталог, XDF, инструменты, рецепты, адреса и таблицы -->

**Evidence / На чём основано:**
<!-- instruction address and what it compares with, a table dump, a log / адрес инструкции и с чем сравнивается, распечатка таблицы, лог -->

**How it was checked / Как проверено:**
- [ ] `python3 tests/test_tools.py` (and with `GS860_STOCK` / `GS8604_STOCK` if tools, catalog, XDF or recipes changed / и с `GS860_STOCK` / `GS8604_STOCK`, если менялись инструменты, каталог, XDF или рецепты)
- [ ] `python3 tools/make_xdf.py check catalog/<catalog>.json`, XDF rebuilt from the catalog / XDF пересобран из каталога
- [ ] EN and RU versions say the same / EN и RU версии совпадают
- [ ] on a car: what was flashed and what the log shows / на машине: что шили и что показал лог

**Dumps / Дампы:** none attached, no VIN or serial in text, logs or file names / не приложены, VIN и серийных номеров нет ни в тексте, ни в логах, ни в именах файлов.
