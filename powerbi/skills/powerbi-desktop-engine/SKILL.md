---
name: powerbi-desktop-engine
description: Use Power BI Desktop's own libraries to compile and parse M, read M out of TMDL, validate a report definition, wait on a refresh with a real condition instead of a sleep, and prove a report edit by the DAX each visual issues. Use this whenever you generate or edit M / Power Query in a PBIP model and need to know it is valid before writing it to a report, whenever you need to parse M into a syntax tree rather than regex it, whenever you must wait for a Desktop refresh to finish or tell a genuine re-run from cached data, whenever a PBIR edit needs verifying by something better than opening Desktop and looking, or whenever a tool must locate Microsoft.MashupEngine.dll or the ADOMD client. Also covers why TMDL parsing succeeding does not mean the model will open.
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

## Checking a report definition (PBIR)

JSON parsing is not PBIR validation, exactly as TMDL parsing is not M validation. A report whose every file is well-formed JSON can still be one Desktop refuses to open, because what matters is whether the pieces REFER to each other correctly.

```bash
python pbircheck.py "<project folder>"
```

Structure a generator must model, measured across five hand-authored reports (2412 files):

- **PBIR is a containment hierarchy, not a flat list.** 387 of 2235 containers are `visualGroup`, not `visual`, and **1572 sit inside one**. Code assuming `visual.visualType` is wrong for 17% of files. Groups nest via `parentGroupName`, scoped per page, and can be `isHidden`.
- **Schema versions are mixed within one report.** Five `visualContainer` versions appear across this corpus, and Butler-Cohen alone uses 2.11.0 and 2.12.0 side by side.
- **Microsoft publishes these schemas, but publication lags Desktop.** 2.8.0 and 2.9.0 resolve; 2.10.0, 2.11.0 and 2.12.0 return 404. Validate against a version you did not declare only if you say so.

`pbircheck` is a pre-filter, not the authority — the authority is Desktop opening the file. It catches what a generator gets wrong: dangling `parentGroupName`, duplicate container names, non-numeric positions, containers that are both visual and group, group cycles, bookmarks naming visuals that no longer exist.

### The shipped schemas are a reference, not a gate

Desktop embeds JSON Schemas for these documents in `Microsoft.PowerBI.ClientResources.dll`; `pbirschemas.py --extract` pulls all 13 out, and `setup.ps1` does it for you. They cover structures the *published* schemas predate — `visualGroup`, `parentGroupName`, `isHidden` — and they work offline.

**They are not the contract Desktop enforces on what it writes.** Measured across five hand-authored reports: **2385 of 2412 files deviate**, in 17 classes — a `$schema` const pinned to one version while real files span five, `filter.Version` pinned to `2` while files carry `1`, and properties Desktop emits that the schema does not declare (`width`, `showSetAlertButton`, `showFollowVisualButton`) under `additionalProperties: false`.

So `pbircheck --schema` is **advisory and never changes the exit code**. A gate that fires on known-good input is worse than no gate. Use the schemas the other way round — as the reference for what properties and enum values exist when *generating* PBIR. `reportthemeschema` is the largest at 914 KB and is the machine-readable form of a design system: `dataColors`, `foreground`, `accent`, `firstLevelElements`, and the per-visual formatting surface.


## Proving a report edit by the query it produces

`pbircheck` says a report is well-formed. It cannot say the edit did what was
intended — for that, someone normally opens Desktop and looks, which is not
evidence anyone can re-run.

A visual's content **is** its DAX query, so the question has an exact answer:
capture the statement each visual issues, and diff the text.

```bash
python paquery.py <baseline.json>                      # per-visual DAX
python paquery.py <baseline.json> --compare <after.json>
```

The recording comes from Desktop's **Performance Analyzer** (View → Performance
Analyzer → Start recording → Export). `Execute DAX Query` carries
`metrics.QueryText`; the visual is found by walking `parentId` up to an id whose
first segment is a 20-hex visual name.

