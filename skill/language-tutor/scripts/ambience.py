#!/usr/bin/env python3
"""Put a listening recording into a real place: metro, café, airport, busy street, park...

    ambience.py --list
    ambience.py --scene metro --in dialogue.webm --out listening.webm --level A1
    ambience.py --scene park --in dialogue.wav --out park.webm --snr 12 --seed 3

The background beds live in text-to-voice/ambience/<scene>/*.ogg (about 60 s each, looped with
a crossfade), short sound events in text-to-voice/ambience/_events/<kind>/*.ogg. See the README
there for where each recording comes from and its licence.

Loudness: the speech stays SNR dB above the background (measured on the speech's active parts).
Defaults by level - easy at A0-A1, realistic from B1:
    A0 22 dB, A1 20, A2 16, B1 12, B2 9, C1 6
The background starts ~2 s before the first word and fades out ~2 s after the last one.

Dialogues made with tts.py --ambience go through scene_dialogue() instead of mix(): every speaker is
placed into the place, not pasted on top of it (tuned with the learner on 2026-10-09, hotel lobby):
  - tone: each voice's long-term spectrum is shaped towards a voice that sat naturally in a room
    (Supertonic F4) - booming close-mic lows and glassy studio highs are what sound "pasted on";
  - one shared room: the same short reverb (size by scene) on every voice, equal amount - a voice
    with no room next to voices with a lot of room stands out either way;
  - stereo places: speakers a little left / right, a third one a bit further back (quieter, more room);
  - pace: syllables per second measured over the whole line, pauses between words included (that is
    what sounds "slow / dictated"), nudged towards the level's pace by at most +-5 % - a little
    difference between people is natural; bigger fixes belong in the generation (speed, settings);
  - turn gaps 0.25-0.6 s at random, the reverb tail running into the gap.
"""
import argparse
import glob
import json
import os
import random
import subprocess
import sys
import tempfile

# scipy / soundfile installed once into the languages folder (text-to-voice/setup_engines.sh)
_here = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(_here, ".env")):
    for _d in sorted(os.listdir(os.path.join(_here, ".env")), reverse=True):
        if _d.startswith("fast-") and os.path.exists(os.path.join(_here, ".env", _d, ".ok")):
            sys.path.insert(0, os.path.join(_here, ".env", _d))
            break

SNR_BY_LEVEL = {"A0": 22, "A1": 20, "A2": 16, "B1": 12, "B2": 9, "C1": 6, "C2": 5}
SR = 24000
# scene -> (folder, events [(kind, mean seconds between, loudness vs bed in dB)], description)
SCENES = {
    "cafe":          ("cafe",          [("laughing", 25, -2), ("pouring", 30, -4)], "café / bar: chatter, cups, coffee machine"),
    "restaurant":    ("restaurant",    [("laughing", 35, -4)], "restaurant dining room"),
    "metro":         ("metro",         [], "inside a metro / underground train"),
    "metro_station": ("metro_station", [], "metro platform or station hall"),
    "train_station": ("train_station", [], "railway station hall / platform"),
    "train":         ("train",         [], "inside a train"),
    "bus":           ("bus",           [], "inside a city bus"),
    "tram":          ("tram",          [], "tram, inside or at the stop"),
    "car":           ("car",           [], "inside a car on the road"),
    "airport":       ("airport",       [], "airport terminal"),
    "airplane":      ("airplane",      [], "airplane cabin"),
    "street":        ("street",        [("footsteps", 30, -6)], "busy pedestrian street"),
    "traffic":       ("traffic",       [("car_horn", 35, -3)], "street with car traffic"),
    "square":        ("square",        [("bells", 60, -2)], "public square"),
    "market":        ("market",        [], "street market"),
    "supermarket":   ("supermarket",   [], "supermarket / grocery store"),
    "shop":          ("shop",          [], "small shop / bakery"),
    "mall":          ("mall",          [], "shopping mall"),
    "hotel":         ("hotel",         [], "hotel lobby"),
    "office":        ("office",        [], "open-plan office"),
    "kitchen":       ("kitchen",       [], "home kitchen"),
    "park":          ("park",          [("birds", 6, 2)], "city park with birds"),
    "river":         ("river",         [("birds", 12, 0)], "by a river"),
    "beach":         ("beach",         [], "beach, waves and people"),
    "rain":          ("rain",          [], "rainy city street"),
}
AUDIO = ("*.ogg", "*.flac", "*.wav", "*.mp3", "*.webm")


