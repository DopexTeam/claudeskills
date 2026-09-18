"""Minimal M let-body linter.

Catches the failure class where two let-bindings get fused because the step
separator was swallowed (e.g. a comma appended into a trailing `// comment`).
A "does the previous line end with a comma" check cannot see this -- the comma
IS there, inside the comment. This is the gate that must pass before applying.
"""
import re


def strip_comments_and_strings(s):
    """Blank string interiors and comments, preserving length and newlines.

    Quote characters themselves are kept so a quoted identifier (#"Renamed
    Columns") stays recognisable as one.
    """
    out = list(s)
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == '"':
            j = i + 1
            while j < n:
                if s[j] == '"':
                    if j + 1 < n and s[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                if s[k] != "\n":
                    out[k] = " "
            i = j + 1
        elif c == '/' and i + 1 < n and s[i + 1] == '/':
            j = s.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c == '/' and i + 1 < n and s[i + 1] == '*':
            j = s.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if s[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def split_top_level(s, seps=","):
    parts, depth, cur = [], 0, []
    for c in s:
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c in seps and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    parts.append("".join(cur))
    return parts


BINDING = re.compile(r'^\s*(?:#"[^"]*"|[A-Za-z_][A-Za-z0-9_\.]*)\s*=', re.S)


def count_depth0_bindings(seg):
    """Line-initial `name =` bindings at paren-depth 0. More than one means a
    lost separator fused two bindings into a single segment."""
    depth, n, at_line_start, i = 0, 0, True, 0
    while i < len(seg):
        c = seg[i]
        if c == "\n":
            at_line_start = True
            i += 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif at_line_start and not c.isspace() and depth == 0:
            if BINDING.match(seg[i:]):
                n += 1
        if not c.isspace():
            at_line_start = False
        i += 1
    return n


def lint_let(m):
    """Return a list of problems for the OUTER let body of an M expression."""
    clean = strip_comments_and_strings(m)
    lm = re.search(r"(?m)^let[ \t]*$", clean)
    ins = list(re.finditer(r"(?m)^in[ \t]*$", clean))
    if not lm or not ins:
        return []
    body = clean[lm.end():ins[-1].start()]
    bad = []
    for idx, seg in enumerate(split_top_level(body)):
        if not seg.strip():
            if idx != len(split_top_level(body)) - 1:
                bad.append("empty binding at position %d" % idx)
            continue
        if not BINDING.match(seg):
            bad.append("not a binding: %r" % seg.strip()[:90])
            continue
        k = count_depth0_bindings(seg)
        if k > 1:
            bad.append("fused bindings (%d in one segment -- missing comma): %r"
                       % (k, seg.strip()[:90]))
    return bad


# M reserved keywords. Using one as a function parameter is a syntax error the
# TMDL parser does NOT catch: TMDL validates structure, the mashup engine
# compiles M, and only the second one sees this. Generating `optional as list`
# cost a broken model open, and the compiler reproduces it exactly --
# "Token Identifier expected" at the parameter name.
#
# A reserved word inside brackets is NOT an error. `[type]` is a FIELD NAME, not
# an expression, so the grammar allows it; Company Review's Commitments query
# uses it and compiles clean. This linter flagged it for a while, which is worse
# than useless -- a validator that cries wolf gets ignored when it is right.
# Binding positions only.
M_KEYWORDS = {
    "and", "as", "each", "else", "error", "false", "if", "in", "is", "let",
    "meta", "not", "otherwise", "or", "section", "shared", "then", "true",
    "try", "type", "optional", "nullable",
}


def lint_identifiers(m):
    """Problems with generated identifiers: reserved words used unquoted."""
    bad = []
    for sig in re.finditer(r"\(([^)]*)\)\s*as\s+\w+\s*=>", m):
        for part in sig.group(1).split(","):
            name = part.strip().split(" ")[0].strip()
            if name in M_KEYWORDS:
                bad.append("reserved word as function parameter: %r" % name)
    for name in re.findall(r"(?m)^\s*([A-Za-z_]\w*)\s*=[^=]", m):
        if name in M_KEYWORDS:
            bad.append("reserved word as unquoted let binding: %r" % name)
    return bad
