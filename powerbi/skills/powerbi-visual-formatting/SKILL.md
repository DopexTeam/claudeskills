---
name: powerbi-visual-formatting
description: Apply consistent number formatting (currency $K/$M, %, counts) to Power BI report visuals at scale via a "Number Formatting" calculation group. Use when a user wants visuals (cards, charts) to share one number format, when fixing inconsistent/overridden formatting across a PBIP/PBIR report, or when rolling a format-spec change across many visuals. Covers the card-vs-chart engine split, display-unit double-scaling, name-routing, and the MCP+PBIR save/close/reopen workflow.
---

# Power BI visual number formatting at scale

Format many visuals consistently using ONE `Number Formatting` calculation group, applied per visual via a visual-level filter. Hard-won rules below — most were learned by getting them wrong first.

## The core split: cards use a VALUE item, charts use a FORMAT-STRING item

A measure's value can only be formatted two ways through a calc group, and they use **different format engines**:

1. **Cards / tables → value-replacement item** (returns formatted TEXT):
   `IF(ISBLANK(SELECTEDMEASURE()), BLANK(), <FORMAT(...) text>)`
   - Renders fine on cards; the text value **ignores the visual's display-units/precision settings** (robust — no override conflicts).
   - Uses the **VBA** format engine: `"$#,##0,K"` → `$987K` (clean 0-decimal K works).
   - **Cannot be used on charts** — a bar/donut needs a *number* to size; a text value blanks/breaks the plot. This is why working reports use the value item on cards only.

2. **Charts → format-string item** (keeps the value numeric):
   - `expression = SELECTEDMEASURE()` (pass-through number so it plots) + a `formatStringExpression` that returns a dynamic format string.
   - Uses the **.NET** format engine: a scaling comma only divides if it sits **immediately before a decimal point**. So `"$#,##0,,.0M"` scales (M, 1-dec) but `"$#,##0,K"` does **not** scale → use `"$#,##0,.0K"` (forces a decimal anchor → 1-dec K). **Charts can't do clean 0-dec K** — `"$#,##0,.K"` renders a trailing dot. Cards (VBA) can; charts (.NET) can't. Accept 1-dec K on charts or use native Auto display units.
   - Set via MCP `calculation_group_operations UpdateItems`/`CreateItems` with `FormatStringExpression`.

Don't trust DAX `FORMAT()` to predict the chart format string — `FORMAT()` is VBA, the dynamic format string is .NET. They differ on exactly the comma-scaling rule. Verify charts by **rendering**, not querying (format strings never show in query output anyway).

## Display units MUST be None on charts (the double-scaling trap)

Chart data labels default to **Auto display units**, which *also* scale + append K/M. Combined with a scaling format string you get `$0.00MM` / `$0MK` (double-scaled, double-suffixed). For every chart you format: set label `labelDisplayUnits` to **None** (`"1D"` in PBIR; `0D`=Auto), and value-axis display units to None too **if the axis is shown** (`valueAxis.show`). Cards don't need this (text ignores units). Also strip per-label `labelPrecision` overrides so the format string controls decimals.

## Name-routing inside the calc item

Route by `SELECTEDMEASURENAME()`: ends `Count`/`Qty` → integer `#,##0`; (starts `%` OR ends `%` OR starts `Pct_`) AND not ends `$` → `0%`; else → currency by magnitude. Harden these to the report's actual naming conventions (e.g. add `Qty`, `%`-suffix, `Pct_`). A measure routes correctly by NAME regardless of its format string, so `Count`-named/`%`-named measures are always safe; the default ($) branch is only correct for genuine currency.

## What to format vs skip (classification)

Only format a visual if EVERY value field is "AUTOFMT-safe":
- **currency** — measure has `$` in format string, or name ends `$`, or it's a currency column (`*_company_currency`, `*_amount`).
- **count** — measure name ends `Count`/`Qty`.
- **clean %** — measure name matches the % rule above.
Extract value fields from value roles (`Y`,`Y2`,`Values`) including **column aggregations** (`Aggregation→Column`), not just measures — charts often plot `Sum(column)`.
**Skip + flag:** operational measures (hours, durations, ratios) and implicit record-counts (`Count of project_id`) — they'd be wrongly $-stamped and an implicit column-count has no `Count` name to route on. **Skip Dummy-measure charts** — a hidden `Dummy` series is a deliberate layout trick (stacks labels vertically); touching it breaks the layout.

## Workflow (model = MCP/Desktop-open; layout = files/Desktop-closed)

1. Inventory measures → format strings (parse `*.SemanticModel/.../tables/*.tmdl` `formatString:` lines, or MCP `INFO.MEASURES()`).
2. Dry-run classify all non-table visuals → sweep / skip / flag lists. Show counts before editing.
3. Calc-item changes via MCP (Desktop open); after any calc-item create/update run a **Calculate-only** refresh (`table_operations Refresh` `refreshType:"Calculate"` on the calc-group table) — recomputes the group without a data reload; then user **saves** (clears the "calculation groups need to be refreshed" prompt — that prompt is safe, the ribbon Refresh is the one that re-pulls data).
4. **Checkpoint-commit** both repos before layout edits.
5. Visual filter edits are PBIR file edits → require Desktop **CLOSED** (it clobbers layout on save and won't load external edits until reopened). Edit `visual.json` via Python `json` (preserves floats faithfully with `ensure_ascii=False`; PowerShell `ConvertTo-Json` reformats/rounds — avoid). The filter object: `filterConfig.filters[]` (top-level, sibling of `visual`) with field `Number Formatting[Calculation group column]`, `type:"Categorical"`, `Where … In ["'<item name>'"]`. Validate `json.loads` on every file before writing.
6. Reopen → spot-check **one of each visual type** (cards, donut, bar, 100%-stacked — the stacked uses a different `detailLabelPrecision` label model) → save → commit.

## Gotchas
- `filterConfig` is **top-level** in `visual.json`, not under `visual`.
- The property `"Calculation group column"` is shared by EVERY calc group — never bulk find-replace it; transform whole filter objects anchored on the unique item-name literal.
- Role bookmarks snapshot visual filters; clicking one re-applies its old snapshot and can strip a newly-added filter. Set role bookmarks to **not capture Data**, or re-update them after filter changes.
- Currency measures with **empty format strings** evade `$`-detection — catch by name (`*$`) or fix the model format string.
- **Mixed-signal names** (a name carrying both `%` and `$`/`Qty`, e.g. `% Complete $`, `% Complete Qty`): the `$`/`Qty` suffix wins the routing, so a percent like `1.0` renders as `1` or `$1` on a KPI card (a tell-tale "just shows 1" symptom). Fix by **renaming the measure to a single intent** (`% …`); cards already carrying the AUTOFMT filter re-route automatically, no visual edit needed. For % **charts** the sweep skipped (no clean name to route), the simplest fix is native per-visual **value formatting = 0 decimal places**, not the calc group.
- **A chart can still break** ("value isn't a number") even with the format-string item if that visual's config won't accept the dynamic value/format. Don't force it — **remove the chart filter from that one visual and use native formatting** instead. Spot-check every chart *type* after a rollout; treat any broken visual as a remove-and-go-native case, not a debugging rabbit hole.
- **Project rollup vs row grain:** a card/measure using `SELECTEDVALUE(payapp[col])` works only when one row is in context. A parent grain (e.g. a project with multiple prime contracts, each contributing its latest pay app) yields N rows → `SELECTEDVALUE` returns BLANK (card shows empty). Rollup cards must `SUMX` across the parent key, not `SELECTEDVALUE`. Single-child cases mask the bug; multi-child expose it.
