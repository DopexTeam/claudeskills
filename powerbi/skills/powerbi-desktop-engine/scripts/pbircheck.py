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

`--schema` is ADVISORY and never changes the exit code. Power BI Desktop
embeds JSON Schemas for these documents and `pbirschemas.py` extracts them, but
measurement says they are not the contract Desktop enforces on what it writes:
2385 of 2412 files in five hand-authored reports fail against them, in 17
classes. The big ones are a `$schema` const pinned to one version while real
files span five, `filter.Version` pinned to 2 while files carry 1, and
properties Desktop emits that the schema does not declare (`width`,
`showSetAlertButton`, `showFollowVisualButton`) under
`additionalProperties: false`.

A gate that fires on known-good input is worse than no gate, so this does not
gate. It is useful for the opposite direction -- as a REFERENCE when generating
PBIR, telling you which properties and enum values exist -- and as a way to see
where a document departs from the shipped schema. The structural checks above
are the part that gates.
"""
import os
import re
import sys
import json
import glob
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbirschemas
import jsonschema_min

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


KIND_OF_FILE = [
    (re.compile(r"visuals/[^/]+/visual\.json$"), "visualcontainer"),
    (re.compile(r"visuals/[^/]+/mobileState\.json$"), "visualcontainermobilestate"),
    (re.compile(r"pages/[^/]+/page\.json$"), "page"),
    (re.compile(r"pages/pages\.json$"), "pagesmetadata"),
    (re.compile(r"bookmarks/.*\.bookmark\.json$"), "bookmark"),
    (re.compile(r"bookmarks/bookmarks\.json$"), "bookmarkmetadata"),
    (re.compile(r"^report\.json$"), "report"),
    (re.compile(r"^reportExtension\.json$"), "reportextension"),
    (re.compile(r"^version\.json$"), "versionmetadata"),
]


def schema_check(d):
    """Validate every file against the schema Desktop itself enforces."""
    if not pbirschemas.available():
        return None, "no schemas cached -- run: python pbirschemas.py --extract"
    reg = pbirschemas.load_all()
    docs, _ = load(d)
    problems, checked = [], collections.Counter()
    for rel, doc in sorted(docs.items()):
        kind = next((k for rx, k in KIND_OF_FILE if rx.search(rel)), None)
        if kind is None or kind not in reg:
            checked["unmapped"] += 1
            continue
        errs = jsonschema_min.validate(doc, reg[kind], registry=reg)
        checked[kind] += 1
        for where, what in errs[:4]:
            problems.append(("schema:" + kind, rel, "%s %s" % (where, what)))
    return (problems, checked), None


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

    want_schema = "--schema" in argv
    snapshot = None
    for i, a in enumerate(argv):
        if a == "--schema-baseline" and i + 1 < len(argv):
            snapshot, want_schema = argv[i + 1], True

    if want_schema:
        res, err = schema_check(d)
        if err:
            print("  SCHEMA: %s" % err)
            return 1
        sproblems, checked = res

        if snapshot:
            # The shipped schemas over-report on hand-authored reports, so the
            # absolute count is noise. The DELTA is not: an error an edit
            # introduces is one Desktop rejects on open, near word for word.
            # Putting `sortDefinition` on `visual` instead of on `visual.query`
            # gave "$.visual unexpected property 'sortDefinition'" here, and
            # "An additional property 'sortDefinition' was included in the
            # /visual property" from Desktop, which refused to open the report.
            # Key on the error CLASS, not on the file. Keying per file means
            # every NEW file trips the gate carrying only the deviations that
            # every existing file already has -- a gate that cries wolf on
            # ordinary work gets switched off, which is worse than no gate.
            # Array indices vary between files, so they normalise out too.
            def klass(p):
                kind, _where, what = p
                return "%s|%s" % (kind, re.sub(r"\[\d+\]", "[*]", what))

            now_classes = sorted({klass(p) for p in sproblems})
            now_full = sorted("%s|%s|%s" % p for p in sproblems)
            if os.path.exists(snapshot):
                saved = json.load(open(snapshot, encoding="utf-8"))
                was_classes = set(saved.get("classes", saved if isinstance(saved, list) else []))
                was_full = set(saved.get("entries", []))
                new_classes = [c for c in now_classes if c not in was_classes]
                if new_classes:
                    print("  SCHEMA REGRESSION: %d NEW error class(es)" % len(new_classes))
                    for c in new_classes[:15]:
                        kind, what = c.split("|", 1)
                        example = next((p[1] for p in sproblems if klass(p) == c), "")
                        print("    %-18s %-46s  e.g. %s" % (kind[:18], what[:46], example[:40]))
                    return 1
                spread = [p for p in now_full if p not in was_full]
                print("  no new schema error classes against %s%s"
                      % (os.path.basename(snapshot),
                         "  (%d known-class instance(s) on new/changed files)"
                         % len(spread) if spread else ""))
            else:
                with open(snapshot, "w", encoding="utf-8") as fh:
                    json.dump({"classes": now_classes, "entries": now_full}, fh, indent=1)
                print("  recorded %d deviation(s) in %d class(es) -> %s"
                      % (len(now_full), len(now_classes), snapshot))
                print("  re-run after an edit; only NEW errors fail.")
            return 0

        print("  schema-checked %d files (%s)"
              % (sum(v for k, v in checked.items() if k != "unmapped"),
                 ", ".join("%s x%d" % kv for kv in sorted(checked.items()) if kv[0] != "unmapped")))
        if checked["unmapped"]:
            print("    %d file(s) had no governing schema and were skipped" % checked["unmapped"])
        if sproblems:
            by = collections.Counter((k, w.split(" ", 1)[-1][:52]) for k, _, w in sproblems)
            print("  ADVISORY: %d deviation(s) from the shipped schemas, %d class(es)."
                  % (len(sproblems), len(by)))
            print("  These do NOT fail the check -- the shipped schemas reject"
                  " hand-authored reports too.")
            for (kind, what), n in by.most_common(10):
                print("    %-22s %-52s x%d" % (kind[:22], what, n))
        else:
            print("  no deviation from the shipped schemas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
