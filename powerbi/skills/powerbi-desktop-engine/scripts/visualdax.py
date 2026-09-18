"""Emit the DAX a PBIR visual's data is, without opening Desktop.

    python visualdax.py "<project>" --page <pageId> --visual <visualId>

Why this exists
---------------
A visual's content is a DAX query, so a report edit can be checked by comparing
queries rather than by looking at two renders. Capturing them from Desktop's
Performance Analyzer (`paquery.py`) works but costs a human clicking once per
visual per interaction, which does not scale to validating a component library.

This derives the query from the PBIR instead. Nothing is clicked and nothing is
open.

It does NOT reproduce Desktop's query text, and should not try. Desktop wraps
the real question in row-window TOPNs, a SUBSTITUTEWITHINDEX column axis and
ROLLUPADDISSUBTOTAL subtotal markers -- presentation machinery that changes with
the visual's size and scroll position. The question underneath is
SUMMARIZECOLUMNS over the active groupings with the filters applied, and that is
what a component's correctness rests on.

So the claim being checked is "the same numbers", not "the same statement".
Calibrate that once per component type against a Performance Analyzer capture;
after that this runs headless against every instance.

Scope
-----
Grouping visuals -- matrix (`pivotTable`), table (`tableEx`), and the cartesian
charts, which all express as groupings plus measures. A card is the degenerate
case with no grouping.

Filters are collected from all three scopes, because a visual's numbers depend
on all three and a generator reading only the visual's own `filterConfig` will
quietly return different totals:

    report.json  ->  page.json  ->  visual.json

Only cards carrying a `filter` are emitted. A card without one is an empty
filter card -- real in a bookmark, where it means "this filter is cleared", but
no restriction on the query.
"""
import os
import sys
import json
import glob
import argparse


def definition_dir(project):
    if os.path.isdir(os.path.join(project, "pages")):
        return project
    hits = glob.glob(os.path.join(project, "*.Report", "definition"))
    if not hits:
        sys.exit("no PBIR definition under %s" % project)
    return hits[0]


def load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def ref(field):
    """A PBIR field expression as a DAX reference."""
    for kind in ("Column", "Measure", "HierarchyLevel"):
        if kind in field:
            node = field[kind]
            src = node.get("Expression", {}).get("SourceRef", {})
            entity = src.get("Entity")
            prop = node.get("Property")
            if entity and prop:
                return "'%s'[%s]" % (entity, prop)
            if prop:
                return "[%s]" % prop
    if "Aggregation" in field:
        return ref(field["Aggregation"]["Expression"])
    raise ValueError("unrecognised field: %s" % json.dumps(field)[:200])


def alias(field, used):
    base = ref(field).split("[")[-1].rstrip("]").replace(" ", "_")
    name, n = base, 1
    while name in used:
        n += 1
        name = "%s_%d" % (base, n)
    used.add(name)
    return name


def literal(node):
    """A filter Values entry as a DAX literal.

    PBIR quotes strings the way M and the query layer do -- 'Evaluation - Vendor'
    -- but DAX reads single quotes as a TABLE name, so passing the value through
    unchanged produces a query that either errors or, worse, resolves against
    something else. Booleans arrive lowercase and DAX wants TRUE/FALSE.
    """
    if "Literal" not in node:
        raise ValueError("unsupported filter value: %s" % json.dumps(node)[:120])
    value = node["Literal"]["Value"]
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return '"%s"' % value[1:-1].replace("'", "''").replace('"', '""')
    if value.lower() in ("true", "false"):
        return value.upper()
    return value                                  # numeric, or already typed


def treatas(card):
    """A Categorical filter card as TREATAS, or None when not expressible."""
    where = card.get("filter", {}).get("Where", [])
    if len(where) != 1:
        return None
    cond = where[0].get("Condition", {})
    inn = cond.get("In")
    if not inn or len(inn.get("Expressions", [])) != 1:
        return None
    try:
        values = [literal(v[0]) for v in inn["Values"] if len(v) == 1]
    except ValueError:
        return None
    if not values:
        return None
    return "TREATAS({%s}, %s)" % (", ".join(values), ref(card["field"]))


def filters(d, page, visual):
    """Selections from report, page and visual scope, outermost first."""
    out, skipped = [], []
    scopes = [("report", load(os.path.join(d, "report.json"))),
              ("page", load(os.path.join(d, "pages", page, "page.json"))),
              ("visual", visual)]
    for scope, obj in scopes:
        for card in (obj.get("filterConfig") or {}).get("filters", []):
            if "filter" not in card:
                continue                          # empty card: no restriction
            expr = treatas(card)
            if expr:
                out.append(expr)
            else:
                skipped.append("%s/%s (%s)" % (scope, card["name"], card["type"]))
    return out, skipped


def query(d, page, vid):
    visual = load(os.path.join(d, "pages", page, "visuals", vid, "visual.json"))
    state = visual["visual"].get("query", {}).get("queryState", {})

    groups, measures, used = [], [], set()
    for role in ("Rows", "Columns", "Category", "Series", "Y", "X"):
        for p in state.get(role, {}).get("projections", []):
            # `active: false` is a level the visual has drilled PAST -- it is
            # not part of the question the visual is currently asking
            if p.get("active", True):
                r = ref(p["field"])
                if r not in groups and "Measure" not in p["field"]:
                    groups.append(r)
    for role in ("Values", "Y", "Size", "Tooltips"):
        for p in state.get(role, {}).get("projections", []):
            if "Measure" in p["field"] or "Aggregation" in p["field"]:
                measures.append(('"%s"' % alias(p["field"], used), ref(p["field"])))

    where, skipped = filters(d, page, visual)
    parts = groups + where + ["%s, %s" % m for m in measures]
    dax = "EVALUATE\nSUMMARIZECOLUMNS(\n    " + ",\n    ".join(parts) + "\n)"
    return dax, skipped, groups, measures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--page", required=True)
    ap.add_argument("--visual", required=True)
    a = ap.parse_args()

    d = definition_dir(a.project)
    dax, skipped, groups, measures = query(d, a.page, a.visual)
    if skipped:
        # silence here would mean returning numbers filtered differently from
        # the report, which is the one failure this tool must never hide
        sys.stderr.write("UNEXPRESSED FILTERS -- results will not match the "
                         "report:\n  %s\n" % "\n  ".join(skipped))
    print(dax)
    return 2 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
