"""Point every Delta Sharing navigation at one shared container expression.

Usage:
  python containerize.py "<project folder>" [--apply] [--unpin] [--share=NAME]

Without --apply it is a dry run. Desktop MUST be closed to apply.

Why
---
These models opened a separate DeltaSharing.Contents connection at every query
site -- 133 in Company Review, 130 in Monthly Review -- and resolved the catalog
independently in each. Consolidating them behind one expression means:

  speed        the connection and catalog resolve once per refresh, not 130 times
  portability  every other query becomes source-agnostic. Repointing the model
               at a different source -- a warehouse, say -- is a one-line change
               here instead of an edit per query.

The share itself stays DERIVED from the entered credential (`Source[Name]{0}`).
Naming it in the M would turn a credential change into a model change: rotating
a token would mean installing Desktop and editing a query rather than swapping
the credential in the Service, where the client administers it.

`--share=NAME` pins the share explicitly and `--unpin` returns it to derived.
Pinning buys one thing: a loud failure when the WRONG credential is cached,
instead of silently loading another tenant -- every Procore tenant is served
from one metastore with identical table names. But that is an authoring-machine
hazard. Desktop caches one credential per data source across files; each Service
dataset carries its own binding. Derived is the default because the deployed
report is what matters.

How
---
Two navigation shapes exist, both rewritten to `Procore2{[Name="tbl"]}[Data]`:

  A  Source = DeltaSharing.Contents(EP, null),
     CatalogColumn = Source[Name]{0},
     X = Source{[Name=CatalogColumn]}[Data]{[Name="public"]}[Data]{[Name="t"]}[Data]

  B  Source = DeltaSharing.Contents(EP, null),
     #"share_token_x" = Source{[Name="share_token_x"]}[Data],
     public = #"share_token_x"{[Name="public"]}[Data],
     X = public{[Name="t"]}[Data]

The dead bindings are removed by deleting WHOLE LINES, never by editing around a
comma. Each is a single line ending in `,` and none is the final binding, so the
neighbours keep their own separators. Comma surgery inside a let is what broke a
production report once already; this avoids needing any.

A binding is only removed once the rewrite proves nothing else in that query
still references it.
"""
import os
import re
import sys
import glob
import json
import time
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: F401  -- puts powerbi-desktop-engine on the path
from paths import data_file, data_dir
from mbody import find_body, deindent, reindent, splice
from usage import BLOCK

CONTAINER = "Procore2"

# stereotyped single-line bindings, matched whole
RE_SOURCE = re.compile(r'(?m)^[ \t]*Source\s*=\s*DeltaSharing\.Contents\((.+?)\)\s*,\s*$')
RE_CATALOG = re.compile(r'(?m)^[ \t]*CatalogColumn\s*=\s*Source\[Name\]\{0\}\s*,\s*$')
RE_SHARE_B = re.compile(r'(?m)^[ \t]*#"(share_token_[^"]+)"\s*=\s*Source\{\[Name="[^"]+"\]\}\[Data\]\s*,\s*$')
RE_PUBLIC_B = re.compile(r'(?m)^[ \t]*public\s*=\s*#"share_token_[^"]+"\{\[Name="public"\]\}\[Data\]\s*,\s*$')

# navigation expressions, rewritten in place
NAV_A_TBL = re.compile(r'Source\{\[Name=CatalogColumn\]\}\[Data\]\{\[Name="public"\]\}\[Data\]'
                       r'\{\[Name="([^"]+)"\]\}\[Data\]')
NAV_A_PUB = re.compile(r'Source\{\[Name=CatalogColumn\]\}\[Data\]\{\[Name="public"\]\}\[Data\]')
NAV_B_TBL = re.compile(r'(?<![A-Za-z0-9_])public\{\[Name="([^"]+)"\]\}\[Data\]')


def endpoint_of(text):
    m = re.search(r'DeltaSharing\.Contents\(\s*"([^"]+)"', text)
    return m.group(1) if m else None


def share_of(text):
    m = re.search(r'\{\[Name="(share_token_[^"]+)"\]\}', text)
    return m.group(1) if m else None


