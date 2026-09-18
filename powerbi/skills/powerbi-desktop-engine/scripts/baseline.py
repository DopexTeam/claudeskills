"""Fingerprint every visual's data, so the next model change is diffable.

    python baseline.py "<project>" --emit  > queries.dax     # 1. generate
    (execute each query; save each result CSV)               # 2. run
    python baseline.py "<project>" --record out/*.csv        # 3. store
    python baseline.py "<project>" --compare out/*.csv       # 4. diff later

Why a fingerprint and not the rows
----------------------------------
Storing every row of every visual is large, slow and mostly noise. What a
regression check needs is a value that moves when the numbers move:

    cells       COUNTROWS            rows appearing or disappearing
    distinct    distinct measure     values collapsing -- see below
    sample      first 5 values       a shift that keeps the shape

`distinct` is the one that earns its place. A First Finish heat map showed 192
cells over 16 vendors with 12 distinct values, exactly one per category: the
measure was blind to its grouping and every vendor read identically. Cells and
sample both looked healthy. A collapse like that is invisible to any check that
does not count distinct values against the grouping.

`sample` is ordered by the groupings, so it is stable across runs and moves when
values shift uniformly -- which `cells` and `distinct` would both miss.

This is a change detector, not an oracle. It says the numbers are the same as
last time, never that they are right. Capture it BEFORE a model change; a
baseline taken afterwards records the new behaviour as though it were intended.
"""
import os
import re
import sys
import csv
import json
import glob
import argparse
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
BATCH = 6          # visuals per query; keeps each statement reviewable


def definition_dir(project):
    if os.path.isdir(os.path.join(project, "pages")):
        return project
    hits = glob.glob(os.path.join(project, "*.Report", "definition"))
    if not hits:
        sys.exit("no PBIR definition under %s" % project)
    return hits[0]


def label_of(d, page, vid):
    name = json.load(open(os.path.join(d, "pages", page, "page.json"),
                          encoding="utf-8-sig")).get("displayName", page)
    return "%s/%s" % (name, vid[:8])


def visuals(d):
    for page in sorted(os.listdir(os.path.join(d, "pages"))):
        vdir = os.path.join(d, "pages", page, "visuals")
        if not os.path.isdir(vdir):
            continue
        for vid in sorted(os.listdir(vdir)):
            yield page, vid


def derive(project, page, vid):
    """The visual's query, via visualdax -- one source of truth for both."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "visualdax.py"),
                        project, "--page", page, "--visual", vid],
                       capture_output=True, text=True)
    if r.returncode not in (0, 2) or not r.stdout.strip():
        return None, None
    body = r.stdout.split("EVALUATE\n", 1)[-1].strip()
    measures = re.findall(r'"([A-Za-z0-9_]+)",\s*\'', body)
    groups = re.findall(r"^\s*('[^']+'\[[^\]]+\]),\s*$", body, re.M)
    if not measures and not groups:
        return None, None          # chrome: a textbox, shape or navigator
    # a card has measures and no grouping; a slicer has a grouping and no
    # measure. Both are worth a fingerprint -- skipping them was covering 7
    # visuals out of 37 and calling it a baseline.
    return body, (measures[-1] if measures else None, groups)


def emit(project, d):
    rows, batch, n = [], [], 0
    for page, vid in visuals(d):
        body, meta = derive(project, page, vid)
        if not body:
            continue
        batch.append((label_of(d, page, vid), body, meta))
        if len(batch) == BATCH:
            rows.append(statement(batch, n)); batch = []; n += 1
    if batch:
        rows.append(statement(batch, n))
    return rows


def statement(batch, n):
    defs, out = [], []
    for i, (label, body, (measure, groups)) in enumerate(batch):
        v = "V%d" % i
        defs.append("\tVAR %s = %s" % (v, body.replace("\n", "\n\t")))
        if groups and measure:
            defs.append('\tVAR %s_s = CONCATENATEX(TOPN(5, %s, %s, ASC), [%s], "|", %s, ASC)'
                        % (v, v, groups[0], measure, groups[0]))
            fields = ('"distinct", COUNTROWS(SUMMARIZE(%s, [%s])), '
                      '"groups", COUNTROWS(SUMMARIZE(%s, %s)), "sample", %s_s'
                      % (v, measure, v, groups[0], v))
        elif measure:                                   # a card: one scalar
            defs.append('\tVAR %s_s = CONCATENATEX(%s, [%s], "|")' % (v, v, measure))
            fields = '"distinct", 1, "groups", 0, "sample", %s_s' % v
        else:                                           # a slicer: its members
            defs.append('\tVAR %s_s = CONCATENATEX(TOPN(5, %s, %s, ASC), %s, "|", %s, ASC)'
                        % (v, v, groups[0], groups[0], groups[0]))
            fields = ('"distinct", COUNTROWS(SUMMARIZE(%s, %s)), '
                      '"groups", COUNTROWS(SUMMARIZE(%s, %s)), "sample", %s_s'
                      % (v, groups[0], v, groups[0], v))
        out.append('\tROW("visual", "%s", "cells", COUNTROWS(%s), %s)'
                   % (label, v, fields))
    return "DEFINE\n%s\nEVALUATE\nUNION(\n%s\n)" % ("\n".join(defs), ",\n".join(out))


def read_results(paths):
    got = {}
    for p in paths:
        with open(p, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                key = next(k for k in row if k.strip("[]").endswith("visual"))
                got[row[key]] = {k.strip("[]").split("]")[-1] or k: v
                                 for k, v in row.items() if k != key}
    return got


def store(d):
    return os.path.join(d, os.pardir, os.pardir, ".baseline.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--record", nargs="+")
    ap.add_argument("--compare", nargs="+")
    ap.add_argument("--out", help="where to keep the baseline")
    a = ap.parse_args()

    d = definition_dir(a.project)
    path = a.out or os.path.abspath(store(d))

    if a.emit:
        for s in emit(a.project, d):
            print(s)
            print("\n/* --- next statement --- */\n")
        return 0

    if a.record:
        got = read_results(a.record)
        json.dump(got, open(path, "w", encoding="utf-8"), indent=1, sort_keys=True)
        print("recorded %d visuals -> %s" % (len(got), path))
        return 0

    if a.compare:
        if not os.path.exists(path):
            sys.exit("no baseline at %s -- run --record first" % path)
        old = json.load(open(path, encoding="utf-8"))
        new = read_results(a.compare)
        bad = 0
        for label in sorted(set(old) | set(new)):
            o, c = old.get(label), new.get(label)
            if o is None:
                print("  %s  NEW" % label); continue
            if c is None:
                print("  %s  MISSING from this run" % label); bad += 1; continue
            diffs = [k for k in o if o[k] != c.get(k)]
            if diffs:
                bad += 1
                print("  %s  CHANGED" % label)
                for k in diffs:
                    print("      %-9s %s -> %s" % (k, o[k], c.get(k)))
        print("\n%s" % ("%d visuals changed" % bad if bad else
                        "every visual matches the baseline"))
        return 1 if bad else 0

    ap.error("one of --emit, --record, --compare")


if __name__ == "__main__":
    sys.exit(main())
