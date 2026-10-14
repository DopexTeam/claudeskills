"""Schema-lock every Procore Delta Sharing query in a PBIP semantic model.

Adds two generated expressions (LockSchema, SchemaContract) and appends a
terminal lock step to each share-backed partition, so a column Procore removes
upstream null-pads instead of hard-failing Service refresh.

Usage:
  python apply_lock.py "<path to project folder>" [--apply] [--only=A,B,C]

Without --apply it is a dry run. Desktop MUST be closed: verify the files are
writable, not merely that no PBIDesktop process is listed (a windowless one
lingers after close).
"""
import os, re, glob, sys, shutil, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: F401  -- puts powerbi-desktop-engine on the path
from paths import data_file, data_dir
from lockm import guard_calls, append_lock, upgrade_inline_lock
from mbody import find_body, deindent, reindent, splice
from renames import extract_renames
from exprcols import extract_expression_cols
from navrefs import share_refs, container_expressions

ROOT = sys.argv[1]
APPLY = "--apply" in sys.argv
ONLY = None
for a in sys.argv:
    if a.startswith("--only="):
        ONLY = {x.strip() for x in a[len("--only="):].split(",") if x.strip()}

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = re.compile(r"(?m)^(?=\t(?:column|measure|partition|hierarchy|annotation)\b)")

d = glob.glob(os.path.join(ROOT, "*.SemanticModel", "definition"))[0]
proj = os.path.basename(os.path.dirname(os.path.dirname(d)))

# per-model allowlist of columns the M itself creates (never present in the share)
dpath = data_file("derived", proj + ".json")
DERIVED = json.load(open(dpath)) if os.path.exists(dpath) else {}

# Required columns, from the leaves->roots dependency graph. Without it every
# column would be treated as required, which is safe but noisy; refuse to guess.
rpath = data_file("required", proj + ".json")
if not os.path.exists(rpath):
    sys.exit("missing %s -- run depgraph first; refusing to guess required/optional" % rpath)
REQUIRED = {k: set(v) for k, v in json.load(open(rpath)).items()}

# ---------- 1. shared DeltaSharing expressions ----------
ef = os.path.join(d, "expressions.tmdl")
etx = open(ef, encoding="utf-8", newline="").read()
out_blocks, ds_names, gsel, gren, expr_bail = [], set(), 0, 0, []
expr_contract = {}
expr_shares = {}
containers = container_expressions(etx)

# Which expressions reach a share, computed in a PRE-PASS.
#
# Keying on the literal `DeltaSharing.Contents` only works while every query
# opens its own connection. Once the navigations are consolidated behind one
# container expression, the others reach the share THROUGH it and the literal
# is gone -- containerising Company Review dropped all 13 expression contract
# entries, and regenerating the contract from that would leave 13 live
# LockSchema calls referencing fields no longer in SchemaContract.
#
# It also has to run to a FIXPOINT. Reaching the share is transitive: once the
# navigations are consolidated, DailyLogHeaderImport reads Procore2, and the
# tables that read DailyLogHeaderImport reach the share through two hops. One
# pass finds only the container, and every table behind an intermediate
# expression silently stops being recognised as share-backed.
_expr_blocks = re.split(r"(?m)^(?=expression )", etx)
_named = []
for _b in _expr_blocks:
    _m = re.match(r"expression\s+(?:'([^']+)'|(\S+))", _b)
    if _m:
        _named.append((_m.group(1) or _m.group(2), _b))
ds_names |= set(containers)
ds_names |= {n for n, b in _named if "DeltaSharing.Contents" in b}
for _ in range(len(_named) + 1):
    _grew = False
    for _n, _b in _named:
        if _n in ds_names:
            continue
        if any(re.search(r'(?<![A-Za-z0-9_])(?:#")?%s(?:")?(?![A-Za-z0-9_])' % re.escape(o), _b)
               for o in ds_names):
            ds_names.add(_n)
            _grew = True
    if not _grew:
        break


def _reads_share(text):
    return "DeltaSharing.Contents" in text or any(
        re.search(r'(?<![A-Za-z0-9_])(?:#")?%s(?:")?(?![A-Za-z0-9_])' % re.escape(n), text)
        for n in ds_names)


for b in _expr_blocks:
    m = re.match(r"expression\s+(?:'([^']+)'|(\S+))", b)
    name = (m.group(1) or m.group(2)) if m else None
    if not m or name in containers or not _reads_share(b):
        out_blocks.append(b); continue
    r = find_body(b, r"^expression\s", 2)
    if not r:
        out_blocks.append(b); continue
    s, e, body_lines, _ = r
    body = deindent(body_lines, 2)
    body, a, ok1 = guard_calls(body, "Table.SelectColumns", "MissingField.UseNull")
    body, k, ok2 = guard_calls(body, "Table.RenameColumns", "MissingField.Ignore")
    if not (ok1 and ok2):
        expr_bail.append(m.group(1) or m.group(2)); out_blocks.append(b); continue
    gsel += a; gren += k
    # audit the expression itself: a shared expression reads a share table no
    # table partition navigates, so without this those share tables go unwatched
    esh = sorted(share_refs(body, containers))
    ecols = extract_expression_cols(body)
    ename = m.group(1) or m.group(2)
    if esh:
        expr_shares[ename] = esh
        if ecols:
            expr_contract["expr:" + ename] = (esh, ecols, extract_renames(body))
    out_blocks.append(splice(b, s, e, reindent(body, 2)))
