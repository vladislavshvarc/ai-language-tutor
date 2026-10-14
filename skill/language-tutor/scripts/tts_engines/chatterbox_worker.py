#!/usr/bin/env python3
"""Chatterbox Multilingual worker for tts.py - runs inside its own venv ($HOME/.venvs/chatterbox).

    python chatterbox_worker.py jobs.json

jobs.json: {"model_dir": ".../models/chatterbox", "lang": "fr", "budget_s": 150,
            "items": [{"text": "...", "voice": "elise", "out": "/path/x.wav"}]}
A voice is a reference clip models/chatterbox/voices/<voice>.wav (10-15 s of clear speech);
its conditionals are cached next to it as <voice>.pt the first time it is used.
Items whose "out" already exists are skipped, so a run cut short by the time budget is simply
started again. Prints one JSON line per finished clip and a final {"remaining": n}.

Memory: the full-precision model does not fit in the ~3.9 GB sandbox, so the language model (T3)
is held and run in bfloat16 (needs PyTorch >= 2.6 on ARM); the vocoder stays float32.
Speed: roughly 9-10 s of work per second of audio on 4 CPU cores.
"style" in jobs.json (exaggeration, cfg_weight, temperature) is passed to generate(); tts.py sends
exaggeration 0.6, cfg_weight 0.3, temperature 0.7 - livelier and at a natural pace (2026-10-09).
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import soundfile as sf
import torch

torch.set_num_threads(os.cpu_count() or 4)
from safetensors import safe_open  # noqa: E402
from chatterbox.mtl_tts import ChatterboxMultilingualTTS, Conditionals  # noqa: E402
from chatterbox.models.t3 import T3  # noqa: E402
from chatterbox.models.t3.modules.t3_config import T3Config  # noqa: E402
from chatterbox.models.s3gen import S3Gen  # noqa: E402
from chatterbox.models.voice_encoder import VoiceEncoder  # noqa: E402
from chatterbox.models.tokenizers import MTLTokenizer  # noqa: E402


def load(model_dir):
    d = Path(model_dir)
    ve = VoiceEncoder()
    ve.load_state_dict(torch.load(d / "ve.pt", map_location="cpu", weights_only=True))
    ve.eval()
    prev = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        t3 = T3(T3Config.multilingual())
    finally:
        torch.set_default_dtype(prev)
    sd = t3.state_dict()
    with safe_open(str(d / "t3_mtl23ls_v2.safetensors"), "pt") as f:
        for k in f.keys():
            with torch.no_grad():
                sd[k].copy_(f.get_tensor(k))
    del sd
    t3.eval()
    inf = t3.inference

    def bf16_inference(*a, **k):
        with torch.autocast("cpu", dtype=torch.bfloat16):
            return inf(*a, **k)
    t3.inference = bf16_inference
    s3 = S3Gen()
    s3.load_state_dict(torch.load(d / "s3gen.pt", map_location="cpu", weights_only=True, mmap=True))
    s3.eval()
    tok = MTLTokenizer(str(d / "grapheme_mtl_merged_expanded_v1.json"))
    return ChatterboxMultilingualTTS(t3, s3, ve, tok, "cpu", conds=None)


def use_voice(m, model_dir, voice):
    vdir = Path(model_dir) / "voices"
    pt, wav = vdir / f"{voice}.pt", vdir / f"{voice}.wav"
    if pt.exists():
        m.conds = Conditionals.load(pt, map_location="cpu")
    elif wav.exists():
        m.prepare_conditionals(str(wav))
        m.conds.save(pt)
    else:
        raise SystemExit(f"chatterbox voice not found: {wav}")


def main():
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    t0 = time.time()
    budget = float(job.get("budget_s", 1e9))
    todo = [it for it in job["items"] if not os.path.exists(it["out"])]
    if not todo:
        print(json.dumps({"remaining": 0}))
        return
    todo.sort(key=lambda it: it["voice"])  # one voice switch per speaker
    m = load(job["model_dir"])
    print(json.dumps({"loaded_s": round(time.time() - t0, 1)}), flush=True)
    done, cur = 0, None
    for it in todo:
        if time.time() - t0 > budget:
            break
        if it["voice"] != cur:
            use_voice(m, job["model_dir"], it["voice"])
            cur = it["voice"]
        t = time.time()
        with torch.inference_mode():
            wav = m.generate(it["text"], language_id=job.get("lang", "fr"), **job.get("style", {}))
        tmp = it["out"] + ".part.wav"
        sf.write(tmp, wav.squeeze().float().cpu().numpy(), m.sr)
        os.replace(tmp, it["out"])
        done += 1
        print(json.dumps({"done": it["out"], "s": round(time.time() - t, 1)}), flush=True)
    print(json.dumps({"remaining": len(todo) - done}), flush=True)


if __name__ == "__main__":
    main()
