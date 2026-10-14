# AI language tutor

A personal language tutor for Claude. It runs structured lessons, checks your answers right away and keeps your progress in plain files, so the next lesson - in any chat - picks up where you stopped.

- **One topic per lesson:** words → grammar → reading → translation → writing → listening → speaking → a conversation with a stranger → flashcards.
- **Workbook** - a page in Claude where you answer; Claude checks each test at once and gives you a short drill on your own mistakes.
- **Grammar course** A0 → C1 (`french/course/`) - the learning roadmap: every lesson takes the next unit.
- **Offline speech:** natural listening dialogues (Chatterbox, native-speaker voices, café / metro / hotel backgrounds…), audio for every word and example (Supertonic).
- **Voice messages transcribed** (whisper.cpp) and checked point by point in the speaking tasks.
- **Spaced-repetition vocabulary** with flashcards.

## How the folder works

This folder is both the **repository** and **your languages folder**. Clone it once, connect it to Claude, and everything your studies produce stays with you - none of it goes to git.

```
skill/language-tutor/     the skill: SKILL.md, references/, scripts/, assets/workbook.html
script/                   helper scripts: vocab.py, tts.py, stt.py, ambience.py, lesson checks
  text-to-voice/          speech: setup, Chatterbox voices, background sounds (ambience/)
  voice-to-text/          voice-message transcription (whisper.cpp)
setup/                    model download and whisper build
french/course/            French course A0 → C1 (syllabus.md + units/)
```

**Never in git** (see `.gitignore` - everything is private by default): `progress.md`, `vocabulary.json`, `mistakes.md`, `course-progress.md`, `sessions/`, any lesson audio and voice messages, the models (~4 GB), the installed engines and the whisper build, API keys.

## Setup

1. **Clone** the repository where your languages will live:
   ```
   git clone https://github.com/vladislavshvarc/ai-language-tutor.git ~/Documents/Languages
   ```
2. **Download the models** (~4 GB, once; in the macOS or Linux terminal):
   ```
   cd ~/Documents/Languages && sh setup/download_models.sh
   ```
   Without Chatterbox (fast voices and transcription only, ~1 GB): `sh setup/download_models.sh fast`.
3. **Add the skill to Claude.** Pack the skill folder and upload it in Claude's settings, in the Skills section:
   ```
   cd ~/Documents/Languages/skill && zip -r ../language-tutor.skill language-tutor
   ```
   In Claude Code instead: `cp -R skill/language-tutor ~/.claude/skills/`.
4. **Connect the folder** `Languages` to a task in the Claude app (Cowork) and write, for example: "Let's learn French, explanations in English".
   In the first lesson Claude installs the speech engines (`script/text-to-voice/setup_engines.sh all`) and builds whisper (`setup/build_whisper.sh`) once - 2-5 minutes. Everything is installed **inside this folder** (`script/.env/`, ~1.7 GB, not in git), so later sessions install nothing: the script answers `ready` in a fraction of a second.

**A new language:** just ask. If there is no course for it yet, the tutor creates one in `<language>/course/`. To share that course through git, add three lines to `.gitignore` following the `french` example.

## Updating

```
git pull
```
Your progress, words and recordings are untouched - they are not in the repository.

## Requirements

- The Claude app with skills; publishing artifacts for the workbook.
- For speech and transcription: ~5 GB of disk space. Chatterbox dialogues take about 45 s per line on a CPU.
- The tutor also works without the models: listening falls back to a read-once text, and voice answers can be typed or dictated.

## Licences

The skill's code and texts are by the repository author. The models are downloaded from their authors' sites and are not part of the repository. Background recordings and voice samples are distributed under their own licences (CC0, CC BY, CC BY-SA, CC BY-NC) - authors and sources in [THIRD_PARTY.md](THIRD_PARTY.md). For personal study.
