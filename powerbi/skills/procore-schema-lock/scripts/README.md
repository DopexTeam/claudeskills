# Procore Delta Share schema lock

Guards Power BI reports against Procore changing the shared schema underneath
them, and reports it when it happens.

## The problem

Procore adds and removes columns in its Analytics 2.0 Delta Sharing tables
without notice. The canned query is a bare navigation with no column
projection, so the rowset shape is whatever Procore ships that day.

Desktop re-detects the schema on refresh and silently reconciles. **The Service
does not** — it binds the published column list to the rowset by name and
hard-fails on the first missing one:

> The 'percentage_paid_company_currency' column does not exist in the rowset.

So the failure only ever appears in the Service, on Procore's release cadence,
and is unreproducible locally because the local copy self-heals every refresh.

## The fix

Columns split into **req** (the report consumes them -> assert, fail loudly and
name them) and **opt** (bound but unreferenced -> null-pad, silent, never
fails). The split is reachability over one dependency graph: leaves are report
bindings, roots are Procore share columns.

Optional columns stay in the model as nulls rather than being pruned, so a
report author still has them to build against while their absence can never
break a refresh.

Two generated expressions plus one line per partition.

```
LockSchema = (tbl as table, req as list, opt as list) as table =>
    let actual  = Table.ColumnNames(tbl),
        missing = List.Difference(req, actual)
    in  if List.IsEmpty(missing)
        then Table.SelectColumns(tbl, List.Distinct(req & opt & actual), MissingField.UseNull)
        else error "Procore removed column(s) this report depends on: " & Text.Combine(List.Sort(missing), ", ")
```

```
#"Schema Locked" = LockSchema(<last step>, SchemaContract[#"<table>"][req], SchemaContract[#"<table>"][opt])
```

Do **not** name these parameters `required`/`optional`: `optional` is a reserved
word in M and the model will not open.

Plus `MissingField.Ignore` on every rename and `MissingField.UseNull` on every
intermediate `SelectColumns`.

**The union is the point.** `List.Distinct(contract & Table.ColumnNames(tbl))`
rather than a plain projection, so columns the source *adds* still flow through.
A projection would have frozen out Budget's dynamically expanded custom budget
view columns — and, observed in practice, three columns Procore added within
twelve days of the first rollout.

The lock converts a loud failure into a silent one, so it is only half a fix.
`Schema Audit` is the other half: it reads the live column list for each share
table and reports every contract column that has gone missing.

## Usage

```
# 1. capture the engine's dependency graph from a LIVE, refreshed instance
#    (DAX: INFO.CALCDEPENDENCY) -> calcdep/<project>.csv
# 2. derive what the report actually consumes
python emit_required.py "<project folder>" calcdep/<project>.csv
# 3. apply
python apply_lock.py    "<project folder>" --apply [--only=TableA,TableB]
python add_canary.py    "<project folder>" --apply
# 4. GATE -- compile with Power BI's own engine before anything is opened
python compilecheck.py  "<project folder>/<name>.SemanticModel/definition"
python lintdir.py       "<project folder>/<name>.SemanticModel/definition"
```

`compilecheck.py` is not optional. It exits non-zero and is the only check that
knows M's grammar.

Desktop **must** be closed. Check the files are writable — a windowless
`PBIDesktop` process lingers after close and the process list lies.

Calibrating the canary: apply, refresh, read `Schema Audit`, write the flagged
(table, column) pairs to `derived/<project>.json`, re-apply, refresh. It should
then read zero. On a cleanly refreshing model every flagged column is by
definition M-created, so this converges rather than guessing.

## Rules that cost something to learn

- The step separator goes on the last line carrying **code**, not the last
  line. A trailing `// comment` swallows the comma and fuses two let-bindings
  into invalid M. This broke a production report.
- Anchor the lock on the last **zero-indent** `in`; a nested `let … in` inside
  `Table.AddColumn` otherwise captures it.
- Paren scanning must skip comments — `// 1) parse HTML` carries an unmatched
  `)`.
- Structural columns (filter predicates, split/merge inputs) stay **ahead** of
  the lock so their loss still fails loudly.
- Never lock the canary; it reads `SchemaContract`, so locking it is circular.
- Keep rename targets **monitored at their source name**. Allowlisting them
  blinds the canary to exactly what it exists to catch.
- A rename target can **shadow a real share column**, so accept either name.
- Fold each shared expression's share table into the consuming partition's
  `shares`, but do **not** take the transitive closure — over-folding lets a
  column missing from one share be "found" in an unrelated one.
- `derived` is calibrated empirically. Never inferred statically.
- **`compilecheck.py` is the gate** — Power BI's own parser, via
  `Microsoft.Mashup.Engine1.Library.Modules.Compile`. Nothing hand-rolled knows
  M's grammar. `mlint` is a secondary structural check, not a substitute.
