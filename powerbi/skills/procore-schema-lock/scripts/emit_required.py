"""Write required/<project>.json from the leaves->roots dependency graph."""
import os, sys, json, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: F401  -- puts powerbi-desktop-engine on the path
from paths import data_file, data_dir
from depgraph import build, reachable

project, calcdep = sys.argv[1], sys.argv[2]
E, leaves, src, grains, shares_of, _unhandled, _errs = build(project, calcdep)
seen = reachable(E, leaves)

req = collections.defaultdict(set)
for n in seen:
    if n[0] == "qcol" and n[2] in src.get(n[1], {}):
        req[n[1]].add(src[n[1]][n[2]])

proj = os.path.basename(os.path.normpath(project))
out = {t: sorted(v) for t, v in sorted(req.items())}
dest = data_file("required", proj + ".json")
json.dump(out, open(dest, "w"), indent=1)

roots = sorted({(n[1], n[2]) for n in seen if n[0] == "share"})
json.dump([list(r) for r in roots],
          open(dest.replace(".json", ".shares.json"), "w"), indent=1)
print("  %s: %d required bound columns across %d tables" % (proj, sum(len(v) for v in out.values()), len(out)))
print("  %d required share columns across %d share tables" % (len(roots), len({r[0] for r in roots})))
print("  wrote", os.path.relpath(dest, os.path.dirname(os.path.abspath(__file__))))
