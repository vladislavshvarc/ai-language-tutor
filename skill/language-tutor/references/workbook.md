# The workbook page (the whole lesson runs there)

The **workbook** is a published page (template: `assets/workbook.html`) where the learner works through a complete lesson without going back to the chat between sections:

1. **Material** - vocabulary table, reading text, audio, grammar explanation - then a **Continue** button.
2. **Test** - the material is hidden; answer fields; **Check my answers** asks Claude inside the page, which marks each item, gives red-pen corrections and a score.
3. **Mistake drill** - 3-5 multiple-choice questions generated from the exact errors just made plus the learner's recurring mistakes ("musèe / musée", "le / la pharmacie"). Checked instantly. Each drill question is an instruction in the explanation language plus ONE target-language sentence with ONE blank that every option fits (the page drops questions with two blanks). A question never contains or describes its own answer (not «un ___ (gâteau, с крышечкой над a)» but «un ___ (торт)») - the page also strips such hints; the same goes for every `choice` item you write (`lesson_check.py` flags it as ERROR).
Every section also has **Skip this section** (two taps to confirm); skipped sections stay open in the section bar and can be done later.
4. **Next section →** - and so on to the end-of-topic exam and the **role-play** conversation.

Any word the learner selects on the page can be added to their vocabulary (a "+ Add to vocabulary" bar appears; Claude fills in translation, gender and an example).

You, the tutor in chat, **prepare the lesson up front**, **sync results back to the files** afterwards, and answer questions. Use the workbook whenever this session can publish artifacts and read/write their database (ArtifactData, or `read_db`/`write_db`); otherwise run the lesson inline in chat.

## Finding or creating it

1. Look for `- **Workbook:** <url>` in any progress.md (one workbook serves all languages).
2. None: publish `assets/workbook.html` with `capabilities: {db: {}, sample: {}, assets: {}}` and icon `notebook`; add the Workbook line to every progress.md.
3. A workbook from an earlier conversation: read it once (Artifact `read`) before writing; republish the template to its `url` if the skill's `assets/workbook.html` is newer than the published page.

## One language for everything the learner reads

The page speaks the learner's **explanation language** (`lesson.explain_lang`, else `dash.explain_lang`, e.g. "Russian" or "ru"): every button, label, status and message (Skip this section, Next card, Grade it myself, learned / coming up, the Progress cards...) is translated - Russian is built in, any other language is translated once by Claude and cached in the learner's browser. The in-page checks (tests, flashcard sentences, role-play corrections and review, recap) are told to write every note, summary and drill question in that language only.

