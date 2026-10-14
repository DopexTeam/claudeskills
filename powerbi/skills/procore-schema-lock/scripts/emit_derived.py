"""Compute the canary's derived-column allowlist instead of calibrating it.

Usage: python emit_derived.py "<project folder>" [--write]

A column the M itself creates is never in the share, so the canary must not
report it as drift. Those lists were built empirically -- run the canary, see
what it cries about, add it -- which leaves a gap every time a query grows a new
computed column. Monthly Review surfaced four that way (TimeAndMaterial
created_on and vProcoreURL, TimeAndMaterialSubcontractor created_on and vKey)
after its contract was regenerated.

The syntax tree already knows: anything appearing as a PRODUCED column in
Table.AddColumn, DuplicateColumn, SplitColumn, ExpandRecordColumn or a
Table.Group aggregate is M-created by construction.

Rename TARGETS are deliberately excluded. They are produced too, but their
source IS a share column, and the canary already probes the pre-rename name --
listing them here would mask a real disappearance upstream of the rename.
"""
import os
import re
import sys
import glob
import json
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: F401  -- puts powerbi-desktop-engine on the path
from paths import data_file, data_dir
import astm
import astedges
from mbody import find_body, deindent
from usage import BLOCK

PRODUCING = {"Table.AddColumn": 1, "Table.DuplicateColumn": 2,
             "Table.SplitColumn": None, "Table.ExpandRecordColumn": None}


def produced_in(ast):
    """Columns this query creates outright."""
    out = set()
    renamed = set()
    for fn, args in astm.invocations(ast):
        if fn == "Table.AddColumn" and len(args) >= 2:
            n = astedges._lit(args[1])
            if n:
                out.add(n)
        elif fn == "Table.DuplicateColumn" and len(args) >= 3:
            n = astedges._lit(args[2])
            if n:
                out.add(n)
        elif fn == "Table.SplitColumn" and len(args) >= 2:
            old = astedges._lit(args[1])
            ls = astedges._list_args(args[2:])
            if ls:
                out |= {x for x in astm.text_of(ls[0]) if x != old}
        elif fn == "Table.ExpandRecordColumn" and len(args) >= 4:
            out |= set(astm.text_of(args[3]))
        elif fn == "Table.Group" and len(args) >= 3:
            for spec in astedges._list_members(args[2]):
                parts = astedges._list_members(spec)
                if parts:
                    n = astedges._lit(parts[0])
                    if n:
                        out.add(n)
        elif fn == "Table.ExpandTableColumn" and len(args) >= 4:
            out |= set(astm.text_of(args[3]))
        elif fn == "Table.AggregateTableColumn" and len(args) >= 3:
            # {{"src_col", List.Max, "NewName"}, ...} -- the produced name is the
            # THIRD element, so PrimeContractPayApp's DatePaid was invisible.
            for spec in astedges._list_members(args[2]):
                names = astm.text_of(spec)
                if len(names) >= 2:
                    out.add(names[-1])
        elif fn == "Table.RenameColumns" and len(args) >= 2:
            for pair in astedges._list_members(args[1]):
                names = astm.text_of(pair)
                if len(names) >= 2:
                    renamed.add((names[0], names[1]))

    # Renaming a DERIVED column yields a derived column, so the chain has to be
    # followed to a fixpoint. Excluding every rename target wholesale dropped
    # `cost_code name`, `infoJson.Approved PCCOs (C)`, `vCOPackageUpper` and
    # others that the hand-calibrated lists had needed -- they are renames of
    # columns the M created, not of share columns.
    #
    # A target whose source is a SHARE column still stays out: the canary probes
    # the pre-rename name, and listing the target would mask that column
    # disappearing upstream.
    for _ in range(len(renamed) + 1):
        grew = False
        for old, new in renamed:
            if old in out and new not in out:
                out.add(new)
                grew = True
        if not grew:
            break
    return out - {new for old, new in renamed if old not in out}


def bodies(d):
    out = {}
    ef = os.path.join(d, "expressions.tmdl")
    if os.path.exists(ef):
        t = open(ef, encoding="utf-8", newline="").read()
        for b in re.split(r"(?m)^(?=expression )", t):
            m = re.match(r"expression\s+(?:'([^']+)'|(\S+))\s*=(.*)", b)
            if not m:
                continue
            name = m.group(1) or m.group(2)
            inline = (m.group(3) or "").strip()
            if inline and inline != "```":
                continue
            r = find_body(b, r"^expression\s", 2)
            body = deindent(r[2], 2) if r else ""
            if body.strip():
                out["expr:" + name] = body
    for f in sorted(glob.glob(os.path.join(d, "tables", "*.tmdl"))):
        txt = open(f, encoding="utf-8", errors="replace", newline="").read()
        tm = re.search(r"(?m)^table\s+(?:'([^']+)'|(\S+))", txt)
        t = (tm.group(1) or tm.group(2)) if tm else os.path.basename(f)[:-5]
        ms = []
        for pb in [b for b in BLOCK.split(txt) if b.startswith("\tpartition")]:
            if not re.search(r"=\s*m\s*$", pb.split("\n", 1)[0].strip()):
                continue
            bd = find_body(pb, r"^\t\tsource =", 4)
            if bd:
                ms.append(deindent(bd[2], 4))
        if ms:
            out[t] = "\n".join(ms)
    return out


def main(root, write):
    d = glob.glob(os.path.join(root, "*.SemanticModel", "definition"))[0]
    proj = os.path.basename(os.path.normpath(root))
    src = bodies(d)
    asts, errs = astm.parse_many(src)
    if errs:
        print("  PARSE FAILURES (excluded, so their derived columns are unknown):")
        for n, e in sorted(errs.items()):
            print("    %-34s %s" % (n, e[:70]))
    out = {}
    for n, a in asts.items():
        if a is None:
            continue
        p = sorted(produced_in(a))
        if p:
            out[n] = p

    here = os.path.dirname(os.path.abspath(__file__))
    path = data_file("derived", proj + ".json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    o_tot = sum(len(v) for v in old.values())
    n_tot = sum(len(v) for v in out.values())
    print("  %s: hand-calibrated %d across %d entries -> computed %d across %d"
          % (proj, o_tot, len(old), n_tot, len(out)))

    missed = {k: sorted(set(v) - set(out.get(k, []))) for k, v in old.items()}
    missed = {k: v for k, v in missed.items() if v}
    if missed:
        print("  IN THE OLD LIST BUT NOT COMPUTED -- these would start being reported:")
        for k, v in sorted(missed.items()):
            print("    %-34s %s" % (k, v[:6]))
    else:
        print("  computed list covers every hand-calibrated entry")

    if write:
        # UNION, never replace. Some produced names are not statically knowable
        # -- a pivot takes its column names from the data -- so a computed list
        # can be incomplete, and replacing would make the canary start crying
        # drift on columns a human already confirmed are M-created. Union can
        # only suppress more, which costs precision in the canary and never
        # correctness in the contract: the two are separate artifacts.
        merged = {k: sorted(set(out.get(k, [])) | set(old.get(k, [])))
                  for k in set(out) | set(old)}
        json.dump({k: v for k, v in sorted(merged.items())}, open(path, "w"), indent=1)
        print("  wrote %s (union: %d across %d entries)"
              % (os.path.relpath(path, here),
                 sum(len(v) for v in merged.values()), len(merged)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], "--write" in sys.argv))
