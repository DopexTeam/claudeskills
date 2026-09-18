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
| **forbidden** | no Power BI equivalent. Do not generate it. |

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

## 2. Heat-map matrix — **clean** (with one forbidden sub-part)

Entities × categories, each cell coloured by a rating band.

*Avila:* `.c` ×175 with `.r3` / `.r4` / `.r5` ramp classes — subcontractors × 15
evaluation categories.

| | |
|---|---|
| HTML | `<table class="table-box">`, cells `class="c r{n}"` |
| Power BI | **matrix**, rows = entity, columns = category, values = rating, background by `fillRule` |
| Data | long format: one row per entity × category × rating |
| Theme | ramp comes from `minimum` / `center` / `maximum` |

**Rotated column headers (`.rot`) are forbidden** — a matrix cannot rotate them.
Use short category names, or accept horizontal scroll. This is the single
biggest visual divergence, so decide it at design time rather than discovering
it at build time.

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

## Forbidden

| Wanted | Why not |
|---|---|
| Rotated column headers | matrix cannot rotate them |
| Dark-mode toggle | a report carries one theme at a time |
| Document flow and pagination | Power BI pages are fixed canvases |
| Arbitrary web fonts | only fonts installed on the viewer's machine render |
| Free-form prose paragraphs | every sentence becomes a DAX measure; see 7 |

---

## The rule that makes this work

A generated document that uses only components 1–9 can be rebuilt in Power BI
without redesign. One that reaches outside them produces something the client
has already seen and approved, and which then cannot be delivered — the worst
order to discover a constraint in.

So the constraint belongs in the **generator prompt**, not in a review step
afterwards.
