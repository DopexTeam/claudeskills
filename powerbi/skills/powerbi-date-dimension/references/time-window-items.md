# Time Window: what each item resolves to

The items are defined in `scripts/build_kit.py`. This file records what they
were measured to do, which the definitions alone do not show.

`_min` is the first selected date. `_end` is the last selected date that is not
in the future. The to-date, rolling and prior items are built from them, and
return blank when `_end` is blank. A change item is blank when the elapsed part
of the selection is. The relative-to-today items use neither.

## The items

| Group | Item | Dates |
|---|---|---|
| As is | `Current` | the selection, unchanged |
| To date | `WTD` | start of `_end`'s week → `_end` |
| | `MTD` | first of `_end`'s month → `_end` |
| | `QTD` | first of `_end`'s quarter → `_end` |
| | `YTD` | 1 January of `_end`'s year → `_end` |
| | `FYTD` | `FirstDayOfFiscalYear` at `_end` → `_end` |
| Rolling | `Rolling 7D`, `30D`, `90D` | the N days ending on `_end` |
| | `Rolling 3M`, `12M` | the N months ending on `_end`; whole months when `_end` is a month-end |
| Prior | `Prior Period` | the same number of days, ending the day before `_min` |
| | `PW` | `_min` − 7 → `_end` − 7 |
| | `PM`, `PQ`, `PY` | `_min` and `_end` moved back 1, 3, 12 months; a whole-month selection stays whole months |
| Prior to date | `PM MTD`, `PQ QTD` | the to-date window, ending one month or one quarter before `_end`; a month-end stays a month-end |
| | `PY MTD`, `PY QTD`, `PY YTD`, `PY FYTD` | the to-date window, ending one year before `_end` |
| Change | `PoP`, `MoM`, `QoQ`, `YoY` | the selection up to today, minus `Prior Period`, `PM`, `PQ`, `PY` |
| | `MTD MoM`, `QTD QoQ`, `YTD YoY`, `FYTD YoY` | `MTD` minus `PM MTD`, `QTD` minus `PQ QTD`, `YTD` minus `PY YTD`, `FYTD` minus `PY FYTD` |
| | each with `%` | the same, divided by the prior; formatted `0.0%` |
| Relative to today | `Today`, `Yesterday` | `Day Offset` 0, −1 |
| | `Last 7 / 30 / 90 Days` | `Day Offset` −(N−1) → 0, so today is included |
| | `Next 7 / 30 Days` | `Day Offset` 1 → N, so today is not |
| | `This / Last Week, Month, Quarter, Year` | the matching offset column = 0 or −1; whole periods |
| | `This Fiscal Year` | `Fiscal Year Offset` = 0 |

Offsets are compared with `==`, and the `Last N Days` ranges test for a blank
first. A fact row with no date sits on the blank row of the date table, where
every offset is blank, and a blank equals 0 under `=`.

To-date, rolling and prior items replace every filter on `DateDimension`,
including one on `WeekDayName` or `IsWorkday`. Relative-to-today items and the
current side of a change item keep them.

`Prior Period`, `PW`, `PM`, `PQ` and `PY` are blank when nothing on
`DateDimension` is filtered, and `PoP`, `MoM`, `QoQ` and `YoY` with them. The
to-date items and their changes need no selection: `_end` is then today.

Prior items treat a selection as one range from `_min` to `_end`. January and
March selected together are compared with a prior January-to-March.

## Measured

Counting rows of the date table, so every figure is checkable by hand. Monday
weeks, January fiscal year, on 28 September 2026.

### A past month: February 2025

| Item | Days | From | To |
|---|---|---|---|
| Current | 28 | 2025-02-01 | 2025-02-28 |
| WTD | 5 | 2025-02-24 | 2025-02-28 |
| YTD | 59 | 2025-01-01 | 2025-02-28 |
| Rolling 3M | 90 | 2024-12-01 | 2025-02-28 |
| Rolling 12M | 365 | 2024-03-01 | 2025-02-28 |
| Prior Period | 28 | 2025-01-04 | 2025-01-31 |
| PM | 31 | 2025-01-01 | 2025-01-31 |
| PQ | 30 | 2024-11-01 | 2024-11-30 |
| PY | 29 | 2024-02-01 | 2024-02-29 |
| PY YTD | 60 | 2024-01-01 | 2024-02-29 |

`PY` is 29 days: the whole of February 2024, not 28 days of it. `Rolling 12M`
is 365 and starts on 1 March. With `EDATE` alone it was 366 and started on 29
February — `EDATE` of a month-end lands on the same day number, which in a leap
year is not the month-end.

### The month in progress: September 2026

| Item | Days | From | To |
|---|---|---|---|
| Current | 30 | 2026-09-01 | 2026-09-30 |
| MTD | 28 | 2026-09-01 | 2026-09-28 |
| FYTD | 271 | 2026-01-01 | 2026-09-28 |
| Rolling 3M | 92 | 2026-06-29 | 2026-09-28 |
| Prior Period | 28 | 2026-08-04 | 2026-08-31 |
| PM | 28 | 2026-08-01 | 2026-08-28 |
| PY | 28 | 2025-09-01 | 2025-09-28 |
| This Week | 3 | 2026-09-28 | 2026-09-30 |
| Next 7 Days | 2 | 2026-09-29 | 2026-09-30 |

`PM` is 28 days, not August's 31: the selection is clipped to the 28th before
it is moved. `This Week` is 3 days because the week runs into October and the
selection does not.

### Days on the axis, across today

10 per day, fact rows on both sides of today.

| Date | Current | WTD | MTD | Rolling 7D | Last 7 Days | Yesterday | Next 7 Days |
|---|---|---|---|---|---|---|---|
| 09-26 | 10 | 60 | 260 | 70 | 10 | | |
| 09-27 | 10 | 70 | 270 | 70 | 10 | 10 | |
| 09-28 | 10 | 10 | 280 | 70 | 10 | | |
| 09-29 | 10 | | | | | | 10 |
| 09-30 | 10 | | | | | | 10 |

### A July fiscal year

| Selection | Item | Days | From | To |
|---|---|---|---|---|
| none | FYTD | 90 | 2026-07-01 | 2026-09-28 |
| none | PY FYTD | 90 | 2025-07-01 | 2025-09-28 |
| none | This Fiscal Year | 365 | 2026-07-01 | 2027-06-30 |
| February 2025 | FYTD | 243 | 2024-07-01 | 2025-02-28 |
| February 2025 | PY FYTD | 244 | 2023-07-01 | 2024-02-29 |

### An October fiscal year, on 29 September 2026

| Item | Days | From | To |
|---|---|---|---|
| FYTD | 364 | 2025-10-01 | 2026-09-29 |
| This Fiscal Year | 365 | 2025-10-01 | 2026-09-30 |
| Last Month | 31 | 2026-08-01 | 2026-08-31 |

Pinned to 1 October 2026, `FYTD` is that one day and `Last Month` is September.

### Text measures

A measure returning `"Showing Sep 2026"` came back unchanged under `MoM`,
`YoY %` and `PoP`. Under `YTD` it returned `"Showing Jan 2026"`: window items do
no arithmetic and so need no guard, but they do move the dates a title is
evaluated over.

### Two items selected

`'Time Window'[Window] IN { "YTD", "FYTD" }` returned the measure unchanged for
every month. The engine applies a calculation group only when one item is in
context.
