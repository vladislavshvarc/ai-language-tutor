# The language course - generate once, reuse, improve, share

Every language has a **course folder** in its progress folder: a complete, ordered grammar course (pronunciation first, then grammar from beginner to advanced), one file per unit. The skill does **not** carry courses itself - it generates the course the first time a language is set up, saves it, and from then on reads the saved units. The learner (or a teacher) can review, correct and polish the files, and the folder can be copied to other learners as is.

```
languages/<language>/
  course/                 shareable - no personal data
    README.md             how the course works, course language, version, how to edit/share
    syllabus.md           all units in order: | id | title | level | prerequisites | file |
    units/<id>-<slug>.md  one unit per file (format below)
    audio/<id>/           audio clips made for a unit + clips.md (file → text); reused
    CHANGELOG.md          | date | version | units | change | why |
  course-progress.md      this learner's position: | id | unit | level | status |
```

## When the course is missing

At language setup (SKILL.md §1a), or the first time a session needs a grammar unit and `<language>/course/` doesn't exist:

1. Ask once: generate a new course, or use one the learner already has (another learner's / teacher's `course/` folder - copy it in, run `course_check.py`, and use it as is).
2. Generating: write `README.md`, then `syllabus.md`, then **every unit file**, then `CHANGELOG.md` (version 1, all units `draft`), then `course-progress.md` for this learner. Run `scripts/course_check.py <dir>/course --progress <dir>/course-progress.md` and fix every error before using the course. Tell the learner the course exists and that they can review/edit it.
   - Write the units in batches (e.g. by level) - it is a lot of text; that's expected and only happens once per language.
   - Course language: English by default (shareable); the tutor translates explanations into the learner's explanation language at lesson time. Use another course language only if the learner asks.

### What the syllabus must cover

From A0 to C1, in teaching order, with levels and prerequisites:
- **Pronunciation first** (3-4 units): the sound system and spelling-to-sound rules - vowels and the written accents/diacritics, special sounds (nasals, umlauts, tones…), silent letters, linking (liaison/elision or the language's equivalent), stress and rhythm, consonant spellings.
- **A1**: nouns, gender and articles; subject pronouns and the key verbs (be/have); present tense of regular verbs; negation; questions; adjectives (agreement, position); possessives; prepositions and contractions, places, transport; frequent irregular verbs and the near future; partitive/quantities (if the language has them); stressed/disjunctive pronouns; other verb groups; reflexive verbs and the imperative; demonstratives, numbers, time, dates.
- **A2**: object pronouns; the past tenses (perfect/preterite, auxiliaries, agreement; imperfect vs perfect); simple future; adverbial pronouns (like y/en); relative pronouns; comparison and adverbs; negation beyond "not"; time expressions (since, ago, for, in).
- **B1**: past perfect; conditional; if-clauses; subjunctive (if any) and its triggers; double pronouns; reported speech; possessive/demonstrative pronouns; participles/gerunds; passive; complex relatives.
- **B2**: past conditional; advanced subjunctive; sequence of tenses; future perfect; connectors and their moods; formal style/nominalisation; literary tenses for recognition.
- **C1**: emphasis structures; literary/formal forms; modal nuance; registers (spoken vs written); hard agreement cases.

Adapt the list to the language (German: cases and word order early, Spanish: ser/estar and two pasts, etc.) - the order is "most needed first", and each unit must be small enough for one session - one theme; split bigger ones with `## Lesson parts`.

### Unit file format

```markdown
---
id: G6
title: Possessive determiners (my, his, her)
level: A1
prerequisites: [G1, G5]
version: 1
status: draft            # draft | reviewed | validated
---
## Goal              one sentence
## Explanation       bullets: the rules, compared with the learner's language where useful
## Forms             table(s)
## Examples          6-10 sentences with translations
## Traps             typical mistakes of speakers of <explanation languages> and how to avoid them; include
                    look-alike constructions side by side (au chocolat / avec du chocolat; c'est / il est)
## Practice bank     | # | Type | Prompt | Answer | Accept also |   (8-12 items, every one with an answer)
## Lesson parts      optional: when the unit has several separate rules, one part per lesson ("1. être и avoir 2. pronouns, tu / vous")
## Mistake patterns  the wrong forms learners produce (comma-separated) - for drills and flashcard distractors
## Quick check       3 numbered items "prompt → answer"
## Videos            optional | Video | Channel | Start | Covers | Added |  - YouTube explanations (below)
```

Quality bar: every example and answer must be correct standard language - double-check accents, agreement and irregular forms; keep explanations short and practical; traps should come from real learner errors (mistakes.md of any learner using the course is the best source).

## Using a unit in a session

1. Next unit = the first in `course-progress.md` that is `current`, `review` or `-` (in syllabus order). If the last unit's test was < 80%, start with a short review of it (new items, same rules) and mark it `review` until passed. **Never run ahead of the course.** A unit is taught only when its prerequisites are done (`course_check.py --progress` warns otherwise). The roadmap is built around the course order - each topic is chosen to fit the next units, not the other way round. When a topic needs a construction from a later unit (je voudrais du café before the partitive, je m'appelle before reflexive verbs), teach it as a fixed phrase in the vocabulary, without the rule, and don't count slips in it as errors. (The French course for this learner ran ahead - G7, G8, G9 and G2 before G1 and G3 - and the checker kept marking gender, articles and conjugation he had never been taught; fixed 2026-10-08.)
2. Read the unit file. Build the session's grammar section from it:
   - **one theme per lesson**: if the unit has a `## Lesson parts` section, teach the next part only; if it doesn't and it holds more than one separate rule, add `## Lesson parts` to the unit first (bump `version`, CHANGELOG row) and teach part 1. In `course-progress.md` write `current - part 1/2 …`. Never put a pronunciation unit into the grammar section - it gets its own short section (lesson-steps.md).
   - material = Explanation + Forms + 4-8 Examples, translated into the learner's explanation language; add "your mistakes this unit fixes" from mistakes.md; for pronunciation units add audio (below).
   - test = 6-10 items from the **Practice bank** (rotate items between sessions; add new ones when reviewing), rubric = their answers + "Accept also".
   - drills / flashcard distractors = **Mistake patterns** + the learner's own mistakes.
   - "known" check = the **Quick check** (3/3 → mark `known`).
