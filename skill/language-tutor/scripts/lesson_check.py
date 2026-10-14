#!/usr/bin/env python3
"""Check a workbook lesson JSON before it is set as lesson/<language>.

    lesson_check.py lesson.json [--previous earlier1.lesson.json earlier2.lesson.json ...]

Reports layout and audio problems the learner has complained about:
  ERROR  audio button reading several words/examples in one clip  ->  one clip per word or example
  WARN   long inline list ("a 10 · b 11 · c 12 ...")              ->  use a table
  WARN   long instruction written as one block                     ->  split into lines / a list
  WARN   listening audio without material.transcript               ->  add it (toggle after 2 listens)
  WARN   vocabulary row without audio for the word or the example
  WARN   flashcards without audio / example_audio
  WARN   grammar section with several themes (two course units, or more than 4 headings)
  WARN   a city in more than 2 sections, two scene sections in the same place, or a city / place /
         title already used by the scene sections of the --previous lessons
  ERROR  speaking with typed answer fields instead of `point` items + one recording
  ERROR  a choice question that contains its own answer ("un ___ (gâteau)")
  WARN   no lesson.grammar {known, later} (what the learner has / hasn't been taught)
  INFO   grammar section without material.videos
Exit code 1 if there is any ERROR.
"""
import json
import re
import sys

CITIES = ("Paris Lyon Marseille Nice Bordeaux Lille Toulouse Nantes Strasbourg Montpellier Rennes Annecy Grenoble Dijon "
          "Avignon Biarritz Reims Rouen Brest Montréal Québec Genève Lausanne Bruxelles Dakar Tours").split()
PLACES = {"café": r"\bcaf[ée]s?\b(?! au lait)|кафе", "restaurant": r"\brestaurants?\b|ресторан", "boulangerie": r"\bboulangerie|пекарн|булочн",
          "gare": r"\bgares?\b|\bTGV\b|\btrain\b|вокзал|поезд", "parc": r"\bparcs?\b|\bпарк", "marché": r"\bmarchés?\b|рын[оке]",
          "avion": r"\bavion|\bvol\b|\bsteward|\bhôtesse|самол[её]т|стюард", "hôtel": r"\bhôtel|\bотел|гостиниц",
          "école": r"\bcours de|\bécole|\buniversité|\bprofesseure? |курс[ауеы]|школ|университет", "bureau": r"\bbureau|офис",
          "plage / mer": r"\bplage|\bmer\b|\bpromenade|пляж|набережн|у моря", "métro / bus": r"\bmétro|\bbus\b|\btram|метро|автобус|трамва",
          "supermarché / magasin": r"\bsupermarché|\bmagasin|магазин|супермаркет", "hôpital": r"\bhôpital|больниц"}
CITY_RU = {"Лион": "Lyon", "Париж": "Paris", "Марсел": "Marseille", "Ницц": "Nice", "Бордо": "Bordeaux", "Лилл": "Lille", "Тулуз": "Toulouse",
           "Нант": "Nantes", "Страсбур": "Strasbourg", "Монпелье": "Montpellier", "Ренн": "Rennes", "Анси": "Annecy", "Монреал": "Montréal",
           "Женев": "Genève", "Брюссел": "Bruxelles"}
SCENE_KEYS = ("reading", "listening", "speaking", "roleplay", "writing")


def scene_text(sec):
    keep = {k: sec.get(k) for k in ("title", "material", "roleplay")}
    t = sec.get("test") or {}
    keep["test"] = {"instructions": t.get("instructions"), "items": t.get("items")}
    txt = json.dumps(keep, ensure_ascii=False)
    return re.sub(r"\(/_blob/[A-Za-z0-9]+\)", "", txt)


def scenes(lesson):
    out = {}
    for s in lesson.get("sections", []):
        k = s.get("key", "")
        base = re.sub(r"[-_]?\d+$", "", k)
        if base not in SCENE_KEYS:
            continue
        txt = scene_text(s)
        title = s.get("title", "")
        cities = {c for c in CITIES if re.search(r"\b" + c + r"\b", txt)} | {c for ru, c in CITY_RU.items() if ru in txt}
        ranked = [p for n, p in sorted(((len(re.findall(rx, txt, re.I)), p) for p, rx in PLACES.items()), reverse=True) if n]
        in_title = [p for p in ranked if re.search(PLACES[p], title, re.I)]
        out[k] = {"title": title, "cities": sorted(cities),
                  "places": in_title + [p for p in ranked if p not in in_title]}  # the place in the title, then the most mentioned
    return out

BTN = re.compile(r"\[([^\]]+)\]\((/_blob/[A-Za-z0-9]+)\)")


def texts(sec):
    m, t = sec.get("material") or {}, sec.get("test") or {}
    yield "material.instructions", m.get("instructions") or ""
    yield "material.body", m.get("body") or ""
    yield "test.instructions", t.get("instructions") or ""
    for it in t.get("items") or []:
        yield f"item {it.get('id')}", it.get("prompt") or ""


