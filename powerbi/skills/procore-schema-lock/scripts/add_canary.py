"""Add / refresh the Schema Audit drift canary in a PBIP semantic model.

Reports every contract column no longer present in its share table. Probes the
pre-rename SOURCE name, so a rename target never masks its source disappearing.
The `derived` allowlist (calibrated empirically, see derived/<project>.json)
suppresses columns the M itself creates, which are never in the share.
"""
import os, re, sys, glob, shutil

ROOT = sys.argv[1]
APPLY = "--apply" in sys.argv
d = glob.glob(os.path.join(ROOT, "*.SemanticModel", "definition"))[0]
proj = os.path.basename(os.path.dirname(os.path.dirname(d)))
ef = os.path.join(d, "expressions.tmdl")
etx = open(ef, encoding="utf-8", newline="").read()
m = re.search(r'DeltaSharing\.Contents\("([^"]+)"', etx)
if not m:
    sys.exit("no DeltaSharing endpoint found")
EP = m.group(1)

# Prefer the model's OWN container expression (one returning the public schema)
# over rebuilding the navigation. Tenants differ: some take the first catalog,
# Butler-Cohen names its share explicitly, so re-deriving the path can land on
# the wrong share entirely.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import data_file, data_dir
from navrefs import container_expressions
_cs = sorted(container_expressions(etx))
CONTAINER = _cs[0] if _cs else None

PREAMBLE = ("    Public = %s," % CONTAINER) if CONTAINER else (
    '''    Source = DeltaSharing.Contents("%s", null),
    CatalogColumn = Source[Name]{0},
    Public = Source{[Name=CatalogColumn]}[Data]{[Name="public"]}[Data],''' % EP)

M = '''let
__PREAMBLE__
    Names = Record.FieldNames(SchemaContract),
    AllShares = List.Distinct(List.Combine(
        List.Transform(Names, each Record.Field(SchemaContract, _)[shares]))),
    // one metadata read per share table, reused across every contract entry
    ColumnMap = Record.FromList(
        List.Transform(AllShares, each try Table.ColumnNames(Public{[Name=_]}[Data]) otherwise null),
        AllShares),
    Rows = List.Combine(List.Transform(Names, (n) =>
        let
            e       = Record.Field(SchemaContract, n),
            derived = if Record.HasFields(e, "derived") then e[derived] else {},
            rens    = if Record.HasFields(e, "renames") then e[renames] else [],
            lists   = List.Transform(e[shares], each Record.Field(ColumnMap, _)),
            // an unreadable share is one explicit row, never "every column missing"
            failed  = List.Contains(lists, null),
            actual  = if failed then {} else List.Combine(lists),
            // probe the ORIGINAL share-side name: a rename target never exists
            // upstream, so checking it would hide its source disappearing
            probes  = List.Transform(List.Difference(e[req] & e[opt], derived), each
                        [ modelCol = _,
                          srcCol   = if Record.HasFields(rens, _) then Record.Field(rens, _) else _ ]),
            // accept either name: a rename TARGET can shadow a real share column
            // (notes <- notes_clean.ExtractedText, where `notes` is also upstream),
            // so requiring only the renamed source would cry drift on a live column
            missing = if List.IsEmpty(e[shares]) then {}
                      else if failed then {[ modelCol = "<share table unreadable>", srcCol = "" ]}
                      else List.Select(probes, each
                             not List.Contains(actual, _[srcCol])
                             and not List.Contains(actual, _[modelCol]))
        in
            List.Transform(missing, each
                {n, Text.Combine(e[shares], ", "), _[modelCol], _[srcCol]}))),
    Result = #table(
        type table [ModelTable = text, ShareTables = text,
                    MissingColumn = text, SourceColumn = text],
        Rows)
in
    Result'''.replace("__PREAMBLE__", PREAMBLE)

src = "\n".join(("\t\t\t\t" + l) if l.strip() else "" for l in M.split("\n"))
COLS = [("ModelTable", "d4f8b213-6c90-4e17-a852-93be0f157cd4"),
        ("ShareTables", "e1c73a56-8d24-4b69-9f30-2ac5d8e04b7a"),
        ("MissingColumn", "f9a2d604-7e51-4c83-b167-08db3f92e5c1"),
        ("SourceColumn", "a8b13e70-5f2c-4d96-b41e-6c07da95f238")]
colblocks = "".join(
    "\tcolumn %s\n\t\tdataType: string\n\t\tlineageTag: %s\n\t\tsummarizeBy: none\n"
    "\t\tsourceColumn: %s\n\n\t\tannotation SummarizationSetBy = Automatic\n\n" % (c, g, c)
    for c, g in COLS)

TMDL = ("table 'Schema Audit'\n\tlineageTag: b7d41f08-2e35-4a90-9c61-5ad0e2f31b47\n\n"
        "\t/// Rows mean Procore removed a column the model still binds. The lock\n"
        "\t/// null-pads it rather than failing refresh, so this is the only thing\n"
        "\t/// that surfaces the loss. Empty = no drift.\n"
        "\tmeasure 'Schema Drift Count' = COUNTROWS('Schema Audit') + 0\n"
        "\t\tformatString: 0\n\t\tlineageTag: c2a6e91d-4b78-4f52-8e03-71fd6a4c8259\n\n"
        + colblocks +
        "\tpartition 'Schema Audit' = m\n\t\tmode: import\n\t\tsource =\n" + src +
        "\n\n\tannotation PBI_ResultType = Table\n").replace("\n", "\r\n")

tpath = os.path.join(d, "tables", "Schema Audit.tmdl")
mpath = os.path.join(d, "model.tmdl")
mtx = open(mpath, encoding="utf-8", newline="").read()
print("  %-18s canary=%-7s container=%s ref=%s" % (proj, "update" if os.path.exists(tpath) else "create", CONTAINER or "-",
      "present" if "ref table 'Schema Audit'" in mtx else "add"))

if APPLY:
    bdir = os.path.join(data_dir("backup"), proj + "_canary")
    os.makedirs(bdir, exist_ok=True)
    if os.path.exists(tpath):
        shutil.copy(tpath, os.path.join(bdir, "Schema Audit.tmdl"))
    shutil.copy(mpath, os.path.join(bdir, "model.tmdl"))
    open(tpath, "w", encoding="utf-8", newline="").write(TMDL)
    if "ref table 'Schema Audit'" not in mtx:
        lines = mtx.split("\r\n")
        last = max(i for i, l in enumerate(lines) if l.startswith("ref table "))
        lines.insert(last + 1, "ref table 'Schema Audit'")
        mtx = "\r\n".join(lines)
        mtx = re.sub(r'(annotation PBI_QueryOrder = \[.*?)\]',
                     lambda mm: mm.group(1) + ',"Schema Audit"]', mtx, count=1)
        open(mpath, "w", encoding="utf-8", newline="").write(mtx)
