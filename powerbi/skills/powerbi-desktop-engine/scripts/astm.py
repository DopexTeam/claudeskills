"""Parse M with Power BI's own parser and extract dependency edges from the tree.

Runs mast.exe (built from mast/MAst.cs) to get the syntax tree as JSON, then
walks it. Every regex in depgraph.query_edges reimplements argument-position
analysis; the tree gives it exactly.

The point is not elegance. Every gap found so far was a PARSING gap producing a
false negative -- a nested call head, a column named as a string inside an
aggregate lambda, an unmatched ')' inside a comment. With regexes there is no
way to enumerate what is unrecognised; with the tree, `unhandled_functions()`
lists every invocation this module has no rule for.
"""
import os
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "mast", "mast.exe")
DLL = os.path.join(HERE, "mast", "Microsoft.MashupEngine.dll")

# node kinds. Invocation nodes are arity-suffixed -- InvocationExpressionSyntaxNode2,
# ...N -- so match the prefix, never an enumerated list.
INVOKE_PREFIX = "InvocationExpressionSyntaxNode"
LIST = "ListExpressionSyntaxNode"
CONST = "ConstantExpressionSyntaxNode"
FIELD = "RequiredFieldAccessExpressionSyntaxNode"


def available():
    return os.path.exists(EXE) and os.path.exists(DLL)


def parse_many(named):
    """{name: m_text} -> {name: ast_or_None}, plus {name: error}."""
    lines = []
    for n, m in named.items():
        lines.append(n.replace("\t", " ") + "\t" +
                     m.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t"))
    r = subprocess.run([EXE, DLL], input="\n".join(lines),
                       capture_output=True, text=True, encoding="utf-8")
    if not (r.stdout or "").strip():
        raise RuntimeError("mast produced no output: " + (r.stderr or "")[:300])
    asts, errs = {}, {}
    for rec in json.loads(r.stdout):
        if rec.get("ok"):
            asts[rec["name"]] = rec["ast"]
        else:
            asts[rec["name"]] = None
            errs[rec["name"]] = rec.get("error", "")
    return asts, errs


def children(node):
    """Child nodes, in declaration order."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "k" or isinstance(v, str):
                continue
            if isinstance(v, list):
                for i in v:
                    if isinstance(i, dict):
                        yield i
            elif isinstance(v, dict):
                yield v
    elif isinstance(node, list):
        for i in node:
            if isinstance(i, dict):
                yield i


def walk(node):
    if isinstance(node, dict):
        yield node
    for c in children(node):
        for n in walk(c):
            yield n


def text_of(node):
    """Every string literal beneath a node (TextValue carries it on `String`)."""
    out = []
    for n in walk(node):
        if n.get("k") == "TextValue" and isinstance(n.get("String"), str):
            out.append(n["String"])
    return out


def identifiers(node):
    """Every identifier name beneath a node."""
    out = []
    for n in walk(node):
        if n.get("k", "").endswith("StringIdentifier") and isinstance(n.get("Name"), str):
            out.append(n["Name"])
    return out


def field_refs(node):
    """[col] references beneath a node -- the FIELD NAME only.

    The name lives on MemberName; `Expression` is the thing being indexed. For
    `each [status]`, which desugars to `(_) => _[status]`, taking every
    identifier beneath the node yields `_` as well, and a stray `_` becomes a
    share root for a column that cannot exist -- an assertion that fires on
    every refresh.
    """
    out = []
    for n in walk(node):
        if n.get("k") == FIELD:
            mn = n.get("MemberName")
            if isinstance(mn, dict) and isinstance(mn.get("Name"), str):
                out.append(mn["Name"])
    return out


_INV_CACHE = {}


def invocations(ast):
    """(function_name, [argument_nodes]) for every call in the tree.

    Uses the node's own Function / Arguments properties rather than child order.
    Memoised by node identity: extraction asks the same subtrees repeatedly, and
    a full re-walk per question is quadratic on real queries.
    """
    key = id(ast)
    hit = _INV_CACHE.get(key)
    if hit is not None and hit[0] is ast:
        return hit[1]
    out = []
    for n in walk(ast):
        if not str(n.get("k", "")).startswith(INVOKE_PREFIX):
            continue
        fn = n.get("Function")
        names = identifiers(fn) if isinstance(fn, dict) else []
        args = n.get("Arguments")
        args = [a for a in args if isinstance(a, dict)] if isinstance(args, list) else []
        out.append((names[0] if names else None, args))
    _INV_CACHE[key] = (ast, out)
    return out


def list_literals(node):
    """{...} list literals beneath a node, each as its list of string members."""
    out = []
    for c in walk(node):
        if c.get("k") == LIST:
            out.append(text_of(c))
    return out


def unhandled_functions(ast, known):
    """Invocations this module has no edge rule for.

    The property regexes cannot have: what is unrecognised is enumerable.
    """
    return sorted({fn for fn, _ in invocations(ast) if fn and fn not in known})
