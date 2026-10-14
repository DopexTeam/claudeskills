"""Put the powerbi-desktop-engine scripts on the import path.

That sibling skill owns everything generic to Power BI: locating Desktop's
libraries, compiling M with Power BI's own engine, parsing M to a syntax tree,
reading M out of TMDL, and watching a refresh. This skill owns only what is
specific to Procore Delta Sharing — the share navigation, the dependency graph
down to share columns, and the lock itself.

The two ship together, so this resolves rather than duplicates. Restating the
generic half here would create exactly the drift the skills manifest warns about
("one home per fact").

Import this before importing any of them:

    import engine            # noqa: F401  -- path side effect
    import astm
    from mbody import find_body
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = "powerbi-desktop-engine"

# sibling skill (…/skills/<name>/scripts), then a plugin layout where both
# skills sit under skills/ and the shared code is one level further out
CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(HERE)), ENGINE, "scripts"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                 "skills", ENGINE, "scripts"),
]


def path():
    for c in CANDIDATES:
        if os.path.isdir(c):
            return c
    raise SystemExit(
        "The %s skill was not found next to this one.\n"
        "These two are vendored together; this skill needs its M compiler,\n"
        "parser and TMDL reader. Looked in:\n  %s"
        % (ENGINE, "\n  ".join(CANDIDATES)))


_p = path()
if _p not in sys.path:
    sys.path.insert(0, _p)
