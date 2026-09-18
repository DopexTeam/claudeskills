"""One dependency graph: report bindings (leaves) -> Procore share columns (roots).

Required = reachable. There are no per-case rules; every way a dependency can
arise is an EDGE KIND, and the traversal is uniform.

Nodes
  ("rep",   entity, property)        a visual / filter / slicer / bookmark binding
  ("obj",   table, name)             a model measure, calculated column or column
  ("qcol",  table, name)             a column as it exists inside one query
  ("share", share_table, column)     a Procore Delta Share column   [ROOT]

Edge kinds
  rep   -> obj     the report binds it
  obj   -> obj     INFO.CALCDEPENDENCY (measures, calc columns, relationships)
  obj   -> qcol    a bound model column is produced by its query
  qcol  -> qcol    produced-from: AddColumn / Split / Duplicate / Rename
  qcol  -> qcol    grain: every output depends on group keys, join keys, row
                   filters and sort keys, because losing one silently changes
                   which rows and which grain the whole query returns
  qcol  -> share   the name is read from a share table
  qcol  -> qcol    cross-query: a query that consumes another query's output

Attribution of a qcol to a specific share table is done where the syntax makes
it unambiguous, and falls back to every share the query reads. The fallback is
an edge like any other, not a separate code path -- it is less precise, never
less safe.
"""
import os
import re
import glob
import collections

from lockm import _scan_call, split_line_comment
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: F401  -- puts powerbi-desktop-engine on the path
from mbody import find_body, deindent
from navrefs import share_refs, container_expressions
from usage import report_refs, calc_dependency, model_inventory, BLOCK, LEAF_OBJ_TYPES

import astm
import astedges

STR = re.compile(r'"((?:[^"]|"")*)"')


def _calls(m, fname):
    i = 0
    while True:
        j = m.find(fname + "(", i)
        if j < 0:
            return
        op = j + len(fname)
        end = _scan_call(m, op)
        if end < 0:
            return
        yield m[op + 1:end - 1]
        i = end


def _lists(args, limit=None):
    out, depth, start = [], 0, None
    for i, c in enumerate(args):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                out.append(args[start:i + 1])
                if limit and len(out) >= limit:
                    return out
    return out


def _arg0(args):
    """Text of the first top-level argument."""
    depth = 0
    for i, c in enumerate(args):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            return args[:i]
    return args


def _names(chunk):
    return {s.replace('""', '"') for s in STR.findall(chunk)}


def _step_sources(m, containers):
    """step name -> share table, for steps that read a share directly."""
    alias = {}
    for a, t in re.findall(r'(?m)^\s*(#"[^"]+"|\w+)\s*=\s*\w+\s*\(\s*"([^"]+)"\s*\)\s*,?\s*$', m):
        alias[a.strip('#"')] = t
    for c in containers | {"[Data]"}:
        pat = (re.escape(c) if c != "[Data]" else r'\[Data\]')
        for a, t in re.findall(r'(?m)^\s*(#"[^"]+"|\w+)\s*=\s*.*?' + pat +
                               r'\s*\{\[Name="([^"]+)"\]\}', m):
            alias[a.strip('#"')] = t
    return alias


def _code_only(m):
    """The M with line comments removed, string literals respected.

    A table name written in prose is not a dependency. EOM's Budget carries
    `// -- Commitment costs -> J : line items in ...`, which made the regex
    record Budget as consuming the Commitment query and pulled Commitment's
    whole column set toward required. The syntax tree never sees comments; this
    is what lets the regex side agree with it.
    """
    return "\n".join(split_line_comment(l)[0] for l in m.split("\n"))


