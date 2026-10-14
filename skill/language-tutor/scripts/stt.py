#!/usr/bin/env python3
"""Transcribe a learner's voice message for the language-tutor skill.

Usage
  stt.py --lang fr path/to/voice.m4a
  stt.py --lang fr --whisper-dir <languages-root>/script/voice-to-text voice.ogg
  stt.py --check [--whisper-dir DIR]     # report which backends work here

Backends, tried in order (force one with --backend):
  cpp     - whisper.cpp: a built `whisper-cli` plus a ggml model file. Found via
            --whisper-dir, $WHISPER_CPP_DIR, or automatically: any folder named
            script/voice-to-text or scripts/voice-to-text next to/above the audio
            file or the current directory (the learner's languages root keeps
            one there). Layout expected in that folder:
                whisper.cpp/build/bin/whisper-cli   (or whisper-cli on PATH)
                models/ggml-<size>.bin              (small > base > tiny preferred)
            Gives per-token confidence. Works offline once the model is there.
  faster  - `pip install faster-whisper`; downloads a model on first use (needs
            Hugging Face access); per-word confidence
  whisper - `pip install openai-whisper`; same idea, slower

Output (JSON on stdout):
  {"backend": ..., "model": ..., "language": ..., "text": ...,
   "words": [{"w": ..., "p": 0.93}, ...], "low_confidence": [...]}

Two cautions for the tutor:
- Low-confidence words are a *hint* for pronunciation feedback (the recognizer
  struggled: often mispronounced, mumbled or noisy). Never present them as a
  certain diagnosis.
- Whisper is trained on fluent speech and tends to "repair" grammar (e.g. hears
  "je ne aime" and writes "je n'aime"). A clean transcript does not prove the
  learner spoke correctly. Show the transcript and ask the learner to confirm or
  fix it before grading grammar.

Exit code 2 = no backend worked; the tutor then asks the learner to type or
dictate what they said and says that pronunciation feedback will be limited.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

LOW = 0.6  # word probability below this counts as "unsure"
MODEL_PREF = ["large-v3-turbo", "medium", "small", "base", "tiny"]


# ---------------------------------------------------------------- discovery

def candidate_dirs(audio, explicit):
    seen, out = set(), []

    def add(p):
        if p and os.path.isdir(p) and os.path.realpath(p) not in seen:
            seen.add(os.path.realpath(p))
            out.append(p)

    add(explicit)
    add(os.environ.get("WHISPER_CPP_DIR"))
    add(os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice-to-text"))
    starts = [os.path.dirname(os.path.abspath(audio))] if audio else []
    starts.append(os.getcwd())
    for s in starts:
        cur = s
        for _ in range(8):
            for sub in ("script/voice-to-text", "scripts/voice-to-text", "voice-to-text"):
                add(os.path.join(cur, sub))
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    # also a mounted languages root, e.g. $HOME/mnt/<Languages>/script/voice-to-text
    mnt = os.path.join(os.path.expanduser("~"), "mnt")
    if os.path.isdir(mnt):
        for name in os.listdir(mnt):
            for sub in ("script/voice-to-text", "scripts/voice-to-text"):
                add(os.path.join(mnt, name, sub))
    return out


def find_cpp(audio, explicit_dir, explicit_model):
    exe = model = None
    for d in candidate_dirs(audio, explicit_dir):
        for rel in ("whisper.cpp/build/bin/whisper-cli", "build/bin/whisper-cli", "whisper-cli"):
            p = os.path.join(d, rel)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                exe = exe or p
        mdir = os.path.join(d, "models")
        if not model and os.path.isdir(mdir):
            bins = [f for f in os.listdir(mdir) if f.startswith("ggml-") and f.endswith(".bin")
                    and not f.startswith("ggml-for-tests") and os.path.getsize(os.path.join(mdir, f)) > 10_000_000]
            for size in MODEL_PREF:
                hit = [f for f in bins if f[5:-4].split(".")[0].split("-q")[0] == size or f[5:-4] == size]
                if hit:
                    model = os.path.join(mdir, sorted(hit)[0])
                    break
        if exe and model:
            break
    exe = exe or next((shutil.which(x) for x in ("whisper-cli", "whisper-cpp") if shutil.which(x)), None)
    model = explicit_model or os.environ.get("WHISPER_CPP_MODEL") or model
    return exe, model


# ---------------------------------------------------------------- backends

def run_cpp(path, lang, _size, a):
    exe, model = find_cpp(path, a.whisper_dir, a.model)
    if not exe or not model:
        raise RuntimeError(f"whisper.cpp not found (binary={exe}, model={model})")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg needed to convert audio to 16 kHz wav")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "in.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ar", "16000", "-ac", "1",
                        "-c:a", "pcm_s16le", wav], check=True)
        base = os.path.join(tmp, "out")
        cmd = [exe, "-m", model, "-f", wav, "-l", lang or "auto", "-t", os.environ.get("STT_THREADS") or str(os.cpu_count() or 4),
               "-ojf", "-of", base, "-np"]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(base + ".json", encoding="utf-8") as fh:
            data = json.load(fh)
    words, text = [], []
    for seg in data.get("transcription", []):
        text.append(seg.get("text", "").strip())
        cur = None
        for t in seg.get("tokens", []):
            tx = t.get("text", "")
            if tx.startswith("[_") or (tx.startswith("[") and tx.endswith("]")):
                continue
            if cur is None or tx.startswith(" "):
                if cur and cur["w"].strip():
                    words.append(cur)
                cur = {"w": tx.strip(), "ps": [t.get("p", 1.0)]}
            else:
                cur["w"] += tx
                cur["ps"].append(t.get("p", 1.0))
        if cur and cur["w"].strip():
            words.append(cur)
    words = [{"w": w["w"], "p": round(min(w["ps"]), 2)} for w in words
             if any(ch.isalnum() for ch in w["w"])]
    detected = (data.get("result") or {}).get("language") or lang
    return {"language": detected, "text": " ".join(x for x in text if x), "words": words,
            "model": os.path.basename(model)}


def run_faster(path, lang, size, _a):
    from faster_whisper import WhisperModel
    m = WhisperModel(size, device="cpu", compute_type="int8")
    segs, info = m.transcribe(path, language=lang, word_timestamps=True, vad_filter=True)
    words, text = [], []
    for s in segs:
        text.append(s.text.strip())
        for w in (s.words or []):
            words.append({"w": w.word.strip(), "p": round(w.probability, 2)})
    return {"language": info.language, "text": " ".join(text), "words": words, "model": size}


def run_whisper(path, lang, size, _a):
    import whisper
    m = whisper.load_model(size)
    r = m.transcribe(path, language=lang, word_timestamps=True)
    words = [{"w": w["word"].strip(), "p": round(w.get("probability", 1.0), 2)}
             for s in r.get("segments", []) for w in s.get("words", [])]
    return {"language": r.get("language"), "text": r["text"].strip(), "words": words, "model": size}


BACKENDS = {"cpp": run_cpp, "faster": run_faster, "whisper": run_whisper}


def check(a):
    exe, model = find_cpp(None, a.whisper_dir, a.model)
    rep = {"cpp": f"ready: {exe} + {model}" if exe and model else f"not ready (binary={exe}, model={model})"}
    for mod, name, pkg in (("faster_whisper", "faster", "faster-whisper"), ("whisper", "whisper", "openai-whisper")):
        try:
            __import__(mod)
            rep[name] = "installed (model download may still be needed on first use)"
        except Exception:  # noqa
            rep[name] = f"not installed: pip install {pkg}"
    rep["ffmpeg"] = "ok" if shutil.which("ffmpeg") else "missing"
    print(json.dumps(rep, indent=1))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("audio", nargs="?")
    p.add_argument("--lang", help="ISO 639-1 code of the language spoken (fr, es, de, ...)")
    p.add_argument("--whisper-dir", help="folder holding whisper.cpp/ and models/ (e.g. <languages>/script/voice-to-text)")
    p.add_argument("--model", help="explicit ggml model file for whisper.cpp")
    p.add_argument("--size", default="small", help="model size for faster-whisper/openai-whisper")
    p.add_argument("--backend", choices=["auto"] + list(BACKENDS), default="auto")
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    if a.check:
        return check(a)
    if not a.audio:
        p.error("audio path required")
    order = list(BACKENDS) if a.backend == "auto" else [a.backend]
    errors = {}
    for name in order:
        try:
            r = BACKENDS[name](a.audio, a.lang, a.size, a)
            r["backend"] = name
            r["low_confidence"] = [w["w"] for w in r["words"] if w["p"] < LOW]
            print(json.dumps(r, ensure_ascii=False, indent=1))
            return
        except Exception as e:  # noqa
            errors[name] = f"{type(e).__name__}: {str(e)[:200]}"
    print(json.dumps({"error": "no speech-to-text backend worked", "details": errors}, indent=1))
    sys.exit(2)


if __name__ == "__main__":
    main()
