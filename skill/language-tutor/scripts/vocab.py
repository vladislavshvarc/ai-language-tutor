#!/usr/bin/env python3
"""Vocabulary + spaced-repetition helper for the language-tutor skill.

Stdlib only, so it runs anywhere Python 3.8+ exists. All commands take the
language folder (e.g. .../languages/french) as the first argument and read or
write <folder>/vocabulary.json.

Commands
  init   <dir> --language french [--explain-lang English]
         Create vocabulary.json (and mistakes.md / sessions/) if missing.
  known  <dir>
         Print every word already taught (normalized) - use it to avoid re-teaching.
         Queued words are not listed: they still have to be taught.
  add    <dir> --topic car [--queue] [--file words.json | JSON on stdin]
         Add new words. Input: a JSON list of objects with at least
         "word" and "translation"; optional "gender", "pos", "example",
         "example_translation", "notes". Duplicates are skipped and reported.
         --queue (or "status": "queued" per item): the word is only noted for
         learning - words the learner picked in the workbook, or a prepared
         lesson's words before it is studied. Queued words are never due and never
         in a review deck. Adding a queued word again without --queue teaches it.
  queue  <dir> [--limit 20]
         Words waiting to be taught, oldest first: pick the ones that fit the next
         lesson's topic for its vocabulary section.
  teach  <dir> --topic slug [--words "a; b; c" | --file list.json]
         The words were studied in a lesson's vocabulary section: queued -> learning
         (box 1, due tomorrow, "added" = today, so `deck --added` finds them).
  due    <dir> [--limit 15] [--topic car]
         List words whose next_review <= today, most overdue / lowest box first.
  grade  <dir> [--file results.json | JSON on stdin]
         Record review/exam results. Input: {"la voiture": true, "le bus": false}
         or a list of {"word": ..., "correct": bool}. Right -> box+1, wrong -> box 1.
         Values may also be "right" / "nearly" / "wrong" (flashcard grades):
         nearly -> same box, due again tomorrow.
  stats  <dir>
         Totals per box, words due today/this week, accuracy.
  deck   <dir> [--topic slug | --added YYYY-MM-DD] [--limit 12] [--min 6]
         Words for a flashcard deck: by default the due words (topped up with the
         weakest words to --min); --topic / --added pick a session's new words.
         Only taught words - never queued ones.
  dash   <dir> [--out dash.json]
         Build the workbook's dashboard document (level, current topic/step,
         roadmap, exam history, vocabulary boxes, top mistakes) from
         progress.md, mistakes.md and vocabulary.json.

Global option: --today YYYY-MM-DD (overrides the system date; useful for tests
or when the user's timezone differs from the machine's).

Leitner boxes (days until next review after landing in the box):
  box 1: 1   box 2: 3   box 3: 7   box 4: 14   box 5: 30
New words start in box 1, due tomorrow. A wrong answer sends the word back to
box 1 and makes it due tomorrow, so it comes back sooner.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata

INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}

# Leading articles stripped when checking whether a word is already known.
ARTICLES = [
    "l'", "l’", "le ", "la ", "les ", "un ", "une ", "des ", "du ", "de la ", "de l'",
    "el ", "los ", "las ", "unos ", "unas ",
    "der ", "die ", "das ", "den ", "dem ", "des ", "ein ", "eine ", "einen ",
    "il ", "lo ", "gli ", "i ", "uno ", "un'",
    "o ", "a ", "os ", "as ", "um ", "uma ",
    "the ", "a ", "an ", "to ",
]


def today(args):
    if getattr(args, "today", None):
        return dt.date.fromisoformat(args.today)
    return dt.date.today()


def normalize(word):
    w = unicodedata.normalize("NFC", word.strip().lower())
    changed = True
    while changed:
        changed = False
        for a in ARTICLES:
            if w.startswith(a) and len(w) > len(a):
                w = w[len(a):].strip()
                changed = True
    w = re.sub(r"\s*\(.*?\)\s*", " ", w)  # drop "(m)", "(f)" style notes
    return re.sub(r"\s+", " ", w).strip()


def vpath(d):
    return os.path.join(d, "vocabulary.json")


def load(d):
    p = vpath(d)
    if not os.path.exists(p):
        sys.exit(f"No vocabulary.json in {d}. Run: vocab.py init {d} --language <name>")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):  # tolerate a bare list
        data = {"language": os.path.basename(os.path.normpath(d)), "words": data}
    data.setdefault("words", [])
    return data


def save(d, data):
    p = vpath(d)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, p)  # atomic: a crash never leaves a half-written file


def read_input(args):
    if getattr(args, "file", None):
        with open(args.file, encoding="utf-8") as f:
            return json.load(f)
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit("Expected JSON on stdin or --file")
    return json.loads(raw)


def cmd_init(args):
    d = args.dir
    os.makedirs(os.path.join(d, "sessions"), exist_ok=True)
    if not os.path.exists(vpath(d)):
        save(d, {"language": args.language, "explanation_language": args.explain_lang,
                 "created": today(args).isoformat(), "words": []})
        print(f"created {vpath(d)}")
    else:
        print(f"exists  {vpath(d)}")
    mp = os.path.join(d, "mistakes.md")
    if not os.path.exists(mp):
        with open(mp, "w", encoding="utf-8") as f:
            f.write(f"# {args.language.title()} - recurring mistakes\n\n"
                    "Most frequent first. Each entry: the rule, how often, dated examples "
                    "(wrong -> right), status.\n")
        print(f"created {mp}")


def cmd_known(args):
    data = load(args.dir)
    taught = [w for w in data["words"] if not queued(w)]
    for w in taught:
        print(f"{w['word']}\t{w.get('translation','')}\tbox {w.get('box',1)}\t{w.get('topic','')}")
    print(f"# {len(taught)} words taught · {len(data['words']) - len(taught)} queued (vocab.py queue)", file=sys.stderr)


def cmd_add(args):
    data = load(args.dir)
    items = read_input(args)
    if isinstance(items, dict):
        items = [items]
    t = today(args)
    existing = {normalize(w["word"]): w for w in data["words"]}
    added, skipped, taught = [], [], []
    for it in items:
        if "word" not in it or "translation" not in it:
            skipped.append((it.get("word", "?"), "missing word/translation"))
            continue
        key = normalize(it["word"])
        want_queue = args.queue or it.get("status") == "queued"
        if key in existing:
            old = existing[key]
            if queued(old) and not want_queue:  # a queued word is being taught now
                for k in ("translation", "gender", "pos", "example", "example_translation", "notes"):
                    if it.get(k):
                        old[k] = it[k].strip() if isinstance(it[k], str) else it[k]
                start_learning(old, t, it.get("topic") or args.topic)
                taught.append(old["word"])
                continue
            skipped.append((it["word"], f"already {'queued' if queued(old) else 'known'} (topic: {old.get('topic','?')})"))
            continue
        entry = {
            "word": it["word"].strip(),
            "translation": it["translation"].strip(),
            "gender": it.get("gender"),
            "pos": it.get("pos"),
            "example": it.get("example"),
            "example_translation": it.get("example_translation"),
            "notes": it.get("notes"),
            "topic": it.get("topic") or args.topic,
            "added": t.isoformat(),
            "status": "queued" if want_queue else "learning",
            "box": 1,
            "next_review": None if want_queue else (t + dt.timedelta(days=INTERVALS[1])).isoformat(),
            "last_reviewed": None,
            "right": 0,
            "wrong": 0,
        }
        data["words"].append(entry)
        existing[key] = entry
        added.append(entry["word"])
    save(args.dir, data)
    print(json.dumps({"added": added, "queued": args.queue, "taught_now": taught, "skipped": skipped,
                      "total": len(data["words"])}, ensure_ascii=False, indent=1))


def cmd_queue(args):
    data = load(args.dir)
    q = sorted((w for w in data["words"] if queued(w)), key=lambda w: w.get("added") or "")
    out = [{"word": w["word"], "translation": w.get("translation"), "gender": w.get("gender"), "pos": w.get("pos"),
            "example": w.get("example"), "noted": w.get("added"), "context": w.get("notes")} for w in q[: args.limit]]
    print(json.dumps({"queued_total": len(q), "items": out}, ensure_ascii=False, indent=1))


def cmd_teach(args):
    data = load(args.dir)
    t = today(args)
    names = json.load(open(args.file, encoding="utf-8")) if args.file else [x for x in re.split(r"[;\n]", args.words or "") if x.strip()]
    names = [n["word"] if isinstance(n, dict) else n for n in names]
    index = {normalize(w["word"]): w for w in data["words"]}
    done, already, missing = [], [], []
    for n in names:
        w = index.get(normalize(n))
        if not w:
            missing.append(n)
        elif queued(w):
            start_learning(w, t, args.topic)
            done.append(w["word"])
        else:
            already.append(w["word"])
    save(args.dir, data)
    print(json.dumps({"taught": done, "already_learning": already, "not_found": missing}, ensure_ascii=False, indent=1))


def cmd_due(args):
    data = load(args.dir)
    t = today(args)
    due = []
    for w in data["words"]:
        if queued(w) or (args.topic and w.get("topic") != args.topic):
            continue
        nr = dt.date.fromisoformat(w.get("next_review") or t.isoformat())
        if nr <= t:
            due.append(((t - nr).days, w))
    due.sort(key=lambda x: (w_box(x[1]), -x[0], x[1].get("right", 0) - x[1].get("wrong", 0)))
    out = [{"word": w["word"], "translation": w.get("translation"), "gender": w.get("gender"),
            "box": w_box(w), "overdue_days": od, "topic": w.get("topic")}
           for od, w in due[: args.limit]]
    print(json.dumps({"today": t.isoformat(), "due_total": len(due), "items": out},
                     ensure_ascii=False, indent=1))


def w_box(w):
    return int(w.get("box") or 1)


def queued(w):
    return w.get("status") == "queued"


def start_learning(w, t, topic=None):
    w["status"] = "learning"
    w["box"] = 1
    w["next_review"] = (t + dt.timedelta(days=INTERVALS[1])).isoformat()
    w["added"] = t.isoformat()
    if topic:
        w["topic"] = topic


def cmd_grade(args):
    data = load(args.dir)
    res = read_input(args)
    if isinstance(res, dict):
        res = [{"word": k, "correct": v} for k, v in res.items()]

    def verdict(v):
        if isinstance(v, str):
            v = v.strip().lower()
            if v in ("right", "correct", "true", "yes", "ok"):
                return "right"
            if v in ("nearly", "nearly right", "almost", "partial"):
                return "nearly"
            return "wrong"
        return "right" if v else "wrong"
    t = today(args)
    index = {normalize(w["word"]): w for w in data["words"]}
    report, missing = [], []
    for r in res:
        w = index.get(normalize(r["word"]))
        if not w:
            missing.append(r["word"])
            continue
        if queued(w):  # graded in a lesson = it was taught there
            start_learning(w, t)
        old = w_box(w)
        # At most one promotion per day: several practice rounds plus an exam on
        # the same day must not push a brand-new word straight to box 3-4.
        already = w.get("last_reviewed") == t.isoformat() and w.get("last_result") == "right"
        v = verdict(r.get("correct", r.get("result")))
        if v == "nearly":
            # half-known: stay in the same box, see it again tomorrow
            new = old
            w["nearly"] = w.get("nearly", 0) + 1
            w["last_result"] = "nearly"
            w["box"] = new
            w["next_review"] = (t + dt.timedelta(days=1)).isoformat()
            w["last_reviewed"] = t.isoformat()
            report.append({"word": w["word"], "result": "nearly", "box": f"{old}->{new}", "next_review": w["next_review"]})
            continue
        if v == "right":
            new = old if already else min(5, old + 1)
            w["right"] = w.get("right", 0) + 1
            w["last_result"] = "right"
        else:
            new = 1
            w["wrong"] = w.get("wrong", 0) + 1
            w["last_result"] = "wrong"
        w["box"] = new
        if not (v == "right" and already):
            w["next_review"] = (t + dt.timedelta(days=INTERVALS[new])).isoformat()
        w["last_reviewed"] = t.isoformat()
        report.append({"word": w["word"], "result": v, "box": f"{old}->{new}",
                       "next_review": w["next_review"]})
    save(args.dir, data)
    print(json.dumps({"graded": report, "not_found": missing}, ensure_ascii=False, indent=1))


def cmd_stats(args):
    data = load(args.dir)
    t = today(args)
    boxes = {b: 0 for b in INTERVALS}
    due_today = due_week = right = wrong = 0
    nq = 0
    for w in data["words"]:
        if queued(w):
            nq += 1
            continue
        boxes[w_box(w)] = boxes.get(w_box(w), 0) + 1
        nr = dt.date.fromisoformat(w.get("next_review") or t.isoformat())
        due_today += nr <= t
        due_week += nr <= t + dt.timedelta(days=7)
        right += w.get("right", 0)
        wrong += w.get("wrong", 0)
    acc = round(100 * right / (right + wrong)) if right + wrong else None
    print(json.dumps({"total": len(data["words"]) - nq, "queued": nq, "boxes": boxes, "due_today": due_today,
                      "due_within_7_days": due_week, "review_accuracy_pct": acc,
                      "mastered_box5": boxes.get(5, 0)}, indent=1))


def cmd_deck(args):
    """Words for a flashcard deck: due words (start of session) or one topic / date (end)."""
    data = load(args.dir)
    t = today(args)
    words = [w for w in data["words"] if not queued(w)]
    if args.topic:
        pick = [w for w in words if w.get("topic") == args.topic]
    elif args.added:
        pick = [w for w in words if w.get("added") == args.added]
    else:
        pick = [w for w in words if dt.date.fromisoformat(w.get("next_review") or t.isoformat()) <= t]
        pick.sort(key=lambda w: (w_box(w), -(w.get("wrong", 0) + w.get("nearly", 0))))
        if len(pick) < args.min:
            rest = sorted((w for w in words if w not in pick),
                          key=lambda w: (w_box(w), -(w.get("wrong", 0) + w.get("nearly", 0))))
            pick += rest[: args.min - len(pick)]
    pick = pick[: args.limit]
    out = [{"word": w["word"], "translation": w.get("translation"), "gender": w.get("gender"),
            "pos": w.get("pos"), "example": w.get("example"), "example_translation": w.get("example_translation"),
            "box": w_box(w), "wrong": w.get("wrong", 0), "nearly": w.get("nearly", 0), "topic": w.get("topic")}
           for w in pick]
    print(json.dumps({"today": t.isoformat(), "count": len(out), "words": out}, ensure_ascii=False, indent=1))


# ------------------------------------------------------------------ dashboard

def _table(lines, start):
    """Parse a markdown table beginning at or after line index `start`."""
    i = start
    while i < len(lines) and not lines[i].lstrip().startswith("|"):
        if lines[i].startswith("## "):
            return []
        i += 1
    rows = []
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            rows.append(cells)
        i += 1
    if not rows:
        return []
    head = [h.lower() for h in rows[0]]
    return [dict(zip(head, r)) for r in rows[1:]]


def _section(lines, *names):
    for i, l in enumerate(lines):
        if l.startswith("## ") and any(n in l.lower() for n in names):
            return i
    return None


def _pick(row, *keys):
    for k in row:
        if any(x in k for x in keys):
            return row[k]
    return ""


def cmd_dash(args):
    """Build the workbook dashboard document from the progress files."""
    d = args.dir
    t = today(args)
    lang = os.path.basename(os.path.realpath(d))
    prog = open(os.path.join(d, "progress.md"), encoding="utf-8").read() if os.path.exists(os.path.join(d, "progress.md")) else ""
    lines = prog.splitlines()

    def field(*names):
        for l in lines:
            for n in names:
                m = re.search(r"\**" + n + r"\**\s*:?\**\s*:?\s*(.+)", l, re.I)
                if m:
                    return m.group(1).strip().strip("*").strip()
        return ""

    level_line = field("Level", "Уровень")
    m = re.search(r"\b(A0|A1|A2|B1|B2|C1|C2)\b", level_line or prog)
    level = m.group(1) if m else ""
    explain = field("Explanations in", "Объяснения")
    explain = re.split(r"[.(]", explain)[0].strip() if explain else ""
    topic = field("Current topic", "Текущая тема")
    topic = re.sub(r"\s*-\s*`.*`$", "", topic)
    step_txt = field("Current step", "Текущий шаг")
    sm = re.match(r"(\d)\s*/\s*7", step_txt)
    step = int(sm.group(1)) if sm else (8 if step_txt.lower().startswith("exam") else 0)

    history = []
    i = _section(lines, "topic history", "история тем")
    for r in (_table(lines, i + 1) if i is not None else []):
        history.append({"date": _pick(r, "date", "дата"), "topic": _pick(r, "topic", "тема"),
                        "score": _pick(r, "exam", "экзамен", "score"), "result": _pick(r, "result", "результат")})
    roadmap = []
    i = _section(lines, "roadmap", "план")
    for r in (_table(lines, i + 1) if i is not None else []):
        roadmap.append({"topic": _pick(r, "topic", "тема"), "grammar": _pick(r, "grammar", "граммат"),
                        "status": _pick(r, "status", "статус")})

    mistakes = []
    mp = os.path.join(d, "mistakes.md")
    if os.path.exists(mp):
        ml = open(mp, encoding="utf-8").read().splitlines()
        for j, l in enumerate(ml):
            if l.startswith("## "):
                rule, count, example = l[3:].strip(), 1, ""
                for k in range(j + 1, min(j + 12, len(ml))):
                    if ml[k].startswith("## "):
                        break
                    cm = re.search(r"count:\s*(\d+)", ml[k])
                    if cm:
                        count = int(cm.group(1))
                    elif not example and re.match(r"-\s*\d{4}-\d\d-\d\d", ml[k]):
                        example = re.sub(r"^-\s*\d{4}-\d\d-\d\d:?\s*", "", ml[k]).strip()
                head = "\n".join(ml[j:j + 4])
                if "status: fixed" not in head and "status: later" not in head:  # later = grammar not taught yet
                    mistakes.append({"rule": rule, "count": count, "example": example})
        mistakes.sort(key=lambda x: -x["count"])

    vocab = {"total": 0, "queued": 0, "boxes": {str(b): 0 for b in INTERVALS}, "due_today": 0, "due_week": 0}
    if os.path.exists(vpath(d)):
        for w in load(d)["words"]:
            if queued(w):
                vocab["queued"] += 1
                continue
            vocab["total"] += 1
            vocab["boxes"][str(w_box(w))] += 1
            nr = dt.date.fromisoformat(w.get("next_review") or t.isoformat())
            vocab["due_today"] += nr <= t
            vocab["due_week"] += nr <= t + dt.timedelta(days=7)

    # labels the learner sees in the workbook are in their explanation language (the page translates its
    # own interface; this text comes from here)
    ru = explain.lower().startswith(("ru", "рус"))
    step_names = (["Слова", "Грамматика", "Чтение", "Перевод", "Письмо", "Аудирование", "Говорение", "Экзамен"] if ru
                  else ["Vocabulary", "Grammar", "Reading", "Translation", "Writing", "Listening", "Speaking", "Exam"])
    step_word = "Шаг" if ru else "Step"
    doc = {"language": lang, "label": lang.title(), "level": level, "explain_lang": explain,
           "topic": topic if topic and topic != "-" else "", "step": step,
           "step_label": (f"{step_word} {step}/7 - {step_names[step-1]}" if 1 <= step <= 7 else (step_names[7] if step == 8 else "")),
           "roadmap": roadmap, "history": history, "vocab": vocab, "mistakes": mistakes[:8],
           "updated": t.isoformat()}
    out = json.dumps(doc, ensure_ascii=False, indent=1)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print(f"wrote {args.out}")
    else:
        print(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--today", help="override today's date (YYYY-MM-DD)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("dir"); s.add_argument("--language", required=True)
    s.add_argument("--explain-lang", default=None); s.set_defaults(fn=cmd_init)
    s = sub.add_parser("known"); s.add_argument("dir"); s.set_defaults(fn=cmd_known)
    s = sub.add_parser("add"); s.add_argument("dir"); s.add_argument("--topic", default=None)
    s.add_argument("--queue", action="store_true"); s.add_argument("--file"); s.set_defaults(fn=cmd_add)
    s = sub.add_parser("queue"); s.add_argument("dir"); s.add_argument("--limit", type=int, default=20); s.set_defaults(fn=cmd_queue)
    s = sub.add_parser("teach"); s.add_argument("dir"); s.add_argument("--topic"); s.add_argument("--words"); s.add_argument("--file")
    s.set_defaults(fn=cmd_teach)
    s = sub.add_parser("due"); s.add_argument("dir"); s.add_argument("--limit", type=int, default=15)
    s.add_argument("--topic"); s.set_defaults(fn=cmd_due)
    s = sub.add_parser("grade"); s.add_argument("dir"); s.add_argument("--file"); s.set_defaults(fn=cmd_grade)
    s = sub.add_parser("stats"); s.add_argument("dir"); s.set_defaults(fn=cmd_stats)
    s = sub.add_parser("deck"); s.add_argument("dir"); s.add_argument("--topic"); s.add_argument("--added")
    s.add_argument("--limit", type=int, default=12); s.add_argument("--min", type=int, default=6)
    s.set_defaults(fn=cmd_deck)
    s = sub.add_parser("dash"); s.add_argument("dir"); s.add_argument("--out")
    s.set_defaults(fn=cmd_dash)

    # allow --today before or after the subcommand
    argv = sys.argv[1:]
    if "--today" in argv[1:] and argv[0] != "--today":
        i = argv.index("--today")
        argv = argv[i:i + 2] + argv[:i] + argv[i + 2:]
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