def _references(m, t):
    """Does this M name table `t`, as a whole identifier?

    A bare identifier cannot contain a space, so `ChangeOrderPotential (2)` can
    only ever appear quoted. Matching the bare name with ordinary word
    boundaries therefore fires INSIDE `#"ChangeOrderPotential (2)"` -- the next
    character is a space, so the lookahead passes -- and Monthly Review's
    `ChangeOrderPotential (2)` was recorded as consuming `ChangeOrderPotential`
    purely because its own name contains it. That pulled two unused columns
    (executed, project_id) into required, which breaks the actual guarantee:
    the report would fail on a column nothing uses.

    So the quoted form must close immediately after the name, and the bare form
    must not sit against a quote.
    """
    e = re.escape(t)
    if re.fullmatch(r"[A-Za-z_]\w*", t):
        pat = r'(?:#"%s"|(?<![A-Za-z0-9_"])%s(?![A-Za-z0-9_"]))' % (e, e)
    else:
        pat = r'#"%s"' % e
    return re.search(pat, m) is not None


def query_edges(table, m, containers, all_tables):
    """Edges contributed by one query's M."""
    E = collections.defaultdict(set)
    shares = share_refs(m, containers)
    step_src = _step_sources(m, containers)

    def qc(n):
        return ("qcol", table, n)

    # --- columns named against a source expression -> that share table ---
    # The head may be nested, e.g. SelectColumns(SelectRows(src("x"), ...), {...}),
    # so resolve every share reachable from it rather than pattern-matching one
    # shape. Partial attribution is worse than none: it narrows the target and
    # suppresses the all-shares fallback.
    attributed = collections.defaultdict(set)
    for fn in ("Table.SelectColumns", "Table.RemoveColumns"):
        for a in _calls(m, fn):
            ls = _lists(a, limit=1)
            if not ls:
                continue
            head = _arg0(a)
            tbls = set(share_refs(head, containers))
            for ref in re.findall(r'(?<![A-Za-z0-9_])(#"[^"]+"|\w+)', head):
                s = step_src.get(ref.strip('#"'))
                if s:
                    tbls.add(s)
            for n in _names(ls[0]):
                attributed[n] |= tbls

    # --- produced-from ---
    for a in _calls(m, "Table.AddColumn"):
        nm = re.search(r',\s*"((?:[^"]|"")*)"', a)
        if nm:
            for r in set(re.findall(r"\[([^\]\[]+)\]", a[nm.end():])):
                E[qc(nm.group(1).replace('""', '"'))].add(qc(r))
    for a in _calls(m, "Table.DuplicateColumn"):
        ns = STR.findall(a)
        if len(ns) >= 2:
            E[qc(ns[1])].add(qc(ns[0]))
    for a in _calls(m, "Table.SplitColumn"):
        ns, ls = STR.findall(a), _lists(a)
        if ns and ls:
            for new in _names(ls[-1]):
                E[qc(new)].add(qc(ns[0]))
    for a in _calls(m, "Table.RenameColumns"):
        for old, new in re.findall(r'\{\s*"((?:[^"]|"")*)"\s*,\s*"((?:[^"]|"")*)"\s*\}', a):
            E[qc(new.replace('""', '"'))].add(qc(old.replace('""', '"')))
    # aggregate lambdas: Table.Group(src, {keys}, {{"cI", each Nlive(_, "extended_amount")}})
    # the consumed column may be a [ref] OR a string passed to a helper
    for a in _calls(m, "Table.Group"):
        ls = _lists(a)
        if len(ls) >= 2:
            for spec in re.finditer(r'\{\s*"((?:[^"]|"")*)"\s*,(.*?)(?=\}\s*(?:,\s*\{|\}))', ls[1], re.S):
                produced = spec.group(1).replace('""', '"')
                body = spec.group(2)
                refs = set(re.findall(r"\[([^\]\[]+)\]", body)) | _names(body)
                for r in refs:
                    if r.strip():
                        E[qc(produced)].add(qc(r))

    # record expansion: the new columns all derive from the record column
    for a in _calls(m, "Table.ExpandRecordColumn"):
        ns, ls = STR.findall(a), _lists(a)
        if ns and ls:
            for new in _names(ls[-1]):
                E[qc(new)].add(qc(ns[0].replace('""', '"')))

    # a named column consumed by a transform is a dependency of the whole query
    for a in _calls(m, "Table.TransformColumns"):
        for p in re.findall(r'\{\s*"((?:[^"]|"")*)"', a):
            E[qc("__query__")].add(qc(p.replace('""', '"')))

    for a in _calls(m, "Table.ExpandTableColumn"):
        ls = _lists(a)
        if len(ls) >= 2:
            for new, old in zip(sorted(_names(ls[1])), sorted(_names(ls[0]))):
                E[qc(new)].add(qc(old))

    # --- grain: everything in the query depends on these ---
    grain = set()
    for a in _calls(m, "Table.Group"):
        ls = _lists(a, limit=1)
        if ls:
            grain |= _names(ls[0])
    for fn in ("Table.NestedJoin", "Table.Join"):
        for a in _calls(m, fn):
            for chunk in _lists(a, limit=2):
                grain |= _names(chunk)
    for a in _calls(m, "Table.SelectRows"):
        grain |= set(re.findall(r"\[([^\]\[]+)\]", a))
    for a in _calls(m, "Table.Sort"):
        grain |= {p.replace('""', '"') for p in re.findall(r'\{\s*"((?:[^"]|"")*)"', a)}
    grain = {g for g in grain if g.strip()}

    # --- cross-query: this query consumes another table's output ---
    code = _code_only(m)
    consumed = {t for t in all_tables if t != table and _references(code, t)}

    return E, shares, attributed, grain, consumed