3. The rest of the session uses the unit: reading contains it, translation and writing practise it, the exam has 2-3 items on it.
4. After the test: `course-progress.md` → `done <date> <score>` (≥ 80%) or `review`; next unit → `current`.

## Audio for units

Pronunciation units (and any unit where hearing helps) get short clips - one per word or example, never a list in one clip: generate with `tts.py --each --vary --verify` (media.md), save to `course/audio/<unit id>/` as .webm and list them in `clips.md` (file → exact text). Next time - and for other learners - reuse the files instead of generating new ones. For the workbook, upload the clips as assets once per workbook and keep the uploaded ids in the learner's own notes (e.g. `<language>/sessions/` or the lesson JSON), not in the course folder.

## Videos for units

A good short video often explains a sound or a rule better than text. When you build a session from a unit whose file has no `## Videos` section yet, look for one:

1. **Preferred channels first.** `<language>/course/README.md` has a `## Video channels` table (preferred / avoid, with the reason). Look in the preferred channels before anything else (French: *Learn French With Alexa* - the learner's favourite); never use a channel marked avoid.
2. **Search** YouTube for the unit's topic in the target language, the learner's explanation language and English - e.g. "French accents explained", "accents français é è ê", "французские акценты"; for grammar: "passé composé être avoir explained".
3. **Check the numbers of every candidate** - a title alone is not enough (a Russian être/avoir video picked by title had 561 views and 3 comments, and the learner found it bad). Use the built-in browser (or Claude in Chrome) on any youtube.com page and run `scripts/youtube_stats.js` with the javascript tool: `ytChannel("@channel", "query")`, `ytSearch("query")` and `ytStats([ids])` return views, likes, comments, channel subscribers, like rate, length and date; on an open watch page scrolled to the comments, `ytTopComments()` gives the top comments to skim. (youtube.com is usually not reachable from the shells, so web search + oEmbed only proves a video exists.) Bar for a pick:
   - views ≥ 50 000 for beginner topics (≥ 10 000 for niche B2+ topics), likes ≥ 1 % of views, comments present and not complaining about mistakes;
   - channel ≥ 100 000 subscribers, or a preferred channel;
   - a teacher, short (ideally under 15 minutes), at the learner's level, about exactly this unit's theme (or one part of it); explanations in the explanation language or slow, clear English / target language.
   Nothing passes → take the best preferred-channel video, or write `none found`. Never fall back to a small channel just because it speaks the explanation language.
4. Pick 1-3 (one per sound or sub-rule for pronunciation units), add an optional start time (`&t=18s`) to skip a long intro.
5. Save the rows in the unit's `## Videos` table with the numbers in the Added column ("2026-10-08 · 3.4M views, 51K likes, 3.2K comments") - shareable course content, reused by every later session and learner - and add a CHANGELOG row (no version bump needed). If nothing suitable exists, write one row `| none found | - | - | - | <date> |` so the search isn't repeated every session.
6. A video or channel the learner recommends goes in first (Added: "learner's pick"; a channel → preferred in the README). If the learner says a video was bad, remove its row and mark the channel avoid when the whole channel is the problem. Re-check old rows that were "picked by title, not watched" the next time the unit is used.

In the workbook each video card shows `title`, `channel`, `duration` and a `note` - put the key numbers in the note ("3,4 млн просмотров") so the learner sees why it was chosen.
The videos go into the section's `material.videos` (grammar or sounds) (link cards that open YouTube in a new tab - the page can't embed them); inline, give the link with one line on what to watch for.

## Improving the course

- When a lesson shows a unit is unclear or wrong (a learner keeps failing because of how something is explained, an answer key is wrong, a better example exists): fix the unit file, bump its `version`, add a CHANGELOG row (date, version, unit, change, why), and mention it to the learner in one line.
- "Review unit G14" / "validate the A2 units": re-read the unit(s) critically (language correctness, clarity, practice answers), fix, run `course_check.py`, set `status: reviewed`. `validated` is for the learner/teacher to set after a native-speaker check or after several learners used it without problems - don't set it yourself.
- Never delete a learner's progress when changing the course; if unit ids change, update `course-progress.md` to match and say so in the CHANGELOG.

## Sharing

The `course/` folder contains no personal data, so it can be given to another learner: they put it in their `languages/<language>/` folder; their tutor validates it with `course_check.py`, creates their own `course-progress.md`, and uses it.