def files_in(d):
    return sorted(f for pat in AUDIO for f in glob.glob(os.path.join(d, pat)))


# A scene whose recordings aren't installed (e.g. the TUT mall recordings, which are not in the shared
# repository) borrows a similar scene's recordings instead of failing.
FALLBACK = {"mall": "supermarket", "supermarket": "shop", "tram": "bus", "square": "street"}


def scene_files(root, scene):
    seen = set()
    while scene and scene not in seen:
        seen.add(scene)
        files = files_in(os.path.join(root, SCENES[scene][0]))
        if files:
            return files
        scene = FALLBACK.get(scene)
    return []

def ambience_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.environ.get("AMBIENCE_DIR"), os.path.join(here, "text-to-voice", "ambience")]
    mnt = os.path.join(os.path.expanduser("~"), "mnt")
    if os.path.isdir(mnt):
        cands += [os.path.join(mnt, n, "script", "text-to-voice", "ambience") for n in sorted(os.listdir(mnt))]
    for c in cands:
        if c and os.path.isdir(c):
            return c
    raise SystemExit("ambience folder not found (text-to-voice/ambience)")


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def load(path):
    import numpy as np
    import soundfile as sf
    with tempfile.TemporaryDirectory() as t:
        w = os.path.join(t, "x.wav")
        ff("-i", path, "-ar", str(SR), "-ac", "1", w)
        a, _ = sf.read(w, dtype="float32")
    return np.asarray(a, dtype=np.float32)


