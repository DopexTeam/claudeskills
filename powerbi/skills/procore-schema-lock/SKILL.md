---
name: procore-schema-lock
description: Make a Procore Analytics 2.0 (Delta Sharing) Power BI report fail to refresh ONLY when a column it actually uses is renamed or removed. Use when a Service refresh fails with "the column X does not exist in the rowset", when applying or upgrading the schema lock / SchemaContract on a PBIP report, when consolidating per-query DeltaSharing.Contents calls behind one expression, or when a Schema Audit canary reports drift. Covers the Desktop-vs-Service asymmetry, the leaves-to-roots dependency graph, and the gates that must pass before any client file is touched.
---

# Procore Delta Share schema lock

Procore changes shared table columns without notice. **Desktop re-detects the schema on refresh and silently reconciles; the Service binds published columns by name and hard-fails.** So the failure only ever appears in the Service, on a report that refreshes fine locally.

The fix is a terminal `LockSchema` step on every share-backed query, driven by a generated `SchemaContract`:

```
(tbl as table, req as list, opt as list) as table =>
    let actual = Table.ColumnNames(tbl), missing = List.Difference(req, actual)
    in  if List.IsEmpty(missing)
        then Table.SelectColumns(tbl, List.Distinct(req & opt & actual), MissingField.UseNull)
        else error "Procore removed column(s) this report depends on: " & Text.Combine(List.Sort(missing), ", ")
```

`req` = columns the report actually consumes → fail loudly and name them. `opt` = bound but unreferenced → null-pad silently. The union with `actual` lets source-ADDED columns through; a plain projection would freeze the schema.

Tools are in `scripts/` beside this file; `scripts/README.md` has the detail. The M compiler, the M parser, the TMDL reader and the refresh watcher come from the sibling **`powerbi-desktop-engine`** skill — it owns everything generic to Power BI, this skill owns only what is specific to Procore Delta Sharing. Never name the parameters `required`/`optional` — **`optional` is a reserved M word** and the model will not open.

## Setup

Run `powerbi-desktop-engine`'s `setup.ps1` — it owns the Power BI Desktop libraries both skills depend on. This skill's tools resolve it automatically via `scripts/engine.py`; the two are vendored together.

Generated state lives OUTSIDE both skills, under `PROCORE_LOCK_DATA` (default `~/.procore-schema-lock`): `calcdep/`, `required/`, `derived/`, `backup/`. That is deliberate — those hold whole client semantic models, column names and the share tokens that appear in `expressions.tmdl`. A `.gitignore` protects a git push; it does not protect someone copying the folder.


## Required is computed, never guessed

`depgraph.py` is one graph, leaves → roots. Leaves are report bindings (PBIR JSON) plus objects that break the model rather than one visual; roots are Procore share columns. Required = reachable.

Both directions of error matter. A false *negative* corrupts numbers in silence. A false *positive* breaks the stated guarantee just as surely — the report fails on a column nothing uses.

Leaves that are not report bindings, each found by a report that had one:
- `*RELATIONSHIP` — a broken key breaks every join
- `ROWS_ALLOWED` — RLS. Company Review filters `ProjectUser` on `email_address`, which no visual binds. Miss it and the predicate silently stops matching: a security failure presenting as a successful refresh.

Reference types that must be followed in `INFO.CALCDEPENDENCY`:
- `ATTRIBUTE_HIERARCHY` — how a hierarchy's levels are recorded. Without it a hierarchy binding reaches nothing.
- `CALC_TABLE` — field parameters **nest**; one `NAMEOF` list can point at other field parameters, not measures.
- `TABLE` is deliberately EXCLUDED. `COUNTROWS(T)` needs the table, not every column; following it marks the whole model required.

Capture from a live instance, after a successful refresh. An object appears only if it depends on something, so constant measures are absent — that is expected, and classification comes from the model inventory, never from the graph.

## Workflow

Order matters, and Desktop must be closed for every file edit.

1. **Capture** `INFO.CALCDEPENDENCY` from the open, refreshed model → `calcdep/<project>.csv`
2. `emit_required.py` → `required/<project>.json`; `emit_derived.py --write` → `derived/<project>.json`
3. `gate_ast.py <project> <calcdep.csv>` — must be CLEAN before anything is written
4. **Desktop closed.** Check `git status` is clean FIRST — Desktop reserialises on save and you need to know what was already there
5. `containerize.py <project> --apply` — one `DeltaSharing.Contents` per model
6. `apply_lock.py <project> --apply`
7. `add_canary.py <project> --apply` — required after any v1→v2 upgrade
8. Gates: `compilecheck.py`, `lintdir.py`, `gate_m.py`, required-set diff, re-run each tool to confirm no-op
9. Commit in BOTH repos, then refresh and watch with `watch_refresh.ps1`

**Do step 5–8 on a copy first.** Every serious defect in this toolchain was caught that way and would otherwise have shipped.

The tools key their inputs on the project FOLDER name, so a copy at `./ev` needs `required/ev.json` and `derived/ev.json` in the data root — copy them alongside, then delete both plus `backup/ev_*` afterwards. Keep the copy's path short: these tools open files with Python, and a deep scratch path plus a long TMDL name exceeds Windows `MAX_PATH`, which fails to open files that `ls` will happily list.

## The share stays DERIVED from the credential

The container resolves `Source[Name]{0}` — whatever share the entered credential exposes. Do **not** hardcode the share name. It makes a credential change a model change: rotating a token would mean installing Desktop and editing a query instead of swapping the credential in the Service, where the client administers it.

Pinning buys a loud failure when the *wrong* credential is cached. That is an authoring-machine hazard only — Desktop caches one credential per data source across files, while each Service dataset carries its own binding. Not worth the cost. (`--share=NAME` and `--unpin` exist; default is derived.)

The consolidation itself is the valuable half: every other query becomes source-agnostic, so repointing at a warehouse is a one-line change.

## Traps

The generic ones — compile before writing, gates that report unearned passes, never truncating `expressions.tmdl`, never doing comma surgery in a `let` — live in **`powerbi-desktop-engine`**. Read those too; they bite here as hard as anywhere, and one of them deleted this skill's container expression. What follows is specific to this workflow.

**The inline lock is also a projection.** The earliest form wrote the column list straight into `Table.SelectColumns(..., MissingField.UseNull)`, doing double duty as lock and as the pruning that keeps the model small. v2 unions `actual`, so replacing the call drops the projection — MJS gained 221 columns on the next refresh. **Wrap** the original call as the lock's first argument.

**The canary breaks silently on a contract version bump.** v2 renames `cols` to `req`/`opt`; a canary still reading `e[cols]` raises at RUNTIME, which the compile gate cannot see — and the thing that breaks is the drift detector itself. `apply_lock` now refuses to finish quietly when it finds one.

**Drift rows are usually derived columns, not drift.** Anything the M creates never exists in the share. `emit_derived.py` computes the allowlist from the syntax tree; it writes a UNION with the existing list, never a replacement, because pivot column names come from data and cannot be computed.

**An OLE DB / ODBC error is never the lock.** When the contract fires it names the columns. Anything below that layer is connection, auth or navigation. Useful triage rule.

## Watching a refresh

Use `powerbi-desktop-engine`'s `watch_refresh.ps1 -Port <n>`; it owns that ground. Baseline for expectations here: a ~120-table First Finish model refreshes in ~9.5 minutes once consolidated.

## Proving it works

`negtest.py` injects a sentinel required column so the assertion must fire. In Desktop the refresh dialog hangs rather than completing — the error text appears in the blocked-query list, but the dialog does not close. That is expected, and is why the Service is the real target.