def rewrite(m):
    """Rewrite one query body. Returns (new_body, n_navs, removed_bindings)."""
    out, navs = m, 0

    def sub_tbl(mo):
        return '%s{[Name="%s"]}[Data]' % (CONTAINER, mo.group(1))

    out, n = NAV_A_TBL.subn(sub_tbl, out)
    navs += n
    out, n = NAV_B_TBL.subn(sub_tbl, out)
    navs += n
    # the canary navigates only as far as the public schema
    out, n = NAV_A_PUB.subn(CONTAINER, out)
    navs += n
    if not navs:
        return m, 0, []

    # Removal runs to a FIXPOINT, re-scanning the current text each pass and
    # dropping at most one binding per pass. Collecting matches up front and
    # then mutating the string leaves every later offset pointing into the old
    # text, which drops one binding per query at best and cuts the wrong span
    # at worst.
    #
    # Order matters as well as rescanning: `public` refers to `#"share_token"`,
    # which refers to `Source`, so each becomes unreferenced only after the one
    # below it goes. A single pass could never unwind that chain.
    removed = []
    rules = (("Source", RE_SOURCE), ("CatalogColumn", RE_CATALOG),
             ("share_token", RE_SHARE_B), ("public", RE_PUBLIC_B))
    changed = True
    while changed:
        changed = False
        for label, rx in rules:
            mo = rx.search(out)
            if not mo:
                continue
            ident = mo.group(1) if label == "share_token" else label
            rest = out[:mo.start()] + out[mo.end():]
            # drop it only once nothing else in the query still names it
            if re.search(r'(?<![A-Za-z0-9_])(?:#")?' + re.escape(ident) + r'(?:")?(?![A-Za-z0-9_])', rest):
                continue
            out = rest
            removed.append(ident)
            changed = True
            break
    return out, navs, removed


def container_block(endpoint, share, nl):
    """The one expression every query navigates through, share named explicitly.

    See container_block_positional for the unpinned variant.

    Built line by line rather than via reindent(), which returns a LIST for
    splice() to join -- interpolating it into a format string writes a
    stringified Python list into the TMDL and the model will not open. The
    newline is taken from the file being edited: TMDL here is CRLF, and a block
    spliced in with bare LF leaves the file mixed.
    """
    return nl.join([
        "expression %s =" % CONTAINER,
        "\t\tlet",
        '\t\t    Source = DeltaSharing.Contents("%s", null),' % endpoint,
        '\t\t    Share = Source{[Name="%s"]}[Data],' % share,
        '\t\t    public = Share{[Name="public"]}[Data]',
        "\t\tin",
        "\t\t    public",
        "\tlineageTag: 9a1f3c07-2b64-4d58-8e13-5c7a90b4e2d1",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
        "",
    ])


def container_block_positional(endpoint, nl):
    """The container, with the share DERIVED from the entered credential.

    This is the default, and deliberately so. Naming the share in the M turns a
    credential change into a model change: rotating a token would mean opening
    Desktop and editing a query rather than swapping the credential in the
    Power BI Service, where the client actually administers it.

    The share is whatever the credential exposes, so credentials rotate freely
    and the model never needs reopening.

    What naming the share would buy is a loud failure if the WRONG credential is
    cached -- but that is a Desktop-side hazard: Desktop caches one credential
    per data source across files, while each Service dataset carries its own
    binding. It is an authoring-machine problem, not a deployed-report one, and
    not worth making token rotation a developer task.
    """
    return nl.join([
        "expression %s =" % CONTAINER,
        "\t\t// The share is whatever the entered credential exposes, so the",
        "\t\t// credential can be rotated or repointed in the Service without",
        "\t\t// touching this model. Every query navigates through here, so a",
        "\t\t// source change is a one-line change.",
        "\t\tlet",
        '\t\t    Source = DeltaSharing.Contents("%s", null),' % endpoint,
        "\t\t    CatalogColumn = Source[Name]{0},",
        '\t\t    public = Source{[Name=CatalogColumn]}[Data]{[Name="public"]}[Data]',
        "\t\tin",
        "\t\t    public",
        "\tlineageTag: 9a1f3c07-2b64-4d58-8e13-5c7a90b4e2d1",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
        "",
    ])


