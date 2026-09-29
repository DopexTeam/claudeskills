"""Regenerate the kit's TMDL from its two sources of truth.

    python build_kit.py

Reads   ../assets/DateDimension.pq     the query
        COLS, HIERARCHIES, ITEMS       below
Writes  ../assets/DateDimension.tmdl   the table
        ../assets/Time Window.tmdl     the calculation group
        ../assets/install.tmdl         both, as a createOrReplace script for TMDL view
        ../references/columns.md       the column list, so it cannot drift from COLS

Why the TMDL is generated rather than edited
--------------------------------------------
The 44 calculation items are a few shapes repeated. Nineteen of them share the
same two opening variables, and the rule those variables encode -- clip the
selection to today, return blank when nothing is left -- is the thing most
likely to need changing. Edited by hand it has to be changed in nineteen places
and will be changed in eighteen.

The table has the same property in a milder form: a column is declared in the
query's record, in the query's schema, and in the TMDL. COLS is the TMDL third.
Adding a column means touching DateDimension.pq twice and COLS once, then
running this.

Desktop writes CRLF, and powerbi-desktop-engine's mbody.py splits on it, so the
output is CRLF. LF output compiles nowhere: compilecheck finds no M and refuses
to report a pass.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
T = "\t"
D = "DateDimension"

# ---------------------------------------------------------------- columns
# (name, type, folder, sortBy, hidden, description)
COLS = [
    ("Date", "date", None, None, False, "One row per calendar day. Relate fact tables to this column."),
    ("DateKey", "int", None, None, False, "Integer key in yyyymmdd form."),
    # Day
    ("Day", "int", "Day", None, False, "Day of the month, 1-31."),
    ("DaySuffix", "text", "Day", None, False, "Ordinal suffix for the day: st, nd, rd or th."),
    ("Weekday", "int", "Day", None, False, "Day of the week as a number, 0 = the configured first day of the week."),
    ("WeekDayName", "text", "Day", "Weekday", False, "Full day name."),
    ("WeekDayNameShort", "text", "Day", "Weekday", False, "Three-letter day name."),
    ("DowInMonth", "int", "Day", None, False, "Which occurrence of this weekday in the month, e.g. 3 for the third Monday."),
    ("DayOfQuarter", "int", "Day", None, False, "Day number within the calendar quarter."),
    ("DayOfYear", "int", "Day", None, False, "Day number within the calendar year."),
    ("IsWeekend", "bool", "Day", None, False, "True on the configured weekend days."),
    ("IsHoliday", "bool", "Day", None, False, "True on a holiday or its observed day."),
    ("HolidayText", "text", "Day", None, False, "Holiday name, blank on other days."),
    ("IsWorkday", "bool", "Day", None, False, "True when the day is neither a weekend day nor a holiday."),
    # Week
    ("WeekOfMonth", "int", "Week", None, False, "Week number within the month."),
    ("WeekOfYear", "int", "Week", None, False, "Week number within the year, using the configured first day of the week."),
    ("Start of Week", "date", "Week", None, False, "First day of the week this date falls in."),
    ("End of Week", "date", "Week", None, False, "Last day of the week this date falls in (week ending)."),
    ("ISOWeekOfYear", "int", "Week", None, False, "ISO 8601 week number."),
    ("ISOYear", "int", "Week", None, False, "ISO 8601 year the week belongs to."),
    ("ISOWeekLabel", "text", "Week", "ISOWeek_sort", False, "ISO week label, e.g. 2026-W40."),
    ("ISOWeek_sort", "int", "Week", None, True, "Sort key for ISOWeekLabel."),
    # Month
    ("Month", "int", "Month", None, False, "Month number, 1-12."),
    ("MonthName", "text", "Month", "Month", False, "Full month name."),
    ("MonthNameShort", "text", "Month", "Month", False, "Three-letter month name."),
    ("MonthYear", "text", "Month", "YYYYMM_sort", False, "Month and year without a space, e.g. Sep2026."),
    ("Month Year", "text", "Month", "YYYYMM_sort", False, "Month and year, e.g. Sep 2026."),
    ("MMYYYY", "text", "Month", "YYYYMM_sort", False, "Month and year as digits, e.g. 092026."),
    ("YearMonth", "text", "Month", "YYYYMM_sort", False, "Year and month, e.g. 2026-09."),
    ("YYYYMM_sort", "int", "Month", None, True, "Sort key for month-and-year labels."),
    ("Days in Month", "int", "Month", None, False, "Number of days in the month."),
    ("FirstDayOfMonth", "date", "Month", None, False, "First day of the month."),
    ("LastDayOfMonth", "date", "Month", None, False, "Last day of the month."),
    ("FirstDayOfNextMonth", "date", "Month", None, False, "First day of the following month."),
    # Quarter
    ("Quarter", "int", "Quarter", None, False, "Calendar quarter number, 1-4."),
    ("QuarterName", "text", "Quarter", "Quarter", False, "Calendar quarter label, e.g. Q3."),
    ("YearQuarter", "text", "Quarter", "YYYYQ_sort", False, "Year and quarter, e.g. 2026 Q3."),
    ("YYYYQ_sort", "int", "Quarter", None, True, "Sort key for YearQuarter."),
    ("FirstDayOfQuarter", "date", "Quarter", None, False, "First day of the calendar quarter."),
    ("LastDayOfQuarter", "date", "Quarter", None, False, "Last day of the calendar quarter."),
    # Year
    ("Year", "int", "Year", None, False, "Calendar year."),
    ("FirstDayofYear", "date", "Year", None, False, "First day of the calendar year."),
    ("LastDayOfYear", "date", "Year", None, False, "Last day of the calendar year."),
    ("FirstDayofNextYear", "date", "Year", None, False, "First day of the following calendar year."),
    # Fiscal
    ("Fiscal Year", "int", "Fiscal", None, False, "Fiscal year, named for the calendar year it ends in."),
    ("Fiscal Quarter", "int", "Fiscal", None, False, "Fiscal quarter number, 1-4."),
    ("Fiscal Month", "int", "Fiscal", None, False, "Fiscal month number, 1-12."),
    ("Fiscal Month Name", "text", "Fiscal", "Fiscal Month", False, "Month name that sorts in fiscal-year order. Use in place of MonthName on fiscal visuals."),
    ("Fiscal Year Label", "text", "Fiscal", "Fiscal Year", False, "Fiscal year label, e.g. FY2026."),
    ("Fiscal Quarter Name", "text", "Fiscal", "Fiscal Quarter", False, "Fiscal quarter label, e.g. FQ3."),
    ("Fiscal Year Quarter", "text", "Fiscal", "FiscalYYYYQ_sort", False, "Fiscal year and quarter, e.g. FY2026 FQ3."),
    ("Fiscal Period", "text", "Fiscal", "FiscalYYYYMM_sort", False, "Fiscal year and month, e.g. FY2026 P09."),
    ("FiscalYYYYQ_sort", "int", "Fiscal", None, True, "Sort key for Fiscal Year Quarter."),
    ("FiscalYYYYMM_sort", "int", "Fiscal", None, True, "Sort key for Fiscal Period."),
    ("FirstDayOfFiscalYear", "date", "Fiscal", None, False, "First day of the fiscal year."),
    ("LastDayOfFiscalYear", "date", "Fiscal", None, False, "Last day of the fiscal year."),
    # Relative
    ("Day Offset", "int", "Relative to today", None, False, "Days from today: 0 = today, -1 = yesterday, 1 = tomorrow. Recomputed on refresh."),
    ("Week Offset", "int", "Relative to today", None, False, "Weeks from the current week: 0 = this week, -1 = last week."),
    ("Month Offset", "int", "Relative to today", None, False, "Months from the current month: 0 = this month, -1 = last month."),
    ("Quarter Offset", "int", "Relative to today", None, False, "Quarters from the current quarter."),
    ("Year Offset", "int", "Relative to today", None, False, "Years from the current year."),
    ("Fiscal Quarter Offset", "int", "Relative to today", None, False, "Fiscal quarters from the current fiscal quarter."),
    ("Fiscal Year Offset", "int", "Relative to today", None, False, "Fiscal years from the current fiscal year."),
    ("IsFuture", "bool", "Relative to today", None, False, "True for dates after today."),
    ("IsMTD", "bool", "Relative to today", None, False, "True when the day of the month is on or before today's. Filters every month to the same point for like-for-like comparison."),
    ("IsQTD", "bool", "Relative to today", None, False, "True when the position in the quarter is on or before today's position in the current quarter."),
    ("IsYTD", "bool", "Relative to today", None, False, "True when the month and day are on or before today's. Filters every year to the same point."),
    ("IsFYTD", "bool", "Relative to today", None, False, "True when the position in the fiscal year is on or before today's."),
]

HIERARCHIES = [
    ("Calendar", [("Year", "Year"), ("Quarter", "QuarterName"), ("Month", "MonthName"), ("Date", "Date")]),
    ("Fiscal", [("Fiscal Year", "Fiscal Year Label"), ("Fiscal Quarter", "Fiscal Quarter Name"), ("Fiscal Period", "Fiscal Period"), ("Date", "Date")]),
    ("ISO Week", [("ISO Year", "ISOYear"), ("ISO Week", "ISOWeekLabel"), ("Date", "Date")]),
]

# ---------------------------------------------------------- calc items
# _end is the last selected date that is not in the future. It is blank when the
# whole selection is in the future, and every windowed item returns blank then.
# It filters Day Offset rather than comparing against TODAY() so that "today"
# has one definition, set by the query's UtcOffsetHours, not two.
HEAD = f"""VAR _min = MIN ( {D}[Date] )
VAR _end = CALCULATE ( MAX ( {D}[Date] ), KEEPFILTERS ( {D}[Day Offset] <= 0 ) )"""

PY_HEAD = HEAD + """
VAR _pyEnd = IF ( _end = EOMONTH ( _end, 0 ), EOMONTH ( _end, -12 ), EDATE ( _end, -12 ) )"""


def window(start, end, op=">="):
    return ("RETURN\n    IF (\n        NOT ISBLANK ( _end ),\n        CALCULATE (\n            SELECTEDMEASURE (),\n"
            f"            REMOVEFILTERS ( {D} ),\n"
            f"            {D}[Date] {op} {start} && {D}[Date] <= {end}\n        )\n    )")


def lookup(col, at):
    return f"CALCULATE ( MAX ( {D}[{col}] ), REMOVEFILTERS ( {D} ), {D}[Date] = {at} )"


def to_date(start_expr):
    return f"{HEAD}\nVAR _start = {start_expr}\n" + window("_start", "_end")


def rolling(start_expr):
    return f"{HEAD}\nVAR _start = {start_expr}\n" + window("_start", "_end", ">")


def rolling_months(n):
    # A window ending on a month-end covers whole months, so it starts after the
    # earlier month-end. EDATE alone gave Rolling 12M for Feb 2025 a 366th day.
    return rolling(f"IF ( _end = EOMONTH ( _end, 0 ), EOMONTH ( _end, -{n} ), EDATE ( _end, -{n} ) )")


def shifted(months):
    return (f"{HEAD}\n"
            f"VAR _wholeMonths = DAY ( _min ) = 1 && _end = EOMONTH ( _end, 0 )\n"
            f"VAR _priorStart = EDATE ( _min, {months} )\n"
            f"VAR _priorEnd = IF ( _wholeMonths, EOMONTH ( _end, {months} ), EDATE ( _end, {months} ) )\n"
            + window("_priorStart", "_priorEnd"))


def py_to_date(start_expr):
    return f"{PY_HEAD}\nVAR _start = {start_expr}\n" + window("_start", "_pyEnd")


def item(name):
    return f"CALCULATE ( SELECTEDMEASURE (), 'Time Window'[Window] = \"{name}\" )"


# The selection without its future dates, so both sides of a comparison cover
# the same span.
ELAPSED = f"CALCULATE ( SELECTEDMEASURE (), KEEPFILTERS ( {D}[Day Offset] <= 0 ) )"

# A slicer on Window reaches every measure on the page, including the text
# measures behind dynamic titles. Arithmetic on one is a visual-breaking error,
# so the change items hand text back untouched.
TEXT_GUARD = ("VAR _measure = SELECTEDMEASURE ()\n"
              "VAR _current = {c}\nVAR _prior = {p}\n"
              "VAR _isText = ISTEXT ( _measure ) || ISTEXT ( _current ) || ISTEXT ( _prior )\n"
              "RETURN\n    IF (\n        _isText,\n        _measure,\n        {math}\n    )")


def delta(cur, prior):
    return TEXT_GUARD.format(
        c=ELAPSED if cur is None else item(cur), p=item(prior),
        math="IF ( NOT ISBLANK ( _current ) && NOT ISBLANK ( _prior ), _current - _prior )")


def pct(cur, prior):
    return TEXT_GUARD.format(
        c=ELAPSED if cur is None else item(cur), p=item(prior),
        math="IF ( NOT ISBLANK ( _current ), DIVIDE ( _current - _prior, _prior ) )")


def offset(col, lo, hi=None):
    cond = f"{D}[{col}] = {lo}" if hi is None else f"{D}[{col}] >= {lo} && {D}[{col}] <= {hi}"
    return f"CALCULATE ( SELECTEDMEASURE (), KEEPFILTERS ( {cond} ) )"


PCT = 'IF ( ISTEXT ( SELECTEDMEASURE () ), SELECTEDMEASUREFORMATSTRING (), "0.0%;-0.0%;0.0%" )'
TO_DATE = "Ends on the last selected date that is not in the future. Blank when every selected date is in the future."
PRIOR = "Future dates in the selection are left out first, so a period in progress is compared with the same span. Blank when every selected date is in the future."
FIXED = "Applied within the dates selected, so on a date axis only the points inside the window show."

ITEMS = [
    # name, description, dax, format
    ("Current", "The measure as it is, under the dates selected.", "SELECTEDMEASURE ()", None),

    ("WTD", "Week to date. " + TO_DATE, to_date(lookup("Start of Week", "_end")), None),
    ("MTD", "Month to date. " + TO_DATE, to_date("EOMONTH ( _end, -1 ) + 1"), None),
    ("QTD", "Quarter to date. " + TO_DATE, to_date(lookup("FirstDayOfQuarter", "_end")), None),
    ("YTD", "Year to date. " + TO_DATE, to_date("DATE ( YEAR ( _end ), 1, 1 )"), None),
    ("FYTD", "Fiscal year to date, using the fiscal year configured in DateDimension. " + TO_DATE,
     to_date(lookup("FirstDayOfFiscalYear", "_end")), None),

    ("Rolling 7D", "The 7 days up to and including the end date. " + TO_DATE, rolling("_end - 7"), None),
    ("Rolling 30D", "The 30 days up to and including the end date. " + TO_DATE, rolling("_end - 30"), None),
    ("Rolling 90D", "The 90 days up to and including the end date. " + TO_DATE, rolling("_end - 90"), None),
    ("Rolling 3M", "The 3 months up to and including the end date. " + TO_DATE, rolling_months(3), None),
    ("Rolling 12M", "The 12 months up to and including the end date. " + TO_DATE, rolling_months(12), None),

    ("Prior Period", "The period of the same length immediately before the selected dates. " + PRIOR,
     f"{HEAD}\nVAR _days = INT ( _end - _min ) + 1\nVAR _priorStart = _min - _days\nVAR _priorEnd = _min - 1\n"
     + window("_priorStart", "_priorEnd"), None),
    ("PW", "The selected dates moved back 7 days. " + PRIOR,
     f"{HEAD}\nVAR _priorStart = _min - 7\nVAR _priorEnd = _end - 7\n" + window("_priorStart", "_priorEnd"), None),
    ("PM", "The selected dates moved back one month. Whole months stay whole months. " + PRIOR, shifted(-1), None),
    ("PQ", "The selected dates moved back one quarter. Whole months stay whole months. " + PRIOR, shifted(-3), None),
    ("PY", "The selected dates moved back one year. Whole months stay whole months. " + PRIOR, shifted(-12), None),

    ("PY MTD", "Month to date as it stood one year before the end date.", py_to_date("EOMONTH ( _pyEnd, -1 ) + 1"), None),
    ("PY QTD", "Quarter to date as it stood one year before the end date.", py_to_date(lookup("FirstDayOfQuarter", "_pyEnd")), None),
    ("PY YTD", "Year to date as it stood one year before the end date.", py_to_date("DATE ( YEAR ( _pyEnd ), 1, 1 )"), None),
    ("PY FYTD", "Fiscal year to date as it stood one year before the end date.", py_to_date(lookup("FirstDayOfFiscalYear", "_pyEnd")), None),

    ("PoP", "Change from the prior period of the same length.", delta(None, "Prior Period"), None),
    ("PoP %", "Percentage change from the prior period of the same length.", pct(None, "Prior Period"), PCT),
    ("MoM", "Change from the same dates one month earlier.", delta(None, "PM"), None),
    ("MoM %", "Percentage change from the same dates one month earlier.", pct(None, "PM"), PCT),
    ("YoY", "Change from the same dates one year earlier.", delta(None, "PY"), None),
    ("YoY %", "Percentage change from the same dates one year earlier.", pct(None, "PY"), PCT),
    ("YTD YoY", "Change in year to date from the same point one year earlier.", delta("YTD", "PY YTD"), None),
    ("YTD YoY %", "Percentage change in year to date from the same point one year earlier.", pct("YTD", "PY YTD"), PCT),

    ("Today", "Today only. " + FIXED, offset("Day Offset", 0), None),
    ("Yesterday", "Yesterday only. " + FIXED, offset("Day Offset", -1), None),
    ("Last 7 Days", "Today and the 6 days before it. " + FIXED, offset("Day Offset", -6, 0), None),
    ("Last 30 Days", "Today and the 29 days before it. " + FIXED, offset("Day Offset", -29, 0), None),
    ("Last 90 Days", "Today and the 89 days before it. " + FIXED, offset("Day Offset", -89, 0), None),
    ("This Week", "The whole current week. " + FIXED, offset("Week Offset", 0), None),
    ("Last Week", "The whole previous week. " + FIXED, offset("Week Offset", -1), None),
    ("This Month", "The whole current month. " + FIXED, offset("Month Offset", 0), None),
    ("Last Month", "The whole previous month. " + FIXED, offset("Month Offset", -1), None),
    ("This Quarter", "The whole current quarter. " + FIXED, offset("Quarter Offset", 0), None),
    ("Last Quarter", "The whole previous quarter. " + FIXED, offset("Quarter Offset", -1), None),
    ("This Year", "The whole current year. " + FIXED, offset("Year Offset", 0), None),
    ("Last Year", "The whole previous year. " + FIXED, offset("Year Offset", -1), None),
    ("This Fiscal Year", "The whole current fiscal year. " + FIXED, offset("Fiscal Year Offset", 0), None),
    ("Next 7 Days", "The 7 days after today. " + FIXED, offset("Day Offset", 1, 7), None),
    ("Next 30 Days", "The 30 days after today. " + FIXED, offset("Day Offset", 1, 30), None),
]


# ------------------------------------------------------------- emitters
def q(name):
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


def indent(text, n):
    return "\n".join((T * n + line) if line.strip() else "" for line in text.split("\n"))


def date_table(m_text):
    out = ["/// Generated date dimension. Configure it at the top of the partition's M query.",
           f"table {D}", T + "dataCategory: Time", ""]
    for name, typ, folder, sort, hidden, desc in COLS:
        out.append(T + "/// " + desc)
        out.append(T + "column " + q(name))
        out.append(T * 2 + "dataType: " + {"date": "dateTime", "int": "int64", "text": "string", "bool": "boolean"}[typ])
        if name == "Date":
            out.append(T * 2 + "isKey")
        if hidden:
            out.append(T * 2 + "isHidden")
        if typ == "date":
            out.append(T * 2 + "formatString: Short Date")
        elif typ == "int":
            out.append(T * 2 + "formatString: 0")
        elif typ == "bool":
            out.append(T * 2 + 'formatString: """TRUE"";""TRUE"";""FALSE"""')
        if folder:
            out.append(T * 2 + "displayFolder: " + folder)
        out.append(T * 2 + "summarizeBy: none")
        out.append(T * 2 + "sourceColumn: " + name)
        if sort:
            out.append(T * 2 + "sortByColumn: " + q(sort))
        out.append("")
        out.append(T * 2 + "annotation SummarizationSetBy = User")
        if typ == "date":
            out.append("")
            out.append(T * 2 + "annotation UnderlyingDateTimeDataType = Date")
        out.append("")
    for hname, levels in HIERARCHIES:
        out.append(T + "hierarchy " + q(hname))
        out.append("")
        for lname, col in levels:
            out.append(T * 2 + "level " + q(lname))
            out.append(T * 3 + "column: " + q(col))
            out.append("")
    out.append(T + f"partition {D} = m")
    out.append(T * 2 + "mode: import")
    out.append(T * 2 + "source = ```")
    out.append(indent(m_text.rstrip("\n"), 4))
    out.append(T * 4 + "```")
    out.append("")
    out.append(T + "annotation PBI_ResultType = Table")
    out.append("")
    return "\n".join(out)


def calc_group():
    out = ["/// Date windows to apply to any measure. Put Window on a slicer, or on the columns or legend of a visual.",
           "table 'Time Window'", "", T + "calculationGroup", T * 2 + "precedence: 10", ""]
    for i, (name, desc, dax, fmt) in enumerate(ITEMS):
        out.append(T * 2 + "/// " + desc)
        if "\n" in dax:
            out.append(T * 2 + f"calculationItem {q(name)} =")
            out.append(indent(dax, 4))
        else:
            out.append(T * 2 + f"calculationItem {q(name)} = {dax}")
        out.append(T * 3 + f"ordinal: {i}")
        if fmt:
            out.append("")
            out.append(T * 3 + f"formatStringDefinition = {fmt}")
        out.append("")
    out += [T + "column Window", T * 2 + "dataType: string", T * 2 + "summarizeBy: none",
            T * 2 + "sourceColumn: Name", T * 2 + "sortByColumn: Ordinal", "",
            T * 2 + "annotation SummarizationSetBy = Automatic", "",
            T + "column Ordinal", T * 2 + "dataType: int64", T * 2 + "isHidden", T * 2 + "formatString: 0",
            T * 2 + "summarizeBy: none", T * 2 + "sourceColumn: Ordinal", "",
            T * 2 + "annotation SummarizationSetBy = User", ""]
    return "\n".join(out)


COLUMNS_MD = """# DateDimension: settings and columns

