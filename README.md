# AI language tutor

A personal language tutor for Claude: structured lessons (words, grammar, reading, translation, writing, listening, speaking, role-play), a workbook page where the learner answers and Claude checks right away, spaced-repetition vocabulary, a grammar course from A0 to C1, and offline speech: natural voices for listening dialogues and transcription of voice messages.

Ниже по-русски.

## Что это

Навык (skill) для Claude, который ведёт уроки иностранного языка:

- урок по одной теме: слова → грамматика → чтение → перевод → письмо → аудирование → говорение → разговор с незнакомцем → карточки;
- **workbook** — страница в Claude, где ты отвечаешь, а Claude сразу проверяет и даёт мини-тест на свои ошибки;
- **курс грамматики** A0 → C1 (`french/course/`) — дорожная карта: каждый урок берёт следующий раздел;
- **озвучка без интернета**: диалоги «как в жизни» (Chatterbox, голоса носителей, фон кафе / метро / отеля…), слова и примеры (Supertonic);
- **расшифровка голосовых** (whisper.cpp) для заданий на говорение.

Прогресс хранится в обычных файлах в этой же папке, поэтому следующий урок в любом чате продолжает с того места, где ты остановился.

## Как устроена папка

Эта папка — одновременно **репозиторий** и **папка с твоими языками**. Клонируешь её один раз, подключаешь к Claude — и всё, что появится в процессе учёбы, остаётся у тебя, а в git не попадает.

```
skill/language-tutor/     сам навык: SKILL.md, references/, scripts/, assets/workbook.html
script/                   вспомогательные скрипты: vocab.py, tts.py, stt.py, ambience.py, проверки уроков
  text-to-voice/          озвучка: настройка, голоса Chatterbox, фоновые звуки (ambience/)
  voice-to-text/          расшифровка голосовых (whisper.cpp)
setup/                    скачивание моделей и сборка whisper
french/course/            курс французского A0 → C1 (syllabus.md + units/)
```

**Не попадает в git** (см. `.gitignore`, там всё закрыто по умолчанию): `progress.md`, `vocabulary.json`, `mistakes.md`, `course-progress.md`, `sessions/`, любое аудио уроков и голосовые, модели (~4 ГБ), собранный whisper, ключи API.

## Установка

1. **Склонируй** репозиторий туда, где будут жить твои языки:
   ```
   git clone https://github.com/vladislavshvarc/ai-language-tutor.git ~/Documents/Languages
   ```
2. **Скачай модели** (~4 ГБ, один раз; в Терминале Mac или Linux):
   ```
   cd ~/Documents/Languages && sh setup/download_models.sh
   ```
   Без Chatterbox (быстрые голоса и расшифровка, ~1 ГБ): `sh setup/download_models.sh fast`.
3. **Добавь навык в Claude.** Упакуй папку навыка и загрузи её в настройках Claude в разделе навыков (Skills):
   ```
   cd ~/Documents/Languages/skill && zip -r ../language-tutor.skill language-tutor
   ```
   В Claude Code вместо этого: `cp -R skill/language-tutor ~/.claude/skills/`.
4. **Подключи папку** `Languages` к задаче в приложении Claude (Cowork) и напиши, например: «Давай учить французский, объяснения на русском».
   В первом уроке Claude один раз поставит движки озвучки (`script/text-to-voice/setup_engines.sh all`) и соберёт whisper (`setup/build_whisper.sh`) — 2–5 минут. Всё ставится **внутрь этой папки** (`script/.env/`, ~1,7 ГБ, в git не попадает), поэтому в следующих сессиях ничего не устанавливается: скрипт за долю секунды отвечает `ready`.

Начать новый язык: просто попроси. Если курса для языка ещё нет, тутор создаст его в `<язык>/course/`. Чтобы курс попал в git, добавь в `.gitignore` три строки по образцу `french`.

## Обновление

```
git pull
```
Прогресс, слова и записи не затрагиваются — их нет в репозитории.

## Требования

- Приложение Claude с навыками (skills); для workbook — публикация артефактов.
- Для озвучки и расшифровки: ~5 ГБ на диске; генерация диалога Chatterbox на CPU — около 45 с на реплику.
- Без моделей тутор тоже работает: аудирование заменяется текстом «прочитай один раз», голосовые можно продиктовать текстом.

## Лицензии

Код и тексты навыка — от автора репозитория. Модели скачиваются с сайтов их авторов и в репозиторий не входят. Фоновые записи и образцы голосов распространяются по своим лицензиям (CC0, CC BY, CC BY-SA, CC BY-NC) — список и авторы в [THIRD_PARTY.md](THIRD_PARTY.md). Используй для личной учёбы.
