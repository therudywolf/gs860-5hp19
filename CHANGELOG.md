# Changelog

Newest first. Each entry: date and title, then **EN** and **RU** with the same facts.

## 2026-11-04: clean start

**EN**

- The repository starts here with one commit. What it holds: the reverse engineering of the Bosch GS8.60.0 (19C0 / 19D0) and GS8.60.4 (20C0) firmware in `docs/en` and `docs/ru` (documents 01-07 and 09-12), the catalogs `catalog/gs8600_19d0.json` (921 entries) and `catalog/gs8604_20c0.json` (1779 entries), the TunerPro XDF files generated from them, `tools/egs_tables.py` (scan, dump, compare, check shift points), `tools/gs860_crc.py` (check the three checksums), `tools/make_xdf.py` (check the catalogs, build the XDF), tests in `tests/test_tools.py`.
- New material is paused (README, "Status"); error reports are read and fixed.

**RU**

- Репозиторий начинается здесь одним коммитом. Что в нём: реверс прошивки Bosch GS8.60.0 (19C0 / 19D0) и GS8.60.4 (20C0) в `docs/en` и `docs/ru` (документы 01-07 и 09-12), каталоги `catalog/gs8600_19d0.json` (921 запись) и `catalog/gs8604_20c0.json` (1779 записей), собранные из них XDF для TunerPro, `tools/egs_tables.py` (скан, распечатка, сравнение, проверка точек переключения), `tools/gs860_crc.py` (проверка трёх контрольных сумм), `tools/make_xdf.py` (проверка каталогов, сборка XDF), тесты в `tests/test_tools.py`.
- Новое наполнение на паузе (README, «Статус»); сообщения об ошибках читаю и исправляю.