def main(path, previous=()):
    d = json.load(open(path, encoding="utf-8"))
    d = d.get("data", d)
    out = []
    g = d.get("grammar") or {}
    if not (g.get("known") or g.get("later")):
        out.append(("WARN", "lesson", "grammar", "no lesson.grammar {known, later} - the in-page checks will count slips in grammar not taught yet"))
    sc = scenes(d)
    city_count = {}
    for k, v in sc.items():
        for c in v["cities"]:
            city_count.setdefault(c, []).append(k)
    for c, ks in city_count.items():
        if len(ks) > 2:
            out.append(("WARN", "variety", "cities", f"{c} appears in {len(ks)} sections ({', '.join(ks)}) - use different cities"))
    main_places = {k: v["places"][:1] for k, v in sc.items() if k.split("-")[0] in ("reading", "listening", "roleplay")}
    seen = {}
    for k, p in main_places.items():
        for x in p:
            if x in seen:
                out.append(("WARN", "variety", "places", f"{seen[x]} and {k} are both set in: {x}"))
            seen[x] = k
    for prev in previous:
        pd = json.load(open(prev, encoding="utf-8"))
        pd = pd.get("data", pd)
        ps = scenes(pd)
        pcities = {c for v in ps.values() for c in v["cities"]}
        ptitles = {v["title"].strip().lower() for v in ps.values()}
        for k, v in sc.items():
            again = [c for c in v["cities"] if c in pcities]
            if again and k.split("-")[0] in ("listening", "roleplay", "reading"):
                out.append(("WARN", "variety", k, f"city {', '.join(again)} was already used in {prev.split('/')[-1]}"))
            if v["title"].strip().lower() in ptitles:
                out.append(("WARN", "variety", k, f"title «{v['title']}» repeats {prev.split('/')[-1]}"))
            for pk, pv in ps.items():
                if pk.split("-")[0] == k.split("-")[0] and v["places"][:1] and v["places"][:1] == pv["places"][:1] and k.split("-")[0] in ("listening", "roleplay"):
                    out.append(("WARN", "variety", k, f"same setting ({v['places'][0]}) as the {pk} of {prev.split('/')[-1]}"))
    if previous or "-v" in sys.argv:
        for k, v in sc.items():
            print(f"scene {k:12s} {v['title'][:34]:34s} cities: {', '.join(v['cities']) or '-'} · places: {', '.join(v['places']) or '-'}")
    for s in d.get("sections", []):
        key = s.get("key", "?")
        for where, txt in texts(s):
            for label, _ in BTN.findall(txt):
                parts = [p for p in re.split(r",|·|…|\.\.\.|;", label) if p.strip()]
                sentence = re.search(r"[.!?]\s*$", label.strip()) and "·" not in label and "…" not in label
                if len(parts) >= 3 and not sentence:
                    out.append(("ERROR", key, where, f"one clip reads {len(parts)} items: «{label[:60]}» - make one clip per word/example"))
            for line in txt.split("\n"):
                if line.count("·") >= 4 and not line.strip().startswith("|"):
                    out.append(("WARN", key, where, f"inline list of {line.count('·') + 1} items - use a table: «{line[:60]}…»"))
            if where.endswith("instructions") and len(txt) > 280 and "\n" not in txt.strip() and not re.search(r"[①-⑳]", txt):
                out.append(("WARN", key, where, "long instruction in one block - split into short lines or a list"))
        for it in (s.get("test") or {}).get("items", []):
            opts = [str(o).strip().lower() for o in it.get("options") or [] if len(str(o).strip()) >= 3]
            prompt = BTN.sub("", str(it.get("prompt") or "")).lower()
            inside = [o for o in opts if o in prompt]
            if len(inside) == 1:
                out.append(("ERROR", key, f"test item {it.get('id')}", f"the question gives the answer away: «{inside[0]}» is in «{prompt[:60]}» - give the meaning instead"))
        if key == "speaking":
            its = (s.get("test") or {}).get("items", [])
            typed = [str(i.get("id")) for i in its if i.get("type") in ("text", "long")]
            if typed:
                out.append(("ERROR", key, "test", f"answer fields ({', '.join(typed)}) in speaking - use `point` items + one `upload` (one voice message, no typing)"))
            if sum(1 for i in its if i.get("type") == "upload") != 1:
                out.append(("ERROR", key, "test", "speaking needs exactly one `upload` item"))
        m = s.get("material") or {}
        if m.get("audio_url") and not m.get("transcript"):
            out.append(("WARN", key, "material", "listening audio has no material.transcript"))
        if key == "vocab":
            for line in (m.get("body") or "").split("\n"):
                if line.strip().startswith("|") and not re.match(r"^\s*\|\s*[-:|\s]+\|\s*$", line):
                    cells = [c for c in line.strip().strip("|").split("|")]
                    n = len(BTN.findall(line))
                    if 0 < n < 2 and len(cells) >= 4:
                        out.append(("WARN", key, "material.body", f"word or example without its own audio: «{line[:60]}»"))
        if s.get("kind") == "flashcards":
            no = [c.get("word") for c in s.get("cards", []) if not c.get("audio")]
            if no:
                out.append(("WARN", key, "cards", f"{len(no)} cards without audio (e.g. {', '.join(map(str, no[:3]))})"))
        if key == "grammar":
            units = sorted(set(re.findall(r"\b[PG]\d{1,2}\b", (s.get("label") or "") + " " + (s.get("title") or ""))))
            heads = [h for h in re.findall(r"^#{1,4} (.+)$", m.get("body") or "", re.M) if not re.search(r"ошибк|mistake", h, re.I)]
            if len(units) > 1 or len(heads) > 4:
                out.append(("WARN", key, "material", f"several themes ({', '.join(units) or str(len(heads)) + ' headings'}) - one grammar theme per lesson; pronunciation goes in its own 'sounds' section, topic phrases in vocab"))
        if key == "grammar" and not m.get("videos"):
            out.append(("INFO", key, "material", "no material.videos (course.md: Videos for units)"))
    for lvl, key, where, msg in out:
        print(f"{lvl:5s} {key:12s} {where:22s} {msg}")
    if not out:
        print("OK - no layout or audio problems found")
    return 1 if any(o[0] == "ERROR" for o in out) else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "-v"]
    prev = args[args.index("--previous") + 1:] if "--previous" in args else []
    sys.exit(main(args[0], prev))
