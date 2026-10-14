# Lesson steps - templates

Each step: short intro line ("Step 2/7 - Grammar"), the content, a clear request for the learner's answer, then stop and wait. After the learner answers: correct, save (session file + progress.md step), then start the next step.

---

## 1. Vocabulary (10-15 items)

1. Run `vocab.py known <dir>` (taught words) and exclude them, and `vocab.py queue <dir>` - words the learner picked in the workbook or that a lesson prepared but never taught. **Words the learner picked are taught here, in a lesson whose topic fits them** (2-4 per lesson, oldest first): they get a row in the table, they appear in the reading / listening texts, and they go into the end-of-lesson deck. A queued word is never shown in a review deck before that - the learner doesn't know it and can't answer.
2. Pick 10-15 items central to the topic: mostly concrete nouns and key verbs at A0-A2; more phrases/collocations from B1. Include items the reading will use, and the fitting queued words.
3. Show a table:

| | Word | Translation | Example |
|---|---|---|---|
| 🚗 | **la voiture** (f) | car | *La voiture de mon père est rouge.* - My father's car is red. |
| 🚪 | **la porte de la voiture** (f) | car door | *Ferme la porte de la voiture, s'il te plaît.* |

   - Gender/article always for gendered languages; plural if irregular; verb type if useful (e.g. *-er* verb, separable verb in German).
   - Visual cue: an emoji or small image for concrete things (see media.md); skip it for abstract words rather than forcing a bad one.
   - Pronunciation hint for tricky words at A0-A1 (simple approximations, not IPA unless the learner wants it).
   - Audio: one clip for every word and one for every example sentence (`tts.py --each --vary --verify`, media.md); in the workbook the word and the example are each a ▶ button.
4. When preparing the lesson, save them with `vocab.py add <dir> --topic <slug> --queue` (JSON list with word, translation, gender, pos, example, example_translation): queued until studied. When the learner has done the vocabulary section (sync, or in chat), run `vocab.py teach <dir> --topic <slug> --words "…; …"` - only then do they enter the Leitner boxes and later review decks.
5. Ask the learner to read through and say when ready (optionally: "try to use 3 of them in a sentence" - correct those sentences).

## 2. Grammar - from the grammar course

The session's grammar is the next unit of the grammar course, taught **right after the new words** (course.md says how to choose the unit and build the section from its file in `<language>/course/units/`; pronunciation units come before everything else).

