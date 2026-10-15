#!/usr/bin/env python3
"""Synthesise the scene sounds no free dataset has, into _events/ next to this script.

  make_events.py [--out _events]

  whistle/       a traffic officer's whistle (pea trill: 2.6-3.2 kHz tone, ~30 Hz warble), 1-3 blasts,
                 heard from across a street (low-passed, a little outdoor reflection) - 24 variants
  rail_clatter/  wheels over rail joints heard inside a carriage: two bogies x two axles per joint, a
                 joint every 25 m, speed drifting 70-100 km/h - 4 stereo loops of 60 s, used as a
                 continuous layer in the train scene

Made for the language-tutor ambience (learner, 2026-10-15: "в поезде стук рельс, на улице свисток
регулировщика"). Deterministic: the same files every run.
"""
import argparse
import os
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000


def _bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo / (SR / 2), hi / (SR / 2)], "band", output="sos"), x)


def _lp(x, f, order=2):
    return sosfilt(butter(order, f / (SR / 2), "low", output="sos"), x)


def _save(y, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        w = os.path.join(t, "x.wav")
        sf.write(w, y.astype(np.float32), SR)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", w, "-c:a", "libopus", "-b:a", "64k", path], check=True)


def whistle(rng):
    f0 = rng.uniform(2650, 3150)
    rate = rng.uniform(26, 38)
    pattern = [[0.35], [0.22, 0.75], [0.18, 0.18, 0.6], [0.9], [0.25, 0.25]][rng.integers(5)]
    out = [np.zeros(int(SR * 0.3))]
    for k, d in enumerate(pattern):
        n = int(SR * d)
        t = np.arange(n) / SR
        trill = np.sin(2 * np.pi * rate * t + rng.uniform(0, 6))
        f = f0 * (1 + 0.035 * trill) * (1 + 0.01 * t)          # rises a little as he blows harder
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = np.sin(ph) + 0.12 * np.sin(2 * ph)
        am = 1 - 0.55 * (0.5 + 0.5 * trill)
        breath = _bp(rng.standard_normal(n), f0 * 0.8, f0 * 1.3) * 0.08
        env = np.minimum(1, t / 0.02) * np.minimum(1, (d - t) / 0.05)
        out.append((tone * am + breath) * env)
        out.append(np.zeros(int(SR * rng.uniform(0.12, 0.2))))
    y = np.concatenate(out + [np.zeros(int(SR * 0.8))])
    y = _lp(y, 6500)
    # across a street: a few building reflections and a short tail
    n = int(SR * 0.6)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR / 0.12)
    ir *= np.sqrt(0.08 / (ir ** 2).sum())      # the tail ~11 dB under the direct sound
    ir[0] = 1.0
    for d, g in ((0.031, 0.35), (0.058, 0.25), (0.094, 0.18)):
        ir[int(SR * d)] += g
    y = fftconvolve(y, ir)[: len(y)]
    return y / np.abs(y).max() * 0.5


def _impact(rng, n=int(SR * 0.12)):
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t / 0.018)
    body = _bp(x, 90, 260) * 1.6 + _bp(x, 300, 700) * 0.9 + _bp(x, 1200, 3200) * 0.25
    thud = np.sin(2 * np.pi * rng.uniform(55, 75) * t) * np.exp(-t / 0.035) * 0.8
    return body + thud


def rail_clatter(rng, seconds=60.0):
    n = int(SR * seconds)
    y = np.zeros((n + SR, 2))
    v = rng.uniform(20, 27)                  # m/s
    pos = rng.uniform(0, 1.0)
    while pos < seconds:
        v = float(np.clip(v + rng.normal(0, 0.4), 19, 28))
        # front bogie (2 axles, 2.5 m apart), rear bogie 19 m later; the rear one is a bit further away
        for off, g, pan in ((0.0, 1.0, -0.15), (2.5, 0.85, -0.1), (19.0, 0.7, 0.15), (21.5, 0.6, 0.2)):
            t = pos + off / v
            if t >= seconds:
                continue
            h = _impact(rng) * g * rng.uniform(0.8, 1.1)
            i = int(t * SR)
            y[i:i + len(h), 0] += h * np.sqrt((1 - pan) / 2)
            y[i:i + len(h), 1] += h * np.sqrt((1 + pan) / 2)
        pos += 25.0 / v * rng.uniform(0.97, 1.03)
    y = y[:n]
    # through the floor: duller, plus a little carriage resonance
    y = np.stack([_lp(y[:, 0], 2500), _lp(y[:, 1], 2500)], 1)
    # loop-friendly ends
    f = int(SR * 0.5)
    y[:f] *= np.linspace(0, 1, f)[:, None]
    y[-f:] *= np.linspace(1, 0, f)[:, None]
    return y / np.abs(y).max() * 0.5


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "_events"))
    a = p.parse_args()
    rng = np.random.default_rng(2026)
    for k in range(24):
        _save(whistle(rng), os.path.join(a.out, "whistle", f"synth-whistle-{k:02d}.ogg"))
    for k in range(4):
        _save(rail_clatter(rng), os.path.join(a.out, "rail_clatter", f"synth-rails-{k}.ogg"))
    print("done:", a.out)


if __name__ == "__main__":
    main()
