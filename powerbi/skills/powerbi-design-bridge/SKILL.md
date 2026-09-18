---
name: powerbi-design-bridge
description: Generate a client-facing HTML report that can later be rebuilt in Power BI without redesign, using a fixed component vocabulary that has a Power BI counterpart for every element. Use this whenever producing a one-off HTML deliverable from live data that the client will expect to see again as a Power BI report, whenever converting an HTML design or design system into a Power BI theme, or whenever deciding whether a design idea is buildable in Power BI before showing it to a client. Covers the component catalogue, the CSS-token to theme mapping, and what Power BI simply cannot do.
---

# From an HTML deliverable to a Power BI report

An LLM writes a beautiful HTML report in minutes because its training is
overwhelmingly web. The same design then takes days by hand in Power BI, or
turns out to be impossible after the client has already seen it. That is the gap.

The fix is not a translator. It is a **closed component vocabulary**: generate
only elements that already have a Power BI realization, so the HTML a client
approves on Tuesday is buildable on Wednesday.

**Read `references/component-catalogue.md` before generating.** Eleven
components, each with an HTML form, a Power BI form, its data contract, and a
verdict — clean, lossy, or needs-a-technique.

**Assume a technique exists.** Power BI's defaults are narrow and its ceiling is
not. Rotated headers, dark mode and pagination all look impossible and are all
buildable — pagination is already running in a production report. A component is
only out of scope once someone has tried and failed, not when the obvious route
is missing.

**Non-scope:** editing models or M → `powerbi-desktop-engine`. Schema drift →
`procore-schema-lock`. Number formatting at scale → `powerbi-visual-formatting`.

## Three inputs

| Input | Supplies |
|---|---|
| the **design system** | tokens in `:root`, and the component vocabulary |
| the **data connector** | live rows; every component states the shape it needs |
| the **prompt** | which questions the document answers, in what order |

The generator's job is to answer the prompt using only catalogue components,
bound to data the connector actually returns.

## The constraint goes in the prompt

Not in a review afterwards. A document that reaches outside the catalogue is one
the client has seen and approved and which then cannot be delivered — the worst
possible order to discover a constraint.

When a design genuinely needs something forbidden, change the design **before**
it ships, or accept in writing that the Power BI version will differ.

## Tokens carry across; markup does not

Put every colour and font in `:root` as custom properties. Then:

```bash
python ../powerbi-desktop-engine/scripts/theme_from_css.py <design.html> -o theme.json
```

That maps the tokens onto a Power BI theme and validates it against the schema
Desktop itself ships. The mapping is direct because both are doing the same job:

    --ok / --alert / --warn    →  good / bad / neutral
    --r2 .. --r5 (a ramp)      →  minimum / center / maximum
    --ink / --ink2 / --muted   →  first .. fourthLevelElements
    --accent                   →  accent, tableAccent, hyperlink
    font families              →  textClasses

The ramp mapping is the one that pays: a heat map's colours become Power BI's
conditional-formatting scale automatically, so the matrix lands in the same
visual language as the document.

**A design decision therefore gets made once.** That is the durable half of the
bridge; the markup is disposable.

## Narrative is a component, not prose

"Strongest subcontractor: MP Mechanical Group, average 3.93 across 15
categories" is `TOPN` plus the fields of the selected row — component 7. It
survives the crossing.

A free paragraph does not. Each sentence becomes a DAX measure whose wording is
frozen in the expression, so write two or three, not an essay.

## Components are sub-skills

Each catalogue entry is a candidate skill of its own: HTML form, Power BI build
steps, DAX, failure modes. The document is then a *composition* of components,
and the Power BI page is the same composition realized differently.

The bar for adding one: **build it in Power BI first, then write down what you
did.** A method or nothing.

## Two documents, two jobs

The HTML is a point-in-time handover: one project, prose, printable, done. The
Power BI report is the recurring interactive view across every project.

Do not try to make Power BI reproduce the document. Make it carry the same
analysis in its own idiom, wearing the same design language. Deciding which of
the two a request actually wants is usually more useful than any translation.
