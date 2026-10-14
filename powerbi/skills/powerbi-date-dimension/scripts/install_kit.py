"""Install the date dimension and the Time Window calculation group into a PBIP project.

    python install_kit.py "<project>" [--fiscal-start 7] [--week-start sunday]
        [--utc-offset -5] [--as-of 2026-10-01] [--table-only] [--apply]

Dry run by default: it reports what it would do and what stops it. Desktop must
be closed -- it reserialises the model on save and will not load an external
edit until the project is reopened.

What it writes
--------------
    tables/DateDimension.tmdl     new, or replacing a table of that name
    tables/Time Window.tmdl       unless --table-only
    model.tmdl                    `ref table` lines, and `discourageImplicitMeasures`
                                  when the calculation group goes in

Why it refuses rather than replacing blindly
--------------------------------------------
Every report this was written against already had a DateDimension, and
replacing a table is a delete followed by a create. What the delete takes with
it is not visible in the new file:

    measures and calculated columns defined ON the old table
    auto date/time variations, whose hidden tables stay behind in
        relationships.tmdl pointing at columns that no longer carry them
    a column something binds to, when the new table lacks it or retypes it
        (IsWeekend was text and is now true/false; DateKey was text and is now
        a whole number)

Each of those opens as a broken model or, worse, as a working one with a filter
that silently stopped matching. So each is a gate, and a gate names what it
found.

Settings on a table this kit already installed are carried over, because a
reinstall that resets the fiscal year to January is the same class of defect.
The exception is the test date set by --as-of, which is cleared by any install
that does not ask for it.
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
TABLE = "DateDimension"
GROUP = "Time Window"

# Settings the old hand-copied script spelled differently.
LEGACY_KEYS = {"startoffiscalyear": "StartOfFiscalYear", "firstdayofweek": "FirstDayOfWeek"}
DAYS = {"monday": "Day.Monday", "tuesday": "Day.Tuesday", "wednesday": "Day.Wednesday",
        "thursday": "Day.Thursday", "friday": "Day.Friday", "saturday": "Day.Saturday",
        "sunday": "Day.Sunday"}


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return fh.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def unquote(name):
    name = name.strip()
    return name[1:-1].replace("''", "'") if name.startswith("'") and name.endswith("'") else name


# ------------------------------------------------------------ table facts
def table_facts(text):
    """Columns with types, plus what a replace would delete."""
    cols, measures, calculated, hierarchies, variations = {}, [], [], [], 0
    current = None
    for line in text.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^\tcolumn (.+?)(\s*=.*)?$", line)
        if m:
            current = unquote(m.group(1))
            cols[current] = None
            if m.group(2):
                calculated.append(current)
            continue
        m = re.match(r"^\tmeasure (.+?)\s*=", line)
        if m:
            measures.append(unquote(m.group(1)))
            current = None
            continue
        m = re.match(r"^\thierarchy (.+)$", line)
        if m:
            hierarchies.append(unquote(m.group(1)))
            current = None
            continue
        if re.match(r"^\t(partition|annotation)\b", line):
            current = None
        m = re.match(r"^\t\tdataType:\s*(\S+)", line)
        if m and current:
            cols[current] = m.group(1)
        if re.match(r"^\t\tvariation\b", line):
            variations += 1
    return {"cols": cols, "measures": measures, "calculated": calculated,
            "hierarchies": hierarchies, "variations": variations,
            "calc_group": bool(re.search(r"(?m)^\tcalculationGroup\b", text))}


def settings(text):
    """{name: value text} from the Configuration block of a kit table, or the legacy script's let."""
    found = {}
    body = text.replace("\r\n", "\n")
    start = body.find("// ---- Configuration")
    end = body.find("// ---- Anchors")
    block = body[start:end] if start >= 0 and end > start else None
    if block is None:                                   # legacy: settings are the first bindings
        m = re.search(r"(?m)^\s*let\s*$", body)
        block = "\n".join(body[m.end():].split("\n")[:8]) if m else ""
    for line in block.split("\n"):
        m = re.match(r"^\s*(\w+)\s*=\s*(.+?),\s*(?://.*)?$", line)
        if m:
            found[m.group(1)] = m.group(2).strip()
    return found, start >= 0


