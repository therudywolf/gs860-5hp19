# Security and dangerous errors / Безопасность и опасные ошибки

**[English](#english) | [Русский](#русский)**

<a name="english"></a>
## English

This repository describes a safety-relevant control unit. A wrong address, a table read the wrong way or a patch that writes outside its place can damage a gearbox, drop the unit into limp mode or leave a car immobile.

**If you find such an error, report it privately first**, not in a public issue: e-mail [alonerudywolf@gmail.com](mailto:alonerudywolf@gmail.com) or Telegram [t.me/rudy_wolf](https://t.me/rudy_wolf). Say what, where (tool, patch, catalog entry, document and section) and the evidence: the instruction address, a table dump or a log. Once a fix is published, the report becomes a normal entry in `CHANGELOG.md` with your name if you want it there.

Never send a firmware dump, a VIN or a unit serial in public, and do not paste them into the report either unless a private exchange has been agreed.

The repository holds no firmware, no keys and no secrets; GitHub secret scanning with push protection is on.

<a name="русский"></a>
## Русский

Этот репозиторий описывает блок, отвечающий за безопасность. Неверный адрес, неправильно прочитанная таблица или патч, который пишет не туда, могут повредить коробку, отправить блок в аварийный режим или оставить машину без хода.

**Если нашли такую ошибку, сначала сообщите о ней лично**, а не в открытом issue: почта [alonerudywolf@gmail.com](mailto:alonerudywolf@gmail.com) или Telegram [t.me/rudy_wolf](https://t.me/rudy_wolf). Напишите, что и где (инструмент, патч, запись каталога, документ и раздел), и доказательство: адрес инструкции, распечатку таблицы или лог. Когда исправление опубликовано, сообщение становится обычной записью в `CHANGELOG.md`, с вашим именем, если хотите.

Никогда не отправляйте дамп прошивки, VIN или серийный номер блока публично и не вставляйте их в сообщение, пока не договорились о приватном обмене.

В репозитории нет прошивок, ключей и секретов; сканирование секретов GitHub с защитой при push включено.