**One theme per lesson.** The grammar section teaches exactly one theme the learner can name in a few words ("être и avoir", "род и артикли"). Never bundle a pronunciation unit, a second unit, or side rules into it - the learner found a section mixing nasal vowels, tu/vous, s'appeler and professions impossible to remember. If a unit holds several separate rules (G2: être/avoir + pronouns/tu-vous), split it into lesson parts (the unit's `## Lesson parts`) and teach one part per lesson. Phrases the topic needs but that belong to later grammar (je m'appelle, je suis ingénieur) are taught in the vocabulary step as phrases to learn whole, without rules. A current pronunciation unit gets its own short section ("Звуки", 5 minutes, 4-6 listening items), separate from grammar - or waits for another lesson.

For the theme:
- **Video**: the unit's YouTube explanation(s) from its `## Videos` section, found once per unit (course.md, "Videos for units").
- **Rule** in one or two plain sentences in the explanation language, compared with the learner's language where useful.
- **Look-alikes**: when the rule has a construction that looks similar but means something else, show both side by side with an example each (*un pain au chocolat* - flavour; *un café avec du lait* - something added; *à la pomme / aux pommes*). The learner asked for this.
- **Pattern** / small table, 4-8 examples - built from the words just learned in step 1 wherever they fit (*du pain, de la confiture* right after learning *le pain, la confiture*) - and the common trap. One audio clip per example (media.md), never a list of examples in one clip.
- A 6-10 item test with the material hidden, then the mistake drill.

Then make the topic use it: the reading text contains it (point it out: "**From the text:** …"), translation and writing practise it, and the exam has 2-3 items on it.

## 3. Reading

- Length from cefr.md for the level. Use most of the new words (bold them) plus known vocabulary; include the grammar you plan to teach in step 3.
- Give a title. A0-A1: short sentences, present tense, high-frequency words; you may add a glossary for 1-2 unavoidable unknown words.
- From B1, you may base it on real material (adapt and cite the source).
- Then a short comprehension test (4-6 questions: details, true/false, one "why") with the text hidden - in the workbook the Continue button hides it; inline, ask the learner to scroll away/not look. If the exam is in this same session, mention that it will ask for a 3-5 sentence retelling.
- Save the text in the session file.

## 4. Translation (5-8 sentences)

**Stay on this lesson's topic - and make every scene new.** Every task after the words - reading, translation, writing, listening, speaking, role-play - is about the session's topic and uses its words. Old mistakes and old words come back **inside a new scene that fits this topic**, never as a rerun of the old one: café-topic errors (du / de la, café, viande) fit an introductions lesson when two passengers meet on a plane and the steward asks «du poulet ou du bœuf ? du café ou du thé ?»; «pas de» fits «Je n'ai pas de frère». A writing or speaking checklist never asks about the previous topic directly (the learner noticed a self-introduction asking what he eats for breakfast).

**Variety.** Before writing the lesson, list the cities, places and characters of the last 3 lessons (`lesson_check.py lesson.json --previous <the last 3 sessions/*.lesson.json>` prints them and warns about repeats). Then:
- each section gets its own place - reading, listening, speaking and role-play never share a setting (one in a café, one on a plane, one at a language school, one by the sea…);
- no city in more than two sections, and a different main city from the previous lessons (France has more than Lyon: Nice, Bordeaux, Toulouse, Lille, Nantes, Strasbourg, Marseille, Rennes, Annecy; also Brussels, Geneva, Montréal, Dakar);
- new characters with new names and jobs each lesson; the learner remembers settings, so a repeated scene feels like the same lesson again.


- Sentences in the explanation language → target language. Use the new words and today's grammar; slip in 1-2 items that target a recurring mistake from mistakes.md - written with this topic's words and situations.
- Number them; learner answers all at once (or in two halves at A0).
- Check each: ✓ if correct (accept any correct variant - there is rarely one right translation), otherwise the correction format with a one-line explanation per change. End with a score (e.g. 6/8) and the 1-2 patterns to watch.

## 5. Writing

- A small real-life scenario **on this lesson's topic** with a concrete goal. **Vary the format** from lesson to lesson and don't repeat the speaking task of the same lesson: a chat message, a profile on a language-exchange site, a postcard, an email to a host family, a note to a neighbour, a short review, a diary entry, a form… Look at the writing tasks in the last 3 session files and pick a different format; give the points in a fresh order with new angles (why you learn the language, one thing you have, a question back). Example (car, A1): "Your car broke down this morning. Write to a colleague: say what happened, how you're getting to work, and when you'll arrive."
- Give the length from cefr.md and 3-4 content points to cover. At A0 give a model sentence or sentence starters.
- Feedback:
  1. Full corrected version (keep the learner's ideas, facts and style; fix, don't rewrite - never change what they said they like, do or have; missing task points may be added as short extra sentences in **bold**, the rest stays theirs).
  2. Numbered changes: *what was wrong → rule → fix*. Separate real errors from "more natural:" suggestions.
  3. 1-2 things done well, and a one-line summary of the main pattern to work on.
- Log recurring mistakes in mistakes.md. Note the format used in the session file (`Writing: profile (language exchange)`).

## 6. Listening (IELTS-style)

- Setting: put the dialogue in a real place with a background (metro, café, airport, street, park... - media.md, "Background sounds"), quieter at A0-A2.
- Content: a 4-10 turn dialogue or short monologue at the level, on the topic (e.g. two people talking about where the bakery is and when it closes), containing specific details that questions can target (places, times, prices, yes/no facts).
- Audio options (media.md): real short audio/video at the right level if you can find and link one, otherwise write the dialogue and generate audio with `tts.py` (use `--slow` at A0-A2). Deliver the audio file; **don't** show the transcript.
- 4-6 questions in the explanation language or the target language (A0-A1: explanation language, answers can be short/multiple choice; B1+: target language, short written answers). Mix detail (what time does it close?), true/false (is it open?), and at B1+ one inference question.
- **Check every question against the transcript before publishing** (reading questions against the text). Each question points to one moment and one speaker, and its wording adds no premise the recording doesn't have: «Что Юго просит попить вместо кофе?» was wrong - he asked for water with the meal and said only «Pas de café» to the coffee; «Что Юго просит попить к обеду?» is right. Watch for answers another speaker gives in the same scene (Amélie orders the tea), and don't make the dictation sentence the answer to another question. Put the answer's exact line in the rubric ("5 de l'eau - line 10, with the beef").
- If a learner shows a question was flawed: accept the answer, correct the stored feedback and score, fix the question in the lesson, and say so - never call it inattention.
- The learner may listen twice. After their answers: score, then reveal the transcript with the answer locations bolded, and explain what caused each miss.
- Fallback when no audio can be made: say so plainly, show the dialogue once, ask them to read it once and reply "done", then ask the questions without the text visible (in a chat they could scroll up - ask them not to). Record in the session file that listening was done as text.

## 7. Speaking

- A situation that needs 30-90 seconds of speech (longer at higher levels), e.g. "You woke up late and missed the train. Call your manager: explain, say you're taking a taxi, give your new arrival time." Give 3 content points and 3-4 useful phrases from the lesson.
- In the workbook: the task points are `point` items and the learner answers them all in ONE voice message - never ask them to type their answers first (workbook.md, `speaking`). Inline: ask for a voice message. When audio arrives: transcribe with `stt.py` (media.md). Show the transcript, then:
  - grammar/vocabulary corrections (correction format),
  - pronunciation: only what the audio evidence supports - words the recognizer misheard or was unsure about are likely trouble spots; name the typical issue for that sound in this language (see the language notes) and give a tip. Don't invent precise judgements you can't hear.
  - fluency/content: covered the 3 points? natural connectors?
- If audio can't be processed: say so, ask the learner to use their device's dictation or type exactly what they said, correct that, and state clearly that pronunciation feedback isn't possible this way.
