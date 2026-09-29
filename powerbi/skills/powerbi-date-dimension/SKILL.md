---
name: powerbi-date-dimension
description: Add a portable, source-free date dimension and a "Time Window" calculation group of date windows (YTD, FYTD, MTD, rolling, prior period, YoY, MoM, last/next N days) to a Power BI PBIP model. Use this whenever a model needs a date or calendar table, whenever an existing DateDimension should be replaced or standardised across reports, whenever someone asks for time intelligence, year-to-date, fiscal year, period-over-period or a slicer that switches a chart between date windows, or whenever a to-date line runs flat into the future or an in-progress month compares badly with the last one. Covers the fiscal-year setting, the gates that stop a replace from deleting measures or orphaning auto date/time tables, and why the windows clip themselves to today.
---

# A date dimension and its windows

Every report needs a calendar, and every report grows its own. Four reports
carried byte-identical copies of one Power Query script, none marked as a date
table, each with a weekend flag that marked Friday and Saturday. This is that
script made once, plus the windows that are otherwise rewritten as measures in
every model.

**Non-scope:** compiling M, reading TMDL, waiting on a refresh →
`powerbi-desktop-engine`. Number formatting, including the `Number Formatting`
calculation group this one has to coexist with → `powerbi-visual-formatting`.
Whether a measure is *correct* → nothing here; a window moves the dates a
measure is evaluated over and takes no view on the measure. Where a slicer sits
on the page → the report's author.

## Two files, one setting

| File | What it is |
|---|---|
| `assets/DateDimension.tmdl` | 68 columns, three hierarchies, marked as the date table. Generated in Power Query, no data source. |
| `assets/Time Window.tmdl` | calculation group, 44 items |
| `assets/DateDimension.pq` | the query alone |
| `assets/install.tmdl` | both tables as a `createOrReplace` script for TMDL view |

The fiscal year start is the one setting most installs need. The rest have
defaults that hold: Monday weeks, Saturday/Sunday weekends, US federal holidays,
a range from 2000 to five years past the current one.

`references/columns.md` lists every column, its type and sort key, and what
changed from the script the reports had. `references/time-window-items.md` gives
the dates each item resolves to.

## Installing

```bash
python scripts/install_kit.py "<project>" --fiscal-start 7          # dry run
python scripts/install_kit.py "<project>" --fiscal-start 7 --apply  # Desktop closed
python ../powerbi-desktop-engine/scripts/compilecheck.py "<project>"
```

Also `--week-start sunday`, `--utc-offset -5`, `--table-only` to leave the
calculation group out, and `--as-of` for testing, covered below.

Run the dry run first and read it. It names what the install replaces, which
columns of the existing table are referenced, and the settings it will carry
over. On a table this kit installed earlier, settings are read back out of the
table and kept, so a reinstall does not reset the fiscal year. The one setting
never carried over is the test date.

### Why it stops

Replacing a table is a delete followed by a create, and what the delete takes is
not visible in the new file. Each of these is a gate, found on a real report:

| It stops when | Because |
|---|---|
| the existing table holds measures or calculated columns | they are deleted with it. One report kept six measures on its date table. |
| columns carry auto date/time variations | the hidden `LocalDateTable_*` tables stay behind in `relationships.tmdl`, pointing at columns that no longer carry them. Commit, turn auto date/time off in Desktop, save, close, re-run. *Commit before turning auto date/time off*, below, says why the commit comes first. |
| a referenced column or hierarchy is missing from the kit | the binding breaks |
| a referenced column changes type | the binding survives and the filter stops matching. `IsWeekend` was the text `"True"` and is now a true/false; a filter on the text matches nothing, silently. |

Three of the four reports this was first run against stop on the second gate.
That is the expected first result, not a fault.

It also refuses a project it cannot read reliably: a model saved as `model.bim`,
a report in the legacy format, or a table named `Time Window` that is not a
calculation group.

Column names compare case-insensitively, as the engine compares them:
`FirstDayOfYear` and `FirstDayofYear` are one column, and both spellings are in
circulation.

### Without the script

Copy the two `.tmdl` files into `<name>.SemanticModel/definition/tables/`, add
`ref table DateDimension` and `ref table 'Time Window'` to `model.tmdl`, and add
`discourageImplicitMeasures` under `model Model`. Without that last line the
engine refuses the calculation group outright:

```
The Model 'Model' property DiscourageImplicitMeasures must be set to true
in order to create any calculation groups.
```

