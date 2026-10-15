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
# Events are rare and varied: with birds every ~6 s (+2 dB) every line of the park dialogue had birds behind it
# and the scene sounded the same throughout (learner, 2026-10-15). Now several kinds per scene, each every
# 30-120 s on average, quieter than the bed; _add_events keeps them apart and never repeats a clip.
SCENES = {
    "cafe":          ("cafe",          [("laughing", 30, -4), ("pouring", 40, -6), ("coughing", 90, -10)], "café / bar: chatter, cups, coffee machine"),
    "restaurant":    ("restaurant",    [("laughing", 40, -6), ("pouring", 60, -8)], "restaurant dining room"),
    "metro":         ("metro",         [("coughing", 70, -10)], "inside a metro / underground train"),
    "metro_station": ("metro_station", [("train", 60, -4), ("footsteps", 40, -8), ("coughing", 90, -10)], "metro platform or station hall"),
    "train_station": ("train_station", [("train", 50, -4), ("footsteps", 40, -8), ("coughing", 90, -10)], "railway station hall / platform"),
    "train":         ("train",         [("coughing", 70, -10), ("laughing", 90, -10)], "inside a train"),
    "bus":           ("bus",           [("coughing", 70, -10)], "inside a city bus"),
    "tram":          ("tram",          [("coughing", 90, -10)], "tram, inside or at the stop"),
    "car":           ("car",           [("car_horn", 90, -10)], "inside a car on the road"),
    "airport":       ("airport",       [("footsteps", 50, -8), ("coughing", 90, -10)], "airport terminal"),
    "airplane":      ("airplane",      [("coughing", 70, -10)], "airplane cabin"),
    "street":        ("street",        [("footsteps", 35, -6), ("laughing", 60, -8), ("dog", 80, -8), ("siren", 150, -12)], "busy pedestrian street"),
    "traffic":       ("traffic",       [("car_horn", 40, -4), ("siren", 120, -10)], "street with car traffic"),
    "square":        ("square",        [("bells", 90, -4), ("footsteps", 45, -8), ("laughing", 60, -8), ("crow", 120, -10)], "public square"),
    "market":        ("market",        [("laughing", 40, -6), ("dog", 90, -8)], "street market"),
    "supermarket":   ("supermarket",   [("coughing", 80, -10)], "supermarket / grocery store"),
    "shop":          ("shop",          [("coughing", 90, -10)], "small shop / bakery"),
    "mall":          ("mall",          [("footsteps", 50, -8), ("laughing", 70, -8)], "shopping mall"),
    "hotel":         ("hotel",         [("footsteps", 45, -8), ("laughing", 90, -10)], "hotel lobby"),
    "office":        ("office",        [("keyboard", 12, -2), ("coughing", 70, -8), ("laughing", 80, -8)], "open-plan office"),
    "kitchen":       ("kitchen",       [("pouring", 60, -6)], "home kitchen"),
    "park":          ("park",          [("birds", 35, -6), ("footsteps", 45, -8), ("laughing", 60, -8), ("dog", 70, -8), ("crow", 120, -10)], "city park"),
    "river":         ("river",         [("birds", 45, -6), ("dog", 80, -8), ("footsteps", 60, -8)], "by a river"),
    "beach":         ("beach",         [("sea_waves", 12, 0), ("laughing", 50, -6), ("dog", 90, -8)], "beach, waves and people"),
    "rain":          ("rain",          [("footsteps", 70, -8)], "rainy city street"),
}
# How much louder than the level's SNR a scene's background is. Learner, 2026-10-15 (same two lines in 11
# scenes at A1): metro and park "not audible at all", train "better", airplane/cafe good, street/market
# excellent. Steady low rumble (metro, train, car) and quiet open air (park, river, beach, rain) hide under
# the voice at the same RMS as a busy street.
SCENE_DB = {"metro": 7, "train": 4, "bus": 4, "tram": 4, "car": 4, "airplane": 1, "metro_station": 3,
            "train_station": 2, "park": 7, "river": 6, "beach": 5, "rain": 6, "office": 3, "kitchen": 3}
# High-pass on the bed (Hz): the office recordings are mostly ventilation hum and sounded like a metro.
BED_HP = {"office": 180, "kitchen": 120, "hotel": 100}

AUDIO = ("*.ogg", "*.flac", "*.wav", "*.mp3", "*.webm")


def files_in(d):
    return sorted(f for pat in AUDIO for f in glob.glob(os.path.join(d, pat)))


