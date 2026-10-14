# DateDimension: settings and columns

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
| `Date` | date |  |  | One row per calendar day. Relate fact tables to this column. |
| `DateKey` | whole number |  |  | Integer key in yyyymmdd form. |
| `Day` | whole number | Day |  | Day of the month, 1-31. |
| `DaySuffix` | text | Day |  | Ordinal suffix for the day: st, nd, rd or th. |
| `Weekday` | whole number | Day |  | Day of the week as a number, 0 = the configured first day of the week. |
| `WeekDayName` | text | Day | `Weekday` | Full day name. |
| `WeekDayNameShort` | text | Day | `Weekday` | Three-letter day name. |
| `DowInMonth` | whole number | Day |  | Which occurrence of this weekday in the month, e.g. 3 for the third Monday. |
| `DayOfQuarter` | whole number | Day |  | Day number within the calendar quarter. |
| `DayOfYear` | whole number | Day |  | Day number within the calendar year. |
| `IsWeekend` | true/false | Day |  | True on the configured weekend days. |
| `IsHoliday` | true/false | Day |  | True on a holiday or its observed day. |
| `HolidayText` | text | Day |  | Holiday name, blank on other days. |
| `IsWorkday` | true/false | Day |  | True when the day is neither a weekend day nor a holiday. |
| `WeekOfMonth` | whole number | Week |  | Week number within the month. |
| `WeekOfYear` | whole number | Week |  | Week number within the year, using the configured first day of the week. |
| `Start of Week` | date | Week |  | First day of the week this date falls in. |
| `End of Week` | date | Week |  | Last day of the week this date falls in (week ending). |
| `ISOWeekOfYear` | whole number | Week |  | ISO 8601 week number. |
| `ISOYear` | whole number | Week |  | ISO 8601 year the week belongs to. |
| `ISOWeekLabel` | text | Week | `ISOWeek_sort` | ISO week label, e.g. 2026-W40. |
| `ISOWeek_sort` (hidden) | whole number | Week |  | Sort key for ISOWeekLabel. |
| `Month` | whole number | Month |  | Month number, 1-12. |
| `MonthName` | text | Month | `Month` | Full month name. |
| `MonthNameShort` | text | Month | `Month` | Three-letter month name. |
| `MonthYear` | text | Month | `YYYYMM_sort` | Month and year without a space, e.g. Sep2026. |
| `Month Year` | text | Month | `YYYYMM_sort` | Month and year, e.g. Sep 2026. |
| `MMYYYY` | text | Month | `YYYYMM_sort` | Month and year as digits, e.g. 092026. |
| `YearMonth` | text | Month | `YYYYMM_sort` | Year and month, e.g. 2026-09. |
| `YYYYMM_sort` (hidden) | whole number | Month |  | Sort key for month-and-year labels. |
| `Days in Month` | whole number | Month |  | Number of days in the month. |
| `FirstDayOfMonth` | date | Month |  | First day of the month. |
| `LastDayOfMonth` | date | Month |  | Last day of the month. |
| `FirstDayOfNextMonth` | date | Month |  | First day of the following month. |
| `Quarter` | whole number | Quarter |  | Calendar quarter number, 1-4. |
| `QuarterName` | text | Quarter | `Quarter` | Calendar quarter label, e.g. Q3. |
| `YearQuarter` | text | Quarter | `YYYYQ_sort` | Year and quarter, e.g. 2026 Q3. |
| `YYYYQ_sort` (hidden) | whole number | Quarter |  | Sort key for YearQuarter. |
| `FirstDayOfQuarter` | date | Quarter |  | First day of the calendar quarter. |
| `LastDayOfQuarter` | date | Quarter |  | Last day of the calendar quarter. |
| `Year` | whole number | Year |  | Calendar year. |
| `FirstDayofYear` | date | Year |  | First day of the calendar year. |
| `LastDayOfYear` | date | Year |  | Last day of the calendar year. |
| `FirstDayofNextYear` | date | Year |  | First day of the following calendar year. |
| `Fiscal Year` | whole number | Fiscal |  | Fiscal year, named for the calendar year it ends in. |
| `Fiscal Quarter` | whole number | Fiscal |  | Fiscal quarter number, 1-4. |
| `Fiscal Month` | whole number | Fiscal |  | Fiscal month number, 1-12. |
| `Fiscal Month Name` | text | Fiscal | `Fiscal Month` | Month name that sorts in fiscal-year order. Use in place of MonthName on fiscal visuals. |
| `Fiscal Year Label` | text | Fiscal | `Fiscal Year` | Fiscal year label, e.g. FY2026. |
| `Fiscal Quarter Name` | text | Fiscal | `Fiscal Quarter` | Fiscal quarter label, e.g. FQ3. |
| `Fiscal Year Quarter` | text | Fiscal | `FiscalYYYYQ_sort` | Fiscal year and quarter, e.g. FY2026 FQ3. |
| `Fiscal Period` | text | Fiscal | `FiscalYYYYMM_sort` | Fiscal year and month, e.g. FY2026 P09. |
| `FiscalYYYYQ_sort` (hidden) | whole number | Fiscal |  | Sort key for Fiscal Year Quarter. |
| `FiscalYYYYMM_sort` (hidden) | whole number | Fiscal |  | Sort key for Fiscal Period. |
| `FirstDayOfFiscalYear` | date | Fiscal |  | First day of the fiscal year. |
| `LastDayOfFiscalYear` | date | Fiscal |  | Last day of the fiscal year. |
| `Day Offset` | whole number | Relative to today |  | Days from today: 0 = today, -1 = yesterday, 1 = tomorrow. Recomputed on refresh. |
| `Week Offset` | whole number | Relative to today |  | Weeks from the current week: 0 = this week, -1 = last week. |
| `Month Offset` | whole number | Relative to today |  | Months from the current month: 0 = this month, -1 = last month. |
| `Quarter Offset` | whole number | Relative to today |  | Quarters from the current quarter. |
| `Year Offset` | whole number | Relative to today |  | Years from the current year. |
| `Fiscal Quarter Offset` | whole number | Relative to today |  | Fiscal quarters from the current fiscal quarter. |
| `Fiscal Year Offset` | whole number | Relative to today |  | Fiscal years from the current fiscal year. |
| `IsFuture` | true/false | Relative to today |  | True for dates after today. |
| `IsMTD` | true/false | Relative to today |  | True when the day of the month is on or before today's. Filters every month to the same point for like-for-like comparison. |
| `IsQTD` | true/false | Relative to today |  | True when the position in the quarter is on or before today's position in the current quarter. |
| `IsYTD` | true/false | Relative to today |  | True when the month and day are on or before today's. Filters every year to the same point. |
| `IsFYTD` | true/false | Relative to today |  | True when the position in the fiscal year is on or before today's. |

## Hierarchies

| Hierarchy | Levels |
|---|---|
| Calendar | Year (`Year`) → Quarter (`QuarterName`) → Month (`MonthName`) → Date (`Date`) |
| Fiscal | Fiscal Year (`Fiscal Year Label`) → Fiscal Quarter (`Fiscal Quarter Name`) → Fiscal Period (`Fiscal Period`) → Date (`Date`) |
| ISO Week | ISO Year (`ISOYear`) → ISO Week (`ISOWeekLabel`) → Date (`Date`) |