Into an open model, turn on **Discourage implicit measures** in Model view, then
apply `assets/install.tmdl` in TMDL view. The table definitions in that script
are the tested ones; applying them *through TMDL view* is the one path here that
has not been run.

## What a calculation group changes about the model

- **Columns can no longer be dropped onto a visual as values.** Existing visuals
  that already aggregate a column keep working.
- **No item reaches those visuals.** A calculation group changes measures only;
  a raw column sum returned the same total under all 44 items. The installer
  counts them. To window one, give it a measure: `Total Amount = SUM ( Fact[Amount] )`.
- **Every measure becomes a variant type** in the report. A dynamic format
  string that reuses a measure can start erroring; wrap it in `FORMAT ( [m], "" )`.
- **A slicer on `Window` reaches every measure on the page,** including the text
  measures behind dynamic titles. The change items hand text back untouched for
  that reason — arithmetic on a title is a visual-breaking error, and it
  surfaces on a visual nobody was editing.

## The windows clip themselves

A to-date measure written the usual way runs flat through every future month,
and compares 28 days of September with 31 of August. The common fix is a visual
filter, which is one more thing to remember on every visual and the first thing
forgotten.

So the items that look back from a date, which are the to-date, rolling and
prior ones, 19 of the 44, open by finding the last selected date that is not in
the future:

```dax
VAR _end = CALCULATE ( MAX ( DateDimension[Date] ), KEEPFILTERS ( DateDimension[Day Offset] <= 0 ) )
```

When that is blank the whole selection is in the future and the item returns
blank. Otherwise the window is built back from `_end`.

The other items get there differently:

| Items | How |
|---|---|
| 8 change items | compare the elapsed part of the selection with the matching prior item, so both sides cover the same span |
| 16 relative-to-today items | filter an offset column directly. They are not clipped: `Next 7 Days` is meant to be in the future. |
| `Current` | the measure unchanged |

Measured, with months on the axis, 10 per day, a July fiscal year, on the 28th
of September:

| Month | Current | YTD | FYTD | PM | MoM | Last 30 Days |
|---|---|---|---|---|---|---|
| Jul 2026 | 310 | 2,120 | 310 | 300 | 10 | |
| Aug 2026 | 310 | 2,430 | 620 | 310 | 0 | 20 |
| Sep 2026 | 300 | 2,710 | 900 | 280 | 0 | 280 |
| Oct 2026 | 310 | | | | | |

September's `PM` is 280 — 1 to 28 August — so `MoM` is 0, where the unclipped
version gave −30. `Current` still shows future-dated rows, because it is the
measure unchanged.

### "Today" is the refresh date

`Day Offset` is computed in the query, so "today" is when the model last
refreshed, in the timezone `UtcOffsetHours` names. The items filter on that
column rather than calling `TODAY()` so there is one definition of today and
not two that disagree for the hours between midnight UTC and midnight local.

It is **not** the last date with data. A model loaded through August and
refreshed in late September still plots September. Finding the last date with
data means evaluating the measure once per date, inside every item, for every
cell of every visual; the kit does not pay that by default.

### Relative-to-today items intersect the selection

`Last 30 Days` with days on the axis plots the last 30 days and nothing else,
which is what makes it usable on a chart. The cost: a card showing `Last 7 Days`
on a page sliced to last year is blank. To make one item ignore the date
selection, change its `KEEPFILTERS ( ... )` to `REMOVEFILTERS ( DateDimension ), ...`
in `scripts/build_kit.py` and rebuild.

## Wiring it to a fact table

Installing the tables changes nothing until a fact table is related to
`DateDimension[Date]`. Four things decided the first real install, on a report
whose KPIs had to follow an October fiscal year.

**A timestamp column joins on its date part.** Fact dates usually carry a time,
and a plain relationship matches none of them. Set `joinOnDateBehavior:
datePartOnly` on the relationship rather than adding a date-only column:

```
relationship <id>
	joinOnDateBehavior: datePartOnly
	fromColumn: Appointments.ScheduledStartDate
	toColumn: DateDimension.Date
```

Desktop writes this property only for its own auto date/time tables, but the
engine honours it on any relationship: 42,220 of 42,250 rows carrying a time
matched. The one that did not was dated in the year 7025.

**A calculation item reaches measures, not expressions.**
`CALCULATE ( COUNTROWS ( Fact ), 'Time Window'[Window] = "FYTD" )` returns the
unwindowed count without complaint, because `COUNTROWS` is not a measure. Write
the base measure first, then window it:

