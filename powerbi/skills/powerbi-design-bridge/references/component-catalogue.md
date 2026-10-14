# Component catalogue — HTML ↔ Power BI

Every component here has a realization on **both** sides. That is the whole
point: a generated document may only use these, so that whatever is produced
for a client on Tuesday can become a Power BI page without redesign.

Derived from a real artifact (`949-00-Avila-evaluations`, 48 CSS classes, 18
tables, no JavaScript) rather than invented, then checked against the formatting
surface Power BI actually exposes — `dataBars`, `icon`, `gradient`, `fillRule`,
`wordWrap` are all present in the schemas Desktop ships.

**Verdicts**

| | meaning |
|---|---|
| **clean** | both sides express it fully; translation is mechanical |
| **lossy** | translates, but something is given up — named explicitly |
| **technique** | no *default* Power BI equivalent; achievable, and the method is given |

There is almost no **forbidden**. An earlier draft of this file listed rotated
headers, dark mode and pagination as impossible. All three are buildable, and
the list was really "things whose method I did not know" wearing the costume of
a capability limit. That mistake is expensive in the wrong direction: it narrows
a design before anyone has tried. When a component looks impossible, the default
assumption is that a technique exists and has not been found yet.

---

## 1. KPI tile — **clean**

Executive-summary numbers: a value, a label, a qualifier.

*Avila:* `.tile` / `.tile-n` / `.tile-l` / `.tile-s` ×6 — "3.53 · Average rating,
all categories · 175 ratings on the 1–5 scale"

| | |
|---|---|
| HTML | `<div class="tile"><div class="tile-n">…</div><div class="tile-l">…</div><div class="tile-s">…</div></div>` |
| Power BI | **card** (`cardVisual`), value + label + optional detail |
| Data | one measure, one scalar |
| Theme | `textClasses.callout` sizes the number |

Keep to 4–6 per strip; Power BI cards stop being readable below ~120px wide.

---

## 2. Heat-map matrix — **clean** (headers need a technique)

Entities × categories, each cell coloured by a rating band.

*Avila:* `.c` ×175 with `.r3` / `.r4` / `.r5` ramp classes — subcontractors × 15
evaluation categories.

| | |
|---|---|
| HTML | `<table class="table-box">`, cells `class="c r{n}"` |
| Power BI | **matrix**, rows = entity, columns = category, values = rating, background by `fillRule` |
| Data | long format: one row per entity × category × rating |
| Theme | ramp comes from `minimum` / `center` / `maximum` |

**Two forms, and the one to reach for.** `objects.values[].properties.backColor`
scoped to one measure by the selector's `metadata`. Either:

- **`Conditional.Cases`** — discrete bands, one colour per rating step. What a
  1–5 scorecard usually wants, because a 3 reads as a 3 rather than as 47% of
  the way along a gradient.
- **`FillRule.linearGradient3`** — continuous. Requires `min`, `mid` and `max`
  (the middle stop is `mid`; `center` is the *theme's* name for the same idea,
  and the two files disagree deliberately). Each stop needs `color` **and**
  `value`.

In a theme these are plain JSON; in a visual every leaf is an expression —
`{"Literal": {"Value": "'#833795'"}}` with the quotes inside the string, and
`"5D"` for a number.

**Pin the domain.** Omitting `value` lets Power BI scale to the observed range,
so the worst performer is always the darkest colour whatever they scored, and
the colours mean something different after every refresh.

**Blanks are not zeros.** `nullColoringStrategy: asZero` paints an unevaluated
cell as 0 — past the bottom of a 1–5 scale — so an entity nobody rated renders
as the worst on the page. Leave blanks unpainted.

**A uniform heat map is a data defect, not a formatting one.** If every row
shows the same colours, count distinct measure values against the grouping
before touching the ramp: a First Finish scorecard had 192 cells, 16 vendors and
12 distinct values — one per category — because the measure could not see its
grouping. The ramp was already correct and had been for months.

**Rotated column headers (`.rot`) — technique.** A matrix will not rotate its
own headers, so turn the native header off and supply the header band yourself:
textboxes with vertical text, or images, positioned above the matrix inside a
visual group so they move together. Costs layout maintenance when categories
change; buys the column density that makes a 15-category scorecard readable.

---

## 3. Status chip — **clean**

A compact verdict attached to a row or section: "Clean", "1 exception".

*Avila:* `.chip` ×39, `.yes` / `.no` / `.flag`

| | |
|---|---|
| HTML | `<span class="chip yes">Clean</span>` |
| Power BI | conditional formatting on a measure: **icon** set, or background `fillRule` |
| Data | a measure returning a small enum, or a count |
| Theme | `good` / `bad` / `neutral` |

---

## 4. Rating bar — **clean**

Magnitude shown inline next to a number.

*Avila:* `.bar` ×14

| | |
|---|---|
| HTML | a div with a percentage width |
| Power BI | **data bars** conditional formatting on a table/matrix value |
| Data | numeric measure with a known domain |

---

## 5. Question-and-answer rows — **clean**

A questionnaire rendered as rows, grouped by section, exceptions marked.

*Avila:* `.q` / `.a` ×66 across 13 sections

| | |
|---|---|
| HTML | `<tr><td class="q">…</td><td class="a">…</td></tr>` |
| Power BI | **table** or **matrix** with section as a row group |
| Data | one row per question: section, question, answer, is_exception |
| Theme | `wordWrap` on the question column |

---

## 6. Evidence quote — **lossy**

A verbatim comment with attribution: who said it, about what.

*Avila:* `.co` / `.cm` / `.who` / `.txt`

