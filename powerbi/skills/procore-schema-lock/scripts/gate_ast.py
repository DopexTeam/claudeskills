"""Diff the regex extractor against the syntax-tree extractor.

Nothing touches a client report until this is clean and every difference is
explained. The two are unioned in production, so a difference is not
automatically a bug -- but an unexplained one is, and the direction matters:

  required only under regex   the tree walk has a gap
  required only under AST     the regexes had a gap (the union already fixes it)

Usage: python gate_ast.py <project_dir> <calcdep.csv>
"""
import os
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: F401  -- puts powerbi-desktop-engine on the path
from depgraph import build, reachable


def req_of(project, calcdep, mode):
    E, leaves, src, grains, shares_of, unhandled, errs = build(project, calcdep, mode=mode)
    seen = reachable(E, leaves)
    bound = {(t, src[t][n]) for (k, t, n) in
             [x for x in seen if x[0] == "qcol"] if n in src.get(t, {})}
    roots = {(n[1], n[2]) for n in seen if n[0] == "share"}
    return bound, roots, unhandled, errs


def main(project, calcdep):
    rb, rr, _, _ = req_of(project, calcdep, "regex")
    ab, ar, unhandled, errs = req_of(project, calcdep, "ast")
    ub, ur, _, _ = req_of(project, calcdep, "union")

    if errs:
        print("PARSE FAILURES (these queries contribute nothing under 'ast'):")
        for t, e in sorted(errs.items()):
            print("  %-40s %s" % (t, e[:90]))

    print("\nbound required columns   regex %4d   ast %4d   union %4d"
          % (len(rb), len(ab), len(ub)))
    print("share roots              regex %4d   ast %4d   union %4d"
          % (len(rr), len(ar), len(ur)))

    def show(title, s, limit=60):
        if not s:
            return
        print("\n%s (%d)" % (title, len(s)))
        by = collections.defaultdict(list)
        for t, n in sorted(s):
            by[t].append(n)
        shown = 0
        for t, ns in sorted(by.items()):
            print("  %-32s %s" % (t, ", ".join(sorted(ns))[:120]))
            shown += 1
            if shown >= limit:
                print("  ...")
                break

    show("REQUIRED ONLY UNDER REGEX  -> gap in the tree walk", rb - ab)
    show("REQUIRED ONLY UNDER AST    -> gap in the regexes", ab - rb)
    show("UNION ADDS OVER REGEX", ub - rb)

    uf = collections.Counter()
    for t, fns in unhandled.items():
        for f in fns:
            uf[f] += 1
    if uf:
        print("\nUNHANDLED FUNCTIONS -- no edge rule, enumerated rather than guessed")
        for f, c in uf.most_common(40):
            print("  %4d  %s" % (c, f))

    clean = not (rb - ab) and not errs
    print("\n%s" % ("GATE CLEAN" if clean else "GATE NOT CLEAN -- explain every line above"))
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
