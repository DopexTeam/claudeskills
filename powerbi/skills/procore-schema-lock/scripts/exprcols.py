"""Columns a shared DeltaSharing expression literally names.

These are references to columns that must exist in the share table the
expression reads, so they can be audited the same way a table's bound columns
are. Anything the expression creates mid-chain is absorbed by the `derived`
allowlist during calibration, exactly as for table entries.
"""
import re
from lockm import _scan_call

STR = re.compile(r'"((?:[^"]|"")*)"')


def _call_args(m, fname):
    """Yield the argument text of each fname(...) call."""
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


def _first_list(args):
    """The first {...} list literal in an argument string."""
    d = 0
    start = None
    for i, c in enumerate(args):
        if c == "{":
            if d == 0:
                start = i
            d += 1
        elif c == "}":
            d -= 1
            if d == 0 and start is not None:
                return args[start:i + 1]
    return ""


def extract_expression_cols(m):
    """Literal share-side column names referenced by this expression."""
    cols = set()
    for fn in ("Table.SelectColumns", "Table.RemoveColumns"):
        for a in _call_args(m, fn):
            cols |= {s.replace('""', '"') for s in STR.findall(_first_list(a))}
    # rename SOURCES (the pre-rename name is what must exist upstream)
    for a in _call_args(m, "Table.RenameColumns"):
        for pair in re.findall(r'\{\s*"((?:[^"]|"")*)"\s*,\s*"(?:[^"]|"")*"\s*\}', a):
            cols.add(pair.replace('""', '"'))
    # group keys
    for a in _call_args(m, "Table.Group"):
        cols |= {s.replace('""', '"') for s in STR.findall(_first_list(a))}
    # left-hand join keys only; the right side belongs to the other query
    for a in _call_args(m, "Table.NestedJoin"):
        cols |= {s.replace('""', '"') for s in STR.findall(_first_list(a))}
    return sorted(cols)
