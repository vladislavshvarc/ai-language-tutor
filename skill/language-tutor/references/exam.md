# End-of-topic exam (and quick quizzes)

## Composition - 15-20 items

| Block | Items | Format |
|---|---|---|
| A. Flashcards | 5-6 | 3 target → explanation language, 3 explanation → target (with article/gender) |
| B. Multiple choice | 3-4 | incl. 1-2 picture-based: "Which one is *la voiture*?" options 🚗 / 🚌 / 🚲 / 🚕 |
| C. Fill in the blank | 3 | tests today's grammar rule(s): "C'est la porte ___ voiture." |
| D. Translate a sentence | 2 | explanation language → target, using topic words + grammar |
| E. Retell a text | 1 (worth 3 points) | 3-5 sentences in the target language about a text from **this** session |
| F. Listening | 1-2 | questions on the step-6 audio/dialogue (replay allowed once) or a new 2-3 line clip |

Total the points so the maximum is 15-20. The retelling scores 0-3: content (main events present, nothing invented) up to 2, language (understandable, mostly correct) up to 1. Language mistakes in the retelling are corrected but only cost the language point.

**Only ask about what the learner has in front of them or saw in this session.** If the topic ran over several sessions, the retelling uses this session's reading; to cover an earlier text ("Léa at the station café"), put it in the exam's material so it is read again right before the test (the material hides on Continue) - never name a story, dialogue or word list from a past session and expect the learner to remember it.

Prefer words the learner got wrong earlier in the lesson and grammar that appears in mistakes.md.

## Delivery

- With a workbook (workbook.md), write the exam there: one exercise per block (A+B, C+D, E+F) or all items at once if the learner prefers; `choice` items with emoji options are the picture questions. Without one, present it in chat in blocks (A+B, then C+D, then E+F), not all 20 at once and not one per message. Multiple-choice and picture items work best with a tappable question tool (e.g. AskUserQuestion, up to 4 questions per call) - put the target word in the question and pictures/emoji as the option labels.
- No hints or corrections during the exam; give feedback at the end. Accept answers with only a missing accent, but note it. A wrong article/gender on a noun counts as wrong for gendered languages (it's the point of learning it with the article) - say so once at the start.

## Result

```
Exam - The car - 17/20 (85%) ✓ pass

Wrong:
- A4 "le volant" → you wrote "wheel"; volant = steering wheel, la roue = wheel.
- C2 "C'est la porte de le garage" → du garage: de + le contracts to du.
- F1 closing time: the audio said 19h (dix-neuf heures), not 18h.

Words back into review sooner: le volant, la roue
```

Then:
1. `vocab.py grade` with every vocabulary item the exam touched (correct/incorrect).
2. progress.md: topic history row, current topic `-`, current step `-`.
3. Session file: exam table + result.
4. mistakes.md: any repeated grammar error.
5. < 80%: offer a redo of only the failed items' material (re-explain the rule, 4-6 new items of the same type), then re-score those items. Record both scores ("62% → redo 5/6").
6. Check the level-up rule in cefr.md.

## Quick vocabulary quiz ("quiz me on my words")

- Words: `vocab.py due <dir> --limit 15`; if fewer than 8 are due, top up with the lowest-box, most-wrong words and say so.
- 10-15 items, mixed: flashcards both directions, picture multiple choice for concrete nouns, a gap-fill using the word's example sentence. Present in 2-3 blocks.
- Grade with `vocab.py grade`, show score, which words moved up/down a box, and when the next review is due. Add a row to progress.md "Reviews".
