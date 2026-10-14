# Flashcard decks - start and end of every session

Two decks per session:

| Deck | When | Words |
|---|---|---|
| **Review** | first section of the session | taught words from earlier sessions that are due: `vocab.py deck <dir>` (due words, topped up with the weakest ones to at least 6, max 12). Queued words - picked in the workbook or prepared but not studied yet - are never in it |
| **New words** | last section of the session | the words taught in this session's vocabulary section (incl. workbook-picked words taught today): `vocab.py teach`, then `vocab.py deck <dir> --added <today>` (or `--topic <slug>`) |

Each word appears as **2 cards in different modes** (so 6-12 words → 12-24 cards). Order the deck so the same word's two cards are not next to each other.

## Card modes

1. `translate` - the target-language word (with its article) → the learner types the meaning in their explanation language. Checked by comparing with the stored translation (all variants separated by `,` `;` `/` count); if it doesn't match exactly, the learner sees the answer and grades themselves (Wrong / Nearly right / Right) - synonyms are fine.
2. `sentence` - the meaning in the explanation language → the learner writes a short sentence in the target language using the word. Claude in the page judges it (right / nearly / wrong + corrected sentence + one-line note); without that, the learner compares with the example and self-grades.
3. `choice` - the meaning → pick the correct target-language form among 3-4 look-alikes. Build the distractors from **the learner's real error patterns** (mistakes.md, the page's drill history): wrong accent (le musèe), wrong gender/article (la musée), wrong ending (je prend), wrong look-alike word (près / prêt), a false friend. Always give `answer` and a one-line `why`.

Prefer `choice` for words connected to recurring mistakes, `sentence` for verbs and phrases, `translate` for nouns. A word the learner got wrong last time gets `choice` + `sentence`.

## Section shape (workbook)

```json
{"key": "cards-start", "kind": "flashcards", "short": "Карточки", "label": "Повторение слов", "title": "Слова прошлых уроков",
 "material": {"instructions": "one line in the explanation language"},
 "prompts": {"translate": "Переведи на русский", "sentence": "Составь короткое предложение по-французски", "choice": "Выбери правильное слово"},
 "cards": [
  {"id": "c1", "word": "la gare", "translation": "вокзал", "gender": "f", "example": "La gare est loin.", "example_translation": "Вокзал далеко.", "mode": "translate", "audio": "/_blob/<word clip>", "example_audio": "/_blob/<example clip>"},
  {"id": "c2", "word": "le musée", "translation": "музей", "mode": "choice", "options": ["le musée", "la musée", "le musèe", "le musé"], "answer": "le musée", "why": "musée - мужской род; é (accent aigu)"},
  {"id": "c3", "word": "prendre", "translation": "брать; садиться на (транспорт)", "mode": "sentence", "example": "Je prends le bus.", "example_translation": "Я сажусь на автобус."}
 ]}
```

The page shows a "learned / coming up" counter like a card stack: Right → learned; Nearly right / Wrong → the card goes to the next **round**: it comes back only after every other card of the current round (never right away or one card later - the learner wants a pause before a repeat), then the missed cards are shuffled into a new round after a short "Круг пройден" screen, until all are right. In chat do the same: collect misses and repeat them after the whole deck.

## Results and sync

The sub doc stores `cards` (per card: first grade, attempts, done) and `word_results` (per word: the worst first-try grade among its cards). On sync, feed `word_results` to `vocab.py grade` - it accepts `"right"`, `"nearly"` (same box, due tomorrow) and `"wrong"` (back to box 1). Grade each word once per deck; review and new-word decks on the same day count once per word (vocab.py never promotes a word twice in one day).

## Inline (no workbook)

Run the same deck in chat: one card per message for `translate` and `sentence`; `choice` cards can go 4 at a time through a tappable question tool. Keep the counter in your message ("✓ 5 learned · 7 coming up").

Audio: give every card `audio` (the word) and, when it has an example, `example_audio` - reuse the clips made for the vocabulary table (`/_blob/...`). The page shows ▶ next to the word in translate mode and after answering in the other modes (never before - the sound would give the answer away).
