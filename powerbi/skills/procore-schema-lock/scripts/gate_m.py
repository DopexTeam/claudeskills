"""Compare the regex and syntax-tree extractors query by query, across projects.

gate_ast.py needs a live CALCDEPENDENCY capture to decide reachability, so it
only runs where one exists. This gate needs nothing but the .pbip: it compares
the raw per-query extraction, so the whole corpus can exercise the tree walk.

Two things fail the gate, because only these two can cause a FALSE NEGATIVE --
a dependency that exists and is not in the graph:

  a parse failure       that query then contributes nothing at all
  attribution narrowed  naming a column's source share stops it falling back to
                        every share the query reads, so a wrong narrowing drops
                        real roots. It is the one subtractive input.

Regex-only extraction is REPORTED, not failed. Both extractors are unioned in
production, so anything only the regexes find is still in the graph. Every such
difference on the current corpus traces to one of three regex defects, none of
them a hole in the tree walk:

  * `"([^"]|"")*"` cannot tell a quoted step name `#"Changed Type"` from a
    string literal, so DuplicateColumn/SplitColumn arguments shift by one --
    Company Review RFI got `vProcoreURL <- Changed Type` (nonsense) and lost the
    real `vToolURL <- vProcoreURL`;
  * scanning for the first `{...}` finds a nested call's list rather than the
    intended argument, so `Table.Group(addCC(Table.SelectColumns(src(..),
    {cols})), {keys}, ..)` takes the projection as the group keys;
  * word-boundary and bracket matches fire inside comments and inside quoted
    identifiers -- EOM Budget "consumed" Commitment because the name appears in
    a comment, and grain picked up `#"Project Active?"` with its `#"` still on.

Usage: python gate_m.py <project_dir> [<project_dir> ...]
"""
import os
import re
import sys
import glob
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: F401  -- puts powerbi-desktop-engine on the path
import astm
import astedges
from depgraph import query_edges
from mbody import find_body, deindent
from navrefs import container_expressions
from usage import model_inventory, BLOCK


def bodies_of(D):
    out = {}
    for f in sorted(glob.glob(os.path.join(D, "tables", "*.tmdl"))):
        txt = open(f, encoding="utf-8", errors="replace", newline="").read()
        tm = re.search(r"(?m)^table\s+(?:'([^']+)'|(\S+))", txt)
        t = (tm.group(1) or tm.group(2)) if tm else os.path.basename(f)[:-5]
        ms = []
        for pb in [b for b in BLOCK.split(txt) if b.startswith("\tpartition")]:
            if not re.search(r"=\s*m\s*$", pb.split("\n", 1)[0].strip()):
                continue
            bd = find_body(pb, r"^\t\tsource =", 4)
            if bd:
                ms.append(deindent(bd[2], 4))
        if ms:
            out[t] = "\n".join(ms)
    return out


def run(project):
    D = glob.glob(os.path.join(project, "*.SemanticModel", "definition"))[0]
    etx = open(os.path.join(D, "expressions.tmdl"), encoding="utf-8", newline="").read()
    i = etx.find("expression LockSchema")
    containers = container_expressions(etx[:i] if i > 0 else etx)
    src, calc, meas, _sb = model_inventory(D)
    all_tables = set(src) | set(calc) | set(meas)

    bodies = bodies_of(D)
    asts, errs = astm.parse_many(bodies)

    name = os.path.basename(os.path.normpath(project))
    print("\n=== %s  (%d M queries) ===" % (name, len(bodies)))
    for t, e in sorted(errs.items()):
        print("  PARSE FAILURE  %-34s %s" % (t, e[:80]))

    tot = collections.Counter()
    gaps = collections.defaultdict(list)
    unhandled = collections.Counter()
    for t, m in sorted(bodies.items()):
        a = asts.get(t)
        if a is None:
            continue
        rE, rS, rA, rG, rC = query_edges(t, m, containers, all_tables)
        aE, aS, aA, aG, aC, aU = astedges.query_edges_ast(t, m, containers, all_tables, a)
        for f in aU:
            unhandled[f] += 1

        redges = {(k, v) for k, vs in rE.items() for v in vs}
        aedges = {(k, v) for k, vs in aE.items() for v in vs}
        # Attribution is the one subtractive input: naming a column's source
        # share stops it falling back to every share the query reads. Narrowing
        # is the whole point, but a WRONG narrowing loses real dependencies, so
        # count it rather than let it happen unremarked.
        for c, tbls in aA.items():
            if tbls and rA.get(c) and not rA[c] <= tbls:
                tot["attribution-narrowed"] += 1
                gaps["attribution-narrowed"].append(
                    (t, [c, "regex=%s" % sorted(rA[c]), "ast=%s" % sorted(tbls)], 1))

        for label, only in (("edge", redges - aedges),
                            ("grain", {(t, g) for g in rG - aG}),
                            ("share", {(t, s) for s in set(rS) - set(aS)}),
                            ("consumes", {(t, c) for c in rC - aC})):
            tot[label] += len(only)
            if only:
                gaps[label].append((t, sorted(only)[:4], len(only)))

    for label in ("attribution-narrowed", "edge", "grain", "share", "consumes"):
        if not tot[label]:
            continue
        print("  REGEX-ONLY %s: %d" % (label.upper(), tot[label]))
        for t, sample, n in gaps[label][:12]:
            print("    %-34s %d  e.g. %s" % (t, n, str(sample)[:110]))
    if not sum(tot.values()) and not errs:
        print("  no regex-only extraction, no parse failure")
    return len(errs) + tot["attribution-narrowed"], unhandled


if __name__ == "__main__":
    bad, uf = 0, collections.Counter()
    for p in sys.argv[1:]:
        b, u = run(p)
        bad += b
        uf += u
    print("\nUNHANDLED FUNCTIONS across corpus (no edge rule; enumerated, not guessed)")
    for f, c in uf.most_common(50):
        print("  %4d  %s" % (c, f))
    print("\n%s" % ("GATE CLEAN" if bad == 0 else "GATE NOT CLEAN -- %d items" % bad))
    sys.exit(0 if bad == 0 else 1)
