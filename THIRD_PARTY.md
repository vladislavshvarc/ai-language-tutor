# Third-party material

## Models (downloaded by `setup/download_models.sh`, not in this repository)

| Model | Source | Licence |
|---|---|---|
| Supertonic 3 | huggingface.co/Supertone/supertonic-3 | Open RAIL-M (see its LICENSE) |
| Kokoro-82M (ONNX int8) | github.com/thewh1teagle/kokoro-onnx, release `model-files-v1.0` | Apache-2.0 |
| Chatterbox Multilingual | huggingface.co/ResembleAI/chatterbox | MIT |
| whisper.cpp + ggml `small` | github.com/ggml-org/whisper.cpp, huggingface.co/ggerganov/whisper.cpp | MIT |

## Chatterbox reference voices (`script/text-to-voice/models/chatterbox/voices/`)

- **bernard, paul, claire, ines, julie** - 14 s cut from native French readers in Multilingual LibriSpeech, French (CC BY 4.0; recordings from LibriVox, public domain). Pratap et al., "MLS: A Large-Scale Multilingual Dataset for Speech Research", Interspeech 2020. Speaker ids and books are in `voices.json` (`from`).
- **elise, maxime, antoine, marc, lea** - generated with Supertonic 3 (voices F4, M1, M3, M5, F1); **margaux** - generated with Kokoro (ff_siwis).
- Clips made from XTTS-v2 voices (Coqui Public Model License, non-commercial) are not included.

## Background sounds (`script/text-to-voice/ambience/`)

- **DEMAND** noise database - Thiemann, Ito, Vincent (2013), zenodo.org/records/1227121 - CC BY-SA 3.0 (`demand-*.ogg`).
- **Freesound** recordings - authors, links and licences (CC0 / CC BY 3.0 / CC BY 4.0) in `script/text-to-voice/ambience/README.md` and `_sources/` (`fs-*.ogg`).
- **ESC-50** short events - Karol J. Piczak, clips from freesound.org, CC BY-NC 3.0; per-clip sources in `_events/sources.json`.
- `cafe-synth-*.ogg` - made with `make_cafe.py` from TTS voices.
- The TUT Urban Acoustic Scenes 2018 recordings used locally are **not** included (research licence); scenes that relied only on them (the mall) fall back to similar scenes.

Personal study only - don't publish lessons containing these recordings commercially.
