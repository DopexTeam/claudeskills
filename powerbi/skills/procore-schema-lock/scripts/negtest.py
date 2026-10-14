"""Negative test for the LockSchema assertion.

Injects a column name that cannot exist upstream into ONE table's req list, so
a refresh must fail with a named error. Proves the guarantee fires, rather than
inferring it from the fact that it has never fired.

  python negtest.py "<project>" inject [table]
  python negtest.py "<project>" remove
"""
import os, re, sys, glob

SENTINEL = "__negtest_column_that_cannot_exist__"
project, mode = sys.argv[1], sys.argv[2]
table = sys.argv[3] if len(sys.argv) > 3 else "Company"

d = glob.glob(os.path.join(project, "*.SemanticModel", "definition"))[0]
ef = os.path.join(d, "expressions.tmdl")
t = open(ef, encoding="utf-8", newline="").read()

if mode == "inject":
    if SENTINEL in t:
        sys.exit("sentinel already present")
    pat = r'(#"%s" = \[ shares = \{[^}]*\}, req = \{)' % re.escape(table)
    m = re.search(pat, t)
    if not m:
        sys.exit("contract entry for %r not found" % table)
    t = t[:m.end()] + '"%s", ' % SENTINEL + t[m.end():]
    open(ef, "w", encoding="utf-8", newline="").write(t)
    print("  injected %s into %s.req" % (SENTINEL, table))
elif mode == "remove":
    n = t.count('"%s", ' % SENTINEL) + t.count('"%s"' % SENTINEL)
    t = t.replace('"%s", ' % SENTINEL, "").replace('"%s"' % SENTINEL, "")
    open(ef, "w", encoding="utf-8", newline="").write(t)
    print("  removed %d sentinel occurrence(s)" % n)
else:
    sys.exit("mode must be inject|remove")