# A scene whose recordings aren't installed (e.g. the TUT mall recordings, which are not in the shared
# repository) borrows a similar scene's recordings instead of failing.
FALLBACK = {"mall": "supermarket", "supermarket": "shop", "tram": "bus", "square": "street"}


def scene_files(root, scene, folder=None):
    seen = set()
    while scene and scene not in seen:
        seen.add(scene)
        files = files_in(os.path.join(root, folder or SCENES.get(scene, (scene,))[0]))
        folder = None
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


def load(path, ch=1):
    import numpy as np
    import soundfile as sf
    with tempfile.TemporaryDirectory() as t:
        w = os.path.join(t, "x.wav")
        ff("-i", path, "-ar", str(SR), "-ac", str(ch), w)
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


def _stereo(a, rnd):
    """A recording as a real stereo pair. Mono recordings (DEMAND, some Freesound) get a different stretch of
    the same recording on the right: the old 11 ms delayed copy of one channel made every noisy background
    (street, market, station, beach, rain) sound alike, with an 'electronic echo' (learner, 2026-10-15)."""
    import numpy as np
    L, R = a[:, 0], a[:, 1]
    c = float(np.corrcoef(L[: SR * 20], R[: SR * 20])[0, 1]) if len(L) > SR else 1.0
    if c > 0.97:
        R = np.roll(L, int(len(L) * rnd.uniform(0.3, 0.7)))
        R = 0.2 * L + 0.98 * R
    return np.stack([L, R], 1).astype(np.float32)


def bed_of_length(files, n, rnd, stereo=False):
    """Loop/crossfade beds (several recordings of the scene, random order and start) to n samples
    (n x 2 with stereo=True)."""
    import numpy as np
    out = None
    fade = int(SR * 1.0)
    order = files[:]
    rnd.shuffle(order)
    k = 0
    while out is None or len(out) < n:
        a = load(order[k % len(order)], 2 if stereo else 1)
        if stereo:
            a = _stereo(a, rnd)
        k += 1
        if k == 1 and len(a) > SR * 20:
            a = a[rnd.randrange(0, len(a) - SR * 15):]
        if out is None:
            out = a
        else:
            r = np.linspace(0, 1, fade, dtype=np.float32)
            if stereo:
                r = r[:, None]
            out = np.concatenate([out[:-fade], out[-fade:] * (1 - r) + a[:fade] * r, a[fade:]])
    return out[:n]


def _prepare_bed(bed, smap):
    """Per-scene filtering of the bed (the map's highpass_hz)."""
    hp = smap.get("highpass_hz")
    if not hp:
        return bed
    import numpy as np
    from scipy.signal import butter, sosfilt
    sos = butter(4, hp / (SR / 2), "high", output="sos")
    return sosfilt(sos, bed, axis=0).astype(np.float32)


def _drift(n, rnd, depth_db=2.5, every=8.0):
    """A slow random loudness drift (+-depth_db over ~every seconds): a real place gets louder and quieter as
    people pass; a bed at one fixed level sounded like the same background under every line."""
    import numpy as np
    k = max(2, int(n / SR / every) + 2)
    pts = np.array([rnd.uniform(-depth_db, depth_db) for _ in range(k)])
    x = np.linspace(0, k - 1, n)
    i = np.minimum(x.astype(int), k - 2)
    f = x - i
    f = 0.5 - 0.5 * np.cos(np.pi * f)
    return (10 ** ((pts[i] * (1 - f) + pts[i + 1] * f) / 20)).astype(np.float32)


