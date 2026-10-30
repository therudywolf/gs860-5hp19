# Changelog

Newest first. Each entry: date and title, then **EN** and **RU** with the same facts. Older entries are not rewritten: what turned out wrong is corrected in a newer entry.

## 2026-10-30 (2): what the 20C0 frames show in logs

**EN**

- Document 11 §16: two facts from logs of a running E46: bits 5–7 of byte 2 of the EGS1 frame are no reliable "S" flag (about 7 % of the frames in S and in D alike), and the torque reduction request comes 0.15–0.5 s before the gear number changes.

**RU**

- Документ 11 §16: два факта из логов живой E46: биты 5–7 байта 2 кадра EGS1 — не надёжный признак «S» (около 7 % кадров и в S, и в D), а запрос снижения момента приходит на 0,15–0,5 с раньше смены номера передачи.

## 2026-10-30: reverse is public, the product is not

**EN**

- Documents 13 (the edits as a description) and 14 (the engine link), published on 29.10, are withdrawn, with the CC BY-NC-SA licence that covered document 14 and the remaining notes of the author's tuning method in documents 03, 10 and 12. The repository is the reverse of the two programs, the catalogs and XDF, and the checking tools; what the author builds on them is paid work (README, "Custom work").

**RU**

- Документы 13 (правки описанием) и 14 (связь с мотором), опубликованные 29.10, отозваны вместе с лицензией CC BY-NC-SA, которая покрывала документ 14, и остатками методики тюна автора в документах 03, 10 и 12. Репозиторий — реверс двух программ, каталоги и XDF, проверялки; то, что автор строит на них, — платная работа (README, «Работа на заказ»).

## 2026-10-29: patches, presets and recipes withdrawn

**EN**

- The repository is the reverse engineering, the XDF definitions and the checking tools; ready-made builds are not part of it any more. Removed: `tools/egs_patch.py`, `tools/apply_recipe.py`, `tools/make_recipe.py`, `recipes/`, documents 08, 13 and 14 (EN and RU) and their tests. The other documents, README, CONTRIBUTING, NOTICE, CITATION, the templates and both catalogs no longer refer to them; the notes on earlier tunes in the catalogs are gone, the XDF files are rebuilt from the catalogs. Older entries below are left as they were; the git history keeps the old files. The releases 2026.10.07, 2026.10.14, 2026.10.28 and 2026.10.28.2 are withdrawn with their tags: they shipped the old tree. Release 2026.10.29 is this tree.
- What stays: the catalogs and XDF of both programs, documents 01–07 and 09–12, `egs_tables.py` (scan, dump, shift, diff, verify-shift), `gs860_crc.py`, `make_xdf.py` and the tests on the stock images.

**RU**

- Репозиторий — это реверс, определения XDF и проверялки; готовых сборок в нём больше нет. Убраны `tools/egs_patch.py`, `tools/apply_recipe.py`, `tools/make_recipe.py`, `recipes/`, документы 08, 13 и 14 (EN и RU) и их тесты. Остальные документы, README, CONTRIBUTING, NOTICE, CITATION, шаблоны и оба каталога на них больше не ссылаются; заметки о ранних тюнах из каталогов убраны, XDF пересобраны из каталогов. Старые записи ниже оставлены как были; история git хранит старые файлы. Релизы 2026.10.07, 2026.10.14, 2026.10.28 и 2026.10.28.2 сняты вместе с тегами: они отдавали старое дерево. Релиз 2026.10.29 — это дерево.
- Остаётся: каталоги и XDF обеих программ, документы 01–07 и 09–12, `egs_tables.py` (scan, dump, shift, diff, verify-shift), `gs860_crc.py`, `make_xdf.py` и тесты на заводских образах.

## 2026-10-28 (5): release 2026.10.28.2

**EN**

- Second release of the day: entries (3) and (4), the English axis labels. Apart from `labels_en` (`make_xdf.py`, both catalogs, the English 20C0 XDF) nothing changes against 2026.10.28; the Russian XDF files are the same.
- README: what is new on 28.10 names the English axis labels, the credits to Jason King name his `labels_en`. `CITATION.cff` carries the release version.

**RU**

- Второй релиз за день: записи (3) и (4), английские подписи осей. Кроме `labels_en` (`make_xdf.py`, оба каталога, английский XDF 20C0) против 2026.10.28 ничего не меняется; русские XDF те же.
- README: в «Что нового» на 28.10 названы английские подписи осей, в благодарности Jason King — его `labels_en`. В `CITATION.cff` номер релиза.

## 2026-10-28 (4): English axis labels in both catalogs

**EN**