def active_rms(x, frame=0.03):
    import numpy as np
    n = int(SR * frame)
    fr = x[: len(x) // n * n].reshape(-1, n)
    e = np.sqrt((fr ** 2).mean(1) + 1e-12)
    thr = max(e.max() * 0.05, 1e-4)
    act = e[e > thr]
    return float(np.sqrt((act ** 2).mean())) if len(act) else float(e.mean())


def bed_of_length(files, n, rnd):
    """Loop/crossfade beds (several recordings of the scene, random order and start) to n samples."""
    import numpy as np
    out = np.zeros(0, np.float32)
    fade = int(SR * 1.0)
    order = files[:]
    rnd.shuffle(order)
    k = 0
    while len(out) < n:
        a = load(order[k % len(order)])
        k += 1
        if k == 1 and len(a) > SR * 20:
            a = a[rnd.randrange(0, len(a) - SR * 15):]
        if len(out) == 0:
            out = a
        else:
            r = np.linspace(0, 1, fade, dtype=np.float32)
            out = np.concatenate([out[:-fade], out[-fade:] * (1 - r) + a[:fade] * r, a[fade:]])
    return out[:n]


def mix(speech_path, out_path, scene, snr=None, level=None, seed=None, intro=2.0, outro=2.0, events=True):
    import numpy as np
    import soundfile as sf
    if scene not in SCENES:
        raise SystemExit(f"unknown scene {scene}; try --list")
    root = ambience_dir()
    folder, evs, _ = SCENES[scene]
    files = scene_files(root, scene)
    if not files:
        raise SystemExit(f"no recordings in {os.path.join(root, folder)}")
    snr = snr if snr is not None else SNR_BY_LEVEL.get((level or "B1").upper(), 12)
    rnd = random.Random(seed if seed is not None else os.path.basename(speech_path))
    sp = load(speech_path)
    pre, post = int(SR * intro), int(SR * outro)
    n = pre + len(sp) + post
    bed = bed_of_length(files, n, rnd)
    # events (birds, cups, horns...) at random times, relative to the bed's loudness
    if events:
        bed_rms = active_rms(bed)
        for kind, every, rel_db in evs:
            ev_files = files_in(os.path.join(root, "_events", kind))
            if not ev_files:
                continue
            t = rnd.uniform(0.3, every)
            while t < n / SR - 1:
                e = _soft(load(rnd.choice(ev_files)))
                e = e / (active_rms(e) + 1e-9) * bed_rms * 10 ** ((rel_db + rnd.uniform(-4, 2)) / 20)
                i = int(t * SR)
                bed[i:i + len(e)] += e[: n - i]
                t += rnd.expovariate(1 / every) + 0.5
    # level: speech SNR dB above the background
    g = active_rms(sp) / (active_rms(bed) + 1e-9) / 10 ** (snr / 20)
    bed *= g
    fi, fo = int(SR * 1.5), int(SR * 1.5)
    bed[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    bed[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    y = bed.copy()
    y[pre:pre + len(sp)] += sp
    peak = float(np.abs(y).max())
    if peak > 0.98:
        y *= 0.98 / peak
    with tempfile.TemporaryDirectory() as t:
        w = os.path.join(t, "mix.wav")
        sf.write(w, y, SR)
        ext = os.path.splitext(out_path)[1].lower()
        codec = {".webm": ["-c:a", "libopus", "-b:a", "64k"], ".ogg": ["-c:a", "libopus", "-b:a", "64k"],
                 ".mp3": ["-c:a", "libmp3lame", "-q:a", "3"], ".m4a": ["-c:a", "aac", "-b:a", "128k"]}.get(ext, [])
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        ff("-i", w, *codec, out_path)
    return {"scene": scene, "snr_db": snr, "file": out_path, "seconds": round(n / SR, 1)}


# ---------------------------------------------------------------- dialogues placed into the scene
# long-term spectrum (25 log bands, 60 Hz - 11 kHz, dB, median 0) of Supertonic F4 in a hotel-lobby
# dialogue - the voice the learner heard as "recorded in the room"
TONE_BANDS = (60, 11000, 25)
TARGET_TONE = [-16.4, -13.4, -13.8, -13.5, 0.9, 19.9, 17.2, 9.5, 14.8, 18.9, 16.2, 12.9, 7.6, 3.1, 2.7,
               4.2, -1.1, -0.9, -5.1, -9.2, -18.3, -17.1, -18.5, -16.9]
# room per scene: (reverb time s, wet amount). Outdoors: almost dry; vehicles: small; halls: long.
ROOM = {"cafe": (0.5, 0.13), "restaurant": (0.55, 0.13), "hotel": (0.45, 0.13), "shop": (0.4, 0.12),
        "supermarket": (0.6, 0.12), "office": (0.4, 0.12), "kitchen": (0.35, 0.12), "mall": (0.9, 0.12),
        "airport": (1.0, 0.12), "train_station": (1.0, 0.12), "metro_station": (0.9, 0.12),
        "metro": (0.25, 0.1), "train": (0.25, 0.1), "bus": (0.22, 0.1), "tram": (0.22, 0.1),
        "car": (0.15, 0.08), "airplane": (0.25, 0.1)}
OUTDOOR = (0.15, 0.05)
PACE = {"A0": 4.6, "A1": 5.1, "A2": 5.5, "B1": 6.0, "B2": 6.4, "C1": 6.8, "C2": 7.0}  # syllables / s, pauses included
PLACES = [(-0.25, 0.0, 0.0), (0.2, 0.0, 0.0), (0.45, -2.0, 0.03), (-0.45, -2.0, 0.03), (0.0, -3.0, 0.05)]  # pan, dB, extra wet


def _frames(a, n):
    import numpy as np
    fr = a[: len(a) // n * n].reshape(-1, n)
    return np.sqrt((fr ** 2).mean(1) + 1e-12)


def _pace(a, text):
    import numpy as np
    import re
    e = _frames(a, int(SR * 0.02))
    idx = np.where(e > e.max() * 0.06)[0]
    if len(idx) < 2:
        return None
    syl = len(re.findall(r"[aeiouyéèêëàâîïôûùœæåäöüáíóúãõ]+", text.lower()))
    return syl / ((idx[-1] - idx[0] + 1) * 0.02)


def _band_db(a):
    import numpy as np
    lo, hi, n = TONE_BANDS
    b = np.geomspace(lo, hi, n)
    S = np.abs(np.fft.rfft(a)) ** 2
    f = np.fft.rfftfreq(len(a), 1 / SR)
    return np.array([10 * np.log10(S[(f >= x) & (f < y)].mean() + 1e-12) for x, y in zip(b[:-1], b[1:])])


def _eq(a, gains_db):
    import numpy as np
    lo, hi, n = TONE_BANDS
    b = np.geomspace(lo, hi, n)
    c = np.sqrt(b[:-1] * b[1:])
    A = np.fft.rfft(a)
    f = np.fft.rfftfreq(len(a), 1 / SR)
    g = np.interp(np.log(np.maximum(f, 1)), np.log(c), gains_db)
    return np.fft.irfft(A * 10 ** (g / 20), len(a)).astype(np.float32)


def _room_ir(rt60, rnd):
    import numpy as np
    n = int(SR * rt60 * 1.2)
    t = np.arange(n) / SR
    noise = np.array([rnd.gauss(0, 1) for _ in range(n)]) * np.exp(-6.9 * t / rt60)
    out = np.zeros(n)
    y = 0.0
    for i in range(n):  # darker as it decays: the one-pole lowpass closes over time
        k = 0.25 + 0.6 * min(1.0, t[i] / rt60)
        y += (1 - k) * (noise[i] - y)
        out[i] = y
    out = np.concatenate([np.zeros(int(SR * 0.01)), out])
    for d, g in ((0.007, 0.5), (0.013, 0.35), (0.021, 0.3), (0.029, 0.2)):  # early reflections
        out[int(SR * d)] += g
    return (out / np.sqrt((out ** 2).sum())).astype(np.float32)


def _reverb(a, ir, wet):
    import numpy as np
    from scipy.signal import fftconvolve
    d = np.concatenate([a, np.zeros(len(ir))])
    w = np.zeros(len(d))
    cv = fftconvolve(a, ir)
    w[: len(cv)] = cv[: len(d)]
    w *= np.sqrt((d ** 2).sum() / ((w ** 2).sum() + 1e-12))
    return ((1 - wet) * d + wet * w).astype(np.float32)


def _tempo(a, f):
    import soundfile as sf
    if abs(f - 1) < 0.015:
        return a
    with tempfile.TemporaryDirectory() as t:
        i, o = os.path.join(t, "i.wav"), os.path.join(t, "o.wav")
        sf.write(i, a, SR)
        ff("-i", i, "-filter:a", f"atempo={f:.3f}", o)
        return sf.read(o, dtype="float32")[0]


def _trim(a, keep_in=0.05, keep_out=0.1):
    """Cut the silence a TTS engine leaves before and after a line (Chatterbox often adds 0.5-1.5 s) -
    otherwise the dialogue gets long dead holes. Only the ends: pauses inside the speech are never cut."""
    import numpy as np
    hop = int(SR * 0.01)
    if len(a) < hop * 10:
        return a
    fr = np.sqrt(np.add.reduceat(a.astype(np.float64) ** 2, np.arange(0, len(a), hop)) / hop)
    on = np.where(fr > fr.max() * 10 ** (-40 / 20))[0]
    if not len(on):
        return a
    return a[max(0, on[0] * hop - int(SR * keep_in)): min(len(a), (on[-1] + 1) * hop + int(SR * keep_out))]


def _inner_pauses(a, min_s=0.4):
    """Silences inside a line longer than min_s seconds (Chatterbox sometimes stops mid-sentence: «c'est ...
    ça»). They are reported so the line is generated again - never cut out (cutting caused a rasp)."""
    import numpy as np
    hop = int(SR * 0.01)
    fr = np.sqrt(np.add.reduceat(a.astype(np.float64) ** 2, np.arange(0, len(a), hop)) / hop)
    loud = fr > fr.max() * 10 ** (-35 / 20)
    out, i, n = [], 0, len(loud)
    first, last = (np.where(loud)[0][[0, -1]] if loud.any() else (0, 0))
    i = first
    while i < last:
        if not loud[i]:
            j = i
            while j < last and not loud[j]:
                j += 1
            if (j - i) * 0.01 >= min_s:
                out.append({"at": round(i * 0.01, 2), "seconds": round((j - i) * 0.01, 2)})
            i = j
        else:
            i += 1
    return out


def _soft(e, fin=0.03, fout=0.6):
    """An event clip (birds, bells...) with soft edges. ESC-50 clips are 5 s cuts from longer recordings and
    often stop mid-sound - added as they are, the birdsong broke off abruptly (park dialogue, 2026-10-15)."""
    import numpy as np
    e = _trim(e, 0.0, 0.0)
    a, b = min(len(e) // 4, int(SR * fin)), min(len(e) // 2, int(SR * fout))
    e = e.astype(np.float32).copy()
    if a:
        e[:a] *= np.linspace(0, 1, a, dtype=np.float32)
    if b:
        e[-b:] *= np.linspace(1, 0, b, dtype=np.float32) ** 2
    return e


def _odd_pauses(a, text):
    """Pauses a listener hears as a jump in the recording:
    - >= 0.45 s away from any punctuation mark («Tu es japonaise, c'est … ça»);
    - > 0.5 s at a , . ! ? - a real speaker breathes for 0.2-0.4 s there; longer sounded like a cut
      («Bonjour ! … Vous êtes Yuki ?», learner 2026-10-15);
    - > 0.9 s at «…» / after «Euh», where a longer hesitation is meant.
    A pause's place in the line is compared with the punctuation's place in the text (by characters)."""
    import re
    dur = len(a) / SR
    marks = [(m.end() / max(1, len(text)), 0.9 if ("…" in m.group() or "..." in m.group()) else 0.5)
             for m in re.finditer(r"[.,;:!?…»]+", text.rstrip(" .!?…"))]
    out = []
    for p in _inner_pauses(a):
        f = (p["at"] + p["seconds"] / 2) / max(dur, 1e-6)
        allowed = [lim for m, lim in marks if abs(f - m) < 0.12]
        if (not allowed and p["seconds"] >= 0.45) or (allowed and p["seconds"] > max(allowed)):
            out.append(p)
    return out


def scene_dialogue(clips, speakers, texts, out_path, scene, snr=None, level=None, seed=None, intro=2.0, outro=2.0,
                   events=True):
    """Place a dialogue (one clean clip per turn) into a recorded scene. Returns a summary dict."""
    import numpy as np
    import soundfile as sf
    if scene not in SCENES:
        raise SystemExit(f"unknown scene {scene}; try --list")
    lvl = (level or "B1").upper()
    snr = snr if snr is not None else SNR_BY_LEVEL.get(lvl, 12)
    rnd = random.Random(seed if seed is not None else "|".join(texts))
    lines = [_trim(load(c)) for c in clips]
    long_pauses = [dict(turn=k + 1, speaker=w, **p) for k, (a, w, t) in enumerate(zip(lines, speakers, texts))
                   for p in _odd_pauses(a, t)]
    order = []
    for s in speakers:
        if s not in order:
            order.append(s)
    # pace: towards the level's pace, at most +-5 %, so people still differ a little
    target = PACE.get(lvl, 6.0)
    pace = {}
    for s in order:
        r = [x for x in (_pace(a, t) for a, t, w in zip(lines, texts, speakers) if w == s) if x]
        pace[s] = float(np.median(r)) if r else target
    tempo = {s: float(np.clip(target / pace[s], 0.95, 1.05)) for s in order}
    lines = [_tempo(a, tempo[w]) for a, w in zip(lines, speakers)]
    # tone: towards the reference voice, gently (smoothed, -6..+5 dB)
    ref = np.array(TARGET_TONE)
    gains = {}
    for s in order:
        b = np.mean([_band_db(a) for a, w in zip(lines, speakers) if w == s], axis=0)
        d = ref - (b - np.median(b))
        d = np.convolve(d, np.ones(3) / 3, mode="same")
        gains[s] = np.clip(d, -6, 5)
    lines = [_eq(a, gains[w]) for a, w in zip(lines, speakers)]
    # one shared room
    rt60, wet = ROOM.get(scene, OUTDOOR)
    ir = _room_ir(rt60, rnd)
    place = {s: PLACES[i % len(PLACES)] for i, s in enumerate(order)}
    lines = [_reverb(a, ir, min(0.5, wet + place[w][2])) for a, w in zip(lines, speakers)]
    # same loudness per speaker, then stereo places and turn gaps
    rms = [active_rms(a) for a in lines]
    ref_rms = float(np.median(rms))
    tail = len(ir)
    segs = []
    for a, w, r in zip(lines, speakers, rms):
        pan, db, _ = place[w]
        a = a * (ref_rms / (r + 1e-9)) * 10 ** (db / 20)
        segs.append((np.stack([a * np.sqrt((1 - pan) / 2), a * np.sqrt((1 + pan) / 2)], 1), rnd.uniform(0.25, 0.6)))
    pre, post = int(SR * intro), int(SR * outro)
    n = pre + sum(len(x) - tail + int(SR * g) for x, g in segs) + tail + post
    speech = np.zeros((n, 2), np.float32)
    pos = pre
    for x, g in segs:
        m = min(len(x), n - pos)
        speech[pos:pos + m] += x[:m]
        pos += len(x) - tail + int(SR * g)
    # the place: bed (+ events) as in mix(), made stereo with a small decorrelation
    root = ambience_dir()
    folder, evs, _ = SCENES[scene]
    files = scene_files(root, scene)
    if not files:
        raise SystemExit(f"no recordings in {os.path.join(root, folder)}")
    bed = bed_of_length(files, n, rnd)
    # the level is set on the steady bed alone: measured with the events (birds, bells...) in it, the bed came
    # out much quieter between them and the background seemed to drop out (park dialogue, 2026-10-15)
    g = active_rms(speech.mean(1)) / (active_rms(bed) + 1e-9) / 10 ** (snr / 20)
    bed = bed * g
    if events:
        bed_rms = active_rms(bed)
        for kind, every, rel_db in evs:
            ev_files = files_in(os.path.join(root, "_events", kind))
            if not ev_files:
                continue
            t = rnd.uniform(0.3, every)
            while t < n / SR - 1:
                e = _soft(load(rnd.choice(ev_files)))
                e = e / (active_rms(e) + 1e-9) * bed_rms * 10 ** ((rel_db + rnd.uniform(-4, 2)) / 20)
                i = int(t * SR)
                bed[i:i + len(e)] += e[: n - i]
                t += rnd.expovariate(1 / every) + 0.5
    fi = int(SR * 1.5)
    bed[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    bed[-fi:] *= np.linspace(1, 0, fi, dtype=np.float32)
    dly = int(SR * 0.011)
    y = speech + np.stack([bed, np.concatenate([np.zeros(dly, np.float32), bed[:-dly]])], 1)
    peak = float(np.abs(y).max())
    if peak > 0.98:
        y *= 0.98 / peak
    with tempfile.TemporaryDirectory() as t:
        w = os.path.join(t, "mix.wav")
        sf.write(w, y, SR)
        ext = os.path.splitext(out_path)[1].lower()
        codec = {".webm": ["-c:a", "libopus", "-b:a", "96k"], ".ogg": ["-c:a", "libopus", "-b:a", "96k"],
                 ".mp3": ["-c:a", "libmp3lame", "-q:a", "2"], ".m4a": ["-c:a", "aac", "-b:a", "160k"]}.get(ext, [])
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        ff("-i", w, *codec, out_path)
    return {"scene": scene, "snr_db": snr, "file": out_path, "seconds": round(n / SR, 1), "room": {"rt60": rt60, "wet": wet},
            "pace_target": target, "pace": {s: round(v, 2) for s, v in pace.items()},
            "tempo": {s: round(v, 3) for s, v in tempo.items()}, "places": {s: place[s][0] for s in order},
            "long_pauses": long_pauses}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true")
    p.add_argument("--scene")
    p.add_argument("--in", dest="inp")
    p.add_argument("--out")
    p.add_argument("--level", help="A0-C1: picks the speech-to-background ratio")
    p.add_argument("--snr", type=float, help="speech above background, dB (overrides --level)")
    p.add_argument("--seed")
    p.add_argument("--no-events", action="store_true")
    a = p.parse_args()
    if a.list:
        root = ambience_dir()
        for s, (folder, evs, desc) in SCENES.items():
            n = len(files_in(os.path.join(root, folder)))
            print(f"{s:14s} {n} recordings  {desc}" + (f"  (+ {', '.join(e[0] for e in evs)})" if evs else ""))
        return
    if not (a.scene and a.inp and a.out):
        p.error("--scene, --in and --out are required")
    print(json.dumps(mix(a.inp, a.out, a.scene, a.snr, a.level, a.seed, events=not a.no_events)))


if __name__ == "__main__":
    sys.exit(main())
