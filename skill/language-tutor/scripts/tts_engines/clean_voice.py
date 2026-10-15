#!/usr/bin/env python3
"""Clean a Chatterbox reference clip, so the voice copied from it doesn't copy its noises.

    python3 clean_voice.py models/chatterbox/voices/claire.wav [more.wav ...]   # cleans in place
    python3 clean_voice.py --check models/chatterbox/voices/*.wav              # report only

Chatterbox imitates everything in the 10-15 s reference: breaths and sighs between phrases, a clip that
stops mid-word, hiss and rumble. Generated lines then end with a sigh or an odd noise (learner,
2026-10-15: "after every Camille line"). Fixing the source once is better than trimming every line.

What it does (the original is kept in voices/originals/<name>.wav the first time):
- resamples to 24 kHz mono, removes rumble below 70 Hz;
- ends the clip at the end of a phrase (if it was cut mid-speech, at the last pause before that), starts
  it 0.1 s before the first sound, and adds 0.3 s of quiet at the end;
- in the pauses between phrases (>= 0.2 s with no voiced sound) replaces breaths, sighs and clicks with the
  clip's own quiet room tone - word endings and beginnings are left alone and the pause keeps its length,
  so the speaking rhythm is unchanged;
- normalises loudness.
The worker re-reads a cleaned clip by itself (its cached .pt is older than the .wav).
"""
import os
import shutil
import sys

import numpy as np
import soundfile as sf

SR = 24000


def _resample(a, sr):
    if sr == SR:
        return a
    from scipy.signal import resample_poly
    from math import gcd
    g = gcd(SR, sr)
    return resample_poly(a, SR // g, sr // g)


def _voiced(f):
    f = f - f.mean()
    F = np.fft.rfft(f, 2 * len(f))
    r = np.fft.irfft(F * np.conj(F))[:len(f)]
    return r[0] > 0 and r[SR // 400:SR // 70].max() / r[0] > 0.45


def analyse(a):
    n, hop = int(SR * 0.03), int(SR * 0.01)
    fr = [a[j:j + n] for j in range(0, len(a) - n, hop)]
    rms = np.array([np.sqrt(np.mean(f ** 2)) for f in fr]) + 1e-12
    db = 20 * np.log10(rms / rms.max())
    vo = np.array([db[k] > -35 and _voiced(f) for k, f in enumerate(fr)])
    speech = np.convolve(vo.astype(int), np.ones(13, int), "same") > 0  # +-60 ms around voiced = consonants
    pauses, k = [], 0
    while k < len(speech):
        if not speech[k]:
            m = k
            while m < len(speech) and not speech[m]:
                m += 1
            if (m - k) * 0.01 >= 0.2:
                pauses.append((k, m, float(db[k:m].max())))
            k = m
        else:
            k += 1
    return db, vo, speech, pauses


def breaths(a, db=None, pauses=None):
    """Breaths, sighs and clicks inside the pauses: runs of frames clearly above the room tone that don't
    touch the start of the pause (that is the end of the last word - a final «s», «f»...) and stop 0.12 s
    before the next word (its first consonant is left alone). Returns [(start_frame, end_frame)]."""
    if db is None:
        db, _, _, pauses = analyse(a)
    floor = float(np.percentile(db, 5))
    out = []
    for k, m, _ in pauses:
        loud = db[k:m] > floor + 15
        i = 0
        while i < len(loud):
            if loud[i]:
                j = i
                while j < len(loud) and loud[j]:
                    j += 1
                s0, s1 = k + i, min(k + j, m - 12)
                if i > 3 and s1 - s0 >= 5:  # not glued to the previous word, at least 50 ms long
                    out.append((s0, s1))
                i = j
            else:
                i += 1
    return out


def report(name, a):
    db, vo, speech, pauses = analyse(a)
    fv = np.where(vo)[0]
    end_cut = len(a) / SR - (fv[-1] * 0.01 + 0.03) < 0.15 if len(fv) else False
    br = breaths(a, db, pauses)
    return {"voice": name, "seconds": round(len(a) / SR, 2), "ends_mid_speech": bool(end_cut),
            "breaths": [(round(i * 0.01, 2), round((j - i) * 0.01, 2), round(float(db[i:j].max()), 1)) for i, j in br],
            "floor_db": round(float(np.percentile(db, 5)), 1)}


def clean(a):
    from scipy.signal import butter, sosfiltfilt
    a = sosfiltfilt(butter(4, 70, "highpass", fs=SR, output="sos"), a)
    db, vo, speech, pauses = analyse(a)
    hop = int(SR * 0.01)
    fv = np.where(vo)[0]
    start = max(0, fv[0] * hop - int(SR * 0.1))
    end_s = (fv[-1] + 3) * hop + int(SR * 0.12)
    if len(a) - end_s < int(SR * 0.05):  # stopped mid-speech: end at the last pause that leaves >= 8 s
        good = [k for k, m, _ in pauses if k * hop - start >= SR * 8]
        if good:
            end_s = good[-1] * hop + int(SR * 0.12)
    a = a[start:min(len(a), end_s)].astype(np.float64)
    # room tone = the quietest 100 ms of the clip
    w = int(SR * 0.1)
    q = min(range(0, max(1, len(a) - w), w // 2), key=lambda j: np.mean(a[j:j + w] ** 2))
    tone = a[q:q + w]
    tone_rms = np.sqrt(np.mean(tone ** 2)) + 1e-9
    db, vo, speech, pauses = analyse(a)
    ramp = int(SR * 0.02)
    for i0, j0 in breaths(a, db, pauses):
        i, j = max(0, i0 * hop - ramp), min(len(a), j0 * hop + int(SR * 0.03) + ramp)
        env = np.ones(j - i)
        env[ramp:-ramp] = 0
        env[:ramp] = np.linspace(1, 0, ramp)
        env[-ramp:] = np.linspace(0, 1, ramp)
        a[i:j] = a[i:j] * env + np.resize(tone, j - i) * (1 - env)
    fo = int(SR * 0.08)
    a[-fo:] *= np.linspace(1, 0, fo)
    a = np.concatenate([a, np.resize(tone, int(SR * 0.3)) * np.linspace(1, 0, int(SR * 0.3))])
    act = a[np.abs(a) > np.abs(a).max() * 0.05]
    a = a * (10 ** (-20 / 20) / (np.sqrt(np.mean(act ** 2)) + 1e-9))
    return np.clip(a, -0.99, 0.99).astype(np.float32)


def main(args):
    check = "--check" in args
    out = []
    for p in [x for x in args if x != "--check"]:
        a, sr = sf.read(p)
        a = _resample(a if a.ndim == 1 else a.mean(1), sr)
        name = os.path.splitext(os.path.basename(p))[0]
        before = report(name, a)
        if check:
            out.append(before)
            continue
        orig = os.path.join(os.path.dirname(p), "originals", os.path.basename(p))
        if not os.path.exists(orig):
            os.makedirs(os.path.dirname(orig), exist_ok=True)
            shutil.copy2(p, orig)
        b = clean(a)
        sf.write(p, b, SR)
        out.append({"before": before, "after": report(name, b)})
    import json
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
