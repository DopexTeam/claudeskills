"""Share-table references in an M query.

Delta Sharing navigation appears in several shapes across real Procore reports:

  1. inline chain     Source{[Name=cat]}[Data]{[Name="public"]}[Data]{[Name="tbl"]}[Data]
  2. named steps      public = #"share_token_x"{[Name="public"]}[Data],
                      tbl    = public{[Name="tbl"]}[Data]
  3. shared container Procore2{[Name="tbl"]}[Data]      (Procore2 returns the public schema)
  4. helper function  src = (n) => Procore2{[Name=n]}[Data]  ...  src("tbl")

Rather than enumerate shapes, take every `{[Name="X"]}` literal and subtract the
ones that are not tables: the share/catalog names (navigated from `Source`) and
`public` itself.

Missing any shape makes the drift canary silently audit nothing, which is
indistinguishable from "no drift" — so this errs toward over-collecting.
"""
import re

NAME = re.compile(r'\{\s*\[\s*Name\s*=\s*"((?:[^"]|"")*)"\s*\]\s*\}')
CATALOG = re.compile(r'Source\s*\{\s*\[\s*Name\s*=\s*"((?:[^"]|"")*)"\s*\]\s*\}')
PARAM_NAV = r'\{\s*\[\s*Name\s*=\s*%s\s*\]\s*\}'


def share_refs(m, containers=()):
    """Return the set of share table names this M query reads."""
    names = {x.replace('""', '"') for x in NAME.findall(m)}
    catalogs = {x.replace('""', '"') for x in CATALOG.findall(m)}
    out = names - catalogs - {"public"}

    # helper functions that indirect the table name through a parameter:
    #   src = (n) => <container>{[Name=n]}[Data]   ...   src("tbl")
    for hm in re.finditer(r'(\w+)\s*=\s*\(\s*(\w+)\s*\)\s*=>[^,\n]*?'
                          + PARAM_NAV % r'(\w+)', m):
        if hm.group(2) == hm.group(3):
            out |= {x.replace('""', '"') for x in re.findall(
                r'(?<![A-Za-z0-9_])' + re.escape(hm.group(1)) + r'\s*\(\s*"((?:[^"]|"")*)"\s*\)', m)}
    return out


def container_expressions(etx):
    """Names of shared expressions that RETURN the public schema.

    Such an expression is referenced by partitions as `Name{[Name="tbl"]}[Data]`,
    and the drift canary should reuse it rather than rebuilding the navigation —
    tenants differ in how the share is addressed (first catalog vs named
    explicitly), so re-deriving the path can land on the wrong share.
    """
    out = set()
    for b in re.split(r"(?m)^(?=expression )", etx):
        m = re.match(r"expression\s+(?:'([^']+)'|(\S+))", b)
        if not m or "DeltaSharing.Contents" not in b:
            continue
        # step that binds the public schema
        # the binding must END at the public schema -- an inline chain that
        # continues on to a table (…{[Name="public"]}[Data]{[Name="tbl"]}[Data])
        # returns a table, not a container
        pub = re.search(r'(?m)^\s*(#"[^"]+"|\w+)\s*=\s*[^\n]*'
                        r'\{\s*\[\s*Name\s*=\s*"public"\s*\]\s*\}\s*\[Data\]\s*,?\s*$', b)
        # the step the expression actually returns
        ins = list(re.finditer(r"(?m)^\s*in\s*$", b))
        if not pub or not ins:
            continue
        tail = b[ins[-1].end():].strip().split("\n")[0].strip()
        if tail and tail == pub.group(1).strip():
            out.add(m.group(1) or m.group(2))
    return out
