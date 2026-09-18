---
name: powerbi-desktop-engine
description: Use Power BI Desktop's own libraries to compile and parse M, read M out of TMDL, and wait on a refresh with a real condition instead of a sleep. Use this whenever you generate or edit M / Power Query in a PBIP model and need to know it is valid before writing it to a report, whenever you need to parse M into a syntax tree rather than regex it, whenever you must wait for a Desktop refresh to finish or tell a genuine re-run from cached data, or whenever a tool must locate Microsoft.MashupEngine.dll or the ADOMD client. Also covers why TMDL parsing succeeding does not mean the model will open.
---

# Power BI Desktop's engine, borrowed

Power BI Desktop ships the components that make M work verifiable. Nothing else does, so these tools copy them out of the local install rather than reimplementing them.

| Library | What it gives you |
|---|---|
| `Microsoft.MashupEngine.dll` | The M compiler and parser Power BI itself uses — the only thing that actually knows M's grammar |
| `Microsoft.PowerBI.AdomdClient.dll` | Query a running Desktop model's DMVs from a shell, which turns refresh-waiting into a condition |

**Non-scope:** this skill owns the generic Power BI layer only. Anything about Procore Delta Sharing — share navigation, schema contracts, drift canaries — belongs to `procore-schema-lock`, which builds on this. Visual and number formatting belongs to `powerbi-visual-formatting`.

## Setup

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

Idempotent; re-run after a Desktop upgrade because the borrowed libraries move with it. It locates the install (MSI, Store or enterprise), records paths in `scripts/pbi_paths.json`, builds `mast.exe`, and proves both libraries work. Needs Python 3.8+, the .NET Framework `csc.exe`, and Power BI Desktop installed — a Service subscription is not enough, these are desktop libraries.

## TMDL parsing is not M validation

TMDL validates *structure*. The M inside an `expression` or `partition` is an opaque string to it, so a model whose M cannot compile will parse as valid TMDL, and `ConnectFolder` will return success on a model that then refuses to open.

**Compile generated M before writing it to any report.**

```bash
python compilecheck.py "<project folder or .SemanticModel/definition>"
```

`optional` is a reserved M word. `(optional as list) => ...` is a syntax error that only the compiler catches — it cost a broken model open. Conversely `[type]` is legal: inside brackets a reserved word is a field NAME, and a linter that flags it is wrong.

## Parsing M, not regexing it

`astm.py` runs `mast.exe` and returns the syntax tree as JSON, so arguments are identified by POSITION rather than by pattern.

Two traps in the tree itself, both of which silently produce wrong answers:

- **The engine interns literals and identifiers.** A cycle guard scoped to the whole tree rather than the current path drops every repeat, so `{"a"} … {"a"}` returns the second list empty and a column named twice becomes invisible the second time. Scope cycle detection to the path.
- **Field references carry the name on `MemberName`.** Taking every identifier beneath the node also yields the target — `each [status]` desugars to `(_) => _[status]`, so you get a spurious `_`.

`unhandled_functions()` is the reason to prefer the tree: what a regex fails to recognise is invisible, but what the tree does not recognise is enumerable.

## Waiting for a refresh

Do not sleep blind.

```powershell
powershell -File watch_refresh.ps1 -Port <n> [-TimeoutMin 60]
```

Exits on a terminal state, so a background shell can block on it. Get the port from `INFO`/the MCP instance list.

The wrinkle that makes this look impossible: the assembly is named `Microsoft.PowerBI.AdomdClient` while its types live in the `Microsoft.AnalysisServices.AdomdClient` namespace, so `Add-Type` appears to succeed and then the type is not found.

Three things it must get right, each learned by getting it wrong:
- **`State = 1` is not success.** The newest `RefreshedTime` must have moved past a baseline taken at start, or you are reading the previous refresh's cached data.
- **A failed refresh leaves the model PARTIALLY loaded**, so "every partition settled" never arrives and waiting for it reports only TIMEOUT. Stalling is its own terminal state.
- **Measure duration across partitions stamped in THIS run.** Subtracting the baseline reports the gap since the previous refresh — 1380s for a run that took 563s.

## Reading M out of TMDL

`mbody.py` extracts and replaces the M body of an `expression` or a `partition ... source =`, handling both the plain and fenced (` ``` `) forms — Desktop rewrites one into the other on save. `BLOCK` splits a table file into its column / measure / partition parts.

**Never do comma surgery inside a `let`.** Appending to the last *line* puts the comma inside a trailing `// comment`, fusing two bindings into invalid M. This broke a production report. Operate on whole lines, or on the last line carrying CODE.

**Never truncate `expressions.tmdl` to EOF.** Desktop reorders expressions on save, so cutting from a known expression to the end deletes whatever it moved past.

## Gates, and gates that lie

A gate that can report an unearned pass is worse than no gate. Two real examples:

- `compilecheck` once blamed the compiler for a model that was fine, because it was handed the wrong path, found zero expressions, and reported the empty result as a failure. **Treat zero inputs as a hard error.**
- The tell was a **count that did not move** when it should have. Watch counts, not just pass/fail — adding an expression should raise the compiled total by one, and it silently did not.

Verify against a known rejection, not just a successful run: `setup.ps1` checks that the compiler *refuses* `optional` as a parameter name, because a stub that accepts everything would pass any check built only on valid input.
