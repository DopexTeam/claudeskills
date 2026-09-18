"""Lint every M expression in a PBIP semantic model definition folder."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mbody import find_body, deindent
from mlint import lint_let, lint_identifiers


def bodies(d):
    out = {}
    ef = os.path.join(d, "expressions.tmdl")
    if os.path.exists(ef):
        t = open(ef, encoding="utf-8", newline="").read()
        for b in re.split(r"(?m)^(?=expression )", t):
            m = re.match(r"expression\s+(?:'([^']+)'|(\S+))", b)
            if not m:
                continue
            r = find_body(b, r"^expression\s", 2)
            if r:
                out["expr:" + (m.group(1) or m.group(2))] = deindent(r[2], 2)
    td = os.path.join(d, "tables")
    for f in sorted(os.listdir(td)):
        if not f.endswith(".tmdl"):
            continue
        t = open(os.path.join(td, f), encoding="utf-8", newline="").read()
        blk = [b for b in re.split(r"(?m)^(?=\t(?:column|measure|partition|hierarchy|annotation)\b)", t)
               if b.startswith("\tpartition")]
        if not blk:
            continue
        r = find_body(blk[0], r"^\t\tsource =", 4)
        if r:
            out[f[:-5]] = deindent(r[2], 4)
    return out


if __name__ == "__main__":
    bs = bodies(sys.argv[1])
    bad = {k: v for k, v in ((k, lint_let(v) + lint_identifiers(v)) for k, v in bs.items()) if v}
    print("%s\n  %d M expressions, %d failing" % (sys.argv[1], len(bs), len(bad)))
    for k, v in list(bad.items())[:12]:
        print("    ", k, "->", v[0][:120])
    sys.exit(1 if bad else 0)