def apply_settings(text, values):
    for key, value in values.items():
        pat = re.compile(r"(?m)^(\s*%s\s*=\s*)(.+?)(,\s*(?://.*)?)$" % re.escape(key))
        if not pat.search(text):
            raise SystemExit("setting %s is not in the kit's query" % key)
        text = pat.sub(lambda m: m.group(1) + value + m.group(3), text, count=1)
    return text


# ------------------------------------------------------------- references
def model_references(definition, skip):
    """{column: [where]} for every reference to the table outside its own file."""
    refs = {}
    dax = re.compile(r"'?%s'?\[([^\]]+)\]" % re.escape(TABLE))
    rel = re.compile(r"(?m)^\s*(?:from|to)Column:\s*'?%s'?\.(.+?)\s*$" % re.escape(TABLE))
    for path in glob.glob(os.path.join(definition, "**", "*.tmdl"), recursive=True):
        if os.path.abspath(path) == os.path.abspath(skip) or os.sep + "cultures" + os.sep in path:
            continue
        text = read(path)
        where = os.path.relpath(path, definition)
        for m in dax.finditer(text):
            refs.setdefault(m.group(1), set()).add(where)
        for m in rel.finditer(text):
            refs.setdefault(unquote(m.group(1)), set()).add(where)
    return refs