- **"TMDL parses" is not "the model loads."** `ConnectFolder` returns success on
  a model whose M is syntactically invalid: TMDL validates structure and treats
  M as an opaque string. Only the mashup engine compiles it. Asserting the next
  layer's behaviour from the previous one's cost a broken model open.
- Feed the compiler only genuine M. Calculated tables are DAX and single-line
  expressions extract as empty; both produce false failures, which are worse
  than no check.
- Prove the assertion fires. `negtest.py` injects an impossible column so a
  refresh must fail by name. A guarantee only ever observed passing is weakly
  evidenced.
- Back up per run. **Never `git checkout` to revert** — these working trees
  routinely hold uncommitted model work.

## Known limits

- Detects columns *missing*. Not type changes, not a dropped table. A rename is
  caught as a removal, reported as missing rather than as a rename.
- Orphaned template queries (no table or expression consumes them) are out of
  scope by design.
- Verification needs a live Desktop instance. An offline checker against the
  Delta Sharing REST API would remove that, given the `config.share` profile.
- **Field parameters are the known hole.** They dispatch to measures at query
  time, so a column reachable only through one is invisible to the static graph
  and would be classified optional — the silent direction. Validate with a
  VertiPaqSEQueryEnd trace before trusting req/opt on a model that uses them.
- `CALCDEPENDENCY` reflects the model as last refreshed, so capture it from a
  live instance after a successful refresh, never from TMDL.
- Intermediate share columns (the roots in `required/<p>.shares.json`) are not
  yet asserted; only bound model columns are. A `SchemaAssert` query would
  close that.

## Parsing M with Power BI's own parser

`mast/MAst.cs` builds `mast.exe`, which loads `Microsoft.MashupEngine.dll` --
the compiler Power BI Desktop itself uses -- and emits the M syntax tree as
JSON. `astm.py` walks it; `astedges.py` extracts dependency edges from it.

    # copy the engine out of the Desktop install first
    cp "/c/Program Files/Microsoft Power BI Desktop/bin/Microsoft.MashupEngine.dll" mast/
    csc.exe /target:exe /out:mast\mast.exe mast\MAst.cs /r:mast\Microsoft.MashupEngine.dll

Both extractors run and are unioned (`depgraph.build(..., mode="union")`). The
regexes are kept because the union can only add edges, and an edge added is a
column that stays in `req` -- it cannot introduce a false negative.

### Gates

    python gate_m.py   <project_dir> [...]          # no capture needed
    python gate_ast.py <project_dir> <calcdep.csv>  # needs a live capture

`gate_m.py` compares the two extractors query by query and fails only on a parse
failure or a narrowed attribution, the two things that can hide a real
dependency. `gate_ast.py` diffs the resulting required sets.

Current corpus: 332 M queries across five reports, zero parse failures, zero
narrowed attributions. On Butler-Cohen the tree walk finds four bound columns
the regexes missed and misses none.

## One connection per model

`containerize.py` rewrites every per-query `DeltaSharing.Contents` navigation to
go through a single `Procore2` expression. Company Review had 133 call sites,
Monthly Review 130, Evaluations 131, MJS 6 — all now 1.

Two payoffs: the connection and catalog resolve once per refresh instead of
once per query, and every other query becomes source-agnostic, so repointing a
model at a different source is a one-line change.

The share stays DERIVED from the entered credential (`Source[Name]{0}`), not
named in the M. Naming it makes a credential change a model change — rotating a
token would mean installing Desktop and editing a query instead of swapping the
credential in the Service. `--share=NAME` pins and `--unpin` returns to derived;
derived is the default.

    python containerize.py "<project>" --apply

## The derived-column allowlist is computed

`emit_derived.py --write` reads produced names off the syntax tree — AddColumn,
DuplicateColumn, SplitColumn, ExpandRecordColumn, ExpandTableColumn,
AggregateTableColumn, Group aggregates — and follows rename chains, because
renaming a derived column yields a derived column.

It writes a UNION with the existing list, never a replacement: a pivot takes its
column names from the data, so a computed list can be incomplete. Union costs
canary precision and never contract correctness; they are separate artifacts.

## Waiting for a refresh

    powershell -File watch_refresh.ps1 -Port <n> [-TimeoutMin 60]

Polls `$SYSTEM.TMSCHEMA_PARTITIONS` through the ADOMD client that ships with
Desktop and exits on a terminal state, so a background shell can block on it.

`State = 1` alone is not success — the newest `RefreshedTime` must have moved
past a baseline taken at start, which is what separates a real re-run from the
previous refresh's cached data. A failed refresh leaves the model PARTIALLY
loaded, so "every partition settled" never arrives; stalling is its own terminal
state. Duration is measured across partitions stamped in that run.

Observed: ~9.5 minutes for a ~120-table First Finish model.
