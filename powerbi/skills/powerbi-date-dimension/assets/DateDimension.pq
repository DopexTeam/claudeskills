// DateDimension: portable, self-contained date dimension.
// No data source. Paste into a blank query, or use the TMDL table in this kit.
// Everything that varies between models is in the Configuration block.
let
    // ---- Configuration -------------------------------------------------
    FromYear          = 2000,            // first year, starts 1 January
    ToYear            = null,            // last year, ends 31 December; null = current year + YearsAhead
    YearsAhead        = 5,               // only used when ToYear is null
    StartOfFiscalYear = 1,               // month number the fiscal year starts in; fiscal year is named for the year it ends in
    FirstDayOfWeek    = Day.Monday,      // Day.Monday, Day.Sunday, ...
    WeekendDays       = {Day.Saturday, Day.Sunday},
    Culture           = "en-US",         // language of day and month names
    UtcOffsetHours    = null,            // null = clock of the machine that refreshes; e.g. -5 pins "today" to UTC-5 wherever the refresh runs
    HolidayCalendar   = "US Federal",    // "US Federal" or "None"
    ObserveHolidays   = true,            // Saturday holidays also mark the Friday, Sunday holidays the Monday
    ExtraHolidays     = #table(type table [Date = date, Holiday = text], {}),   // e.g. {{#date(2026, 11, 27), "Company Holiday"}}
    AsOfDate          = null,            // TESTING ONLY: a fixed "today", e.g. #date(2026, 10, 1). null = the real date. Never publish with this set.

    // ---- Anchors -------------------------------------------------------
    Today =
        if AsOfDate <> null then AsOfDate
        else if UtcOffsetHours = null
        then Date.From(DateTime.LocalNow())
        else Date.From(DateTimeZone.RemoveZone(DateTimeZone.SwitchZone(DateTimeZone.UtcNow(), UtcOffsetHours))),
    EndYear  = if ToYear = null then Date.Year(Today) + YearsAhead else ToYear,
    FromDate = #date(FromYear, 1, 1),
    ToDate   = #date(EndYear, 12, 31),
    Dates    = List.Dates(FromDate, Duration.Days(ToDate - FromDate) + 1, #duration(1, 0, 0, 0)),

    // ---- Fiscal helpers ------------------------------------------------
    FiscalShift   = Number.Mod(13 - StartOfFiscalYear, 12),
    FiscalBase    = (d as date) as date => Date.AddMonths(Date.StartOfMonth(d), FiscalShift),
    FiscalYearOf  = (d as date) as number => Date.Year(FiscalBase(d)),
    FiscalStartOf = (d as date) as date => Date.AddMonths(#date(FiscalYearOf(d), 1, 1), -FiscalShift),

    // ---- Position of "today", used by offsets and like-for-like flags --
    TodayYear          = Date.Year(Today),
    TodayMonth         = Date.Month(Today),
    TodayQuarter       = Date.QuarterOfYear(Today),
    TodayDay           = Date.Day(Today),
    TodayWeekStart     = Date.StartOfWeek(Today, FirstDayOfWeek),
    TodayFiscalYear    = FiscalYearOf(Today),
    TodayFiscalMonth   = Date.Month(FiscalBase(Today)),
    TodayFiscalQuarter = Date.QuarterOfYear(FiscalBase(Today)),
    MonthInQuarter     = (d as date) as number => Number.Mod(Date.Month(d) - 1, 3) + 1,

    // ---- Holidays ------------------------------------------------------
    // dow: 0 = Sunday ... 6 = Saturday
    NthWeekday = (y as number, m as number, dow as number, n as number) as date =>
        let
            first = #date(y, m, 1),
            shift = Number.Mod(dow - Date.DayOfWeek(first, Day.Sunday) + 7, 7)
        in
            Date.AddDays(first, shift + 7 * (n - 1)),
    LastWeekday = (y as number, m as number, dow as number) as date =>
        let
            last = Date.EndOfMonth(#date(y, m, 1)),
            back = Number.Mod(Date.DayOfWeek(last, Day.Sunday) - dow + 7, 7)
        in
            Date.AddDays(last, -back),
    UsFederal = (y as number) as list =>
        {
            {#date(y, 1, 1),          "New Year's Day"},
            {NthWeekday(y, 1, 1, 3),  "Martin Luther King Jr. Day"},
            {NthWeekday(y, 2, 1, 3),  "Presidents' Day"},
            {LastWeekday(y, 5, 1),    "Memorial Day"},
            {#date(y, 7, 4),          "Independence Day"},
            {NthWeekday(y, 9, 1, 1),  "Labor Day"},
            {NthWeekday(y, 10, 1, 2), "Columbus Day"},
            {#date(y, 11, 11),        "Veterans Day"},
            {NthWeekday(y, 11, 4, 4), "Thanksgiving Day"},
            {#date(y, 12, 25),        "Christmas Day"}
        }
        & (if y >= 2021 then {{#date(y, 6, 19), "Juneteenth"}} else {}),
    CalendarHolidays =
        if HolidayCalendar = "US Federal"
        then List.Combine(List.Transform({FromYear .. EndYear + 1}, UsFederal))
        else {},
    ActualHolidays = CalendarHolidays & Table.ToRows(Table.SelectColumns(ExtraHolidays, {"Date", "Holiday"})),
    ObservedHolidays =
        if ObserveHolidays
        then List.Combine(List.Transform(ActualHolidays, (h) =>
            let dow = Date.DayOfWeek(h{0}, Day.Sunday)
            in
                if dow = 6 then {{Date.AddDays(h{0}, -1), h{1} & " (Observed)"}}
                else if dow = 0 then {{Date.AddDays(h{0}, 1), h{1} & " (Observed)"}}
                else {}))
        else {},
    HolidayTable  = #table(type table [Date = date, Holiday = text], ActualHolidays & ObservedHolidays),
    HolidayByDate = Table.Group(HolidayTable, {"Date"}, {{"Holiday", each Text.Combine(List.Distinct([Holiday]), " / "), type text}}),
    KeyOf         = (d as date) as number => Date.Year(d) * 10000 + Date.Month(d) * 100 + Date.Day(d),
    KeyText       = (d as date) as text => Text.From(KeyOf(d), "en-US"),
    HolidayLookup = Record.FromList(HolidayByDate[Holiday], List.Transform(HolidayByDate[Date], KeyText)),

    // ---- One record per date -------------------------------------------
    Row = (d as date) as record =>
        let
            y   = Date.Year(d),
            m   = Date.Month(d),
            q   = Date.QuarterOfYear(d),
            dd  = Date.Day(d),
            fb  = FiscalBase(d),
            fy  = Date.Year(fb),
            fm  = Date.Month(fb),
            fq  = Date.QuarterOfYear(fb),
            fys = FiscalStartOf(d),
            isoThursday = Date.AddDays(d, 3 - Date.DayOfWeek(d, Day.Monday)),
            isoYear     = Date.Year(isoThursday),
            isoWeek     = Number.IntegerDivide(Date.DayOfYear(isoThursday) - 1, 7) + 1,
            holiday     = Record.FieldOrDefault(HolidayLookup, KeyText(d), null),
            isWeekend   = List.Contains(WeekendDays, Date.DayOfWeek(d, Day.Sunday)),
            two         = (n as number) as text => Text.PadStart(Text.From(n, "en-US"), 2, "0")
        in
            [
                // Keys
                Date    = d,
                DateKey = KeyOf(d),

                // Day
                Day              = dd,
                DaySuffix        = if dd >= 11 and dd <= 13 then "th" else {"th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"}{Number.Mod(dd, 10)},
                Weekday          = Date.DayOfWeek(d, FirstDayOfWeek),
                WeekDayName      = Date.DayOfWeekName(d, Culture),
                WeekDayNameShort = Date.ToText(d, "ddd", Culture),
                DowInMonth       = Number.IntegerDivide(dd - 1, 7) + 1,
                DayOfQuarter     = Duration.Days(d - Date.StartOfQuarter(d)) + 1,
                DayOfYear        = Date.DayOfYear(d),
                IsWeekend        = isWeekend,
                IsHoliday        = holiday <> null,
                HolidayText      = holiday,
                IsWorkday        = not isWeekend and holiday = null,

                // Week
                WeekOfMonth     = Date.WeekOfMonth(d, FirstDayOfWeek),
                WeekOfYear      = Date.WeekOfYear(d, FirstDayOfWeek),
                #"Start of Week" = Date.StartOfWeek(d, FirstDayOfWeek),
                #"End of Week"   = Date.EndOfWeek(d, FirstDayOfWeek),
                ISOWeekOfYear   = isoWeek,
                ISOYear         = isoYear,
                ISOWeekLabel    = Text.From(isoYear, "en-US") & "-W" & two(isoWeek),
                ISOWeek_sort    = isoYear * 100 + isoWeek,

                // Month
                Month               = m,
                MonthName           = Date.MonthName(d, Culture),
                MonthNameShort      = Date.ToText(d, "MMM", Culture),
                MonthYear           = Date.ToText(d, "MMMyyyy", Culture),
                #"Month Year"       = Date.ToText(d, "MMM yyyy", Culture),
                MMYYYY              = two(m) & Text.From(y, "en-US"),
                YearMonth           = Text.From(y, "en-US") & "-" & two(m),
                YYYYMM_sort         = y * 100 + m,
                #"Days in Month"    = Date.DaysInMonth(d),
                FirstDayOfMonth     = Date.StartOfMonth(d),
                LastDayOfMonth      = Date.EndOfMonth(d),
                FirstDayOfNextMonth = Date.StartOfMonth(Date.AddMonths(d, 1)),

                // Quarter
                Quarter           = q,
                QuarterName       = "Q" & Text.From(q, "en-US"),
                YearQuarter       = Text.From(y, "en-US") & " Q" & Text.From(q, "en-US"),
                YYYYQ_sort        = y * 10 + q,
                FirstDayOfQuarter = Date.StartOfQuarter(d),
                LastDayOfQuarter  = Date.EndOfQuarter(d),

                // Year
                Year               = y,
                FirstDayofYear     = Date.StartOfYear(d),
                LastDayOfYear      = Date.EndOfYear(d),
                FirstDayofNextYear = Date.StartOfYear(Date.AddYears(d, 1)),

                // Fiscal
                #"Fiscal Year"         = fy,
                #"Fiscal Quarter"      = fq,
                #"Fiscal Month"        = fm,
                #"Fiscal Month Name"   = Date.MonthName(d, Culture),
                #"Fiscal Year Label"   = "FY" & Text.From(fy, "en-US"),
                #"Fiscal Quarter Name" = "FQ" & Text.From(fq, "en-US"),
                #"Fiscal Year Quarter" = "FY" & Text.From(fy, "en-US") & " FQ" & Text.From(fq, "en-US"),
                #"Fiscal Period"       = "FY" & Text.From(fy, "en-US") & " P" & two(fm),
                FiscalYYYYQ_sort       = fy * 10 + fq,
                FiscalYYYYMM_sort      = fy * 100 + fm,
                FirstDayOfFiscalYear   = fys,
                LastDayOfFiscalYear    = Date.AddDays(Date.AddMonths(fys, 12), -1),

                // Relative to today (recomputed on every refresh)
                #"Day Offset"            = Duration.Days(d - Today),
                #"Week Offset"           = Number.IntegerDivide(Duration.Days(Date.StartOfWeek(d, FirstDayOfWeek) - TodayWeekStart), 7),
                #"Month Offset"          = (y - TodayYear) * 12 + (m - TodayMonth),
                #"Quarter Offset"        = (y - TodayYear) * 4 + (q - TodayQuarter),
                #"Year Offset"           = y - TodayYear,
                #"Fiscal Quarter Offset" = (fy - TodayFiscalYear) * 4 + (fq - TodayFiscalQuarter),
                #"Fiscal Year Offset"    = fy - TodayFiscalYear,
                IsFuture = d > Today,
                IsMTD    = dd <= TodayDay,
                IsQTD    = MonthInQuarter(d) * 100 + dd <= MonthInQuarter(Today) * 100 + TodayDay,
                IsYTD    = m * 100 + dd <= TodayMonth * 100 + TodayDay,
                IsFYTD   = fm * 100 + dd <= TodayFiscalMonth * 100 + TodayDay
            ],

    Schema = type table [
        Date = date, DateKey = Int64.Type,
        Day = Int64.Type, DaySuffix = text, Weekday = Int64.Type, WeekDayName = text, WeekDayNameShort = text,
        DowInMonth = Int64.Type, DayOfQuarter = Int64.Type, DayOfYear = Int64.Type,
        IsWeekend = logical, IsHoliday = logical, HolidayText = nullable text, IsWorkday = logical,
        WeekOfMonth = Int64.Type, WeekOfYear = Int64.Type, #"Start of Week" = date, #"End of Week" = date,
        ISOWeekOfYear = Int64.Type, ISOYear = Int64.Type, ISOWeekLabel = text, ISOWeek_sort = Int64.Type,
        Month = Int64.Type, MonthName = text, MonthNameShort = text, MonthYear = text, #"Month Year" = text,
        MMYYYY = text, YearMonth = text, YYYYMM_sort = Int64.Type, #"Days in Month" = Int64.Type,
        FirstDayOfMonth = date, LastDayOfMonth = date, FirstDayOfNextMonth = date,
        Quarter = Int64.Type, QuarterName = text, YearQuarter = text, YYYYQ_sort = Int64.Type,
        FirstDayOfQuarter = date, LastDayOfQuarter = date,
        Year = Int64.Type, FirstDayofYear = date, LastDayOfYear = date, FirstDayofNextYear = date,
        #"Fiscal Year" = Int64.Type, #"Fiscal Quarter" = Int64.Type, #"Fiscal Month" = Int64.Type,
        #"Fiscal Month Name" = text, #"Fiscal Year Label" = text, #"Fiscal Quarter Name" = text, #"Fiscal Year Quarter" = text, #"Fiscal Period" = text,
        FiscalYYYYQ_sort = Int64.Type, FiscalYYYYMM_sort = Int64.Type,
        FirstDayOfFiscalYear = date, LastDayOfFiscalYear = date,
        #"Day Offset" = Int64.Type, #"Week Offset" = Int64.Type, #"Month Offset" = Int64.Type,
        #"Quarter Offset" = Int64.Type, #"Year Offset" = Int64.Type,
        #"Fiscal Quarter Offset" = Int64.Type, #"Fiscal Year Offset" = Int64.Type,
        IsFuture = logical, IsMTD = logical, IsQTD = logical, IsYTD = logical, IsFYTD = logical
    ],

    DateDimension = Table.FromRecords(List.Transform(Dates, Row), Schema)
in
    DateDimension