etx_new = "".join(out_blocks)

# ---------- 2. table partitions ----------
contract, files, skipped, already, deferred, upgraded, psel, pren = {}, {}, [], [], [], [], 0, 0
for f in sorted(glob.glob(os.path.join(d, "tables", "*.tmdl"))):
    txt = open(f, encoding="utf-8", newline="").read()
    tm = re.search(r"(?m)^table\s+(?:'([^']+)'|(\S+))", txt)
    tname = (tm.group(1) or tm.group(2)) if tm else os.path.basename(f)[:-5]
    blocks = BLOCK.split(txt)
    cols, pi = [], None
    for k, b in enumerate(blocks):
        cm = re.match(r"\tcolumn\s+(?:'([^']+)'|(\S+))", b)
        if cm:
            calc = bool(re.match(r"\tcolumn\s+(?:'[^']+'|\S+)\s*=", b)) or "\n\t\texpression" in b
            sc = re.search(r"\n\t\tsourceColumn:\s*(.+)", b)
            if not calc and sc and not sc.group(1).strip().startswith("["):
                cols.append(sc.group(1).strip())
        elif b.startswith("\tpartition"):
            pi = k
    if pi is None:
        continue
    pb = blocks[pi]
    r = find_body(pb, r"^\t\tsource =", 4)
    if not r:
        skipped.append((tname, "no source body")); continue
    s, e, body_lines, _ = r
    raw = deindent(body_lines, 4)
    if not _reads_share(raw):
        continue
    # never lock the canary: it reads SchemaContract, so locking it is circular
    if tname == "Schema Audit":
        skipped.append((tname, "canary table")); continue
    if not cols:
        skipped.append((tname, "no bound source columns")); continue
    shares = share_refs(raw, containers)
    # a partition that sources through a shared expression reads that
    # expression's share table too; fold it in so nothing goes unwatched
    for en, esh in expr_shares.items():
        if re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(en), raw):
            shares |= set(esh)
    shares = sorted(shares)
    contract[tname] = (shares, cols, extract_renames(raw))
    if "Schema Locked" in raw:
        # upgrade a v1 single-list lock in place rather than stripping and
        # re-applying -- stripping has to reconstruct the previous terminal step,
        # which is exactly where the nested let..in queries get mangled
        up = re.sub(r'LockSchema\(([^,]+),\s*SchemaContract\[#"[^"]+"\]\[cols\]\)',
                    lambda mm: 'LockSchema(%s, SchemaContract[#"%s"][req], SchemaContract[#"%s"][opt])'
                               % (mm.group(1).strip(), tname, tname), raw)
        if up == raw and "LockSchema(" not in raw:
            # the pre-contract INLINE form: the column list written straight
            # into Table.SelectColumns(..., MissingField.UseNull). It null-pads
            # everything, so nothing ever fails and every column is effectively
            # optional -- a column the report genuinely uses can vanish and the
            # refresh still succeeds with wrong numbers. Counting it as "already
            # locked" is how MJS sat unprotected while reporting as done.
            up, ok_in, why = upgrade_inline_lock(raw, tname)
            if not ok_in:
                skipped.append((tname, "inline lock: " + why))
                continue
        if up != raw:
            blocks[pi] = splice(pb, s, e, reindent(up, 4))
            files[f] = "".join(blocks)
            upgraded.append(tname)
        else:
            already.append(tname)
        continue
    if ONLY is not None and tname not in ONLY:
        deferred.append(tname); continue
    body, a, ok1 = guard_calls(raw, "Table.SelectColumns", "MissingField.UseNull")
    body, k, ok2 = guard_calls(body, "Table.RenameColumns", "MissingField.Ignore")
    if not (ok1 and ok2):
        skipped.append((tname, "unscannable call")); continue
    body, ok = append_lock(
        body,
        'LockSchema(<LAST>, SchemaContract[#"%s"][req], SchemaContract[#"%s"][opt])'
        % (tname, tname))
    if not ok:
        skipped.append((tname, "non-simple in-clause")); continue
    psel += a; pren += k
    blocks[pi] = splice(pb, s, e, reindent(body, 4))
    files[f] = "".join(blocks)

# ---------- 3. generated expressions ----------
def mlist(cs):
    return "{" + ", ".join('"%s"' % c for c in cs) + "}"
def mrec(dd):
    if not dd:
        return "[]"
    return "[ " + ", ".join('#"%s" = "%s"' % (k, v) for k, v in sorted(dd.items())) + " ]"