The column table below is generated from `scripts/build_kit.py`. Edit it there.

## Settings

At the top of the query, between `// ---- Configuration` and `// ---- Anchors`.
`install_kit.py` sets the first three and the last from the command line. On a
reinstall it carries every setting over except `AsOfDate`, which it clears.

| Setting | Default | Meaning |
|---|---|---|
| `StartOfFiscalYear` | 1 | Month the fiscal year starts. The fiscal year is named for the year it ends in: a July start puts 1 July 2026 in FY2027. |
| `FirstDayOfWeek` | `Day.Monday` | Drives week numbers, week start and end, `Weekday` and `Week Offset`. |
| `UtcOffsetHours` | null | null uses the clock of the machine that refreshes. The Service runs in UTC, so set this to keep "today" local. It does not follow daylight saving. |
| `FromYear` | 2000 | First year, from 1 January. |
| `ToYear` | null | Last year, to 31 December. null means the current year plus `YearsAhead`, so the table never runs out. |
| `YearsAhead` | 5 | Used when `ToYear` is null. |
| `WeekendDays` | Saturday, Sunday | Drives `IsWeekend` and `IsWorkday`. |
| `Culture` | en-US | Language of day and month names. |
| `HolidayCalendar` | US Federal | Or "None". |
| `ObserveHolidays` | true | A Saturday holiday also marks the Friday; a Sunday holiday also marks the Monday. |
| `ExtraHolidays` | empty | Your own dates and names. A date already in the calendar gets both names. |
| `AsOfDate` | null | Testing only. Pins "today" to a fixed date so a future day can be checked now. `install_kit.py --as-of` sets it, and any install without that flag clears it. Never publish with it set. |