| | |
|---|---|
| HTML | blockquote with attribution line |
| Power BI | **table** column with word wrap, or a card with a text measure |
| Data | the comment text must be a column, not derived |

**Lossy:** Power BI gives no control over quote typography, and long text in a
card clips rather than reflowing. Budget a fixed height and expect truncation.

---

## 7. Ranked callout — **lossy, and the one worth building well**

"Strongest subcontractor: MP Mechanical Group, average 3.93 across 15
categories, no rating below 3" — a selection, its metrics, and its evidence.

This is not prose. It is `TOPN` + the fields of the selected row.

| | |
|---|---|
| HTML | a `.lede` / `.note` paragraph with the values interpolated |
| Power BI | **card** bound to DAX text measures |
| Data | a ranked measure, plus the descriptive columns to quote |

```
Top Sub =
VAR t = TOPN(1, VALUES(Sub[Name]), [Avg Rating], DESC)
RETURN CONCATENATEX(t, Sub[Name])

Top Sub Detail =
VAR t = TOPN(1, VALUES(Sub[Name]), [Avg Rating], DESC)
RETURN "average " & FORMAT(CALCULATE([Avg Rating], t), "0.00")
    & " across " & CALCULATE(DISTINCTCOUNT(Eval[Category]), t) & " categories"
```

**Lossy:** each sentence costs a measure, and the sentence structure is frozen
in DAX. Write two or three, not a paragraph. Keep the *selection logic* in the
measure and the *wording* short, because changing wording later means editing
DAX rather than a template.

---

## 8. Section header — **lossy**

*Avila:* `.sec-head` ×5 — "1 · Subcontractor scorecard"

| | |
|---|---|
| HTML | `<h2>` / `<h3>` |
| Power BI | **textbox**, or a matrix row-group header |

**Lossy:** a textbox is static and unaware of filters. If the heading needs to
restate the filter context, it becomes a text measure on a card — component 7.

---

## 9. Callout box — **lossy**

*Avila:* `.note` / `.alert` / `.warn` ×13

| | |
|---|---|
| HTML | a bordered block with a semantic colour |
| Power BI | card or textbox on a coloured **shape** |
| Theme | `good` / `bad` / `neutral` |

**Lossy:** conditional visibility needs a bookmark or a measure-driven
transparency trick. Prefer a chip (component 3) where the verdict is per-row.

---

## 10. Pagination — **technique**

A long list shown a page at a time, with the page count derived from the data.
Implemented in MJS; the pattern is general.

Two disconnected what-if tables, a stable rank, and two filter measures:

```
# Items Value = SELECTEDVALUE('# Items'[# Items], 28)     -- rows per page
# Pages Value = SELECTEDVALUE('# Pages'[# Pages], 1)      -- current page

Project Rank  = RANKX(ALLSELECTED(Project), ProjectDate[Project Start Date], , ASC)

Item Filter =                      -- visual-level filter, keep = 1
VAR _Page  = [# Pages Value]
VAR _Size  = [# Items Value]
VAR _Rank  = Project[Project Rank]
VAR _Window =
    FILTER(ALLSELECTED(Project[Project Start Date]),
        _Rank > (_Page - 1) * _Size && _Rank <= _Page * _Size)
RETURN IF(SELECTEDVALUE(Project[Project Start Date]) IN _Window, 1, 0)

Page Filter =                      -- filter on the page slicer, keep = 1
VAR _Total = CALCULATE(DISTINCTCOUNT(Project[id]), ALL(Project[id]))
VAR _Pages = ROUNDUP(DIVIDE(_Total, [# Items Value]), 0)
RETURN IF(SELECTEDVALUE('# Pages'[# Pages]) <= _Pages, 1, 0)
```

`Item Filter` windows the rows; `Page Filter` hides page numbers past the end so
the slicer never offers an empty page. The rank must be stable and total, or
rows fall between pages.

---

## 11. Theme switching — **technique**

A report carries one theme file, but the *rendered* colours need not be fixed.
Drive them from measures: a disconnected selection table, and colour measures
consumed by conditional formatting.

```
Mode = SELECTEDVALUE('Mode'[Mode], "Light")
Ink  = IF([Mode] = "Dark", "#ECEBEF", "#32373C")
Page = IF([Mode] = "Dark", "#141317", "#F5F4F6")
```

Anything that accepts conditional formatting — background, font colour, data
bars, shape fill — can read these. Costs one measure per token and does not
reach visual chrome; enough for a document-style page whose surfaces are mostly
cards, tables and shapes.

The HTML side already has both palettes: a `:root` block and its dark override.
Generate both, and keep the token names identical so the measures line up.

## Still genuinely expensive

| Wanted | Cost |
|---|---|
| Free-form prose paragraphs | every sentence becomes a DAX measure with its wording frozen in the expression; see 7 |
| Arbitrary web fonts | only fonts installed on the viewer's machine render; pick from a common set |

---

## The rule that makes this work

A generated document built from components 1–11 can be rebuilt in Power BI
without redesign. One that reaches outside them produces something the client
has already seen and approved, and which then costs an unplanned R&D cycle to
deliver — the worst order to discover a constraint in.

So the vocabulary belongs in the **generator prompt**, not in a review step
afterwards.

## Growing the catalogue

Each component is a candidate sub-skill: its HTML form, its Power BI build
steps, its DAX, its failure modes. Composition then becomes the job — a
document is a sequence of components, and a Power BI page is the same sequence
realized differently.

Adding one has a standard: **build it in Power BI first**, then write down what
you did. A component enters this file with a working method or not at all. That
is what separates it from the earlier draft, which listed three things as
impossible because nobody had tried.
