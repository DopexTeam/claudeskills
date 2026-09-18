"""Which model columns are REQUIRED -- ones the report actually consumes.

Two authoritative inputs, no inference:

  report side  PBIR JSON -- every visual / filter / slicer / bookmark binding
  model side   INFO.CALCDEPENDENCY() -- the engine's own dependency graph,
               captured from a live instance after a successful refresh

Required = transitive closure of (report bindings -> calc dependencies), plus
relationship key columns, which break the model rather than one visual.
Everything else a table binds is OPTIONAL and may be null-padded silently.

The split must err toward REQUIRED. A false "required" costs a refresh failure
on a column nobody watches; a false "optional" corrupts numbers in silence.

Two traps, both hit while building this:
  * the report and the dependency graph speak model column NAMES, while the
    schema contract speaks sourceColumn -- translate, or every renamed column
    looks unused;
  * the dependency graph only contains objects something else DEPENDS ON, so a
    plain column dropped straight onto a visual is absent from it entirely.
    Classification comes from the model inventory, never from the graph.
"""
import os
import re
import csv
import glob
import json
import collections

BLOCK = re.compile(r"(?m)^(?=\t(?:column|measure|partition|hierarchy|annotation)\b)")


def _alias_map(node, inherited):
    """Alias -> Entity for this query scope.

    PBIR declares sources once per query and refers to them by alias:
        "From": [{"Name": "p", "Entity": "Project", "Type": 0}]
        {"SourceRef": {"Source": "p"}, "Property": "Project Active?"}
    Aliases are scoped to the query that declares them, so the map is inherited
    down the subtree and overridden where a nested From appears.
    """
    out = dict(inherited)
    frm = node.get("From")
    if isinstance(frm, list):
        for f in frm:
            if isinstance(f, dict) and f.get("Name") and f.get("Entity"):
                out[f["Name"]] = f["Entity"]
    return out


def _walk_refs(node, aliases, out):
    if isinstance(node, dict):
        aliases = _alias_map(node, aliases)
        # a binding: something carrying Property alongside a SourceRef
        prop = node.get("Property")
        if isinstance(prop, str):
            expr = node.get("Expression")
            ref = expr.get("SourceRef") if isinstance(expr, dict) else None
            if isinstance(ref, dict):
                ent = ref.get("Entity") or aliases.get(ref.get("Source"))
                if ent:
                    out.add((ent, prop))
        # hierarchy level: a different shape entirely -- Hierarchy + Level rather
        # than Property. Monthly Review has 32 of these; matching only Property
        # leaves every one of them, and the columns beneath, unreachable.
        lvl = node.get("Level")
        expr = node.get("Expression")
        hier = expr.get("Hierarchy") if isinstance(expr, dict) else None
        if isinstance(lvl, str) and isinstance(hier, dict):
            hexpr = hier.get("Expression")
            href = hexpr.get("SourceRef") if isinstance(hexpr, dict) else None
            if isinstance(href, dict):
                ent = href.get("Entity") or aliases.get(href.get("Source"))
                if ent:
                    out.add((ent, lvl))                      # the level column
                    if isinstance(hier.get("Hierarchy"), str):
                        out.add((ent, hier["Hierarchy"]))    # and the hierarchy
        for v in node.values():
            _walk_refs(v, aliases, out)
    elif isinstance(node, list):
        for v in node:
            _walk_refs(v, aliases, out)


def report_refs(report_def_dir):
    """(entity, property) pairs bound anywhere in the report definition.

    Parses the JSON and resolves query aliases. A regex over "Entity"/"Property"
    pairs silently misses every alias-only binding -- on BC that was ten of them,
    including cost_code name and Project Active?. A binding reachable ONLY that
    way would be classified optional and null-pad in silence.
    """
    out = set()
    for dp, _, fs in os.walk(report_def_dir):
        for f in fs:
            if not f.endswith(".json"):
                continue
            try:
                doc = json.load(open(os.path.join(dp, f), encoding="utf-8-sig"))
            except Exception:
                continue
            _walk_refs(doc, {}, out)
    return out


