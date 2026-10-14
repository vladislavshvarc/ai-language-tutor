#!/usr/bin/env python3
"""Turn a listening text, dialogue or word list into audio for the language-tutor skill.

Usage
  tts.py --lang fr --out listening.webm --file dialogue.txt      # one joined file
  tts.py --lang fr --out-dir clips/ --each --file words.txt       # one file per line
  tts.py --lang es --out word.webm --text "la panadería"
  tts.py --lang fr --list-voices      # voices installed here
  tts.py --check                      # which backends work here

Input: one line per turn/item. "Speaker: text" lines are dialogue turns - each
distinct speaker gets a different voice (alternating female/male). Lines without
"Speaker:" are read by the narrator voice. With --each every line becomes its own
file (word lists, example sentences: ONE word or ONE sentence per clip) and
--vary rotates the voice from line to line.

Local neural voices (offline, natural) - all found under `text-to-voice/models`
next to this script, under a mounted languages root, or via --models-dir:
  kokoro - Kokoro-82M: kokoro-v1.0.int8.onnx + voices-v1.0.bin; `pip install
           kokoro-onnx soundfile`. fr, es, it, pt, en, ja, zh, hi (not de/ru);
           French has one voice (ff_siwis).
  supertonic - Supertonic 3 (ONNX, fast on CPU): `pip install supertonic`
           + models/supertonic-3/{onnx/, voice_styles/} (Supertone/supertonic-3 on
           huggingface.co). 31 languages incl. fr, de, es, it, ru, uk; 10 voices
           F1-F5 (female), M1-M5 (male) shared by all languages.
  chatterbox - Chatterbox Multilingual (PyTorch 2.6, installed once into script/.env/ by setup_engines.sh):
           models/chatterbox/ + voices/<name>.wav reference clips (+ voices.json with
           gender); ~10 s of work per second of audio. 23 languages.
  Chatterbox runs in a separate worker process (engines/chatterbox_worker.py; it needs most
  of the sandbox's RAM). Finished clips are cached in
  ~/.cache/tts-clips, and a run stops starting new slow clips after --budget seconds
  (default 140) with exit code 3: run the SAME command again to continue.
Casting (learner's choice 2026-10-09; XTTS-v2, MeloTTS and Piper were removed):
  dialogues  - Chatterbox voices first (they sit in a room best), then Supertonic and Kokoro;
  --each     - word lists and example sentences use Supertonic only (fast); --all-voices
               lets every engine take part.
The
voice choice is seeded by the text: the same text always sounds the same, a new
dialogue gets a different mix. Force voices with --voice, or per speaker with --voices "Serveur=m,Cliente=f"
(any voice of that gender) or "Léa=supertonic:F1" (that exact voice).

Fallbacks when no local voice exists: edge (internet), gtts (internet), say
(macOS), espeak (robotic). --backend forces one of: local, supertonic, kokoro, chatterbox, edge,
gtts, say, espeak.

Output format follows the extension (.webm = Opus, what the workbook stores;
.mp3, .wav, .m4a). Needs ffmpeg for joining/converting.

--verify transcribes every output with stt.py (next to this script) and reports
what a listener hears and a word-match score; regenerate anything below ~0.85
with another --voice / --seed.

--ambience <scene> places the dialogue into a recorded background (cafe, hotel, airport,
street, metro, airplane, park... - ambience.py --list): every speaker gets the same room
(reverb sized for the place), a tone shaped like a voice recorded in a room, a stereo
place, the level's pace (+-5 %, pauses included) and natural turn gaps; --level A1
(or --snr dB) sets how loud the background is. Output is stereo.

Dialogue text: write it like people talk - 1-3 hesitations per dialogue ("Euh…",
"Alors…", "Bon,", a name trailing off "Monsieur Benali…", "Ah bon ?") - the voices
render them and it is what made the hotel dialogue sound real (2026-10-09).

Exit code 0 = audio written (JSON printed: backend, files, voices).
Exit code 2 = nothing worked; fall back to the read-once text version.
Exit code 3 = not finished within --budget (slow engines); run the same command again.
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata


def env_dir(name):
    """The engine packages installed once into the languages folder by setup_engines.sh:
    script/.env/<name>-N with a .ok stamp for this Python (see that script). None if not installed."""
    import platform
    tag = "py%d.%d-%s" % (sys.version_info[0], sys.version_info[1], platform.machine())
    here = os.path.dirname(os.path.abspath(__file__))
    roots = [os.path.join(here, ".env")]
    mnt = os.path.join(os.path.expanduser("~"), "mnt")
    if os.path.isdir(mnt):
        roots += [os.path.join(mnt, n, "script", ".env") for n in sorted(os.listdir(mnt))]
    for r in roots:
        if not os.path.isdir(r):
            continue
        for d in sorted(os.listdir(r), reverse=True):
            p = os.path.join(r, d, ".ok")
            if d.startswith(name + "-") and os.path.exists(p) and open(p).read().strip() == tag:
                return os.path.join(r, d)
    return None


_FAST = env_dir("fast")
if _FAST and _FAST not in sys.path:
    sys.path.insert(0, _FAST)

EDGE_VOICES = {  # (female, male)
    "fr": ("fr-FR-DeniseNeural", "fr-FR-HenriNeural"),
    "es": ("es-ES-ElviraNeural", "es-ES-AlvaroNeural"),
    "de": ("de-DE-KatjaNeural", "de-DE-ConradNeural"),
    "it": ("it-IT-ElsaNeural", "it-IT-DiegoNeural"),
    "pt": ("pt-PT-RaquelNeural", "pt-PT-DuarteNeural"),
    "en": ("en-GB-SoniaNeural", "en-GB-RyanNeural"),
    "ru": ("ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"),
}
SAY_VOICES = {"fr": ("Amélie", "Thomas"), "es": ("Mónica", "Jorge"), "de": ("Anna", "Markus"),
              "it": ("Alice", "Luca"), "en": ("Samantha", "Daniel"), "ru": ("Milena", "Yuri")}

KOKORO = {  # lang -> (kokoro lang code, [(voice, gender)])
    "fr": ("fr-fr", [("ff_siwis", "f")]),
    "es": ("es", [("ef_dora", "f"), ("em_alex", "m")]),
    "it": ("it", [("if_sara", "f"), ("im_nicola", "m")]),
    "pt": ("pt-br", [("pf_dora", "f"), ("pm_alex", "m")]),
    "en": ("en-gb", [("bf_emma", "f"), ("bm_george", "m")]),
    "ja": ("ja", [("jf_alpha", "f"), ("jm_kumo", "m")]),
    "zh": ("cmn", [("zf_xiaoxiao", "f"), ("zm_yunxi", "m")]),
    "hi": ("hi", [("hf_alpha", "f"), ("hm_omega", "m")]),
}
MODELS_DIR = None  # set from --models-dir
VENVS = os.path.join(os.path.expanduser("~"), ".venvs")
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "tts-clips")
WORKER_ENGINES = ("chatterbox",)          # runs in its own venv + process
EACH_ENGINES = ("supertonic",)            # word lists / example sentences: fast, one clip per line


def model_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [MODELS_DIR, os.environ.get("KOKORO_MODELS"), os.environ.get("TTS_MODELS"),
             os.path.join(here, "text-to-voice", "models")]
    mnt = os.path.join(os.path.expanduser("~"), "mnt")
    if os.path.isdir(mnt):
        for n in sorted(os.listdir(mnt)):
            cands += [os.path.join(mnt, n, "script", "text-to-voice", "models"),
                      os.path.join(mnt, n, "scripts", "text-to-voice", "models")]
    cur = os.getcwd()
    for _ in range(6):
        cands.append(os.path.join(cur, "script", "text-to-voice", "models"))
        cur = os.path.dirname(cur)
    seen, out = set(), []
    for c in cands:
        if c and os.path.isdir(c) and os.path.realpath(c) not in seen:
            seen.add(os.path.realpath(c))
            out.append(c)
    return out


def find_kokoro_models():
    for c in model_dirs():
        onnx = sorted(f for f in os.listdir(c) if f.startswith("kokoro") and f.endswith(".onnx"))
        if onnx and os.path.exists(os.path.join(c, "voices-v1.0.bin")):
            return os.path.join(c, onnx[0]), os.path.join(c, "voices-v1.0.bin")
    raise RuntimeError("Kokoro model files not found")


SUPERTONIC_LANGS = set("en ko ja ar bg cs da de el es et fi fr hi hr hu id it lt lv nl pl pt ro ru sk sl sv tr uk vi".split())


def supertonic_dir():
    for c in model_dirs():
        d = os.path.join(c, "supertonic-3")
        if os.path.exists(os.path.join(d, "onnx", "vector_estimator.onnx")):
            return d
    raise RuntimeError("Supertonic 3 model files not found")


def engine_dir(sub):
    """models/<sub> holding a voices.json, the worker script and its venv - or None."""
    for c in model_dirs():
        d = os.path.join(c, sub)
        if os.path.isdir(d):
            return d
    return None


def worker_voices(engine, lang):
    sub = {"chatterbox": "chatterbox"}[engine]
    d = engine_dir(sub)
    pp = env_dir(engine)  # installed once into the languages folder (setup_engines.sh) ...
    py = sys.executable if pp else os.path.join(VENVS, engine, "bin", "python")  # ... or an old per-session venv
    script = os.path.join(os.path.dirname(os.path.dirname(d or "/x")), "engines", f"{engine}_worker.py") if d else ""
    vj = os.path.join(d or "", "voices.json")
    if not (d and os.path.exists(py) and os.path.exists(script) and os.path.exists(vj)):
        return []
    out = []
    for v in json.load(open(vj, encoding="utf-8")).get("voices", []):
        if v.get("use", True) is False or lang not in v.get("langs", [lang]):
            continue
        if engine == "chatterbox" and not any(os.path.exists(os.path.join(d, "voices", v["name"] + x)) for x in (".wav", ".pt")):
            continue  # listed but its reference clip isn't installed here (e.g. a fresh clone)
        out.append(dict(id=f"{engine}:{v['name'].replace(' ', '_')}", engine=engine, name=v["name"],
                        gender=v.get("gender", "?"), model_dir=d, python=py, pythonpath=pp, script=script,
                        slow=bool(v.get("slow"))))
    return out


def cast_for(lang, engines=("supertonic", "kokoro", "chatterbox")):
    """Every installed local voice for this language: [dict(id, engine, gender, ...)]."""
    voices = []
    if "supertonic" in engines and lang in SUPERTONIC_LANGS:
        try:
            import importlib.util
            d = supertonic_dir()
            if importlib.util.find_spec("supertonic"):
                for f in sorted(os.listdir(os.path.join(d, "voice_styles"))):
                    if f.endswith(".json"):
                        n = f[:-5]
                        voices.append(dict(id=f"supertonic:{n}", engine="supertonic", name=n,
                                           gender="f" if n.startswith("F") else "m"))
        except Exception:  # noqa
            pass
    if "kokoro" in engines and lang in KOKORO:
        try:
            find_kokoro_models()
            import kokoro_onnx  # noqa
            for name, g in KOKORO[lang][1]:
                voices.append(dict(id=f"kokoro:{name}", engine="kokoro", name=name, gender=g))
        except Exception:  # noqa
            pass
    for eng in WORKER_ENGINES:
        if eng in engines:
            try:
                voices += worker_voices(eng, lang)
            except Exception:  # noqa
                pass
    return voices


def parse_turns(text):
    turns = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([^:]{1,25}):\s+(.+)$", line)
        turns.append((m.group(1).strip(), m.group(2).strip()) if m else ("_narrator", line))
    return turns


NATURAL = ("supertonic", "kokoro", "chatterbox")


def assign_voices(turns, cast, seed, forced, vary, all_voices=False):
    """Return one voice dict per turn."""
    by_id = {v["id"]: v for v in cast}
    if not cast:
        raise RuntimeError("no local voices")
    h = int(hashlib.sha1(seed.encode("utf-8")).hexdigest(), 16)
    natural = [v for v in cast if v["engine"] in NATURAL]
    # Chatterbox first in dialogues: with the lively style and the scene placement its voices sat in the room
    # best (learner, 2026-10-09). Its voices are reference clips of native readers and of the voices the
    # learner rated great (Supertonic F4/M1/M3, Kokoro ff_siwis) - models/chatterbox/voices.json.
    FIRST = ("chatterbox",)
    n_speakers = len({spk for spk, _ in turns if forced.get(spk, "m") in ("m", "f")})
    if natural and (n_speakers <= len(natural) or vary):
        def tiers(g, hh):
            vs = [v for v in natural if v["gender"] == g]
            # voices marked "slow" in voices.json come last: their lines often had to be voiced again
            return (_by_engine([v for v in vs if v["engine"] in FIRST and not v.get("slow")], hh) +
                    _by_engine([v for v in vs if v["engine"] not in FIRST and not v.get("slow")], hh) +
                    _by_engine([v for v in vs if v.get("slow")], hh))
        nf, nm = tiers("f", h), tiers("m", h // 7)
        a, b = (nf, nm) if (h // 13) % 2 == 0 else (nm, nf)
        order = []
        for i in range(max(len(a), len(b))):
            order += ([a[i]] if i < len(a) else []) + ([b[i]] if i < len(b) else [])
        return _pick(turns, order, forced, vary, by_id)
    fem = [v for v in cast if v["gender"] == "f"]
    mal = [v for v in cast if v["gender"] != "f"]
    if fem:
        fem = fem[h % len(fem):] + fem[:h % len(fem)]
    if mal:
        mal = mal[(h // 7) % len(mal):] + mal[:(h // 7) % len(mal)]
    # interleave so consecutive speakers differ in gender where possible
    order, start_f = [], (h // 13) % 2 == 0
    a, b = (fem, mal) if start_f else (mal, fem)
    for i in range(max(len(a), len(b))):
        order += ([a[i]] if i < len(a) else []) + ([b[i]] if i < len(b) else [])
    return _pick(turns, order, forced, vary, by_id)


def _by_engine(voices, h):
    """Round-robin over engines (engine order and the voice within each engine seeded by h)."""
    groups = {}
    for v in voices:
        groups.setdefault(v["engine"], []).append(v)
    engines = sorted(groups)
    if not engines:
        return []
    k = h % len(engines)
    engines = engines[k:] + engines[:k]
    for e in engines:
        g = groups[e]
        j = (h // 11) % len(g)
        groups[e] = g[j:] + g[:j]
    out, i = [], 0
    while any(groups[e] for e in engines):
        e = engines[i % len(engines)]
        if groups[e]:
            out.append(groups[e].pop(0))
        i += 1
    return out


def _pick(turns, order, forced, vary, by_id):
    """forced[speaker] is a voice id, or "m"/"f" = any unused voice of that gender."""
    speakers, out, used = {}, [], set()
    for spk, v in forced.items():
        if v not in ("m", "f"):
            used.add(v)
    for k, (spk, _) in enumerate(turns):
        if spk in forced and forced[spk] not in ("m", "f"):
            v = forced[spk]
        elif vary and spk == "_narrator" and spk not in forced:
            v = order[k % len(order)]
        else:
            if spk not in speakers:
                want = forced.get(spk)
                pool = [x for x in order if x["id"] not in used and (want is None or x["gender"] == want)] \
                    or [x for x in order if want is None or x["gender"] == want] or order
                speakers[spk] = pool[0]
                used.add(pool[0]["id"])
            v = speakers[spk]
        if isinstance(v, str):
            if v not in by_id:
                raise RuntimeError(f"voice {v} not installed (try --list-voices)")
            v = by_id[v]
        out.append(v)
    return out


# ---------- synthesis ----------
_KOKORO, _SUPER = None, None


def synth_local(voice, text, lang, slow, path):
    import soundfile as sf
    global _KOKORO, _SUPER
    if voice["engine"] == "supertonic":
        import numpy as np
        if _SUPER is None:
            os.environ["SUPERTONIC_CACHE_DIR"] = supertonic_dir()
            from supertonic import TTS as _ST
            _SUPER = _ST(auto_download=False)
        wav, _ = _SUPER.synthesize(text=text, lang=lang, voice_style=_SUPER.get_voice_style(voice_name=voice["name"]),
                                   speed=0.9 if slow else 1.05)
        sf.write(path, np.asarray(wav, dtype=np.float32).reshape(-1), _SUPER.sample_rate)
        return path
    if voice["engine"] == "kokoro":
        if _KOKORO is None:
            from kokoro_onnx import Kokoro
            _KOKORO = Kokoro(*find_kokoro_models())
        samples, sr = _KOKORO.create(text, voice=voice["name"], speed=0.85 if slow else 1.0,
                                     lang=KOKORO[lang][0])
    else:
        raise RuntimeError(f"unknown local engine {voice['engine']}")
    sf.write(path, samples, sr)
    return path


class Incomplete(Exception):
    pass


# Chatterbox with its defaults sounded slow and over-articulated; these were "great" in a scene (2026-10-09):
# more expression, a looser hold on the reference clip (natural pace, no word-by-word pauses), a bit less
# randomness (fewer artefacts).
CHATTERBOX_STYLE = {"exaggeration": 0.6, "cfg_weight": 0.3, "temperature": 0.7}
SCENE = False   # set for --ambience dialogues: pace is evened out in ambience.scene_dialogue


def clip_key(voice, text, lang, slow):
    style = "lively1" if voice["engine"] == "chatterbox" else ""
    k = "|".join([voice["id"], lang, "slow" if slow and voice["engine"] != "chatterbox" else "", style, text])
    return os.path.join(CACHE, hashlib.sha1(k.encode("utf-8")).hexdigest()[:20] + ".wav")


def run_workers(jobs, lang, deadline):
    """jobs: [(voice, text, cache_path)] for chatterbox. Returns how many are still missing."""
    import time
    missing = 0
    for eng in WORKER_ENGINES:
        todo = [(v, t, p) for v, t, p in jobs if v["engine"] == eng and not os.path.exists(p)]
        if not todo:
            continue
        left = deadline - time.time()
        if left < 30:
            missing += len(todo)
            continue
        v0 = todo[0][0]
        job = {"model_dir": v0["model_dir"], "lang": lang, "budget_s": max(5, left - 25),
               "style": CHATTERBOX_STYLE if eng == "chatterbox" else {},
               "items": [{"text": t, "voice": v["name"], "out": p, "slow": bool(SLOW_FLAG)} for v, t, p in todo]}
        jf = os.path.join(CACHE, f"job-{eng}.json")
        json.dump(job, open(jf, "w", encoding="utf-8"), ensure_ascii=False)
        env = dict(os.environ, PYTHONWARNINGS="ignore")
        if v0.get("pythonpath"):
            env["PYTHONPATH"] = v0["pythonpath"]
        r = subprocess.run([v0["python"], v0["script"], jf], capture_output=True, text=True, env=env,
                           timeout=max(60, left + 120))
        if r.returncode != 0 and "remaining" not in r.stdout:
            raise RuntimeError(f"{eng} worker failed: {r.stderr.strip()[-300:]}")
        missing += sum(1 for _, _, p in todo if not os.path.exists(p))
    return missing


SLOW_FLAG = False


def run_local(turns, lang, tmp, slow, engines, seed, forced, vary, all_voices=False, deadline=None):
    import time
    global SLOW_FLAG
    SLOW_FLAG = slow
    os.makedirs(CACHE, exist_ok=True)
    cast = cast_for(lang, engines)
    voices = assign_voices(turns, cast, seed, forced, vary, all_voices)
    paths = [clip_key(v, txt, lang, slow) for (_, txt), v in zip(turns, voices)]
    # slow engines first, in their own processes, before this process loads any model (RAM)
    jobs = [(v, txt, p) for (_, txt), v, p in zip(turns, voices, paths) if v["engine"] in WORKER_ENGINES]
    if jobs:
        left = run_workers(jobs, lang, deadline or time.time() + 1e9)
        if left:
            done = sum(1 for p in paths if os.path.exists(p))
            raise Incomplete(json.dumps({"incomplete": True, "clips_done": done, "clips_left": left,
                                         "next": "run the same command again to continue"}))
    files = []
    for i, ((_, txt), v, p) in enumerate(zip(turns, voices, paths)):
        if not os.path.exists(p):
            synth_local(v, txt, lang, slow, p + ".part.wav")
            os.replace(p + ".part.wav", p)
        f = p
        if slow and not SCENE and v["engine"] == "chatterbox" and shutil.which("ffmpeg"):  # no speed control there
            f = os.path.join(tmp, f"slow{i:03d}.wav")
            ffmpeg("-i", p, "-filter:a", "atempo=0.88", f)
        files.append(f)
    return files, "wav", [v["id"] for v in voices]


def run_edge(turns, lang, tmp, slow):
    import edge_tts  # noqa
    voices = EDGE_VOICES.get(lang)
    if not voices:
        raise RuntimeError(f"no edge voice configured for {lang}")
    order, files, used = [], [], []

    async def go():
        for i, (spk, txt) in enumerate(turns):
            if spk not in order:
                order.append(spk)
            v = voices[order.index(spk) % 2]
            f = os.path.join(tmp, f"seg{i:03d}.mp3")
            await edge_tts.Communicate(txt, v, rate="-20%" if slow else "+0%").save(f)
            files.append(f)
            used.append("edge:" + v)
    asyncio.run(go())
    return files, "mp3", used


def run_gtts(turns, lang, tmp, slow):
    from gtts import gTTS
    files = []
    for i, (_, txt) in enumerate(turns):
        f = os.path.join(tmp, f"seg{i:03d}.mp3")
        gTTS(txt, lang=lang, slow=slow).save(f)
        files.append(f)
    return files, "mp3", ["gtts"] * len(files)


def run_say(turns, lang, tmp, slow):
    if not shutil.which("say"):
        raise RuntimeError("macOS `say` not available")
    voices = SAY_VOICES.get(lang)
    order, files, used = [], [], []
    for i, (spk, txt) in enumerate(turns):
        if spk not in order:
            order.append(spk)
        f = os.path.join(tmp, f"seg{i:03d}.aiff")
        cmd = ["say", "-o", f]
        if voices:
            cmd += ["-v", voices[order.index(spk) % 2]]
        if slow:
            cmd += ["-r", "140"]
        subprocess.run(cmd + [txt], check=True, capture_output=True)
        files.append(f)
        used.append("say")
    return files, "aiff", used


def run_espeak(turns, lang, tmp, slow):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("espeak-ng not installed")
    order, files = [], []
    for i, (spk, txt) in enumerate(turns):
        if spk not in order:
            order.append(spk)
        f = os.path.join(tmp, f"seg{i:03d}.wav")
        variant = "+f3" if order.index(spk) % 2 == 0 else "+m3"
        subprocess.run([exe, "-v", lang + variant, "-s", "120" if slow else "150", "-w", f, txt],
                       check=True, capture_output=True)
        files.append(f)
    return files, "wav", ["espeak"] * len(files)


FALLBACKS = {"edge": run_edge, "gtts": run_gtts, "say": run_say, "espeak": run_espeak}
LOCAL = {"local": ("supertonic", "kokoro", "chatterbox"), "supertonic": ("supertonic",),
         "kokoro": ("kokoro",), "chatterbox": ("chatterbox",)}


# ---------- output ----------
def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def encode(src, dst):
    ext = os.path.splitext(dst)[1].lower()
    if ext == os.path.splitext(src)[1].lower() or not shutil.which("ffmpeg"):
        shutil.copy(src, dst if ext == os.path.splitext(src)[1].lower() else os.path.splitext(dst)[0] + os.path.splitext(src)[1])
        return dst
    codec = {".webm": ["-c:a", "libopus", "-b:a", "48k"], ".mp3": ["-c:a", "libmp3lame", "-q:a", "4"],
             ".m4a": ["-c:a", "aac", "-b:a", "96k"], ".ogg": ["-c:a", "libopus", "-b:a", "48k"]}.get(ext, [])
    ffmpeg("-i", src, *codec, dst)
    return dst


def join(files, out, pause=0.6):
    if len(files) == 1:
        return [encode(files[0], out)]
    if not shutil.which("ffmpeg"):
        base, ext = os.path.splitext(out)
        outs = []
        for i, f in enumerate(files, 1):
            p = f"{base}_{i:02d}{os.path.splitext(f)[1]}"
            shutil.copy(f, p)
            outs.append(p)
        return outs
    tmp = os.path.dirname(files[0])
    sil = os.path.join(tmp, "silence.wav")
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(pause), "-c:a", "pcm_s16le", sil)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        for i, f in enumerate(files):
            n = os.path.join(tmp, f"n{i:03d}.wav")
            ffmpeg("-i", f, "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", n)
            if i:
                fh.write(f"file '{sil}'\n")
            fh.write(f"file '{n}'\n")
    joined = os.path.join(tmp, "joined.wav")
    ffmpeg("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined)
    return [encode(joined, out)]


def _words(t):
    t = unicodedata.normalize("NFC", t.lower())
    return re.findall(r"[^\W\d_]+|\d+", t)


NUMS = {"fr": {"un": "1", "une": "1", "deux": "2", "trois": "3", "quatre": "4", "cinq": "5", "six": "6",
               "sept": "7", "huit": "8", "neuf": "9", "dix": "10", "onze": "11", "douze": "12",
               "quinze": "15", "vingt": "20", "trente": "30", "cent": "100", "premier": "1", "première": "1"}}


def verify_many(jobs, lang, workers=2):
    """verify() for [(path, text)] - two transcriptions at a time (each with half the cores; the
    'small' model needs ~0.6 GB, so more in parallel risks running out of memory)."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda j: verify(j[0], j[1], lang, threads=max(1, (os.cpu_count() or 4) // workers)), jobs))