def scene_map(scene, root=None):
    """The scene's sound map: text-to-voice/ambience/scenes/<scene>.json if it exists, else built from SCENES.
    {"theme", "description", "leitmotif" (folder of base recordings), "loudness_db", "highpass_hz",
     "room" ([rt60, wet] or "outdoor"), "layers" [{"sound", "db"}] (continuous, e.g. rail clatter),
     "sounds" [{"sound", "every", "db", "signature", "max_seconds"}] (short details), "max_per_minute", "calm" [min, max] s}"""
    root = root or ambience_dir()
    p = os.path.join(root, "scenes", scene + ".json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
    else:
        folder, evs, desc = SCENES[scene]
        m = {"theme": scene, "description": desc, "leitmotif": folder,
             "sounds": [{"sound": k, "every": e, "db": d} for k, e, d in evs]}
    m.setdefault("leitmotif", scene)
    m.setdefault("loudness_db", SCENE_DB.get(scene, 0))
    m.setdefault("highpass_hz", BED_HP.get(scene, 0))
    m.setdefault("layers", [])
    m.setdefault("sounds", [])
    m.setdefault("max_per_minute", 4)
    m.setdefault("calm", [4, 12])
    return m


def scene_names(root=None):
    root = root or ambience_dir()
    d = os.path.join(root, "scenes")
    names = set(SCENES)
    if os.path.isdir(d):
        names |= {f[:-5] for f in os.listdir(d) if f.endswith(".json")}
    return sorted(names)


def _add_layers(bed, smap, root, rnd):
    """Continuous layers (rail clatter in a train...) under the whole dialogue, slowly drifting."""
    import numpy as np
    bed_rms = active_rms(bed.mean(1))
    for L in smap.get("layers", []):
        files = files_in(os.path.join(root, "_events", L["sound"]))
        if not files:
            continue
        x = bed_of_length(files, len(bed), rnd, stereo=True)
        x = x / (active_rms(x.mean(1)) + 1e-9) * bed_rms * 10 ** (L.get("db", -6) / 20)
        bed += x * _drift(len(bed), rnd, depth_db=3, every=6)[:, None]


def _add_events(bed, smap, root, rnd, busy=None):
    """Short details (birds, a dog, a horn...) on ONE timeline, so the place sounds alive, not chaotic
    (learner, 2026-10-15: "запись должна быть живой, а не хаосом"):
    - one sound at a time; after it a calm stretch of `calm` seconds (random), sometimes a longer one;
    - at most `max_per_minute` starts per minute;
    - which sound comes next is random, weighted by how often it should be heard (`every`, seconds), and
      never the same sound twice in a row (unless the map has only one);
    - no clip is used twice in a recording; a sound that starts while someone speaks is 5 dB quieter.
    Returns {sound: count}."""
    import numpy as np
    n = len(bed)
    dur = n / SR
    bed_rms = active_rms(bed if bed.ndim == 1 else bed.mean(1))
    pool = []
    for s in smap.get("sounds", []):
        files = files_in(os.path.join(root, "_events", s["sound"]))
        if files:
            rnd.shuffle(files)
            pool.append((s, files))
    if not pool:
        return {}
    lo, hi = smap.get("calm", [4, 12])
    min_step = 60.0 / max(0.5, smap.get("max_per_minute", 4))
    weights = [1.0 / max(1.0, s.get("every", 30)) for s, _ in pool]
    # the expected pause follows the map: frequent sounds -> shorter waits
    t = rnd.uniform(1.0, max(1.5, min(lo + 2, 6)))
    last, counts, used = None, {}, set()
    while t < dur - 2:
        # the place's signature sounds ("signature": true - birds in a park, thunder in rain) come first, so
        # even a short dialogue has them; then the weighted mix
        sig = [(1.0, k) for k, (sd, _) in enumerate(pool) if sd.get("signature") and sd["sound"] not in counts
               and weights[k] and k != last]
        cand = sig or [(w, k) for k, w in enumerate(weights) if (k != last or len(pool) == 1) and w]
        r = rnd.uniform(0, sum(w for w, _ in cand))
        for w, k in cand:
            r -= w
            if r <= 0:
                break
        s, files = pool[k]
        left = [f for f in files if f not in used]
        if not left:
            weights[k] = 0.0
            if not any(weights):
                break
            continue
        f = left[0]
        used.add(f)
        e = _soft(load(f))
        if s.get("max_seconds"):
            e = _soft(e[: int(SR * s["max_seconds"])], 0.0, 0.8)
        if len(e) < SR * 0.3:
            continue
        db = s.get("db", -6) + rnd.uniform(-3, 1)
        if busy is not None:
            j = int(t * 100)
            if busy[j:j + 100].mean() > 0.3:
                db -= 5
        e = e / (active_rms(e) + 1e-9) * bed_rms * 10 ** (db / 20)
        i = int(t * SR)
        m = min(len(e), n - i)
        if bed.ndim == 2:
            pan = rnd.uniform(-0.7, 0.7)
            e = np.stack([e * np.sqrt((1 - pan) / 2), e * np.sqrt((1 + pan) / 2)], 1) * np.sqrt(2)
        bed[i:i + m] += e[:m]
        counts[s["sound"]] = counts.get(s["sound"], 0) + 1
        last = k
        calm = rnd.uniform(lo, hi) * (2.0 if rnd.random() < 0.2 else 1.0)
        t = max(t + m / SR + calm, t + min_step)
    return counts


def mix(speech_path, out_path, scene, snr=None, level=None, seed=None, intro=2.0, outro=2.0, events=True):
    import numpy as np
    import soundfile as sf
    if scene not in scene_names():
        raise SystemExit(f"unknown scene {scene}; try --list")
    root = ambience_dir()
    smap = scene_map(scene, root)
    folder = smap["leitmotif"]
    files = scene_files(root, scene, folder)
    if not files:
        raise SystemExit(f"no recordings in {os.path.join(root, folder)}")
    snr = snr if snr is not None else SNR_BY_LEVEL.get((level or "B1").upper(), 12)
    rnd = random.Random(seed if seed is not None else os.path.basename(speech_path))
    sp = load(speech_path)
    pre, post = int(SR * intro), int(SR * outro)
    n = pre + len(sp) + post
    bed = _prepare_bed(bed_of_length(files, n, rnd, stereo=True), smap)
    # level: speech SNR dB above the steady bed (measured before the events, as in scene_dialogue)
    snr_eff = snr - smap["loudness_db"]
    g = active_rms(sp) / (active_rms(bed.mean(1)) + 1e-9) / 10 ** (snr_eff / 20)
    bed = bed * g * _drift(n, rnd)[:, None]
    ev_counts = {}
    if events:
        _add_layers(bed, smap, root, rnd)
        ev_counts = _add_events(bed, smap, root, rnd)
    fi, fo = int(SR * 1.5), int(SR * 1.5)
    bed[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
    bed[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
    y = bed.copy()
    y[pre:pre + len(sp)] += sp[:, None]
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
    return {"scene": scene, "snr_db": snr_eff, "file": out_path, "seconds": round(n / SR, 1),
            "events": ev_counts}


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


def _last_voiced(a, thr=0.5):
    """Time (s) where the last voiced sound (a vowel, a voiced consonant) ends, or None. A 30 ms frame is
    voiced when it is periodic at a speaking pitch (70-400 Hz) and not much quieter than the line."""
    import numpy as np
    n, hop = int(SR * 0.03), int(SR * 0.02)
    if len(a) < n * 2:
        return None
    lo, hi = SR // 400, SR // 70
    peak = float(np.abs(a).max()) + 1e-9
    last = None
    for j in range(0, len(a) - n, hop):
        f = a[j:j + n].astype(np.float64)
        f = f - f.mean()
        if np.sqrt(np.mean(f ** 2)) < peak * 10 ** (-38 / 20):
            continue
        F = np.fft.rfft(f, 2 * n)
        r = np.fft.irfft(F * np.conj(F))[:n]
        if r[0] > 0 and r[lo:hi].max() / r[0] > thr:
            last = j + n
    return None if last is None else last / SR


def _trim(a, keep_in=0.05, keep_out=0.1, after_voice=None):
    """Cut the silence a TTS engine leaves before and after a line (Chatterbox often adds 0.5-1.5 s) -
    otherwise the dialogue gets long dead holes. Also cut what comes after the last voiced sound but more
    than `after_voice` s later: some Chatterbox voices end lines with a sigh, a breath or an odd noise
    («Bienvenue au club ! - haah», learner 2026-10-15). Only the ends: pauses inside are never cut."""
    import numpy as np
    hop = int(SR * 0.01)
    if len(a) < hop * 10:
        return a
    fr = np.sqrt(np.add.reduceat(a.astype(np.float64) ** 2, np.arange(0, len(a), hop)) / hop)
    on = np.where(fr > fr.max() * 10 ** (-40 / 20))[0]
    if not len(on):
        return a
    start = max(0, on[0] * hop - int(SR * keep_in))
    stop = min(len(a), (on[-1] + 1) * hop + int(SR * keep_out))
    if after_voice is not None:
        v = _last_voiced(a)
        if v is not None and int((v + after_voice) * SR) < stop:
            stop = int((v + after_voice) * SR)
            a = a.astype(np.float32).copy()
            fo = min(int(SR * 0.08), stop - start)
            a[stop - fo:stop] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, fo))).astype(np.float32)
    return a[start:stop]


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