## What changed from the script the reports had

All 40 of its column names are kept. Only `Date` and `WeekDayName` were
referenced by any report or measure, which is what made the rest safe to fix.

| Column | Was | Now |
|---|---|---|
| `IsWeekend` | Text. Marked **Friday and Saturday**: `Date.DayOfWeek([Date]) >= 5` with no first-day argument counts from the culture's first day, which in en-US is Sunday. | True/false. Marks the configured weekend days. |
| `Isholidy` | Text, always "False". | Renamed `IsHoliday`. True/false, from the holiday calendar. |
| `HolidayText` | Always empty. | Holiday name. |
| `DowInMonth` | Always 0. | Occurrence of the weekday in the month. |
| `DateKey` | Text. | Whole number. |
| `YYYYMM_sort` | Visible. | Hidden; a sort key. |
| `MonthName`, `MonthYear`, `MMYYYY`, `QuarterName` | Sorted alphabetically. | Sorted in calendar order. |
| range | Fixed, 2000 to 2030. | 2000 to the current year plus five. |

## Dates are stored as datetimes at midnight

The query types them `date` and the table marks them date-only, but the engine
has one underlying type. A fact column with a time portion matches no row of
`DateDimension[Date]`. Relate on a date-only column.

## Like-for-like flags

`IsMTD`, `IsQTD`, `IsYTD` and `IsFYTD` cut every period off at today's position
in it. Filter `IsYTD = TRUE` and every year shows 1 January to today's month and
day. They compare month-and-day rather than day-of-year, so a leap year does not
shift the cut by a day.