- The English 20C0 XDF showed 132 Russian axis labels on 36 axes. The 20C0 generator now writes `labels_en` for them: the gear records (`down to`, `up to`, `down column`, `up column`, `down program`, `up program`), the groups of the second TCC check (`g1 t0` ... `g2 t2`), `sel. 1-4`, `level 1-4`, `branch 0-1` and the one-label axes (`threshold`, `points`, `ticks`, `offset`, `value`, `mask`, `pedal`, `pressure units`). The English XDF has no Russian label left; apart from `labels_en` the regenerated catalog is byte for byte the previous one.
- 19D0: the 13 axes with Russian labels get `labels_en` (`step 1-2`, `step 2-3`, `step 3-4` of the AGS pedal thresholds, `ticks`, `mask`, `pedal`).
- CONTRIBUTING: `labels_en` joins the list of English fields of the 19D0 catalog. Tests: without `labels_en` the English file carries the labels of the Russian one (before, the test compared a render with itself); every Russian axis label of 20C0 has an English one and the English XDF shows none. The Russian XDF files, the addresses and the data do not change.

**RU**

- Английский XDF 20C0 показывал 132 русские подписи на 36 осях. Генератор 20C0 теперь пишет для них `labels_en`: записи передач (`down to`, `up to`, `down column`, `up column`, `down program`, `up program`), группы второй проверки ГДТ (`g1 t0` ... `g2 t2`), `sel. 1-4`, `level 1-4`, `branch 0-1` и оси с одной подписью (`threshold`, `points`, `ticks`, `offset`, `value`, `mask`, `pedal`, `pressure units`). Русских подписей в английском XDF не осталось; кроме `labels_en`, пересобранный каталог байт в байт прежний.
- 19D0: 13 осей с русскими подписями получили `labels_en` (`step 1-2`, `step 2-3`, `step 3-4` у порогов педали AGS, `ticks`, `mask`, `pedal`).
- CONTRIBUTING: `labels_en` вошло в список английских полей каталога 19D0. Тесты: без `labels_en` английский файл несёт подписи русского (раньше тест сравнивал сборку саму с собой); у каждой русской подписи осей 20C0 есть английская, и английский XDF не показывает ни одной русской. Русские XDF, адреса и данные не меняются.

## 2026-10-28 (3): optional English axis labels (KingAiCodeForge)

**EN**

- Optional `labels_en` on table X/Y axes is selected only by the English XDF renderer. Without it, original `labels` are used; Russian output is unchanged.
- `check` rejects translations without original labels, mismatched counts, empty/non-string labels and Cyrillic text. Tests cover 19D0 and 20C0, preserving addresses, equations and dimensions. No catalog, generated XDF or firmware changed.

**RU**

- Необязательное поле `labels_en` для осей X/Y используется только при создании английского XDF. Если поля нет, остаются исходные `labels`; русский XDF не меняется.
- Проверка `check` отклоняет переводы без исходных подписей, несовпадение количества, пустые или нестроковые подписи и кириллицу. Тесты охватывают 19D0 и 20C0 с сохранением адресов, формул и размеров. Каталоги, готовые XDF и прошивки не менялись.

## 2026-10-28 (2): repository guard, `SECURITY.md`, credits; release 2026.10.28

**EN**

- Audit before the release: the tree, the whole git history, the pull requests and the release notes hold no firmware, no VIN, no unit serials, no private paths and no names of car owners. No webhooks, deploy keys or Actions secrets; secret scanning with push protection is on.
- `test_nothing_private_in_the_tree`: no firmware images or dumps in any form (by extension and by the 32K / 256K / 512K image sizes), binary files only as pictures in `assets/`, nothing that looks like a VIN in any text file (62 tests). `.gitignore` also keeps archives (`*.zip`, `*.7z`, `*.rar`), WinOLS files and A2L out.
- `SECURITY.md`: a dangerous error (one that can damage a gearbox) is reported privately first; CONTRIBUTING and the issue template point to it.
- README: what is new on 28.10; credits to Jason King (KingAI) for the questions and cross-checks behind the 19D0 catalog v3.3 and the converter ratio.
- `CITATION.cff` carries the release version.

**RU**

- Проверка перед релизом: в дереве, во всей истории git, в pull request и в описаниях релизов нет прошивок, VIN, серийных номеров, приватных путей и имён владельцев машин. Нет вебхуков, ключей развёртывания и секретов Actions; сканирование секретов с защитой при push включено.
- `test_nothing_private_in_the_tree`: никаких образов прошивок и дампов ни в каком виде (по расширению и по размерам образов 32K / 256K / 512K), двоичные файлы только как картинки в `assets/`, ничего похожего на VIN ни в одном текстовом файле (62 теста). `.gitignore` теперь не пускает и архивы (`*.zip`, `*.7z`, `*.rar`), файлы WinOLS и A2L.
- `SECURITY.md`: об опасной ошибке (такой, что может повредить коробку) сначала сообщают лично; CONTRIBUTING и шаблон issue ссылаются на него.
- README: что нового на 28.10; благодарность Jason King (KingAI) за вопросы и сверки, стоящие за каталогом 19D0 v3.3 и коэффициентом ГДТ.
- В `CITATION.cff` номер релиза.

