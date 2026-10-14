#!/usr/bin/env python3
"""Check a language course folder for structural problems (language-tutor skill).

Usage
  course_check.py <languages-root>/<language>/course            # full report
  course_check.py <course-dir> --unit G14                         # one unit
  course_check.py <course-dir> --progress ../course-progress.md   # also check the learner tracker

Checks
  - syllabus.md lists every unit file and every unit file is listed
  - unit ids in front matter match the syllabus and file names; levels match
  - prerequisites refer to existing units that come earlier in the syllabus
  - optional "## Videos" rows carry a YouTube [title](url) link (or say "none found")
  - each unit has front matter (id, title, level, prerequisites, version, status)
    and all sections: Goal, Explanation, Forms, Examples, Traps, Practice bank,
    Mistake patterns, Quick check
  - practice bank has >= 8 rows with an answer; quick check has 3 items
  - status values are draft / reviewed / validated
  - (with --progress) every syllabus unit has a row in the tracker, and no unit was started before its
    prerequisites (lessons running ahead of the course)

It does not judge language correctness - that's the tutor's (and a human's) job.
Prints a summary and exits 1 if there are errors.
"""
import argparse
import os
import re
import sys

SECTIONS = ["Goal", "Explanation", "Forms", "Examples", "Traps", "Practice bank", "Mistake patterns", "Quick check"]
STATUSES = {"draft", "reviewed", "validated"}
LEVELS = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]


def front_matter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.split("#")[0].strip()
    return fm


def section(text, name):
    m = re.search(r"^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course")
    ap.add_argument("--unit")
    ap.add_argument("--progress")
    a = ap.parse_args()
    d = a.course
    errors, warnings = [], []
    with_video = []
    syl_path = os.path.join(d, "syllabus.md")
    if not os.path.exists(syl_path):
        print(f"ERROR: {syl_path} missing")
        sys.exit(1)
    syl = open(syl_path, encoding="utf-8").read()
    rows = re.findall(r"^\|\s*([A-Z]\d+)\s*\|\s*(.+?)\s*\|\s*([ABC][0-2])\s*\|\s*(.*?)\s*\|\s*(\S+\.md)\s*\|", syl, re.M)
    if not rows:
        errors.append("syllabus.md: no unit rows found (expected | id | title | level | prerequisites | file |)")
    order = [r[0] for r in rows]
    listed = {r[4] for r in rows}
    units_dir = os.path.join(d, "units")
    on_disk = {"units/" + f for f in os.listdir(units_dir)} if os.path.isdir(units_dir) else set()
    for f in sorted(on_disk - listed):
        errors.append(f"{f}: not listed in syllabus.md")
    counts = {"draft": 0, "reviewed": 0, "validated": 0}
    for uid, title, level, prereq, path in rows:
        if a.unit and uid != a.unit:
            continue
        full = os.path.join(d, path)
        if not os.path.exists(full):
            errors.append(f"{uid}: file {path} missing")
            continue
        text = open(full, encoding="utf-8").read()
        fm = front_matter(text)
        if fm is None:
            errors.append(f"{uid}: no front matter")
            continue
        for k in ("id", "title", "level", "prerequisites", "version", "status"):
            if k not in fm:
                errors.append(f"{uid}: front matter lacks '{k}'")
        if fm.get("id") != uid:
            errors.append(f"{uid}: front matter id is {fm.get('id')}")
        if not os.path.basename(path).startswith(uid + "-"):
            warnings.append(f"{uid}: file name {path} doesn't start with '{uid}-'")
        if fm.get("level") and fm["level"] != level:
            errors.append(f"{uid}: level {fm['level']} in file vs {level} in syllabus")
        st = fm.get("status", "")
        if st not in STATUSES:
            errors.append(f"{uid}: status '{st}' (use draft / reviewed / validated)")
        else:
            counts[st] += 1
        for p in re.findall(r"[A-Z]\d+", fm.get("prerequisites", "")):
            if p not in order:
                errors.append(f"{uid}: prerequisite {p} is not in the syllabus")
            elif order.index(p) > order.index(uid):
                warnings.append(f"{uid}: prerequisite {p} comes later in the syllabus")
        for s in SECTIONS:
            body = section(text, s)
            if body is None:
                errors.append(f"{uid}: section '## {s}' missing")
            elif not body.strip():
                errors.append(f"{uid}: section '## {s}' empty")
        pb = section(text, "Practice bank") or ""
        items = [l for l in pb.splitlines() if re.match(r"^\|\s*\d+\s*\|", l)]
        if len(items) < 8:
            warnings.append(f"{uid}: practice bank has {len(items)} items (aim for 8-12)")
        for l in items:
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            if len(cells) < 4 or not cells[3]:
                errors.append(f"{uid}: practice item without an answer: {l[:60]}")
        qc = section(text, "Quick check") or ""
        n_qc = len(re.findall(r"^\s*\d+\.", qc, re.M))
        if n_qc != 3:
            warnings.append(f"{uid}: quick check has {n_qc} items (expected 3)")
        vids = section(text, "Videos")  # optional: | Video | Channel | Start | Covers | Added |
        if vids is not None:
            vrows = [l for l in vids.splitlines() if l.strip().startswith("|") and not re.match(r"^\|\s*(Video|-)", l.strip())]
            for l in vrows:
                if not re.search(r"\]\(https://(www\.|m\.)?(youtube\.com|youtu\.be)/[^)]+\)", l) and "none found" not in l.lower():
                    errors.append(f"{uid}: video row without a YouTube link [title](url): {l[:60]}")
            if vrows:
                with_video.append(uid)
    if a.progress:
        if os.path.exists(a.progress):
            prog = open(a.progress, encoding="utf-8").read()
            status = {}
            for uid in order:
                m = re.search(r"^\|\s*" + uid + r"\s*\|[^\n]*\|\s*([^|\n]*?)\s*\|\s*$", prog, re.M)
                if not m:
                    warnings.append(f"progress: no row for {uid}")
                else:
                    status[uid] = m.group(1).strip()
            # order check: a unit that was started (current / partly / review / done) while one of its
            # prerequisites is still untouched ("-") means lessons ran ahead of the course
            started = lambda st: bool(st) and st != "-" and not st.lower().startswith("known")
            for uid, title, level, prereq, path in rows:
                if not started(status.get(uid, "-")):
                    continue
                missing = [p for p in re.findall(r"[A-Z]\d+", prereq) if status.get(p, "-") == "-"]
                if missing:
                    warnings.append(f"progress: {uid} was started before its prerequisite(s) {', '.join(missing)} - teach those next; until then don't count {uid}-type slips that depend on them as errors")
            nxt = [u for u in order if status.get(u, "-") in ("-", "") or status.get(u, "").lower().startswith(("next", "current", "review", "partly"))]
            if nxt:
                print("Next units in course order: " + ", ".join(nxt[:5]))
        else:
            warnings.append(f"progress file {a.progress} not found")
    print(f"Units in syllabus: {len(rows)} · draft {counts['draft']} · reviewed {counts['reviewed']} · validated {counts['validated']}")
    print(f"Units with a Videos section: {len(with_video)}/{len(rows)}" + (f" ({', '.join(with_video)})" if with_video else ""))
    for e in errors:
        print("ERROR:", e)
    for w in warnings:
        print("warn: ", w)
    if not errors and not warnings:
        print("OK - no structural problems found")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
