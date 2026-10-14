# Progress files - formats

```
languages/
  script/                (optional helpers: vocab.py, tts.py, stt.py, voice-to-text/ with whisper.cpp)
languages/<language>/
  course/                (the language's grammar course - shareable; see course.md)
  course-progress.md     (this learner's position in the course)
  progress.md
  vocabulary.json        (managed by scripts/vocab.py)
  mistakes.md
  sessions/YYYY-MM-DD_<topic-slug>.md
  sessions/audio/        (listening audio, optional)
```

Folder and slug names: lowercase English, hyphens (`french`, `missed-train`); session files are `YYYY-MM-DD_<topic-slug>.md` (underscore after the date). Dates: ISO `YYYY-MM-DD` in the user's timezone.

Edit files in place (update the relevant lines/sections); never regenerate a whole file from memory - you might drop history. Keep the headings below exactly, so the next session can find things quickly.

## progress.md

```markdown
# French - progress

- **Level:** A1 (since 2026-09-30, placement 9/15)
- **Explanations in:** English
- **Started:** 2026-09-30
- **Current topic:** The car (la voiture) - `sessions/2026-09-30_car.md`
- **Current step:** 4/7 Translation
- **Paused at:** -
- **Preferences:** likes short readings; asked for "harder" on 2026-10-02
- **Workbook:** https://claude.ai/artifact/... (the page where exercises are answered; see workbook.md)

## Roadmap

| # | Topic | Grammar | Status |
|---|---|---|---|
| 1 | The car (la voiture) | possession with de; noun gender | current |
| 2 | At the café | partitive du/de la/des; je voudrais | next |
| 3 | My day | reflexive verbs; telling the time | - |

## Topic history

| Date | Topic | Level | Exam | Result |
|---|---|---|---|---|
| 2026-09-30 | The car (la voiture) | A1 | 17/20 (85%) | pass |

## Reviews

| Date | Words | Score |
|---|---|---|
| 2026-10-01 | 10 | 8/10 |

## Level history

| Date | Level | Why |
|---|---|---|
| 2026-09-30 | A1 | placement 9/15 |
```

Roadmap status values: one or two words in the learner's explanation language - `done`, `current`, `next`, `-` (Russian: `пройдено`, `сейчас`, `дальше`, `-`); details go into the Grammar cell. The Topic history's Exam cell is the short score ("14/20 (70%)"), the Result cell the verdict and per-part scores - also in the explanation language. These rows are shown on the workbook's Progress page. Re-plan the remaining rows freely (new interests, level change), but keep finished rows.

`Current step` values: `Flashcards`, `1/7 Vocabulary`, `2/7 Grammar`, `3/7 Reading`, `4/7 Translation`, `5/7 Writing`, `6/7 Listening`, `7/7 Speaking`, `Exam`, or `-` when no topic is open. Skipped steps: note them in the session file ("skipped by learner").

## vocabulary.json

Managed by `scripts/vocab.py`. Shape:

```json
{
  "language": "french",
  "explanation_language": "English",
  "created": "2026-09-30",
  "words": [
    {
      "word": "la voiture",
      "translation": "car",
      "gender": "f",
      "pos": "noun",
      "example": "La voiture de mon père est rouge.",
      "example_translation": "My father's car is red.",
      "notes": null,
      "topic": "car",
      "added": "2026-09-30",
      "box": 1,
      "next_review": "2026-10-01",
      "last_reviewed": null,
      "right": 0,
      "wrong": 0
    }
  ]
}
```

- `word`: nouns with their article (la voiture, el coche, das Auto); verbs in the infinitive; phrases as taught.
- `gender`: `m` / `f` / `n` / `null`. `pos`: noun, verb, adj, adv, phrase, ...
- `translation` is in the explanation language.
- Leitner boxes 1-5; days to next review after landing in a box: 1, 3, 7, 14, 30. Right → box+1 (max 5). Wrong → box 1, due tomorrow.
- `topic` = the topic slug. For words met outside a lesson (e.g. in a correction), use `misc`.

If you must edit it by hand (no Python), keep the same fields and apply exactly the box rules above.

## mistakes.md

Grouped by rule, most frequent first. Update the count and add a dated example each time; mark `status: fixed?` after the learner gets it right several times in a row.

```markdown
# French - recurring mistakes

## à + le → au, de + le → du (contraction)
- count: 3 · last: 2026-10-02 · status: active
- 2026-09-30: "à le travail" → "au travail"
- 2026-10-02: "de le bus" → "du bus"

## Noun gender with possessives (mon/ma)
- count: 2 · last: 2026-09-30 · status: active
- 2026-09-30: "mon voiture" → "ma voiture"
```

Log a mistake the first time you see it in a writing/speaking/translation answer too (count: 1); that way the second occurrence is recognisable as recurring. Don't log pure typos.

## sessions/YYYY-MM-DD_<topic-slug>.md

One file per topic (if a topic spans several days, keep the original file and add a dated "Continued YYYY-MM-DD" line). Append each section as the exercise finishes:

```markdown
# The car (la voiture) - 2026-09-30 - A1

## 1. Vocabulary
| Word | Translation | Example |
|---|---|---|
| la voiture (f) | car | La voiture est rouge. |

## 2. Grammar
- de for belonging: la porte de la voiture ...

## 3. Reading
<text>

## 4. Translation
1. EN: My car is red. · Learner: "Mon voiture est rouge." · Correct: "Ma voiture est rouge." · Note: voiture is feminine → ma.

## 5. Writing
Task: ...
Learner's text: ...
Corrected: ...
Changes: 1. ... 2. ...

## 6. Listening
Source/audio: sessions/audio/2026-09-30_car.mp3 (espeak TTS)
Answers: 4/5 - Q3 wrong (said 18h, audio said 19h)
Transcript: (added after answers)

## 7. Speaking
Task: ... · Transcript: ... · Corrections: ... · Pronunciation notes: ...

## Exam - 17/20 (85%) - pass
| # | Type | Item | Learner | Correct? |
|---|---|---|---|---|
Wrong items → review: le volant, la roue
```
