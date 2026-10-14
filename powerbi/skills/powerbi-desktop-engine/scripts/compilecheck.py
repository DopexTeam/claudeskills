"""Compile every M expression in a PBIP semantic model with Power BI's engine.

Takes either the project folder or the .SemanticModel/definition folder.

Both are accepted because passing the wrong one used to produce
"1 M expressions compiled, 1 failing / <compiler> no output": m_sources found
nothing, PowerShell serialised an empty array, and the gate reported a compiler
fault for a model that was fine. A gate that misreports its own plumbing as a
result is worse than no gate, so zero expressions is now a hard error.
"""
import os
import sys
import glob
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcompile


def resolve(path):
    if os.path.exists(os.path.join(path, "expressions.tmdl")) or \
       os.path.isdir(os.path.join(path, "tables")):
        return path
    hits = glob.glob(os.path.join(path, "*.SemanticModel", "definition"))
    if not hits:
        sys.exit("no semantic model definition under %s" % path)
    return hits[0]


d = resolve(sys.argv[1])
if not mcompile.available():
    sys.exit("mashup engine not found at %s" % mcompile.DLL)

exprs = mcompile.m_sources(d)
if not exprs:
    sys.exit("no M expressions found in %s -- refusing to report a pass" % d)

with tempfile.TemporaryDirectory() as tmp:
    results = mcompile.compile_all(exprs, tmp)
if len(results) == 1 and results[0][0] == "<compiler>":
    sys.exit("compiler did not run: %s" % results[0][2])

bad = [(n, e) for n, ok, e in results if not ok]
print("%s\n  %d M expressions compiled, %d failing" % (d, len(results), len(bad)))
for n, e in bad[:15]:
    print("    %-34s %s" % (n, e[:110]))
sys.exit(1 if bad else 0)
