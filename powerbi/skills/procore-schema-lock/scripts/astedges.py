"""Dependency edges for one query, read off Power BI's own M syntax tree.

Mirrors depgraph.query_edges. The difference is that arguments are identified
by POSITION and share navigations by SHAPE, both of which the regexes could only
approximate -- and every gap found so far was exactly that approximation
failing: a nested call head, a column named as a string inside an aggregate
lambda, an unmatched ')' inside a comment.

Returns the same shape as the regex extractor so the two can be unioned:
    (edges, shares, attributed, grain, consumed, unhandled)

The union is the safety argument. emit_required builds the applied contract only
from qcol nodes that are real bound model columns, so adding edges can add
required columns but can never remove one. A mistake here costs precision, not
correctness -- with one exception, noted on `attributed` below.
"""
import collections

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: F401  -- puts powerbi-desktop-engine on the path
import astm

ELEM = "RequiredElementAccessExpressionSyntaxNode"
LIST = "ListExpressionSyntaxNode"
FUNC = "FunctionExpressionSyntaxNode"

# function -> how its arguments carry dependencies
KNOWN = {
    "Table.SelectColumns": "project",
    "Table.RemoveColumns": "project",
    "Table.ReorderColumns": "project",
    "Table.Group": "group",
    "Table.NestedJoin": "join",
    "Table.Join": "join",
    "Table.SelectRows": "filter",
    "Table.Sort": "sort",
    "Table.AddColumn": "add",
    "Table.DuplicateColumn": "dup",
    "Table.SplitColumn": "split",
    "Table.RenameColumns": "rename",
    "Table.ExpandTableColumn": "expand",
    "Table.ExpandRecordColumn": "expand",
    "Table.TransformColumns": "consume",
    "Table.AggregateTableColumn": "consume",
    "Table.TransformColumnTypes": "consume",
}


def _members(node):
    m = node.get("Members") if isinstance(node, dict) else None
    return [x for x in m if isinstance(x, dict)] if isinstance(m, list) else []


def _list_members(node):
    """Item nodes of a list literal, or [] if this node is not one."""
    return _members(node) if isinstance(node, dict) and node.get("k") == LIST else []


def _list_args(args):
    """Arguments that are literally {...} lists, in order."""
    return [a for a in args if isinstance(a, dict) and a.get("k") == LIST]


def _lit(node):
    """The one string this node is, if it is a bare text constant."""
    t = astm.text_of(node)
    return t[0] if len(t) == 1 else None


def _nav_key(elem):
    """Share table named by a `X{[Name=...]}` element access.

    ("lit", name) when the key is a literal, ("param", ident) when it is a
    function parameter -- the helper-function shape `(n) => Procore2{[Name=n]}`.
    """
    key = elem.get("Key")
    if not isinstance(key, dict) or key.get("k") != "RecordExpressionSyntaxNode":
        return None
    for mem in _members(key):
        nm = mem.get("Name")
        if not (isinstance(nm, dict) and nm.get("Name") == "Name"):
            continue
        val = mem.get("Value")
        lit = _lit(val)
        if lit is not None:
            return ("lit", lit)
        ids = astm.identifiers(val)
        if ids:
            return ("param", ids[0])
    return None


def direct_navs(node):
    """Share tables named by literal navigations anywhere beneath a node."""
    out = set()
    for n in astm.walk(node):
        if n.get("k") != ELEM:
            continue
        k = _nav_key(n)
        if k and k[0] == "lit":
            out.add(k[1])
    return out


def helper_defs(ast):
    """Variables bound to a function that navigates by its own parameter."""
    out = set()
    for n in astm.walk(ast):
        if n.get("k") != "VariableInitializer":
            continue
        nm = n.get("Name")
        val = n.get("Value")
        if not (isinstance(nm, dict) and isinstance(val, dict)):
            continue
        if val.get("k") != FUNC:
            continue
        params = {i for p in ([val.get("Parameters")] if isinstance(val.get("Parameters"), dict)
                              else val.get("Parameters") or [])
                  if isinstance(p, dict) for i in astm.identifiers(p)}
        for e in astm.walk(val):
            if e.get("k") != ELEM:
                continue
            k = _nav_key(e)
            if k and k[0] == "param" and (not params or k[1] in params):
                out.add(nm.get("Name"))
    return out


def _navs_in(node, helpers):
    """Shares a subtree reads: literal navigations plus helper calls."""
    out = direct_navs(node)
    for fn, args in astm.invocations(node):
        if fn in helpers:
            for a in args:
                lit = _lit(a)
                if lit:
                    out.add(lit)
    return out


