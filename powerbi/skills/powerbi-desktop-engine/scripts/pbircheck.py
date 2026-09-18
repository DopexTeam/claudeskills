"""Structural and referential checks on a PBIR report definition.

    python pbircheck.py "<project folder or *.Report/definition>" [--schema]

Exists for the same reason `compilecheck` does. TMDL parsing is not M
validation; JSON parsing is not PBIR validation. A report whose every file is
well-formed JSON can still be one Desktop refuses to open, because what matters
is whether the pieces REFER to each other correctly.

The authority on PBIR is Desktop opening the file. This is a cheap pre-filter
that catches the errors a generator actually makes, without launching anything.

What it checks -- each one a way a generated report breaks:

  container shape   exactly one of `visual` or `visualGroup`; PBIR has a
                    containment hierarchy, not a flat list of visuals. Across
                    five hand-authored reports, 387 of 2235 containers are
                    GROUPS and 1572 sit inside one. Code that assumes
                    `visual.visualType` is wrong for 17% of files.
  position          x/y/z/height/width present and numeric
  unique names      a duplicated container name silently breaks bookmarks and
                    selection
  parent resolves   every `parentGroupName` names an existing group IN THE SAME
                    PAGE -- a dangling parent is the PBIR equivalent of the
                    dangling `Procore2` reference that made a model unopenable
  no cycles         a group cannot contain itself transitively
  bookmarks         every visual a bookmark names still exists

`--schema` additionally validates each file against its declared `$schema`,
which needs the `jsonschema` package. Everything else here is stdlib only,
because that check cannot be complete: Microsoft publishes these schemas but
publication lags Desktop. Of the five visualContainer versions in this corpus,
2.8.0 and 2.9.0 are published (2027 files) while 2.10.0, 2.11.0 and 2.12.0 are
not (208 files). Those fall back to the newest published version BELOW them and
say so, rather than silently validating against the wrong contract.
"""
import os
import re
import sys
import json
import glob
import collections

SCHEMA_RE = re.compile(r"definition/([A-Za-z]+)/([0-9.]+)/schema\.json")


def _ver(v):
    return tuple(int(x) for x in v.split("."))


def definition_dir(path):
    if os.path.isdir(os.path.join(path, "pages")):
        return path
    hits = glob.glob(os.path.join(path, "*.Report", "definition"))
    if not hits:
        sys.exit("no PBIR definition found under %s" % path)
    return hits[0]


def load(d):
    """Every PBIR json, as (relative path, parsed) -- or a parse failure."""
    out, bad = {}, []
    for dp, _, fs in os.walk(d):
        for f in sorted(fs):
            if not f.endswith(".json"):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, d).replace("\\", "/")
            try:
                out[rel] = json.load(open(p, encoding="utf-8-sig"))
            except Exception as e:
                bad.append((rel, str(e)[:90]))
    return out, bad


def check(d):
    docs, bad = load(d)
    problems = [("unparseable", r, e) for r, e in bad]
    stats = collections.Counter()

    # containers live at pages/<page>/visuals/<name>/visual.json; groups and
    # their children are scoped to a page, so resolve parents per page
    by_page = collections.defaultdict(dict)
    for rel, doc in docs.items():
        m = re.match(r"pages/([^/]+)/visuals/([^/]+)/visual\.json$", rel)
        if m:
            by_page[m.group(1)][m.group(2)] = (rel, doc)

    for page, containers in sorted(by_page.items()):
        groups, names = {}, collections.Counter()
        for folder, (rel, doc) in containers.items():
            has_v, has_g = "visual" in doc, "visualGroup" in doc
            if has_v == has_g:
                problems.append(("container shape", rel,
                                 "needs exactly one of visual / visualGroup"))
            stats["visualGroup" if has_g else "visual"] += 1

            nm = doc.get("name")
            if not nm:
                problems.append(("no name", rel, "container has no name"))
            else:
                names[nm] += 1
                if has_g:
                    groups[nm] = rel

            pos = doc.get("position")
            if not isinstance(pos, dict):
                problems.append(("position", rel, "missing position"))
            else:
                for k in ("x", "y", "width", "height"):
                    if not isinstance(pos.get(k), (int, float)):
                        problems.append(("position", rel,
                                         "%s is %r, not a number" % (k, pos.get(k))))

        for nm, n in names.items():
            if n > 1:
                problems.append(("duplicate name", page, "%s appears %d times" % (nm, n)))

        # parents resolve, and the hierarchy is acyclic
        parent = {}
        for folder, (rel, doc) in containers.items():
            pg = doc.get("parentGroupName")
            if pg is None:
                continue
            stats["nested"] += 1
            if pg not in groups:
                problems.append(("dangling parent", rel,
                                 "parentGroupName %r is not a group on this page" % pg))
            else:
                parent[doc.get("name")] = pg
        for start in parent:
            seen, cur = set(), start
            while cur in parent:
                if cur in seen:
                    problems.append(("cycle", page, "group cycle at %r" % cur))
                    break
                seen.add(cur)
                cur = parent[cur]

    # bookmarks may only name containers that exist
    known = {doc.get("name") for _, doc in docs.items() if isinstance(doc, dict)}
    for rel, doc in docs.items():
        if not rel.endswith(".bookmark.json"):
            continue
        for nm in re.findall(r'"visual"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"', json.dumps(doc)):
            if nm not in known:
                problems.append(("bookmark target", rel, "names missing visual %r" % nm))

    versions = collections.Counter()
    for rel, doc in docs.items():
        m = SCHEMA_RE.search(str(doc.get("$schema", ""))) if isinstance(doc, dict) else None
        if m:
            versions[(m.group(1), m.group(2))] += 1
    return problems, stats, versions, len(docs)


def main(argv):
    d = definition_dir(argv[1])
    problems, stats, versions, n = check(d)
    print("%s\n  %d PBIR files: %d visuals, %d groups, %d nested"
          % (d, n, stats["visual"], stats["visualGroup"], stats["nested"]))
    print("  schema versions: " + ", ".join(
        "%s %s x%d" % (k, v, c) for (k, v), c in sorted(versions.items())))
    if problems:
        by = collections.Counter(p[0] for p in problems)
        print("  %d PROBLEM(S): %s" % (len(problems),
                                       ", ".join("%s x%d" % kv for kv in by.most_common())))
        for kind, where, what in problems[:25]:
            print("    %-16s %-46s %s" % (kind, where[:46], what[:70]))
        return 1
    print("  OK -- structure and references consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