contract.update(expr_contract)
entries = ",\n".join(
    '\t\t        #"%s" = [ shares = %s, req = %s, opt = %s, renames = %s, derived = %s ]'
    % (k, mlist(s),
       mlist(sorted(set(c) & REQUIRED.get(k, set()))),
       mlist(sorted(set(c) - REQUIRED.get(k, set()))),
       mrec(r), mlist(DERIVED.get(k, [])))
    for k, (s, c, r) in sorted(contract.items()))

TPL = """expression LockSchema = ```
		// req : the report consumes these, directly or through a measure,
		//            calculated column, relationship or Power Query dependency.
		//            Their loss is a REAL break, so fail loudly and name them --
		//            far better than Power BI's generic "does not exist in the
		//            rowset", which names one column and stops.
		// opt : bound but unreferenced. Null-padded, silent, never fails.
		// The union with the live column list lets columns the source ADDS flow
		// through; a plain projection would freeze the schema.
		(tbl as table, req as list, opt as list) as table =>
		    let
		        actual  = Table.ColumnNames(tbl),
		        missing = List.Difference(req, actual)
		    in
		        if List.IsEmpty(missing) then
		            Table.SelectColumns(tbl, List.Distinct(req & opt & actual), MissingField.UseNull)
		        else
		            error "Procore removed column(s) this report depends on: "
		                  & Text.Combine(List.Sort(missing), ", ")
		```
	lineageTag: 8c41d6b2-57ae-4f30-9b12-6d0ea3517c94

	annotation PBI_ResultType = Function

expression SchemaContract = ```
		let
		    Contract = [
__ENTRIES__
		    ]
		in
		    Contract
		```
	lineageTag: 3f2a17c4-9d05-4c1e-b6a8-0e51d7c93b40

	annotation PBI_ResultType = Record

"""
sc = TPL.replace("__ENTRIES__", entries).replace("\n", "\r\n")
# Replace the two generated expressions WHEREVER they sit, and keep everything
# else.
#
# This used to truncate the file from `expression LockSchema` to the end, on the
# assumption that the generated pair is always last. Desktop does not honour
# that: after Monthly Review was opened and saved it had moved Procore2 to the
# end of the file, past SchemaContract, and the next apply_lock silently deleted
# it -- the one expression all 93 queries navigate through, leaving 37 dangling
# references and a model that could not load.
_GENERATED = ("LockSchema", "SchemaContract")
_kept = []
for _b in re.split(r"(?m)^(?=expression )", etx_new):
    _m = re.match(r"expression\s+(?:'([^']+)'|(\S+))", _b)
    if _m and (_m.group(1) or _m.group(2)) in _GENERATED:
        continue
    _kept.append(_b)
etx_new = "".join(_kept).rstrip("\r\n") + "\r\n\r\n" + sc

print("=== %s ===" % proj)
print("  partitions locked      : %d" % len(files))
print("  contract entries       : %d (tables %d + expressions %d)" % (len(contract), len(contract)-len(expr_contract), len(expr_contract)))
print("  guarded in partitions  : SelectColumns +%d  RenameColumns +%d" % (psel, pren))
print("  guarded in expressions : SelectColumns +%d  RenameColumns +%d" % (gsel, gren))
print("  upgraded v1 -> v2      : %d" % len(upgraded))
print("  already locked         : %d" % len(already))
print("  deferred (--only)      : %d" % len(deferred))
print("  container expressions  : %s" % (sorted(containers) or "none"))
print("  skipped                : %d" % len(skipped))
if expr_bail:
    print("  expression bail-outs   :", expr_bail)
for t, why in skipped[:20]:
    print("      - %s: %s" % (t, why))

if APPLY:
    bdir = os.path.join(data_dir("backup"), proj + "_" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy(ef, os.path.join(bdir, "expressions.tmdl"))
    open(ef, "w", encoding="utf-8", newline="").write(etx_new)
    for f, t in files.items():
        shutil.copy(f, os.path.join(bdir, os.path.basename(f)))
        open(f, "w", encoding="utf-8", newline="").write(t)
    print("  APPLIED (backup: %s)" % os.path.relpath(bdir, HERE))
else:
    print("  DRY RUN")

# A v1 -> v2 upgrade renames the contract's `cols` field to `req` + `opt`, but
# this script SKIPS the canary table, so a canary written against v1 is left
# reading a field the contract no longer has. `e[cols]` on such a record is a
# runtime error, not a syntax error, so the compile gate cannot see it and the
# canary -- the thing that reports drift -- is the part that breaks. Refuse to
# report success quietly; re-run add_canary.py.
stale = []
for f in glob.glob(os.path.join(d, "tables", "*.tmdl")):
    txt = open(f, encoding="utf-8", errors="replace", newline="").read()
    if "e[cols]" in txt:
        stale.append(os.path.basename(f)[:-5])
if stale:
    print("  STALE CANARY (reads e[cols], contract now has req/opt): %s" % ", ".join(stale))
    sys.exit("  re-run: python add_canary.py %r --apply" % ROOT)