def step_sources(ast, helpers):
    """Variable name -> shares it resolves to, to a fixpoint.

    A step is a share source directly (a navigation), through a helper call, or
    transitively by being built from another step.
    """
    inits = [(n["Name"]["Name"], n["Value"]) for n in astm.walk(ast)
             if n.get("k") == "VariableInitializer"
             and isinstance(n.get("Name"), dict) and isinstance(n.get("Value"), dict)
             and isinstance(n["Name"].get("Name"), str)]
    alias = collections.defaultdict(set)
    refs = {}
    for name, val in inits:
        alias[name] |= _navs_in(val, helpers)
        # hoisted: re-walking each step's subtree once per fixpoint pass is
        # quadratic in step count, and these queries run to a hundred steps
        refs[name] = set(astm.identifiers(val)) - {name}
    for _ in range(len(inits) + 1):
        changed = False
        for name in refs:
            for ident in refs[name]:
                got = alias.get(ident)
                if got and not got <= alias[name]:
                    alias[name] |= got
                    changed = True
        if not changed:
            break
    return {k: v for k, v in alias.items() if v}


def query_edges_ast(table, m, containers, all_tables, ast):
    E = collections.defaultdict(set)
    attributed = collections.defaultdict(set)
    grain = set()

    def qc(n):
        return ("qcol", table, n)

    helpers = helper_defs(ast)
    alias = step_sources(ast, helpers)
    shares = set(direct_navs(ast))
    for fn, args in astm.invocations(ast):
        if fn in helpers:
            for a in args:
                lit = _lit(a)
                if lit:
                    shares.add(lit)

    for fn, args in astm.invocations(ast):
        kind = KNOWN.get(fn)
        if kind is None:
            continue
        lists = [astm.text_of(a) for a in args]

        if kind == "project" and len(args) >= 2:
            # Attribution NARROWS a column from "every share this query reads"
            # to a specific one, so unlike every other edge it can subtract.
            # It must therefore resolve the whole head -- a nested call, a step
            # alias, a helper call -- or resolve nothing at all. Partial
            # attribution suppresses the all-shares fallback and loses real
            # dependencies; that is a false negative, and it has happened.
            tbls = set(_navs_in(args[0], helpers))
            for ident in set(astm.identifiers(args[0])):
                tbls |= alias.get(ident, set())
            for c in lists[1]:
                attributed[c] |= tbls

        elif kind == "group":
            if len(args) >= 2:
                grain |= set(astm.text_of(args[1]))
            if len(args) >= 3:
                # {{"name", each f([col])}, ...} -- pair each produced name with
                # its own lambda. Scraping the whole argument instead makes
                # every aggregate depend on every other's inputs.
                for spec in _list_members(args[2]):
                    parts = _list_members(spec)
                    if not parts:
                        continue
                    produced = _lit(parts[0])
                    if not produced:
                        continue
                    for body in parts[1:]:
                        for r in set(astm.field_refs(body)) | set(astm.text_of(body)):
                            if r and r != produced:
                                E[qc(produced)].add(qc(r))

        elif kind == "join" and len(args) >= 4:
            grain |= set(astm.text_of(args[1])) | set(astm.text_of(args[3]))

        elif kind == "filter" and len(args) >= 2:
            grain |= set(astm.field_refs(args[1]))

        elif kind == "sort" and len(args) >= 2:
            grain |= set(astm.text_of(args[1]))

        elif kind == "add" and len(args) >= 3:
            new = _lit(args[1])
            if new:
                for r in astm.field_refs(args[2]):
                    E[qc(new)].add(qc(r))

        elif kind == "dup" and len(args) >= 3:
            old, new = _lit(args[1]), _lit(args[2])
            if old and new:
                E[qc(new)].add(qc(old))

        elif kind == "split" and len(args) >= 2:
            old = _lit(args[1])
            ls = _list_args(args[2:])
            if old and ls:
                for new in astm.text_of(ls[0]):
                    if new != old:
                        E[qc(new)].add(qc(old))

        elif kind == "rename" and len(args) >= 2:
            for pair in _list_members(args[1]):
                names = astm.text_of(pair)
                if len(names) >= 2:
                    E[qc(names[1])].add(qc(names[0]))

        elif kind == "expand" and len(args) >= 3:
            src_col = _lit(args[1])
            olds = astm.text_of(args[2])
            news = astm.text_of(args[3]) if len(args) >= 4 else olds
            for i, new in enumerate(news):
                if i < len(olds):
                    E[qc(new)].add(qc(olds[i]))
                if src_col:
                    E[qc(new)].add(qc(src_col))

        elif kind == "consume" and len(args) >= 2:
            for spec in _list_members(args[1]):
                c = _lit(_list_members(spec)[0]) if _list_members(spec) else _lit(spec)
                if c:
                    E[qc("__query__")].add(qc(c))

    idents = set(astm.identifiers(ast))
    consumed = {t for t in all_tables if t != table and t in idents}
    unhandled = astm.unhandled_functions(ast, set(KNOWN))

    return E, shares, attributed, grain, consumed, unhandled
