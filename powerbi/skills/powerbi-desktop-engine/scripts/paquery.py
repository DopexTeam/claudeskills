"""Read Power BI Desktop's Performance Analyzer export as per-visual DAX.

    python paquery.py <PowerBIPerformanceData.json>
    python paquery.py <baseline.json> --compare <after.json>

A visual's content IS its DAX query, so "did this edit change what the report
shows" is answerable exactly rather than by eye: capture the statement each
visual issues, and compare the text.

Performance Analyzer is the only instrument that sees this. The modeling MCP's
trace_operations captures its own connection only -- `filterCurrentSessionOnly:
false` does not reach Desktop's UI session, and a page switch through it records
nothing. Desktop's own recorder does, and labels each query with the visual.

Reading a recording
-------------------
`Execute DAX Query` carries `metrics.QueryText`. It does not carry the visual;
that is found by walking `parentId` up the event tree until an id appears whose
first segment is a 20-hex visual name, which is how PBIR names visuals.

WHAT SILENCE MEANS
------------------
A visual re-queries only when its query-relevant state actually changes. So a
recording of a bookmark toggle is usually EMPTY, because the bookmark asserts
the state the visual is already in. That absence is weak evidence: it is equally
consistent with a correct bookmark and with one the report ignored.

To get a positive result, perturb first and refresh last:

    1. Refresh visuals                        -> baseline: the designed query
    2. drill or filter away from that state   -> forces a real divergence
    3. apply the edit under test
    4. Refresh visuals                        -> the state the edit left behind
    5. compare against the baseline           -> must be identical

Step 2 is what makes step 5 mean anything: without it a pass only says nothing
happened. Step 4 is what makes it observable. Desktop serves a state it has
already rendered from cache, so restoring the designed state usually emits NO
query -- the evidence goes missing exactly when the edit works. Refresh bypasses
that cache and forces every visual to re-state its query.

A recording with no `UserAction_Refresh` after the perturbation cannot support a
conclusion, and this tool says so rather than scoring it.

Note that Performance Analyzer logs no User Action for applying a bookmark, so
its absence from a recording is not evidence the bookmark was not applied.
"""
import os
import re
import sys
import json
import argparse
import collections

VISUAL_ID = re.compile(r"^([0-9a-f]{20})\b")


def load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)["events"]


def visual_of(event, by_id):
    """Walk parentId up until an id names a visual."""
    seen = set()
    node = event
    while node is not None:
        for key in ("parentId", "id"):
            val = node.get(key)
            if isinstance(val, str):
                m = VISUAL_ID.match(val)
                if m:
                    return m.group(1)
        parent = node.get("parentId")
        if parent is None or parent in seen:
            return None
        seen.add(parent)
        node = by_id.get(parent)
    return None


def normalize(dax):
    """Strip what varies between runs but not between results."""
    dax = dax.replace("\r\n", "\n")
    # the row-limit wrapper carries a per-request number
    dax = re.sub(r"TOPN\(\s*\d+,", "TOPN(N,", dax)
    return "\n".join(line.rstrip() for line in dax.split("\n")).strip()


def queries(events):
    """{visualId: [normalized DAX, ...]} in capture order."""
    by_id = {e["id"]: e for e in events if "id" in e}
    out = collections.defaultdict(list)
    for e in events:
        if e.get("name") != "Execute DAX Query":
            continue
        text = (e.get("metrics") or {}).get("QueryText")
        if not text:
            continue
        out[visual_of(e, by_id) or "?unattributed"].append(normalize(text))
    return out


def actions(events):
    return [(e["start"], (e.get("metrics") or {}).get("sourceLabel"))
            for e in events if e.get("name") == "User Action"]


def report(path):
    ev = load(path)
    q = queries(ev)
    print("%s  %d events, %d DAX queries across %d visuals"
          % (os.path.basename(path), len(ev), sum(len(v) for v in q.values()), len(q)))
    for act in actions(ev):
        print("   action  %s  %s" % act)
    for vid, texts in q.items():
        for i, t in enumerate(texts):
            print("   %s [%d]  %d chars  %s" % (vid, i, len(t), t.split("\n")[0][:60]))
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("recording")
    ap.add_argument("--compare", help="a second recording to diff against")
    ap.add_argument("--visual", action="append",
                    help="restrict the comparison to these visual ids")
    a = ap.parse_args()

    base = report(a.recording)
    if not a.compare:
        if not any(base.values()):
            print("\nNO QUERIES RECORDED -- the visuals did not re-query, so this\n"
                  "recording cannot tell a correct edit from an ignored one.\n"
                  "Perturb the visual first, then apply, then record.")
        return 0

    print()
    after_events = load(a.compare)
    after = report(a.compare)

    labels = [lab for _, lab in actions(after_events)]
    if "UserAction_Refresh" not in labels:
        print("\nINCONCLUSIVE -- no Refresh visuals in the second recording.\n"
              "Desktop serves an already-rendered state from cache, so an edit\n"
              "that correctly restores it emits no query and looks like silence\n"
              "or, worse, leaves the perturbed query as the last one recorded.\n"
              "Re-record: perturb, apply, THEN Refresh visuals, then export.")
        return 2

    vids = set(a.visual) if a.visual else set(base) | set(after)
    print("\ncomparison")
    bad = 0
    for vid in sorted(vids):
        b, c = base.get(vid, []), after.get(vid, [])
        if not b and not c:
            continue
        if not c:
            print("   %s  SILENT in the second recording -- no query issued" % vid)
            continue
        if not b:
            print("   %s  absent from the baseline, nothing to compare" % vid)
            bad += 1
            continue
        # the last statement is the visual's settled state in each recording
        if b[-1] == c[-1]:
            print("   %s  IDENTICAL  (%d chars)" % (vid, len(b[-1])))
        else:
            bad += 1
            print("   %s  DIFFERS" % vid)
            for line in difference(b[-1], c[-1]):
                print("        %s" % line)
    print("\n%s" % ("MISMATCH" if bad else "all compared visuals issue the same statement"))
    return 1 if bad else 0


def difference(x, y):
    import difflib
    return list(difflib.unified_diff(x.split("\n"), y.split("\n"),
                                     "baseline", "after", n=1, lineterm=""))[:40]


if __name__ == "__main__":
    sys.exit(main())
