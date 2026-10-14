# Voice-to-text for the language tutor (whisper.cpp)

Offline speech recognition used by `../stt.py` to transcribe speaking exercises and voice messages.

| Path | What | In git |
|---|---|---|
| `models/ggml-small.bin` | multilingual "small" model, 466 MiB (SHA1 `55356645c2b361a969dfd0ef2c5a50d530afd8d5`) - better on accented speech, ~4 s per short clip | no - `sh ../../setup/download_models.sh whisper` |
| `whisper.cpp/build/bin/whisper-cli` | the recognizer, built for the machine that runs it (the Claude desktop workspace is Linux; a Mac build won't run there) | no - `sh ../../setup/build_whisper.sh` |

`stt.py` picks the best model present (medium > small > base > tiny): add `ggml-base.bin` for speed or `ggml-medium.bin` for accuracy (huggingface.co/ggerganov/whisper.cpp). Without whisper.cpp it can also use `faster-whisper` (`pip install faster-whisper`).

## Use

```
python3 ../stt.py --check
python3 ../stt.py --lang fr path/to/recording.m4a
```

It prints JSON: the transcript, per-word confidence and the low-confidence words (likely pronunciation trouble spots).