## Columns

| Column | Type | Folder | Sorted by | Description |
|---|---|---|---|---|
%(rows)s

## Hierarchies

| Hierarchy | Levels |
|---|---|
%(hier)s
"""


def columns_md():
    kinds = {"date": "date", "int": "whole number", "text": "text", "bool": "true/false"}
    rows = "\n".join("| `%s`%s | %s | %s | %s | %s |" % (
        n, " (hidden)" if h else "", kinds[t], f or "", ("`%s`" % s) if s else "", d)
        for n, t, f, s, h, d in COLS)
    hier = "\n".join("| %s | %s |" % (n, " → ".join("%s (`%s`)" % lv for lv in levels))
                     for n, levels in HIERARCHIES)
    return COLUMNS_MD % {"rows": rows, "hier": hier}


def write(name, text, folder=ASSETS, newline="\r\n"):
    with open(os.path.join(folder, name), "w", encoding="utf-8", newline=newline) as fh:
        fh.write(text.replace("\r\n", "\n"))


def check_query_matches(m_text):
    """COLS and the query's schema are the same list written twice. Say so when they drift."""
    import re
    schema = m_text[m_text.index("Schema = type table ["):]
    schema = schema[:schema.index("],")]
    in_query = re.findall(r'(?:#"([^"]+)"|\b([A-Za-z_]\w*))\s*=\s*(?:nullable\s+)?(?:date|text|logical|Int64\.Type)', schema)
    in_query = [a or b for a, b in in_query]
    in_cols = [c[0] for c in COLS]
    missing = [c for c in in_query if c not in in_cols]
    extra = [c for c in in_cols if c not in in_query]
    if missing or extra:
        raise SystemExit("COLS and DateDimension.pq disagree.\n  in the query only: %s\n  in COLS only:      %s"
                         % (missing or "-", extra or "-"))


if __name__ == "__main__":
    with open(os.path.join(ASSETS, "DateDimension.pq"), encoding="utf-8") as fh:
        m = fh.read()
    check_query_matches(m)
    dt, cg = date_table(m), calc_group()
    write("DateDimension.tmdl", dt)
    write("Time Window.tmdl", cg)
    write("install.tmdl", "createOrReplace\n\n" + indent(dt, 1) + "\n\n" + indent(cg, 1) + "\n")
    refs = os.path.join(HERE, "..", "references")
    os.makedirs(refs, exist_ok=True)
    write("columns.md", columns_md(), folder=refs, newline="\n")
    print("%d columns, %d hierarchies, %d calculation items" % (len(COLS), len(HIERARCHIES), len(ITEMS)))