Everything **you** write into the database must follow the same rule - nothing in English, and nothing explained in the target language:
- `lesson`: section `label`, `short`, `title` of non-target-language parts, all `instructions`, explanations in `body`, `rubric` notes the learner may see in `reveal`, flashcard `prompts` (`{"translate": "Переведи на русский", "sentence": "Составь короткое предложение по-французски с этим словом", "choice": "Выбери правильный вариант"}`), card `why`, role-play `goal_text`, `next_hint`, `link.label`.
- `dash`: `label` (the language's name in the explanation language, e.g. "Французский"), roadmap `status` - **short** ("пройдено", "сейчас", "закрываю", "-"; details go into `grammar`), history `result` and `score` (short: "14/20 (70%)"; per-part details go into `result`), mistake `rule` and `example`, `topic`.
- Only target-language material stays in the target language: words, examples, texts, dialogues, the role-play character's lines.

## Database layout

| Doc | Written by | Content |
|---|---|---|
| `dash/<language>` | you | dashboard: level, explain_lang, topic, step, roadmap, history, vocab boxes, mistakes (from `vocab.py dash`) |
| `lesson/<language>` | you | the current lesson: all its sections (shape below) |
| `state/<language>` | page | where the learner is: `{lesson_id, index, phase}` |
| `sub/<language>--<lesson id>--<section key>` | page (or you) | answers, feedback, drill answers, role-play turns, `synced` flag |
| `words/<id>` | page | words the learner added: `{language, word, translation, gender, pos, example, example_translation, context, selected, source_language, needs_lookup?, added, synced}` - `word` is always in the target language: if the learner selected a word in their own language (e.g. «потом»), the page translates it first (`word: "puis"`, `source_language: "other"`); `needs_lookup: true` means Claude wasn't available - translate it yourself at sync |
| `sub/<language>--<lesson id>--finish` | page | the learner pressed **Finish - save the lesson**: `{kind: "finish", status: "requested", digest: [per-section status/score/mistakes], new_words, recap}` |
| `ex/<language>` | legacy | single exercise from older sessions; shown only when no `lesson/<language>` exists - don't write it any more |

`<language>` = the progress folder name (`french`). Pass `if_version` on every overwrite; if a write is refused because the version moved, re-read and merge - another chat may be working on the same workbook.

### `lesson/<language>`

```json
{
  "id": "fr-2026-10-02-food",
  "target_lang": "fr", "level": "A1", "explain_lang": "Russian",
  "topic": "Еда и кафе",
  "grammar": {"known": ["être и avoir", "частичный артикль du / de la (как фразы)"], "later": ["род и артикли le / la, un / une (G1)", "спряжение глаголов на -er (G3)", "вопросы (G4)"]},
  "next_hint": "markdown shown on the 'Lesson complete' screen",
  "sections": [
    {
      "key": "vocab", "short": "1 · Слова", "label": "Шаг 1/7 · Слова", "title": "Au café", "kind": "lesson",
      "material": {"instructions": "...", "body": "markdown: table of words with emoji", "audio_url": "/_blob/...", "link": {"url": "https://...", "label": "Открыть запись", "note": "..."}},
      "test": {"instructions": "...", "items": [ ... ], "rubric": "answer key + accepted variants (never shown)", "reveal": "markdown shown after checking (transcript, key)"}
    },
    {"key": "roleplay", "short": "Разговор", "label": "Разговор", "title": "Au comptoir", "kind": "roleplay",
     "material": {"instructions": "scenario + goal in the explanation language", "body": "useful phrases"},
     "roleplay": {"name": "Mme Morel", "theme": "act as ... (who, situation, what they want - one sentence)", "persona": "...", "scenario": "...",
                  "agenda": ["point 1 the character steers to", "point 2", "...", "goodbye"], "never_act_as": ["a waiter or any staff", "the learner"],
                  "goal": "...", "goal_text": "goal shown to the learner", "opening": "first line, in the target language", "focus": "words/grammar to bring in", "turns": 8}}
  ]
}
```

- **Items**: `text` (one line), `long` (writing, retelling), `point` (a task point with no answer field - speaking), `choice` (`options`; emoji options = picture questions), `upload` (optional voice recording: a Record/Stop button that records in the page with the microphone, plus a file picker and a drop zone, with playback; .m4a/.mp4/.webm are stored as assets - a Voice Memos .m4a is relabelled to the generic MP4 brand first, because the asset store rejects the M4A brand; other formats must come through chat). Every Claude call in the page has a time limit, and Restart / Finish in the role-play cancel a pending reply, so a request that never answers can't freeze the page. If the browser or the viewer's frame blocks the microphone, the page says so and falls back to the phone's recorder or a file.
- **Material** is shown first with a Continue button and is **hidden during the test**; it reappears after checking. Omit `material` for sections that are only a task (translation, writing). Put answer keys and transcripts in `rubric`/`reveal`, never in `material.body`.
- `kind: "flashcards"` for the decks (shape in flashcards.md: `cards` with `mode` translate / sentence / choice).
- `kind: "exam"` for the end-of-topic exam (15-20 items; material can hold the exam's listening clip). `kind: "roleplay"` for the conversation.
- `material.transcript`: markdown text of `material.audio_url`. It sits hidden under the player; a "Show the text" toggle appears only after the learner has listened to the recording to the end twice (counted in their browser). If they open it before the test, the page tells the in-page checker and saves `transcript_viewed: true` in the sub. Put the transcript here **and** in `test.reveal`.
- `material.videos`: `[{url, title, channel, start (seconds), note}]` - YouTube explanations shown as link cards above the body (YouTube can't be embedded in the page). Use them for the grammar section (course.md, "Videos").
- Body markdown: paragraphs, **bold**, *italic*, `code`, `- lists`, `> dialogue quotes`, `### headings`, `| tables |`, links `[text](https://…)` (open in a new tab) and audio buttons `[text](/_blob/<asset id>)` (play a short clip - phonetics examples, word pronunciation).
- Keep the lesson under ~200 KB (one doc).

### A normal lesson's sections

0. `cards-start` - `kind: "flashcards"`: review deck of earlier words (flashcards.md).
1. `vocab` - comes **before** grammar. Material: word table where the word AND the example are each their own audio button: `| 🥖 | [le pain](/_blob/<word clip>) | хлеб | [Du pain, s'il vous plaît.](/_blob/<example clip>) |`; test: 6-10 items both directions + 1-2 picture choices.
1a. `sounds` (only when a pronunciation unit is current) - its own short section, never inside grammar: one sound theme, ▶ examples, 4-6 listening/choice items; `label` "Звуки · P2", `short` "Звуки".
2. `grammar` - **one theme** (lesson-steps.md, "One theme per lesson"): the session's course unit or its next lesson part, right after the words (its examples use them) (course.md; read from `<language>/course/units/`): material = the unit's videos (`material.videos`, from its `## Videos`) + rules, table, examples, traps (▶ audio buttons `[mot](/_blob/<id>)` - the page draws the ▶ - **one clip per word or example**: `[du pain](/_blob/a) · [de la soupe](/_blob/b)`, never `[du pain, de la soupe, des frites](/_blob/x)`); test: 6-10 items; key in `reveal`.
3. `reading` - material: the text + glossary (uses the grammar unit); test: 4-6 comprehension questions (choice + short answers). Store the text in the session file.
4. `translation` - test only: 5-8 sentences on the lesson's topic, aimed at the grammar unit and the learner's recurring mistakes (recycled with this topic's words, lesson-steps.md "Stay on this lesson's topic").
5. `writing` - test only: scenario on the lesson's topic, in a format not used in the last few lessons (message, profile, postcard, email…) + one `long` item; checklist points only about this topic. Rubric says: score per sentence, give the full corrected text.
6. `listening` - material: audio (see media.md for where it comes from - usually with a background scene, `tts.py --ambience`) + one-line context + `material.transcript` (hidden until two full listens); test: 4-6 questions + 1-2 dictation lines; transcript in `reveal`.
7. `speaking` - **voice first** (learner, 2026-10-13: never make them type what they are about to say): the test is the task + 4-6 `point` items (one task point each, with `hint` for words they may need, no answer fields, no placeholders) + ONE `upload` item («Запись - все пункты одним голосовым»). Instructions say to answer every point in one voice message and that nothing is typed. While the learner records, the page transcribes live where the browser can (Web Speech API, e.g. Chrome/Safari) and shows the transcript to fix misheard words; «Проверить» then sends it to Claude, which splits it by point (`said` per item, shown as «…» under the point) and checks each. Where live transcription isn't available (e.g. the desktop app), the recording is uploaded and the sub gets `status: "awaiting_transcript"` - the page asks the learner to write «проверь говорение» in chat (see sync). Rubric: model sentence per point. Pronunciation is reviewed in chat from the recording.
8. `exam` - when the topic ends: all exam types from exam.md (retelling of a text from **this** lesson as a `long` item - for an earlier part of the topic, show that text again in the exam's material first; 2-3 items on the grammar unit, listening questions on a new short clip in the exam's material).
9. `roleplay` - the conversation (below).
10. `cards-end` - `kind: "flashcards"`: the new words of this session (flashcards.md).

The page counts a test's score itself from the per-item verdicts (`ok`), so the score always matches the ✓/✗ the learner sees - Claude's own count was sometimes one off. `lesson.grammar` (in the explanation language, from `course-progress.md`): `known` = units done or current; `later` = the next A-level units not taught yet. Every in-page check gets them: slips in `later` grammar are shown as «Ещё не проходили: …» and don't count. Every check also ignores punctuation and typography - including «oe» for «œ» and «ae» for «æ», which the learner's keyboard can't type («soeur»; flashcard answers match them too) - but a missing accent, also on a capital (Ecole → École), is a spelling error - and accepts all correct variants. For a typo in one word («enterprise» → «entreprise», «Vouz» → «Vous») the page marks only the letters that differ, not the whole word. Feedback notes use one form, which the page styles (the learner's words in normal text with the mistake in red bold, the fix in green bold, the rule after it, a line under the corrected text): `«je suis entraîneur **dans l'école**» -> dans une école: rule`. Write notes you store yourself (corrected feedback, chat sync) the same way. Write good rubrics: the in-page check is a separate, memory-less Claude that only sees the section, the rubric and the learner's recurring mistakes. Put the answer key, accepted variants, what counts as an error, and how to score (e.g. "total = 20, retelling worth 3") in the rubric.

### The role-play (end of every lesson)

Pick a situation where the learner meets a **stranger** who talks to them - at a bus stop, in a café queue, a neighbour on the stairs, a market seller - connected to the lesson's topic or the learner's interests, at their level. The stranger has a name and a personality, opens the conversation (`opening`), asks questions, and steers towards a concrete `goal` the learner must reach (find out which bus goes where, order for a friend with an allergy...). In the page, each learner message gets an inline correction, the stranger answers in character, and "Finish" produces a communication score, a summary and a mistake drill; "Start the conversation over" keeps the old attempt in `attempts`.

Fill the character fields carefully - the in-page Claude has no memory: every turn it receives one JSON object `{theme, character: {name, persona, never_act_as}, setting, agenda, learner_goal, target_language, level, explanation_language, words_to_bring_in, turn_limit, learner_turns_so_far, conversation: [{actor: "claude"|"user", message}], last_user_message}` and returns `{reply, correction, end}` for `last_user_message` only. So:
- `theme`: one sentence "act as …" naming who the character is, why they are there and what they want.
- `agenda`: 3-5 ordered points the character works through (the last one is the goodbye) - this keeps the conversation on track instead of drifting.
- `never_act_as`: the roles the setting might tempt the model into (in a café scene: "a waiter or any café staff").
- `focus`: words that fit the character's own lines - ordering vocabulary in a scene where the character is a customer pushes the model into playing the waiter.

## Your loop in chat

**At session start (and when the learner says "sync", "save my lesson" / "Save my <language> lesson <id>" in the learner's language (e.g. «Сохрани мой урок (французский) fr-intro-1») - the message the Finish button tells them to send - or comes back after working in the workbook):**
1. `query` `sub` for docs with `synced: false`, and `words` with `synced: false`.
2. For each sub (`status: "skipped"` = the learner pressed *Skip this section*: note it as skipped by the learner in the session file and progress.md Open items, and offer it again later - a skipped section stays open in the page): write the section into the session file (task, answers, corrections, score, drill score; role-play: the transcript and summary), update mistakes.md (count + dated example per real error; the page's feedback lists `mistakes`), `vocab.py grade` for vocabulary items, and progress.md (current step / exam history). Skim the page's feedback first - it can be wrong; if you correct it, tell the learner.
   - A speaking sub with `status: "awaiting_transcript"` (or the learner writes «проверь говорение»): fetch the recording as below, transcribe it with `stt.py`, show the learner the transcript, then do the page's check yourself: for every `point` item write `answers[<id>]` = the words that answer it (verbatim) and `answers.transcript` = the whole transcript, and `feedback` in the page's shape (`items` with `id, ok, corrected, notes, note, said`, `summary`, `mistakes`, `drill` - same note format, same rules as `checkRules`), `status: "checked"`, `checked_by: "tutor"`. The page then shows it like any checked test. Add pronunciation feedback in chat.
   - A sub with an `audio` attachment (speaking): the page cannot listen to audio, so this is yours. Fetch the asset (Artifact `read` with the artifact `url` and `path` = the asset id from `audio.url`; it is saved to a local file), copy it to `<language>/sessions/audio/<date>_<topic>_speaking.<ext>` on the learner's computer, run `stt.py`, compare the transcript with their typed answers and the task, and give pronunciation feedback in chat (media.md); save it in the session file.
   - A sub with `audio_error` (or the learner says the recording didn't go through): ask them to attach the file in the chat and process it the same way. Never say a recording "couldn't be processed" without saying what to do instead.
3. Flashcard subs (`kind: "flashcards"`): `vocab.py grade` with their `word_results` (right / nearly / wrong). New words: check each is a target-language word with a translation in the explanation language (fix it - and the `words` doc - if not; translate `needs_lookup` ones), then `vocab.py add <dir> --topic <topic slug or misc> --queue` with its fields: picked words are only noted for learning and come into a later lesson's vocabulary section (lesson-steps.md) - never straight into a deck. When a lesson's vocabulary section is done, run `vocab.py teach` with its words (a skipped section stays queued).
   - The `finish` sub (`kind: "finish"`): the lesson is over. After the section subs: put its `recap` and `digest` at the top of the session file, close the lesson in progress.md (step → done, next step/topic), update course-progress.md for the grammar unit (≥ 80% → `done <date> <score>`, else `review`), then `update` the sub to `{status: "saved", saved_at, synced: true}` - the page then shows "Saved to your files".
4. Mark each processed doc `synced: true` (update with `if_version`).
5. Rebuild the dashboard: `vocab.py dash <language dir> --out <root>/script/.cache/dash-<language>.json` → `set` `dash/<language>` from that file (stage it into your sandbox first if it was made on another machine).
6. Tell the learner in 2-3 lines what was saved and what's next.

**Layout rules the learner asked for:**
- Instructions with several steps or a checklist: one step per line (a markdown list, or ① ② ③ - the page puts each on its own line). Never one long paragraph.
- Five or more word-meaning or word-number pairs (numbers, glossaries, prices): a table, never a `·`-separated line. For long lists use two pairs per row (`| word | 10 | word | 15 |`).
- In material bodies, every `###` heading starts a new visual block - give each grammar point its own heading.
- Explanations of mistakes contrast look-alike constructions (the page's checker does this too): *un pain **au** chocolat / une tarte **aux** pommes* (flavour, main ingredient: à + article) vs *un café **avec du** lait* (something added).

**Before setting a lesson:** `python3 <root>/script/lesson_check.py lesson.json --previous <the last 3 sessions/*.lesson.json>` (also in this skill's `scripts/`) - fix every ERROR (several words in one audio clip) and the WARNs about inline lists, one-block instructions, missing transcripts, missing word/example audio, a grammar section with several themes, and repeated cities / settings (within the lesson and against the previous ones - lesson-steps.md, "Variety").

**Preparing a lesson - text first, audio last.** Audio is made ONCE, from the checked final text; voicing a draft and then re-voicing after every fix is what made lessons take over an hour. In this order:
1. Choose the topic (SKILL.md §2) and write ALL sections as the lesson JSON, with placeholder audio buttons `[J'ai une chambre.](audio)` (one per word / example sentence), cards without audio fields, and the listening dialogue as `material.transcript` (`Name: text` lines).
2. `lesson_check.py lesson.json --draft --previous <last 3 lessons>` - fix every ERROR and WARN in the TEXT (cities, places, themes, leaks, speaking format). Nothing is voiced yet, so a change costs nothing.
3. Only now the audio: `audio_plan.py lesson.json --list clips.txt` → `tts.py --each --vary --file clips.txt` (Supertonic, ~1 s per clip) → upload → `audio_plan.py --fill map.json`; the dialogue with `tts.py --ambience` from the transcript (Chatterbox, ~45 s per line - the slow part, done once). `--verify` checks only sentences and the dialogue, two at a time.
4. `lesson_check.py` on the final JSON (now with the audio checks), then `set` `lesson/<language>`, update progress.md (current topic, "Current step: workbook lesson <id>") and the dashboard, then one line in chat: "Your lesson is ready in the workbook." The page starts at section 1 for a new lesson id.

**If the learner answers in chat instead** (phone, habit): correct as usual and write the answers + feedback into the matching sub doc so the page shows the same state.

Files stay the source of truth; the workbook is the interface. If the two disagree, trust the files and rewrite the workbook docs from them.
