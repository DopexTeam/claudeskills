# SKILLS-MANIFEST.md — `powerbi`

**Owner:** David McDonnel, Jr.
**Status:** v0.1 — contract doc for this plugin
**Purpose:** Decision record for the Power BI skill set. Same contract as `dev-standards/SKILLS-MANIFEST.md`: nothing in a SKILL.md may contradict this file, and the load-bearing content is the **non-scope** lines, not the names.

---

## 0. What makes this plugin different

Every skill in `dev-standards` is prose. These three carry **executable payload** — Python and PowerShell that edit client semantic models. That changes two things:

- **A skill here can be wrong in a way prose cannot.** It can write invalid M into a report that then will not open. So each one states its gates, and the tooling refuses to proceed rather than guessing.
- **They borrow Microsoft's libraries rather than shipping them.** Power BI Desktop must be installed; `setup.ps1` locates it, copies what it needs out of the local install, and proves the result works. Nothing redistributable is committed.

**Client data never ships.** Everything the tooling generates — dependency captures, contracts, backups of whole semantic models, and the share tokens inside them — lives under `PROCORE_LOCK_DATA` (default `~/.procore-schema-lock`), deliberately outside the skill folders. A `.gitignore` protects a git push; it does not protect a folder copy.

---

## 1. The skills

### 1.1 `powerbi-desktop-engine` — foundation

**Description (paste-ready):**
> Use Power BI Desktop's own libraries to compile and parse M, read M out of TMDL, and wait on a refresh with a real condition instead of a sleep. Use this whenever you generate or edit M / Power Query in a PBIP model and need to know it is valid before writing it to a report, whenever you need to parse M into a syntax tree rather than regex it, whenever you must wait for a Desktop refresh to finish or tell a genuine re-run from cached data, or whenever a tool must locate Microsoft.MashupEngine.dll or the ADOMD client. Also covers why TMDL parsing succeeding does not mean the model will open.

**Owns:** locating Desktop's libraries. Compiling M with the mashup engine. Parsing M to a syntax tree. Reading and replacing M inside TMDL. M linting. Refresh watching via ADOMD. `setup.ps1` for the whole plugin.

**Non-scope:**
- Anything specific to Procore Delta Sharing — share navigation, contracts, drift → `procore-schema-lock`
- Deciding *which* columns a report needs → `procore-schema-lock` owns the dependency graph
- Visual and number formatting → `powerbi-visual-formatting`
- Writing DAX, or judging whether a measure is correct → nothing here; see `dev-standards/verification-discipline` for how to check
- Report layout and visual placement → nothing here

**Bundled:** `scripts/` — `mcompile.py` + `compilecheck.py` (compile), `astm.py` + `mast/` (parse), `mbody.py` (TMDL), `mlint.py` + `lintdir.py` (lint), `watch_refresh.ps1` (refresh), `pbidesktop.py` (library resolution)

**Pairs with:** `procore-schema-lock`, which depends on it and resolves it via `scripts/engine.py`. Ship together.

**Evals:**
1. "I'm about to generate a Power Query step into all 93 tables of a PBIP model programmatically. The TMDL parses fine after my edits but I've been burned before — how do I actually know the model will still open in Desktop?"
2. "I kicked off a refresh on a 120-table model and the dialog is still up after 20 minutes with no error. Is it actually doing anything, and when it finishes how do I tell real data from what was already cached?"

---

### 1.2 `procore-schema-lock` — depends on `powerbi-desktop-engine`

**Description (paste-ready):**
> Make a Procore Analytics 2.0 (Delta Sharing) Power BI report fail to refresh ONLY when a column it actually uses is renamed or removed. Use when a Service refresh fails with "the column X does not exist in the rowset", when applying or upgrading the schema lock / SchemaContract on a PBIP report, when consolidating per-query DeltaSharing.Contents calls behind one expression, or when a Schema Audit canary reports drift. Covers the Desktop-vs-Service asymmetry, the leaves-to-roots dependency graph, and the gates that must pass before any client file is touched.

**Owns:** the Desktop/Service asymmetry and why the failure only appears in the Service. The leaves-to-roots dependency graph (report bindings → Procore share columns). The `LockSchema` / `SchemaContract` shape and its required/optional split. The Schema Audit drift canary and its derived-column allowlist. Consolidating Delta Sharing navigation behind one expression.

**Non-scope:**
- Compiling or parsing M, reading TMDL, waiting on a refresh → `powerbi-desktop-engine`
- What a Procore column *means* — pay-app ranking, billing periods, budget semantics → nothing here; this skill only decides whether a column is *used*
- Visual or number formatting → `powerbi-visual-formatting`
- Deciding what a report should contain → the report's author

**Bundled:** `scripts/` — the graph (`depgraph.py`, `usage.py`, `astedges.py`), the lock (`apply_lock.py`, `lockm.py`), consolidation (`containerize.py`), the canary (`add_canary.py`), generators (`emit_required.py`, `emit_derived.py`), gates (`gate_ast.py`, `gate_m.py`, `negtest.py`)

**Pairs with:** `powerbi-desktop-engine`. Will not run without it.

**Evals:**
1. "A Procore-sourced report refreshes fine on my machine but the scheduled refresh in the Service failed with `The 'percentage_paid_company_currency' column does not exist in the rowset`. I didn't change anything. What happened, and how do I stop it recurring across my other Procore reports?"
2. "I want a guarantee these reports only fail to refresh if a column that's actually used in the report gets renamed or removed — not on a column nothing touches. Can you apply that across the four Procore reports I maintain?"

---

### 1.3 `powerbi-visual-formatting`

**Description (paste-ready):** see the skill's own frontmatter.

**Owns:** number formatting at scale through one `Number Formatting` calculation group. The card-vs-chart engine split. Display-unit double-scaling. Name-routing inside a calc item.

**Non-scope:**
- Editing M or the model's queries → `powerbi-desktop-engine`
- Schema drift and contracts → `procore-schema-lock`
- Theme files and colour tokens → nothing here yet
- Visual placement and page layout → nothing here

**Evals:**
1. "The cards on this report show raw numbers like 1435820.44 while the charts next to them show 1.4M. I want every currency figure across ~40 visuals to read as $K consistently, without touching each visual by hand."
2. "We changed the house format spec from $M to $K. How do I roll that across a report without re-formatting every visual individually, and what breaks if a visual already has its own formatting set?"

---

## 2. Amendments

- **v0.1** — plugin created. Three skills, first executable payload in this repository.