## 2026-10-28: licence with attribution, credit in every XDF

**EN**

- Code (`tools/`, `tests/`) moves from MIT to the **Apache License 2.0** with a [`NOTICE`](NOTICE) file: whoever redistributes the tools, or tools built on them, keeps the credit "rudywolf, https://github.com/therudywolf/gs860-5hp19". `LICENSE` holds the full text, GitHub recognises it now. Releases up to v2026.10.14 stay under MIT for those who downloaded them.
- Documents, catalogs and XDF stay under **CC BY-SA 4.0**; `LICENSE-docs` now holds the full legal code, and `catalog/` is named explicitly (`NOTICE`).
- Every XDF carries the licence and the credit at the end of its header description and the repository link in its author field (`tools/make_xdf.py`, `LICENCE_NOTE`); the four XDF files were regenerated, only their headers changed. `import` strips both again.
- `CITATION.cff` for "Cite this repository"; an SPDX line in every script; a test checks the licence files, the SPDX lines and the XDF headers (61 tests).

**RU**

- Код (`tools/`, `tests/`) переходит с MIT на **Apache License 2.0** с файлом [`NOTICE`](NOTICE): кто распространяет инструменты или сделанные на их основе, сохраняет указание «rudywolf, https://github.com/therudywolf/gs860-5hp19». В `LICENSE` полный текст, GitHub его теперь распознаёт. Релизы до v2026.10.14 для тех, кто их скачал, остаются под MIT.
- Документы, каталоги и XDF остаются под **CC BY-SA 4.0**; в `LICENSE-docs` теперь полный юридический текст, `catalog/` назван явно (`NOTICE`).
- Каждый XDF несёт лицензию и автора в конце описания заголовка и ссылку на репозиторий в поле автора (`tools/make_xdf.py`, `LICENCE_NOTE`); четыре XDF пересобраны, изменились только заголовки. `import` убирает и то и другое.
- `CITATION.cff` для кнопки «Cite this repository»; строка SPDX в каждом скрипте; тест проверяет файлы лицензий, строки SPDX и заголовки XDF (61 тест).

## 2026-09-16 to 2026-10-14: the reverse up to then (condensed on 30.10.2026)

**EN**

- 16.09: first public version: the 19D0 catalog and XDF, `egs_tables.py`, documents 01–10.
- 23.09: the three checksums found (CRC-16/XMODEM, routine `0x221C`, table `0x3EDA`, document 07); the shift-matrix unit corrected: output shaft rpm / 32, not km/h (document 02).
- 25.09: AGS separated from the TCC lockup, the program-to-matrix mapping, the turbine monitor; the documents corrected from the code.
- 27.09 to 01.10: GS8.60.4 20C0 covered: catalog, XDF in Russian and English, the tools, documents 11 and 12; the record field roles proven by the 20C0 code, all 20 record roots.
- 07.10 to 08.10: the 20C0 roles of D / S / M, warm-up and kick-down, stock against stock; 176 more table roles, AGS inactive in stock, read evidence for 19x0; the 22C0 described (document 12 §11); the 19x0 checks its sums in the background too.
- 13.10 to 14.10: the first road test on a 20C0 (the field note in document 13 §2); readers found for the 19D0 catalog, scanner objects remodelled, DS2 `0x0B` and `0x06` corrected (document 06); tests on every pull request, `main` protected.
- The entries of the same period about the patch tool, the presets and the recipes are withdrawn with them (29.10.2026) and remain in the git history.

**RU**

- 16.09: первая публичная версия: каталог и XDF 19D0, `egs_tables.py`, документы 01–10.
- 23.09: найдены три контрольные суммы (CRC-16/XMODEM, функция `0x221C`, таблица `0x3EDA`, документ 07); исправлена единица матриц переключения: обороты выходного вала / 32, не км/ч (документ 02).
- 25.09: AGS отделён от блокировки ГДТ, соответствие программ и матриц, монитор турбины; документы исправлены по коду.
- 27.09–01.10: покрыт GS8.60.4 20C0: каталог, XDF на русском и английском, инструменты, документы 11 и 12; роли полей записей доказаны кодом 20C0, все 20 корней записей.
- 07.10–08.10: роли D / S / M у 20C0, прогрев и кикдаун, сток против стока; ещё 176 ролей таблиц, AGS в стоке не активен, доказательства чтения для 19x0; описан 22C0 (документ 12 §11); 19x0 тоже проверяет суммы в фоне.
- 13.10–14.10: первый выезд на 20C0 (полевая заметка в документе 13 §2); найдены читатели каталога 19D0, объекты сканера переописаны, исправлены DS2 `0x0B` и `0x06` (документ 06); тесты на каждом pull request, `main` защищён.
- Записи того же периода о патч-инструменте, пресетах и рецептах сняты вместе с ними (29.10.2026) и остаются в истории git.