def _merge(a, b):
    """Union two (edges, shares, attributed, grain, consumed) tuples.

    Every component unions except `attributed`, which is the one narrowing
    input: a column attributed to a specific share stops falling back to every
    share the query reads. Unioning attributions keeps each side's targets, so
    a column either side resolves stays at least as broad as that side alone.
    """
    (Ea, sa, ata, ga, ca), (Eb, sb, atb, gb, cb) = a, b
    E = collections.defaultdict(set, {k: set(v) for k, v in Ea.items()})
    for k, v in Eb.items():
        E[k] |= v
    at = collections.defaultdict(set, {k: set(v) for k, v in ata.items()})
    for k, v in atb.items():
        at[k] |= v
    return E, set(sa) | set(sb), at, set(ga) | set(gb), set(ca) | set(cb)


def build(project_dir, calcdep_csv, mode="union"):
    """mode: 'regex' (original), 'ast' (syntax tree only), 'union' (both).

    'union' is what ships. The other two exist so the gate can diff them: a
    difference is either a gap in the regexes or a gap in the tree walk, and
    both have to be explained before anything touches a client report.
    """
    R = glob.glob(os.path.join(project_dir, "*.Report", "definition"))[0]
    D = glob.glob(os.path.join(project_dir, "*.SemanticModel", "definition"))[0]
    etx = open(os.path.join(D, "expressions.tmdl"), encoding="utf-8", newline="").read()
    i = etx.find("expression LockSchema")
    containers = container_expressions(etx[:i] if i > 0 else etx)

    src, calc, meas, sort_by = model_inventory(D)
    dep_edges, kinds = calc_dependency(calcdep_csv)
    all_tables = set(src) | set(calc) | set(meas)

    E = collections.defaultdict(set)

    # report bindings -> model objects
    leaves = set()
    for ent, prop in report_refs(R):
        leaves.add(("rep", ent, prop))
        E[("rep", ent, prop)].add(("obj", ent, prop))

    # model dependency graph, verbatim
    for (t, o), deps in dep_edges.items():
        node = ("obj", t, o)
        if kinds.get((t, o), "").endswith(LEAF_OBJ_TYPES):
            leaves.add(node)               # breaks the model, not just one visual
        for dt, do in deps:
            E[node].add(("obj", dt, do))

    # a calculated table's every column depends on the table's own expression.
    #
    # Field parameters are the case that matters. The engine resolves their
    # NAMEOF list into real CALC_TABLE -> MEASURE edges, but those hang off the
    # node ("obj", T, T), which is only reached when the report binds the
    # column named after the table. A field parameter also carries `<T> Fields`
    # and `<T> Order`, and a report that binds only one of those -- a sort, or a
    # slicer on the order column -- would reach none of the dispatched measures,
    # and every column under them would be classified optional and null-pad in
    # silence. Butler-Cohen binds both, so it happens to be safe; that is luck,
    # not a property of the graph.
    for (t, o), _deps in dep_edges.items():
        if not kinds.get((t, o), "").endswith("CALC_TABLE"):
            continue
        for c in set(src.get(t, {})) | calc.get(t, set()) | meas.get(t, set()):
            if c != o:
                E[("obj", t, c)].add(("obj", t, o))

    # bound model column -> its column inside the query
    for t, mapping in src.items():
        for name in mapping:
            E[("obj", t, name)].add(("qcol", t, name))

    # sortByColumn: displaying a column requires whatever orders it. Nothing else
    # reaches a sort key, so without this edge it lands in optional, null-pads,
    # and the axis silently loses its ordering -- a visual failure, easy to miss.
    for t, mapping in sort_by.items():
        for col, key in mapping.items():
            E[("obj", t, col)].add(("obj", t, key))

    # per-query M edges
    grains, shares_of = {}, {}
    bodies, unhandled = {}, {}
    for f in sorted(glob.glob(os.path.join(D, "tables", "*.tmdl"))):
        txt = open(f, encoding="utf-8", errors="replace", newline="").read()
        tm = re.search(r"(?m)^table\s+(?:'([^']+)'|(\S+))", txt)
        t = (tm.group(1) or tm.group(2)) if tm else os.path.basename(f)[:-5]
        blk = [b for b in BLOCK.split(txt) if b.startswith("\tpartition")]
        if not blk:
            continue
        # every partition, not just the first: an incremental-refresh table has
        # one M expression per partition, and taking blk[0] silently analyses a
        # fraction of the table
        bodies_m = []
        for pb in blk:
            # TMDL's own discriminator. A partition whose mode is not `m` holds
            # DAX -- a calculated table, a calc group, or a FIELD PARAMETER,
            # whose body is a NAMEOF list. Feeding those to the M parser reports
            # a parse failure for something that was never M, which buries a
            # real failure in noise.
            if not re.search(r"=\s*m\s*$", pb.split("\n", 1)[0].strip()):
                continue
            bd = find_body(pb, r"^\t\tsource =", 4)
            if bd:
                bodies_m.append(deindent(bd[2], 4))
        if not bodies_m:
            continue
        bodies[t] = "\n".join(bodies_m)

    # one mast.exe round trip for the whole model rather than one per table
    asts, parse_errs = {}, {}
    if mode in ("ast", "union"):
        asts, parse_errs = astm.parse_many(bodies)

    for t, m in sorted(bodies.items()):
        got = None
        if mode in ("regex", "union"):
            got = query_edges(t, m, containers, all_tables)
        if mode in ("ast", "union") and asts.get(t) is not None:
            a = astedges.query_edges_ast(t, m, containers, all_tables, asts[t])
            unhandled[t] = a[5]
            got = a[:5] if got is None else _merge(got, a[:5])
        elif mode == "ast":
            # a query the parser rejected contributes nothing, which would be a
            # silent false negative -- surface it rather than treat it as empty
            parse_errs.setdefault(t, "not parsed")
        if got is None:
            continue
        qe, shares, attributed, grain, consumed = got
        for k, v in qe.items():
            E[k] |= v
        grains[t], shares_of[t] = grain, shares

        # every qcol of this query depends on its grain
        for g in grain:
            for other in set(list(qe.keys()) + [("qcol", t, n) for n in src.get(t, {})]):
                if other != ("qcol", t, g):
                    E[other].add(("qcol", t, g))

        # qcol -> share root (attributed where possible, else every share read)
        for n in list(src.get(t, {})):
            E[("qcol", t, n)].add(("qcol", t, "__query__"))
        named = set(attributed) | grain | set(src.get(t, {})) | {n for (_, _, n) in qe}
        for n in named:
            tgt = attributed.get(n) or shares
            for s in tgt:
                E[("qcol", t, n)].add(("share", s, n))

        # a query consuming another query depends on that query's columns
        for c in consumed:
            for n in src.get(c, {}):
                E[("qcol", t, n)].add(("qcol", c, n))

    return E, leaves, src, grains, shares_of, unhandled, parse_errs


def reachable(E, leaves):
    seen, stack = set(), list(leaves)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(E.get(n, ()))
    return seen