def verify(path, text, lang, threads=None):
    """Transcribe with stt.py and compare with the text that was spoken."""
    import difflib
    stt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stt.py")
    env = dict(os.environ, STT_THREADS=str(threads)) if threads else None
    try:
        r = subprocess.run([sys.executable, stt, "--lang", lang, path], capture_output=True, text=True, timeout=300, env=env)
        heard = json.loads(r.stdout).get("text", "")
    except Exception as e:  # noqa
        return {"error": f"{type(e).__name__}: {str(e)[:80]}"}
    nums = NUMS.get(lang, {})
    heard = re.sub(r"(\d+)(?:er|re|ère|ème|e)\b", r"\1", heard)  # "1er étage" = "premier étage"
    a = [nums.get(w, w) for w in _words(text)]
    b = [nums.get(w, w) for w in _words(heard)]
    return {"heard": heard.strip(), "match": round(difflib.SequenceMatcher(None, a, b).ratio(), 2)}


def slug(text, n=40):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:n] or "clip"


def synthesize(turns, a, tmp, forced):
    import time
    errors = {}
    deadline = START + a.budget
    order = ["local", "edge", "gtts", "say", "espeak"] if a.backend == "auto" else [a.backend]
    seed = a.seed or "\n".join(t for _, t in turns)
    for name in order:
        try:
            if name in LOCAL:
                engines = LOCAL[name]
                exact = any(":" in v for v in forced.values())
                if a.each and name == "local" and not a.all_voices and not exact:
                    engines = EACH_ENGINES  # word lists: Supertonic only (fast)
                return name, *run_local(turns, a.lang, tmp, a.slow, engines, seed, forced, a.vary,
                                        a.all_voices, deadline)
            return name, *FALLBACKS[name](turns, a.lang, tmp, a.slow)
        except Incomplete:
            raise
        except Exception as e:  # noqa
            errors[name] = f"{type(e).__name__}: {str(e)[:160]}"
    raise RuntimeError(json.dumps(errors))