```dax
Completed = CALCULATE ( COUNTROWS ( Fact ), KEEPFILTERS ( Fact[Status] = "Completed" ) )
Completed FYTD = CALCULATE ( [Completed], 'Time Window'[Window] = "FYTD" )
```

**Two date roles, one active relationship.** Make active the role the report's
implicit aggregations already use, since a column count cannot ask for another
relationship. Measures on the other role name it with `USERELATIONSHIP` inside
the base measure; the window then arrives through whichever relationship the
measure activated.

**Commit before turning auto date/time off.** A visual whose axis is a column's
built-in `Date Hierarchy` does not break when the switch is made. Desktop
quietly flattens the axis to the raw date column, and the levels, and which of
them were switched on, are gone from the file. Four bar charts here went from
Year / Month / Day to one timestamp per bar.

Search the report for `PropertyVariationSource` first, and commit, so the
designed axis can be read back from the commit and rebuilt on `DateDimension`
level for level. Two of those four charts had Year switched on and two did not;
a rebuild from memory would have made them all the same.

Let Desktop make the switch rather than editing the files. It removes its own
hidden tables, their relationships and the column variations in one pass, and
it is the authority on all three.

### Testing a date that has not happened

`install_kit.py --as-of 2026-10-01` pins the model's "today", so the first day
of a fiscal year can be checked in September without touching the machine clock.
Any install without the flag clears it, because a model published with it set
shows the same day forever.

Pin a date inside the data as well as the one being asked about. On a boundary
the data has not reached, zero from the rule and zero from there being no rows
look the same. Moving the fiscal start to a month the data does cover is what
separated them: 505 under the old logic, 0 under the rule.

`Offset = 0` is true for a blank. A lookup that finds no date returns blank, and
`_month = 0` then flags every undated row as this month. Use `==`.

## Using it on a visual

- **Trend:** a `DateDimension` column on the axis, a measure on the values,
  `Window` on a single-select slicer.
- **Windows side by side:** `Window` on the axis or legend with no date column.
  One bar per item; a column chart or matrix, not a line.
- **Single-select.** With two items selected the engine skips the calculation
  group and the measure comes back unchanged. That can be changed for the group
  as a whole with a selection expression, which needs compatibility level 1605.
  A model below that level would refuse the table, so the kit does not set one.
- **Fiscal visuals use `Fiscal Month Name`,** which sorts July to June.
  `MonthName` holds the same text and sorts January to December, and a column
  can have only one sort key.

## Changing the kit

The TMDL is generated. `scripts/build_kit.py` holds the column list and the item
definitions; `assets/DateDimension.pq` holds the query.

```bash
python scripts/build_kit.py
```

Nineteen of the 44 items share their opening variables, so a change to the
clipping rule is one edit there and nineteen by hand. A new column is declared
three times — the query's record, the query's schema, `COLS` — and the build
refuses when the last two disagree.

Do not edit the `.tmdl` files directly. The next build overwrites them, and the
edit is lost without a diff to show it went.

## Verify

`compilecheck` proves the M compiles. It does not prove a window resolves to the
right dates, and nothing short of running it does.

A measure over the date table itself is the cheapest honest test, because its
answer is countable by hand. With the model open and refreshed in Desktop, run
this in DAX query view or through the modeling MCP:

```dax
DEFINE
    MEASURE DateDimension[Days] = COUNTROWS ( DateDimension )
    MEASURE DateDimension[From] = MIN ( DateDimension[Date] )
    MEASURE DateDimension[To]   = MAX ( DateDimension[Date] )
EVALUATE
    CALCULATETABLE (
        SUMMARIZECOLUMNS ( 'Time Window'[Window], "Days", [Days], "From", [From], "To", [To] ),
        DateDimension[YYYYMM_sort] = 202502
    )
```

`From` and `To` are the window's edges; `Days` catches an off-by-one that the
edges hide. February of a year after a leap year is the selection to use — it
is where `Rolling 12M` once returned 366 days, starting on 29 February instead
of 1 March.

Keep `From` and `To` as dates. Formatted as text they make the change items
subtract strings, and the query fails on the test's own measures rather than on
anything under test.

Test under at least: no selection, a month containing today, a past month, a
single day, and a month wholly in the future. The last was missing from the
first round of tests, which is how a YTD line that ran flat to December got as
far as being handed over.
