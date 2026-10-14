# French grammar course (A0 → C1)

A complete, ordered grammar course used by the **language-tutor** skill. Every session teaches the next unit; the skill reads the unit file instead of inventing the material each time, so the course can be checked, corrected and polished over time - and shared with other learners as it is.

- **Course language:** English (explanations). Examples are in French with English translations. The tutor translates explanations into each learner's explanation language at lesson time.
- **Target learners:** adults; traps are noted for speakers of Russian and English.
- **Version:** 1 (generated 2026-10-01). Status of each unit is in its front matter (`draft` → `reviewed` → `validated`).

## Folder layout

```
course/
  README.md        this file: how the course works, how to edit and share it
  syllabus.md      every unit in teaching order, with level and prerequisites
  units/           one file per unit (P = pronunciation, G = grammar)
  audio/           audio clips made for units (created on first use, reused afterwards)
  CHANGELOG.md     what was changed and why
```

Learner-specific data is **not** in this folder: each learner's position in the course lives in `../course-progress.md`, their mistakes in `../mistakes.md`. So the `course/` folder can be copied to someone else as is.

## Unit file format

```markdown
---
id: G6
title: Possessive determiners (my, his, her)
level: A1
prerequisites: [G1, G5]
version: 1
status: draft            # draft | reviewed | validated
---
## Goal            one sentence: what the learner can do after the unit
## Explanation     the rules, short and plain
## Forms           table(s)
## Examples        6-10 French sentences with translations
## Traps           typical mistakes (Russian / English speakers) and how to avoid them
## Practice bank   10-12 exercise items with answers and accepted variants
## Mistake patterns  wrong forms learners produce - used for drills and flashcard distractors
## Quick check     3 items; all correct → the unit can be marked "known"
```

## Editing and validating

- Edit any unit directly; bump `version` and add a line to `CHANGELOG.md`.
- Mark a unit `reviewed` after a careful read, `validated` after a native speaker / teacher checked it or after several learners used it without problems.
- If a lesson shows a unit is unclear or wrong (the learner keeps failing for a reason the explanation causes), the tutor fixes the unit file and logs the change, so the next learner gets the better version.
- To ask the tutor for a review: "review course unit G14" or "validate the A2 units".

## Sharing

Copy the `course/` folder into another learner's `languages/french/` folder. Their tutor will use it as is and keep their own `course-progress.md`.

## Video channels

Checked before a video goes into a unit (course.md in the skill: views, likes, comments, channel size). Search these first.

| Channel | Link | Verdict | Why | Added |
|---|---|---|---|---|
| Learn French With Alexa | https://www.youtube.com/@learnfrenchwithalexa | preferred | real teacher, slow clear explanations in English, 2.45M subscribers; the learner: "a great channel to learn French" | 2026-10-08 |
| Français et Julia | - | avoid | weak video (561 views, 3 comments); the learner found it bad | 2026-10-08 |