**The modeling MCP's `trace_operations` cannot do this.** Even with
`filterCurrentSessionOnly: false` it captures only its own connection — a page
switch in Desktop records zero events, while a query issued over the MCP
connection records fine. Desktop's UI session is not visible to it.

### The protocol, and why each step is load-bearing

```
1. Refresh visuals                       baseline: the designed query
2. drill or filter away from that state  forces a real divergence
3. apply the edit under test
4. Refresh visuals                       the state the edit left behind
5. diff against the baseline             must be identical
```

**Without step 2** the recording is silent, because a bookmark asserting the
state a visual is already in makes it re-query nothing. Silence is consistent
with a correct edit *and* with one Desktop ignored, so it scores neither.

**Without step 4** the evidence goes missing exactly when the edit works:
Desktop serves an already-rendered state from cache, so a correct restore emits
no query and the perturbed statement stays the last one recorded — which reads
as a mismatch and blames a working edit. `paquery` returns INCONCLUSIVE rather
than scoring a recording with no `UserAction_Refresh` after the perturbation.

Performance Analyzer logs no User Action for applying a bookmark, so its absence
is not evidence the bookmark was not applied.

### Headless: derive the query instead of recording it

A capture costs one human interaction per visual, which does not scale to
validating a component library — a trace per component per interaction is
infeasible, and it is also the wrong unit of work.

```bash
python visualdax.py "<project>" --page <pageId> --visual <visualId>
```

This reads the query out of PBIR: active projections become the groupings,
`filterConfig.filters` from **report, page and visual scope** become `TREATAS`,
and the `Values` role becomes the measures. Execute it through the modeling MCP
and compare rows. Nothing is clicked and nothing needs to be open but the model.

It deliberately does **not** reproduce Desktop's text. Desktop wraps the real
question in row-window `TOPN`s, a `SUBSTITUTEWITHINDEX` column axis and
`ROLLUPADDISSUBTOTAL` subtotal markers — presentation machinery that varies with
the visual's size and scroll position. Underneath is `SUMMARIZECOLUMNS` over the
active groupings under the active filters, which is what correctness rests on.

**So the division of labour is: record once per component TYPE to calibrate,
then run headless per instance.** The expensive instrument earns its cost by
validating the cheap one, not by being run at scale.

Two traps that make generated DAX wrong rather than failing:

- **PBIR quotes strings the way M does** — `'Evaluation - Vendor'`. DAX reads
  single quotes as a *table* name, so passing the literal through unchanged
  either errors or silently resolves against something else. Booleans arrive
  lowercase and DAX wants `TRUE`.
- **Filters live at three scopes.** Reading only the visual's own
  `filterConfig` returns different numbers from the report, quietly. A card with
  no `filter` key is an empty card and restricts nothing — meaningful in a
  bookmark, where it means "cleared", but not a filter.

A filter the generator cannot express must be reported, never skipped: numbers
filtered differently from the report are the one failure this must not hide.

**What this does not cover.** Identical DAX means identical data, not identical
appearance — colours, fonts and conditional formatting produce the same
statement. A visual that is hidden issues no query and is reported SILENT, not
passed. And a human still has to perform the clicks; what the harness removes is
the human as *judge*, not as actuator.

## Gates, and gates that lie

A gate that can report an unearned pass is worse than no gate. Two real examples:

- `compilecheck` once blamed the compiler for a model that was fine, because it was handed the wrong path, found zero expressions, and reported the empty result as a failure. **Treat zero inputs as a hard error.**
- The tell was a **count that did not move** when it should have. Watch counts, not just pass/fail — adding an expression should raise the compiled total by one, and it silently did not.

Verify against a known rejection, not just a successful run: `setup.ps1` checks that the compiler *refuses* `optional` as a parameter name, because a stub that accepts everything would pass any check built only on valid input.
