#!/usr/bin/env python3
"""Make a lesson's audio ONCE, from the checked final text.

Write the lesson draft with placeholder audio buttons - `[J'ai une réservation.](audio)` - and no
audio fields on flashcards. Then:

    lesson_check.py lesson.json --draft --previous ...      # fix every ERROR / WARN first
    audio_plan.py lesson.json --list clips.txt              # every text to voice, one per line
    tts.py --lang fr --each --vary --file clips.txt --out-dir clips/   # Supertonic, fast
    (upload the clips as assets; write {"text": "/_blob/<id>", ...} to map.json)
    audio_plan.py lesson.json --fill map.json --out lesson.final.json
    lesson_check.py lesson.final.json --previous ...        # now with the audio checks

--list also covers flashcards (word and example) that have no audio yet. --fill replaces every
`(audio)` placeholder and fills `audio` / `example_audio` on cards; anything left without a clip is
reported (exit code 1). Listening dialogues are voiced separately with tts.py --ambience from
material.transcript - after the draft check, never before.
"""
import json
import re
import sys

BTN = re.compile(r"\[([^\]]+)\]\(audio\)")


def strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def plan(d):
    texts = []
    for _, s in strings(d):
        texts += [m.strip() for m in BTN.findall(s)]
    for sec in d.get("sections", []):
        for c in sec.get("cards", []) or []:
            if c.get("word") and not c.get("audio"):
                texts.append(c["word"].strip())
            if c.get("example") and not c.get("example_audio"):
                texts.append(c["example"].strip())
    seen, out = set(), []
    for t in texts:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def fill(o, mp, missing):
    if isinstance(o, dict):
        if "word" in o and ("translation" in o or "answer" in o):
            for f, a in (("word", "audio"), ("example", "example_audio")):
                if o.get(f) and not o.get(a):
                    u = mp.get(o[f].strip())
                    if u:
                        o[a] = u
                    else:
                        missing.add(o[f].strip())
        return {k: fill(v, mp, missing) for k, v in o.items()}
    if isinstance(o, list):
        return [fill(v, mp, missing) for v in o]
    if isinstance(o, str):
        def sub(m):
            u = mp.get(m.group(1).strip())
            if not u:
                missing.add(m.group(1).strip())
                return m.group(0)
            return f"[{m.group(1)}]({u})"
        return BTN.sub(sub, o)
    return o


def main(a):
    d = json.load(open(a[0], encoding="utf-8"))
    d = d.get("data", d)
    if "--list" in a:
        texts = plan(d)
        open(a[a.index("--list") + 1], "w", encoding="utf-8").write("\n".join(texts) + "\n")
        print(json.dumps({"clips": len(texts)}))
        return 0
    if "--fill" in a:
        mp = json.load(open(a[a.index("--fill") + 1], encoding="utf-8"))
        missing = set()
        out = fill(d, mp, missing)
        dst = a[a.index("--out") + 1] if "--out" in a else a[0]
        json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"written": dst, "without_clip": sorted(missing)}, ensure_ascii=False))
        return 1 if missing else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
