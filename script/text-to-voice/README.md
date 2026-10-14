# Text-to-voice for the language tutor

Offline neural voices used by `../tts.py` for listening dialogues, word clips and example sentences. Everything runs on this computer - no internet needed after setup.

**Models (once):** `sh ../../setup/download_models.sh` - they are not in git (~4 GB).

**Setup each session:** `sh setup_engines.sh all` (about 1-2 minutes; without `all` only Supertonic and Kokoro - enough for word clips). Then `python3 ../tts.py --lang fr --list-voices`.

## Engines (learner's choice 2026-10-09)

| Folder | What | Used for | Size |
|---|---|---|---|
| `models/chatterbox/` | Chatterbox Multilingual (MIT) - voices = 12-15 s reference clips in `voices/` + `voices.json` | dialogues (cast first) | 3.1 GB |
| `models/supertonic-3/` | Supertonic 3 (Open RAIL-M, huggingface.co Supertone/supertonic-3) - 10 voices F1-F5 / M1-M5, 31 languages, fast | words and example sentences (`--each`: Supertonic only); dialogue backup | 0.4 GB |
| `models/kokoro-v1.0.int8.onnx`, `models/voices-v1.0.bin` | Kokoro-82M (github.com/thewh1teagle/kokoro-onnx) - French: ff_siwis | dialogue backup | 0.1 GB |
| `requirements/` | pinned Python packages for Chatterbox's own venv (`$HOME/.venvs/chatterbox`), installed from PyPI - or from `wheels/chatterbox/` when that offline copy exists | setup | - |
| `engines/chatterbox_worker.py` | the worker tts.py runs inside that venv | - | - |

XTTS-v2, MeloTTS and Piper were removed on 2026-10-09 (learner: not needed; Piper robotic, XTTS dictation-like) - their models, wheels and samples were deleted to free ~3 GB.

```
python3 ../tts.py --lang fr --list-voices
python3 ../tts.py --lang fr --file /tmp/dialogue.txt --ambience hotel --level A1 --out /tmp/listening.webm   # Chatterbox voices, placed in the scene
python3 ../tts.py --lang fr --each --vary --file /tmp/words.txt --out-dir /tmp/clips --verify               # Supertonic, one clip per line
```

Chatterbox is slow (~45 s per sentence on 4 CPU cores): tts.py stops after `--budget` seconds with exit code 3 - run the same command again until it exits 0 (finished clips are cached in `~/.cache/tts-clips`). It occasionally stops a sentence early (seen once: 1.8 s instead of 4.4 s) - check with `--verify` (in a separate run when there are many clips) and regenerate that clip by deleting its file in the cache.

## Chatterbox voices

Ratings by the learner, each voice placed in the hotel scene (2026-10-09, `samples/2026-10-09_chatterbox-voices-reel.mp3`):

| Voice | Gender | Source | Rating |
|---|---|---|---|
| bernard, paul | m | native readers, MLS French | good |
| maxime, antoine | m | Supertonic M1, M3 | good |
| luis | m | XTTS Luis Moray clip (kept as a Chatterbox reference; local only - not in the shared repository) | great - best fit in the room |
| marc | m | Supertonic M5 | older, not rated in the reel |
| claire, ines, julie | f | native readers, MLS French | good |
| elise | f | Supertonic F4 (the hotel receptionist - learner's favourite) | good |
| margaux | f | Kokoro ff_siwis | good |
| lea, ana, gitta | f | Supertonic F1; XTTS Ana Florence / Gitta Nikolina clips (local only) | older, not rated in the reel |

Deleted: hugo, olivier (too much echo), sophie, camille (poor recordings); thomas, nathalie, damien (only passable - the learner keeps the good ones only).

New voice: 12-15 s of clean, dry speech (no room echo, no hiss, lively intonation) as `models/chatterbox/voices/<name>.wav` (24 kHz mono, loudness-normalised) plus `{"name", "gender", "from", "note"}` in `voices.json`. Native readers came from Multilingual LibriSpeech French (CC BY 4.0 - credit: Pratap et al., "MLS: A Large-Scale Multilingual Dataset for Speech Research", 2020; speaker ids and LibriVox books in `voices.json` `from`), fetched through the Hugging Face dataset viewer. Never add a voice made from a real person's recording without their consent.

## Scene dialogues

`tts.py ... --ambience <scene> --level <lvl>` places all voices in one shared room, EQs them towards one tone (Supertonic F4), pans them in stereo, nudges pace (syllables/s over the whole turn incl. pauses, max ±5%) and adds random 0.25-0.6 s gaps - `ambience.scene_dialogue`. Chatterbox uses the lively style (exaggeration 0.6, cfg_weight 0.3, temperature 0.7). Never cut pauses out of finished speech (it causes a rasp) - regenerate instead. Write small natural fillers into dialogue.txt (Euh…, Alors…). Keep dialogue text files out of the language folders - the learner would see the transcript before the test. Test and ratings: `samples/2026-10-09_hotel-scene/README.md`.

## Benchmark 2026-10-05 (4 CPU cores, 3.9 GB RAM, no graphics card)

"rtf" = seconds of work per second of audio.

| Engine | Load | rtf | RAM | Notes |
|---|---|---|---|---|
| Supertonic 3 | ~1 s | 0.22 | ~0.5 GB | F1, F4, M4, M5 clearest in the whisper test |
| Kokoro | ~1 s | 0.60 | ~0.5 GB | occasionally swallows short words |
| Chatterbox Multilingual | ~11 s | 9.5 | ~3.5 GB (limit) | language model in bf16 + PyTorch 2.6 (full precision runs out of memory) |