def main(root, apply, share_override=None, unpin=False):
    d = glob.glob(os.path.join(root, "*.SemanticModel", "definition"))[0]
    proj = os.path.basename(os.path.normpath(root))
    ef = os.path.join(d, "expressions.tmdl")
    etx = open(ef, encoding="utf-8", newline="").read()

    # Detection scans the tables too. A model can have every connection in its
    # partitions and none in expressions.tmdl -- MJS does -- and looking only at
    # expressions reports "no endpoint" for a model with six of them.
    scan = etx + "".join(
        open(f, encoding="utf-8", errors="replace", newline="").read()
        for f in sorted(glob.glob(os.path.join(d, "tables", "*.tmdl"))))
    endpoint = endpoint_of(scan)
    share = None if unpin else (share_override or share_of(scan))
    if not endpoint:
        sys.exit("no DeltaSharing endpoint found")

    print("=== %s ===" % proj)
    print("  endpoint : %s" % endpoint)
    print("  share    : %s" % (share or "NOT NAMED IN MODEL -- consolidating unpinned"))
    if ("expression %s " % CONTAINER) in etx:
        new_etx = etx
        if unpin and "CatalogColumn = Source[Name]{0}" not in etx:
            nl = "\r\n" if "\r\n" in etx else "\n"
            i = etx.index("expression %s " % CONTAINER)
            j = etx.find(nl + "expression ", i + 1)
            j = len(etx) if j < 0 else j + len(nl)
            new_etx = etx[:i] + container_block_positional(endpoint, nl) + etx[j:]
            print("  container: %s UNPINNED -- share derived from the credential"
                  % CONTAINER)
        elif share and "CatalogColumn = Source[Name]{0}" in etx:
            # An existing container built UNPINNED, now that the share name is
            # known. Pinning is a separate change from consolidating, so it has
            # to be possible after the fact -- the token may live only in
            # Desktop's credential store and arrive later.
            nl = "\r\n" if "\r\n" in etx else "\n"
            i = etx.index("expression %s " % CONTAINER)
            j = etx.find(nl + "expression ", i + 1)
            if j < 0:
                j = len(etx)
            else:
                j += len(nl)
            new_etx = etx[:i] + container_block(endpoint, share, nl) + etx[j:]
            print("  container: %s REPINNED to %s" % (CONTAINER, share))
        else:
            print("  container: %s already present" % CONTAINER)
    else:
        print("  container: adding %s%s" % (CONTAINER, "" if share else " (unpinned)"))
        nl = "\r\n" if "\r\n" in etx else "\n"
        new_etx = ((container_block(endpoint, share, nl) if share
                    else container_block_positional(endpoint, nl)) + etx)

    # --- expressions ---
    blocks, e_navs, e_removed, e_hits = [], 0, 0, []
    for b in re.split(r"(?m)^(?=expression )", new_etx):
        mm = re.match(r"expression\s+(?:'([^']+)'|(\S+))", b)
        if not mm or "DeltaSharing.Contents" not in b or b.startswith("expression %s " % CONTAINER):
            blocks.append(b)
            continue
        name = mm.group(1) or mm.group(2)
        r = find_body(b, r"^expression\s", 2)
        if not r:
            blocks.append(b)
            continue
        body = deindent(r[2], 2)
        nb, navs, removed = rewrite(body)
        if navs:
            e_navs += navs
            e_removed += len(removed)
            e_hits.append(name)
            b = splice(b, r[0], r[1], reindent(nb, 2))
        blocks.append(b)
    new_etx = "".join(blocks)

    # --- table partitions ---
    files, t_navs, t_removed, t_hits = {}, 0, 0, []
    for f in sorted(glob.glob(os.path.join(d, "tables", "*.tmdl"))):
        txt = open(f, encoding="utf-8", newline="").read()
        if "DeltaSharing.Contents" not in txt:
            continue
        tm = re.search(r"(?m)^table\s+(?:'([^']+)'|(\S+))", txt)
        tname = (tm.group(1) or tm.group(2)) if tm else os.path.basename(f)[:-5]
        changed = False
        for blk in [b for b in BLOCK.split(txt) if b.startswith("\tpartition")]:
            if not re.search(r"=\s*m\s*$", blk.split("\n", 1)[0].strip()):
                continue
            r = find_body(blk, r"^\t\tsource =", 4)
            if not r:
                continue
            body = deindent(r[2], 4)
            nb, navs, removed = rewrite(body)
            if not navs:
                continue
            newblk = splice(blk, r[0], r[1], reindent(nb, 4))
            txt = txt.replace(blk, newblk)
            t_navs += navs
            t_removed += len(removed)
            changed = True
        if changed:
            files[f] = txt
            t_hits.append(tname)

    print("  expressions rewritten : %d  (%d navigations, %d dead bindings dropped)"
          % (len(e_hits), e_navs, e_removed))
    print("  tables rewritten      : %d  (%d navigations, %d dead bindings dropped)"
          % (len(t_hits), t_navs, t_removed))
    left = sum(len(re.findall("DeltaSharing.Contents", t)) for t in files.values()) \
        + len(re.findall("DeltaSharing.Contents", new_etx))
    print("  DeltaSharing.Contents call sites remaining: %d (target: 1)" % left)
    pos = len(re.findall(r"Source\[Name\]\{0\}", new_etx)) \
        + sum(len(re.findall(r"Source\[Name\]\{0\}", t)) for t in files.values())
    print("  positional catalog lookups remaining      : %d (target: %d)"
          % (pos, 0 if share else 1))
    if not share:
        print("  NOTE: consolidated but UNPINNED. The cross-tenant risk is not")
        print("        removed, only centralised -- supply the share token and")
        print("        the fix is one line in %s." % CONTAINER)

    if not apply:
        print("  DRY RUN")
        return 0

    bdir = os.path.join(data_dir("backup"),
                        proj + "_container_" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy(ef, os.path.join(bdir, "expressions.tmdl"))
    open(ef, "w", encoding="utf-8", newline="").write(new_etx)
    for f, t in files.items():
        shutil.copy(f, os.path.join(bdir, os.path.basename(f)))
        open(f, "w", encoding="utf-8", newline="").write(t)
    print("  APPLIED (backup: %s)" % bdir)
    return 0


if __name__ == "__main__":
    _share = None
    for _a in sys.argv[2:]:
        if _a.startswith("--share="):
            _share = _a[len("--share="):]
    sys.exit(main(sys.argv[1], "--apply" in sys.argv, _share, "--unpin" in sys.argv))