import time as _time  # noqa: E402
START = _time.time()


def check():
    report = {}
    for lang in ("fr", "es", "de", "en"):
        report[f"local voices {lang}"] = [v["id"] for v in cast_for(lang)] or "none"
    for name, fn in FALLBACKS.items():
        with tempfile.TemporaryDirectory() as tmp:
            try:
                fn([("_", "test")], "en", tmp, False)
                report[name] = "ok"
            except Exception as e:  # noqa
                report[name] = f"unavailable: {type(e).__name__}: {str(e)[:100]}"
    report["ffmpeg"] = "ok" if shutil.which("ffmpeg") else "missing (segments won't be joined/converted)"
    print(json.dumps(report, indent=1, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lang", help="ISO 639-1 code: fr, es, de, it, ...")
    p.add_argument("--out", help="joined output file, e.g. course/audio/P2/dialogue.webm")
    p.add_argument("--out-dir", help="with --each: folder for the per-line files")
    p.add_argument("--each", action="store_true", help="one file per line (word lists, example sentences)")
    p.add_argument("--vary", action="store_true", help="rotate the voice from line to line (narrator lines)")
    p.add_argument("--format", default="webm", help="with --each: file extension (webm, mp3, wav, m4a)")
    p.add_argument("--text")
    p.add_argument("--file")
    p.add_argument("--backend", choices=["auto", "local", "supertonic", "kokoro", "chatterbox"] + list(FALLBACKS), default="auto")
    p.add_argument("--voices", help='speaker=voice or speaker=m/f, e.g. "Serveur=m,Léa=f" or "Léa=supertonic:F1"')
    p.add_argument("--voice", help="one voice for every line, e.g. supertonic:M5")
    p.add_argument("--seed", help="change to get a different voice mix for the same text")
    p.add_argument("--slow", action="store_true", help="slower speech for A0-A2")
    p.add_argument("--verify", action="store_true", help="transcribe the result with stt.py and score it")
    p.add_argument("--ambience", help="put the joined result into a place: metro, cafe, airport, street, park... (ambience.py --list)")
    p.add_argument("--level", help="with --ambience: learner level A0-C1, sets how loud the background is")
    p.add_argument("--snr", type=float, help="with --ambience: speech above background in dB (overrides --level)")
    p.add_argument("--budget", type=float, default=140, help="seconds to spend on slow engines before stopping (exit 3)")
    p.add_argument("--all-voices", action="store_true", help="with --each: use every engine (default: Supertonic only)")
    p.add_argument("--list-voices", action="store_true")
    p.add_argument("--check", action="store_true")
    p.add_argument("--models-dir", help="folder holding supertonic-3/, kokoro-*.onnx + voices-v1.0.bin, chatterbox/")
    a = p.parse_args()
    global MODELS_DIR, SCENE
    MODELS_DIR = a.models_dir
    SCENE = bool(a.ambience and not a.each)
    if a.check:
        return check()
    if a.list_voices:
        if not a.lang:
            p.error("--list-voices needs --lang")
        return print(json.dumps(cast_for(a.lang), indent=1, ensure_ascii=False))
    if not (a.lang and (a.text or a.file) and (a.out or (a.each and a.out_dir))):
        p.error("--lang, --text/--file and --out (or --each --out-dir) are required")
    text = a.text if a.text is not None else open(a.file, encoding="utf-8").read()
    turns = parse_turns(text)
    forced = {}
    if a.voices:
        for part in a.voices.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                forced[k.strip()] = v.strip()
    if a.voice:
        forced = {spk: a.voice for spk, _ in turns}
    with tempfile.TemporaryDirectory() as tmp:
        try:
            backend, files, ext, used = synthesize(turns, a, tmp, forced)
        except Incomplete as e:
            print(str(e))
            sys.exit(3)
        except RuntimeError as e:
            print(json.dumps({"error": "no TTS backend worked", "details": json.loads(str(e))}, indent=1))
            sys.exit(2)
        if a.each:
            os.makedirs(a.out_dir, exist_ok=True)
            items = []
            for i, (f, (spk, txt), v) in enumerate(zip(files, turns, used), 1):
                dst = os.path.join(a.out_dir, f"{i:02d}-{slug(txt)}.{a.format.lstrip('.')}")
                items.append({"text": txt, "speaker": None if spk == "_narrator" else spk,
                              "file": encode(f, dst), "voice": v})
            if a.verify:
                # single words and short phrases are not checked: without context the recognizer can't
                # tell homophones apart (inviter / invitez) and the check only causes needless re-voicing
                todo = [(k, f, t) for k, (f, (_, t)) in enumerate(zip(files, turns)) if len(_words(t)) >= 3]
                for (k, _, _), r in zip(todo, verify_many([(f, t) for _, f, t in todo], a.lang)):
                    items[k]["check"] = r
            print(json.dumps({"backend": backend, "items": items}, ensure_ascii=False, indent=1))
        else:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            amb = None
            if a.ambience:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import ambience
                # each speaker placed into the scene: tone, shared room, stereo place, pace, turn gaps
                amb = ambience.scene_dialogue(files, [s for s, _ in turns], [t for _, t in turns], a.out, a.ambience,
                                              a.snr, a.level, a.seed)
                outs = [a.out]
            else:
                outs = join(files, a.out)
            res = {"backend": backend, "files": outs, "voices": dict(zip([s for s, _ in turns], used))}
            if amb:
                res["ambience"] = amb
            if a.verify:
                res["check"] = [dict(text=t, voice=v, **r) for (_, t), v, r in
                                zip(turns, used, verify_many([(f, t) for f, (_, t) in zip(files, turns)], a.lang))]
                if amb:  # can a listener still follow it through the background?
                    res["check_with_ambience"] = verify(a.out, " ".join(t for _, t in turns), a.lang)
            print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