def _soft(e, fin=0.3, fout=2.5):
    """An event clip (birds, bells...) with soft edges. ESC-50 clips are 5 s cuts from longer recordings and
    often stop mid-sound - added as they are, the birdsong broke off abruptly; a 0.6 s fade still sounded
    abrupt (learner, 2026-10-15). Now: 0.3 s in, up to 2.5 s out (at most 45 % of the clip), raised-cosine."""
    import numpy as np
    e = _trim(e, 0.0, 0.0, after_voice=None).astype(np.float32).copy()
    a, b = min(len(e) // 5, int(SR * fin)), min(int(len(e) * 0.45), int(SR * fout))
    if a:
        e[:a] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))).astype(np.float32)
    if b:
        e[-b:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b))).astype(np.float32)
    return e


def _tail_noise(a):
    """A sound after the end of the line (> 0.25 s after the last voiced sound, louder than -40 dB): Chatterbox
    sometimes adds a sigh, a click or a breath after the last word. Reported so the line is generated
    again (--retry) - generated lines are not cut (learner, 2026-10-15: fix the source, regenerate)."""
    import numpy as np
    v = _last_voiced(a)
    if v is None:
        return []
    hop = int(SR * 0.01)
    fr = np.sqrt(np.add.reduceat(a.astype(np.float64) ** 2, np.arange(0, len(a), hop)) / hop) + 1e-12
    db = 20 * np.log10(fr / fr.max())
    after = db[int((v + 0.25) * 100):]
    # at least 80 ms of it: a 30-40 ms click at -30 dB is lost in any background, and flagging it made
    # 7 of 12 lines of the park dialogue "bad" (2026-10-15)
    if len(after) and (after > -40).sum() >= 8:
        k = int(np.argmax(after))
        return [{"at": round(v + 0.25 + k * 0.01, 2), "seconds": 0, "kind": "sound after the last word"}]
    return []


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
    if scene not in scene_names():
        raise SystemExit(f"unknown scene {scene}; try --list")
    lvl = (level or "B1").upper()
    snr = snr if snr is not None else SNR_BY_LEVEL.get(lvl, 12)
    rnd = random.Random(seed if seed is not None else "|".join(texts))
    lines = [_trim(load(c)) for c in clips]
    long_pauses = [dict(turn=k + 1, speaker=w, **p) for k, (a, w, t) in enumerate(zip(lines, speakers, texts))
                   for p in _odd_pauses(a, t)]
    long_pauses += [dict(turn=k + 1, speaker=w, **p) for k, (a, w) in enumerate(zip(lines, speakers))
                    for p in _tail_noise(a)]
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
    room = scene_map(scene).get("room")
    rt60, wet = (OUTDOOR if room == "outdoor" else tuple(room)) if room else ROOM.get(scene, OUTDOOR)
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
    # the place: bed (+ events) in real stereo
    root = ambience_dir()
    smap = scene_map(scene, root)
    folder = smap["leitmotif"]
    files = scene_files(root, scene, folder)
    if not files:
        raise SystemExit(f"no recordings in {os.path.join(root, folder)}")
    bed = _prepare_bed(bed_of_length(files, n, rnd, stereo=True), smap)
    # the level is set on the steady bed alone: measured with the events (birds, bells...) in it, the bed came
    # out much quieter between them and the background seemed to drop out (park dialogue, 2026-10-15)
    snr_eff = snr - smap["loudness_db"]
    g = active_rms(speech.mean(1)) / (active_rms(bed.mean(1)) + 1e-9) / 10 ** (snr_eff / 20)
    bed = bed * g * _drift(n, rnd)[:, None]
    ev_counts = {}
    if events:
        env = np.abs(speech).max(1)
        hop = int(SR * 0.01)
        fr = np.maximum.reduceat(env, np.arange(0, n, hop))
        busy = fr > fr.max() * 0.05
        _add_layers(bed, smap, root, rnd)
        ev_counts = _add_events(bed, smap, root, rnd, busy=busy)
    fi = int(SR * 1.5)
    bed[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
    bed[-fi:] *= np.linspace(1, 0, fi, dtype=np.float32)[:, None]
    y = speech + bed
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
    return {"scene": scene, "snr_db": snr_eff, "file": out_path, "seconds": round(n / SR, 1), "events": ev_counts, "room": {"rt60": rt60, "wet": wet},
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
        for s in scene_names(root):
            m = scene_map(s, root)
            n = len(files_in(os.path.join(root, m["leitmotif"])))
            det = [x["sound"] for x in m["layers"]] + [x["sound"] for x in m["sounds"]]
            print(f"{s:14s} {n} recordings  {m.get('description', '')}" + (f"  (+ {', '.join(det)})" if det else ""))
        return
    if not (a.scene and a.inp and a.out):
        p.error("--scene, --in and --out are required")
    print(json.dumps(mix(a.inp, a.out, a.scene, a.snr, a.level, a.seed, events=not a.no_events)))


if __name__ == "__main__":
    sys.exit(main())