# Reference types that name a model object precise enough to depend on.
#
# ATTRIBUTE_HIERARCHY is how a hierarchy's levels are recorded: `Date Hierarchy`
# -> Year, Quarter, MonthName, Day, Date. Without it a hierarchy binding reaches
# nothing, so every level the report does not happen to name individually is
# classified optional and null-pads in silence.
#
# TABLE is deliberately excluded. `COUNTROWS(Commitment)` depends on the table,
# not on each of its columns, and following it would mark the whole model
# required -- turning every Procore change anywhere into a refresh failure.
# M_EXPRESSION is excluded because the query side already traces navigation.
# CALC_TABLE is included because field parameters NEST: Company Review's
# `Buyout Metric Options` is a field parameter whose NAMEOF list points at other
# field parameters (`Buyout Complete`, `Buyout Incomplete`), not at measures
# directly. Without this the chain breaks at the first hop and every measure
# under the nested parameters is unreachable. A calculated table's expression
# genuinely has to evaluate for the table to exist, so following it is correct,
# not merely cautious -- unlike TABLE, which names a whole physical table.
REF_TYPES = ("COLUMN", "CALC_COLUMN", "MEASURE", "CALC_TABLE",
             "ATTRIBUTE_HIERARCHY", "HIERARCHY", "CALCULATION_ITEM")

# Objects that are their own leaves: nothing in the report binds them, but if a
# column they name disappears the model breaks rather than one visual.
#
#   *RELATIONSHIP  a broken key breaks every join through it
#   ROWS_ALLOWED   row-level security. Company Review filters ProjectUser on
#                  email_address, which no visual binds -- so without this the
#                  column is optional, null-pads, and the RLS predicate quietly
#                  stops matching. That is a security failure that shows up as
#                  a successful refresh.
LEAF_OBJ_TYPES = ("RELATIONSHIP", "ROWS_ALLOWED")


def calc_dependency(csv_path):
    """edges[(table, object)] -> {(refTable, refObject)}, plus object kinds."""
    edges = collections.defaultdict(set)
    kinds = {}
    for r in csv.DictReader(open(csv_path, encoding="utf-8-sig")):
        col = lambda k: r[[c for c in r if c.endswith("[%s]" % k)][0]]
        obj = (col("table"), col("obj"))
        kinds[obj] = col("objType")
        if col("refType") in REF_TYPES:
            edges[obj].add((col("refTable"), col("refObj")))
    return edges, kinds


def model_inventory(model_def_dir):
    """Per table: {column name -> sourceColumn}, calc columns, measures, sortByColumn.

    sortByColumn matters: a column used only as a sort key is reachable from
    nothing else, so without it the key lands in `optional`, null-pads, and the
    axis ordering breaks silently. The First Finish models carry ~30 each.
    """
    src, calc, meas, sort_by = {}, {}, {}, {}
    for f in sorted(glob.glob(os.path.join(model_def_dir, "tables", "*.tmdl"))):
        txt = open(f, encoding="utf-8", errors="replace", newline="").read()
        tm = re.search(r"(?m)^table\s+(?:'([^']+)'|(\S+))", txt)
        t = (tm.group(1) or tm.group(2)) if tm else os.path.basename(f)[:-5]
        src.setdefault(t, {})
        calc.setdefault(t, set())
        meas.setdefault(t, set())
        sort_by.setdefault(t, {})
        for b in BLOCK.split(txt):
            mm = re.match(r"\tmeasure\s+(?:'([^']+)'|(\S+))", b)
            cm = re.match(r"\tcolumn\s+(?:'([^']+)'|(\S+))", b)
            if mm:
                meas[t].add(mm.group(1) or mm.group(2))
            elif cm:
                nm = cm.group(1) or cm.group(2)
                is_calc = (bool(re.match(r"\tcolumn\s+(?:'[^']+'|\S+)\s*=", b))
                           or "\n\t\texpression" in b)
                sc = re.search(r"\n\t\tsourceColumn:\s*(.+)", b)
                if not is_calc and sc and not sc.group(1).strip().startswith("["):
                    src[t][nm] = sc.group(1).strip()
                else:
                    calc[t].add(nm)
                sb = re.search(r"(?m)^		sortByColumn:\s*(.+)$", b)
                if sb:
                    sort_by.setdefault(t, {})[nm] = sb.group(1).strip().strip("'")
    return src, calc, meas, sort_by


def required_columns(report_def_dir, calcdep_csv, model_def_dir):
    """Return ({table: {sourceColumn}}, visited nodes)."""
    edges, kinds = calc_dependency(calcdep_csv)
    src, _calc, _meas, _sb = model_inventory(model_def_dir)

    seeds = set(report_refs(report_def_dir))
    for obj, deps in edges.items():
        if kinds.get(obj, "").endswith(LEAF_OBJ_TYPES):
            seeds |= deps

    seen = set()
    stack = list(seeds)
    out = collections.defaultdict(set)
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        t, o = node
        if o in src.get(t, {}):
            out[t].add(src[t][o])
        for d in edges.get(node, ()):
            stack.append(d)
    return dict(out), seen