def report_references(project):
    """References from PBIR, resolved through each file's own aliases.

    A filter names its table once in `From` and refers to it by alias after
    that, so matching on "Entity" alone misses every filter.
    """
    refs, implicit = {}, []
    roots = glob.glob(os.path.join(project, "*.Report"))
    for root in roots:
        legacy = os.path.join(root, "report.json")
        if os.path.exists(legacy):
            raise SystemExit("%s uses the legacy report format. Save it as PBIR first: references "
                             "inside a legacy report are strings inside strings and cannot be "
                             "resolved reliably." % os.path.basename(root))
        for path in glob.glob(os.path.join(root, "definition", "**", "*.json"), recursive=True):
            try:
                doc = json.loads(read(path))
            except ValueError:
                continue
            where = os.path.relpath(path, project)
            aliases = {}

            def collect(node):
                if isinstance(node, dict):
                    if isinstance(node.get("Name"), str) and isinstance(node.get("Entity"), str):
                        aliases[node["Name"]] = node["Entity"]
                    for v in node.values():
                        collect(v)
                elif isinstance(node, list):
                    for v in node:
                        collect(v)

            def entity_of(expr):
                ref = (expr or {}).get("SourceRef") or {}
                return ref.get("Entity") or aliases.get(ref.get("Source"))

            def walk(node):
                if isinstance(node, dict):
                    for kind in ("Column", "Measure"):
                        f = node.get(kind)
                        if isinstance(f, dict) and "Property" in f and entity_of(f.get("Expression")) == TABLE:
                            refs.setdefault(f["Property"], set()).add(where)
                    h = node.get("Hierarchy")
                    if isinstance(h, dict) and "Hierarchy" in h and entity_of(h.get("Expression")) == TABLE:
                        refs.setdefault("hierarchy:" + h["Hierarchy"], set()).add(where)
                    agg = node.get("Aggregation")
                    if isinstance(agg, dict) and isinstance((agg.get("Expression") or {}).get("Column"), dict):
                        implicit.append(where)
                    for v in node.values():
                        walk(v)
                elif isinstance(node, list):
                    for v in node:
                        walk(v)

            collect(doc)
            walk(doc)
    return refs, sorted(set(implicit))


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project")
    ap.add_argument("--fiscal-start", type=int, choices=range(1, 13), metavar="1-12")
    ap.add_argument("--week-start", choices=sorted(DAYS))
    ap.add_argument("--utc-offset", type=int, metavar="HOURS")
    ap.add_argument("--as-of", metavar="YYYY-MM-DD",
                    help="TESTING ONLY: pin the model's \"today\". Never carried over; omit it to clear it.")
    ap.add_argument("--table-only", action="store_true", help="leave the calculation group out")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    hits = glob.glob(os.path.join(a.project, "*.SemanticModel", "definition"))
    if len(hits) != 1 or not os.path.isdir(os.path.join(hits[0], "tables")):
        if glob.glob(os.path.join(a.project, "*.SemanticModel", "model.bim")):
            sys.exit("model.bim format. Save the project as TMDL first.")
        sys.exit("expected one *.SemanticModel/definition/tables under %s" % a.project)
    definition = hits[0]
    model_path = os.path.join(definition, "model.tmdl")
    model = read(model_path)
    eol = "\r\n" if "\r\n" in model else "\n"

    new_table = read(os.path.join(ASSETS, TABLE + ".tmdl"))
    new_group = read(os.path.join(ASSETS, GROUP + ".tmdl"))
    new = table_facts(new_table)

    stops, notes = [], []
    carried = {}

    # ---- the table already there
    old_path = os.path.join(definition, "tables", TABLE + ".tmdl")
    if os.path.exists(old_path):
        old_text = read(old_path)
        old = table_facts(old_text)
        old_settings, is_kit = settings(old_text)
        notes.append("replaces the existing %s (%d columns, %s)"
                     % (TABLE, len(old["cols"]), "installed by this kit" if is_kit else "not from this kit"))

        if old["measures"]:
            stops.append("the existing table holds measures, which a replace deletes: %s. "
                         "Move them to another table first." % ", ".join(old["measures"]))
        if old["calculated"]:
            stops.append("the existing table holds calculated columns, which a replace deletes: %s"
                         % ", ".join(old["calculated"]))
        if old["variations"]:
            stops.append("%d columns of the existing table carry auto date/time variations. Turn off "
                         "auto date/time in Desktop (Options > Current file > Data Load), save, close, "
                         "and run this again." % old["variations"])

        refs = model_references(definition, old_path)
        rrefs, implicit = report_references(a.project)
        for k, v in rrefs.items():
            refs.setdefault(k, set()).update(v)

        # Names are case-insensitive to the engine: FirstDayOfYear and
        # FirstDayofYear are one column, and both spellings are in circulation.
        new_ci = {k.lower(): v for k, v in new["cols"].items()}
        old_ci = {k.lower(): v for k, v in old["cols"].items()}
        old_measures = {m.lower() for m in old["measures"]}
        new_hier = {h.lower() for h in new["hierarchies"]}
        for name, where in sorted(refs.items()):
            shown = ", ".join(sorted(where)[:3]) + (" ..." if len(where) > 3 else "")
            key = name.lower()
            if key.startswith("hierarchy:"):
                if key[10:] not in new_hier:
                    stops.append("hierarchy '%s' is used and the kit has none of that name (%s)"
                                 % (name[10:], shown))
            elif key in old_measures:
                continue                                   # already reported above
            elif key not in new_ci:
                stops.append("column '%s' is used and the kit does not have it (%s)" % (name, shown))
            elif old_ci.get(key) and old_ci[key] != new_ci[key]:
                stops.append("column '%s' is used and changes type, %s to %s (%s)"
                             % (name, old_ci[key], new_ci[key], shown))
        notes.append("%d of its columns are referenced elsewhere: %s"
                     % (len([r for r in refs if not r.startswith("hierarchy:")]),
                        ", ".join(sorted(r for r in refs if not r.startswith("hierarchy:"))) or "-"))

        for key, value in old_settings.items():
            canonical = key if is_kit else LEGACY_KEYS.get(key.lower())
            if canonical:
                carried[canonical] = value
    else:
        _, implicit = report_references(a.project)
        if re.search(r"__PBI_TimeIntelligenceEnabled\s*=\s*1", model):
            notes.append("auto date/time is ON, so Desktop will add hidden tables for the kit's date "
                         "columns. Before turning it off, commit, and search the report for "
                         "PropertyVariationSource: Desktop flattens any axis built on a built-in "
                         "date hierarchy. See SKILL.md.")

    # ---- the calculation group
    group_path = os.path.join(definition, "tables", GROUP + ".tmdl")
    if not a.table_only:
        if os.path.exists(group_path):
            if not table_facts(read(group_path))["calc_group"]:
                stops.append("a table named '%s' exists and is not a calculation group" % GROUP)
            else:
                notes.append("replaces the existing '%s' calculation group" % GROUP)
        if implicit:
            notes.append("%d report files aggregate a column directly. Those visuals keep working, "
                         "but no calculation item reaches them: a calculation group changes measures "
                         "only. First: %s" % (len(implicit), implicit[0]))
        if not re.search(r"(?m)^\tdiscourageImplicitMeasures\b", model):
            notes.append("turns on discourageImplicitMeasures, which the engine requires before it "
                         "will create a calculation group. Columns can no longer be dropped onto a "
                         "visual as values; existing ones are unaffected.")

    # ---- settings
    # A pinned date is the one setting that must not survive a reinstall: it is
    # a test fixture, and a model published with it shows the same day forever.
    pinned = carried.pop("AsOfDate", "null")
    if pinned != "null" and not a.as_of:
        notes.append("the existing table was pinned to AsOfDate = %s. Cleared: the model follows the real date again." % pinned)
    if a.as_of:
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", a.as_of)
        if not m:
            sys.exit("--as-of takes YYYY-MM-DD")
        carried["AsOfDate"] = "#date(%d, %d, %d)" % tuple(int(g) for g in m.groups())
        notes.append("PINNED to %s for testing. Every window and offset is computed as of that day. "
                     "Re-run without --as-of before this model is published." % a.as_of)
    if a.fiscal_start is not None:
        carried["StartOfFiscalYear"] = str(a.fiscal_start)
    if a.week_start:
        carried["FirstDayOfWeek"] = DAYS[a.week_start]
    if a.utc_offset is not None:
        carried["UtcOffsetHours"] = str(a.utc_offset)
    default_settings, _ = settings(new_table)
    changed = {k: v for k, v in carried.items() if k in default_settings and default_settings[k] != v}
    unknown = [k for k in carried if k not in default_settings]
    if unknown:
        notes.append("settings on the existing table the kit no longer has, dropped: %s" % ", ".join(unknown))
    new_table = apply_settings(new_table, changed)
    notes.append("settings: " + (", ".join("%s = %s" % kv for kv in sorted(changed.items())) or "kit defaults"))

    # ---- model.tmdl
    edited = model
    if not a.table_only and not re.search(r"(?m)^\tdiscourageImplicitMeasures\b", edited):
        edited = re.sub(r"(?m)^(model [^\r\n]*)(\r?\n)", lambda m: m.group(1) + m.group(2)
                        + "\tdiscourageImplicitMeasures" + m.group(2), edited, count=1)
    wanted = [TABLE] + ([] if a.table_only else [GROUP])
    for name in wanted:
        quoted = name if re.fullmatch(r"\w+", name) else "'%s'" % name
        if not re.search(r"(?m)^ref table %s[ \t]*\r?$" % re.escape(quoted), edited):
            last = None
            # [^\r\n]* and not .* -- with CRLF, `.` swallows the \r and the
            # insert lands between \r and \n, leaving a line ending of \r\r\n
            for m in re.finditer(r"(?m)^ref table [^\r\n]*", edited):
                last = m
            line = "ref table " + quoted
            if last:
                edited = edited[:last.end()] + eol + line + edited[last.end():]
            else:
                edited = edited.rstrip("\r\n") + eol + eol + line + eol

    # ---- report
    print(os.path.relpath(definition, a.project))
    for n in notes:
        print("  " + n)
    if stops:
        print("\nSTOPPED, %d reason%s:" % (len(stops), "" if len(stops) == 1 else "s"))
        for s in stops:
            print("  - " + s)
        sys.exit(1)
    if not a.apply:
        print("\ndry run. Nothing written. Re-run with --apply, Desktop closed.")
        return
    write(old_path, new_table)
    if not a.table_only:
        write(group_path, new_group)
    if edited != model:
        write(model_path, edited)
    print("\nwritten. Now compile: python ../powerbi-desktop-engine/scripts/compilecheck.py \"%s\"" % a.project)


if __name__ == "__main__":
    main()
