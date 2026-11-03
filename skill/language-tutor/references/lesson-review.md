# Lesson review - a fresh pair of eyes before the lesson goes out

The tutor who wrote a lesson reads it with everything it meant to write in its head, so it misses what is actually on the page: a ✗ example paired with an unrelated ✓ sentence (2026-11-02, «Est-ce que la piscine est ouvre ?» next to «Est-ce que tu habites avec une colocataire ?»), a question whose answer isn't in the text, a distractor that is also correct. A reviewer that has **only the lesson file** sees the page the way the learner will.

## When

After `lesson_check.py --draft` passes and **before any audio is made** (workbook.md, "Preparing a lesson", step 2) - every fix is still free. Again after a larger rewrite of a section. Not needed for a one-line fix.

## How

Start a **fresh subagent** - one that does not inherit this conversation (in Claude Code: the Agent tool with a general-purpose agent, not a fork). Give it only file paths and the prompt below; never paste your own explanation of the lesson - that is exactly the context that hides the mistakes. Without a subagent tool (e.g. a chat-only client), do the review yourself in a separate pass: read the lesson JSON top to bottom as if you had never seen it, with this checklist next to it.

Prompt (fill in the paths and the two languages):

```
You review a language lesson before a learner gets it. You have no other context: judge only what is in the files.
Lesson: <path to lesson.json> (sections with material, test items, rubric, reveal, cards, roleplay).
Grammar unit taught: <path to course/units/<unit>.md>. Learner: <level>, explanations in <explanation language>, learning <target language>.
Checklist: <path to references/lesson-review.md> - go through every point for every section.
Do not edit anything. Reply with a list of findings, most serious first, each:
SEVERITY (ERROR = wrong or misleading for the learner, WARN = unclear or weak) | section key | item id or "material" | the exact text | what is wrong | the fix.
End with "No findings" if there are none. Don't report style preferences.
```

Then fix every ERROR and the WARNs you agree with, run `lesson_check.py --draft` again, and note the review in the session file ("review: 3 errors fixed - …"). If you disagree with a finding, say why in the session file instead of ignoring it.

## Checklist

**Target language**
- Every word, example, option and model answer is correct standard language: spelling and accents, gender and articles, agreement, verb forms, elision (j', l', d'), word order. A wrong answer key is the worst error a lesson can have.
- Translations and glossary entries mean what the target text means, in this context.
- Tasks need only grammar the learner has (`lesson.grammar.known`); anything from `later` is given as a whole phrase, never required as a rule.

**Wrong examples (✗) and corrections**
- Every ✗ example sits next to **its own corrected version** - the same sentence with only the error fixed - never a different correct sentence.
- Every ✗ says what is wrong and why in a few words (*est + ouvre = два глагола*), in the explanation language.
- A look-alike pair shows both forms with an example of each (*au chocolat / avec du lait*).

**Examples and tables**
- Every example shows the rule of the heading it stands under. A sentence without the construction being taught - in a table about *ne … pas*, a row «Je mange une pomme.» - is either removed or shown for what it is: an answer next to its question («Tu manges une pomme ? - Non, je ne mange pas de pomme.»).
- Every row is understandable on its own: what it shows and how it relates to the rows around it. A row the learner can't connect to the topic is an ERROR, even if the sentence itself is correct.
- A column means the same in every row: a "meaning" column holds meanings, not a ✗ example squeezed in brackets.

**Questions and answers**
- Every test question can be answered from what the learner has: the section's material, its transcript or the text it asks about - not from another section, outside knowledge or the tutor's intention.
- The answer exists exactly once and matches the rubric; the rubric names where it is (paragraph, line, speaker).
- The question adds no premise the text doesn't have and points to one moment and one speaker; another speaker's line doesn't also answer it.
- `choice` items: exactly one option is right; no distractor is also correct (a synonym, the other gender of a noun that has both, an equally correct word order); the prompt doesn't contain or describe its own answer.
- A dictation line is not the answer to another question.
- The rubric lists the accepted variants (other correct word orders, question forms, synonyms) and says how to score; exam totals add up (count of items = total, pass mark stated).

**Structure**
- Instructions match the items: the number of points, ① ② ③ checklists, what the learner must write or say; speaking is `point` items + one `upload`, no answer fields.
- Every word of the vocabulary table is practised somewhere (test or cards); the test asks only words taught in this lesson or earlier.
- Flashcards: `translation` matches the word; `choice` options contain the `answer` exactly once and it is the correct form; `why` explains the trap; the example uses the word.
- The exam's retelling uses a text from this lesson; listening questions match the clip's transcript.
- Role-play: `opening` is in the target language; `agenda`, `goal` and `goal_text` agree; the details the learner must find out are only given when asked; `never_act_as` covers the roles the setting tempts.
- Everything the learner reads that isn't target-language material is in the explanation language - labels, instructions, notes, `why`, `goal_text`.
- One audio button = one word or one sentence; the button text is exactly what the clip should say.
