---
name: powerbi-bookmark-toggle
description: Create or repair a Power BI visual toggle — a bookmark group plus a bookmark navigator that swaps which visual is shown — by writing PBIR directly, with no clicking through Desktop. Use this whenever a page needs a summary/detail switch or tabbed views, whenever a duplicated page's bookmark navigator does nothing, or whenever a toggle switches visibility but shows the wrong drill level or resets the wrong filters. Covers the display-hidden mechanism, the drill and filter state a bookmark must carry and where each one lives, remapping bookmarks between pages, and the navigator's second reference.
---

# Toggling visuals with bookmarks

Two visuals occupy the same rectangle; a bookmark group decides which one is
visible. This is how a page offers a summary and a breakdown of the same data
without spending twice the canvas.

**Non-scope:** validating the result → `powerbi-desktop-engine`'s `pbircheck`.
Whether a toggle is the right component at all → `powerbi-design-bridge`.
Measures and model edits → `powerbi-desktop-engine`.

Desktop must be **closed**: bookmarks live in PBIR, and the MCP reaches only the
model, never the report.

## The mechanism is one property

A bookmark records `singleVisual.display = {"mode": "hidden"}` for the visual it
hides. The visual it shows simply **omits `display` entirely** — there is no
`"visible"` value, and writing one is not how Desktop expresses it.

```
bookmarks/<id>.bookmark.json
  explorationState.sections.<pageId>.visualContainers
    <visualId>.singleVisual.display = {"mode": "hidden"}     ← hidden
    <otherId>.singleVisual                                    ← shown: no display key
```

Two bookmarks, each hiding the other's visual, is the whole toggle.

## Two options that decide whether it behaves

```json
"options": {
  "applyOnlyToTargetVisuals": true,
  "targetVisualNames": ["<visualA>", "<visualB>"],
  "suppressActiveSection": true
}
```

- **`applyOnlyToTargetVisuals`** — without it the bookmark restores every visual's
  state, so clicking the toggle resets the user's slicers. This is the single
  most common complaint about bookmark toggles and it is a one-line fix.
- **`suppressActiveSection`** — without it the bookmark navigates to the page it
  was captured on. Harmless until the bookmark is reused elsewhere, then
  baffling.

## Building one from scratch

```bash
python scripts/bookmark_toggle.py "<project>" --page <pageId> --group "Views" \
    --view "Summary=<visualId>" --view "Breakdown=<visualId>" \
    --navigator <visualId> --apply
```

A bookmark is far more than the visibility flag, and everything it carries is
readable off the targets' own `visual.json` — so a from-scratch bookmark can
match a Desktop-captured one without capturing anything.

| Block | Lives in the bookmark at | Derived from |
|---|---|---|
| `display` | `singleVisual.display` | the view being written |
| drill level | `singleVisual.activeProjections` | projections whose `active` is not `false` |
| expand-all / pinning | `singleVisual.expansionStates` | copies across; `root: {}` becomes `{"identityValues": []}` |
| filter cards | **`filters.byExpr`, beside `singleVisual`** | `filterConfig.filters`, renaming `field`→`expression`, `howCreated: "User"`→`1` |

Measured against a Desktop-authored equivalent: 8.2 KB versus 19.5 KB, with
every named filter card byte-identical. The remainder is the page's *untargeted*
visuals, which `applyOnlyToTargetVisuals` excludes from application anyway.

### What goes wrong if a block is dropped

**Drill state is not cosmetic.** A matrix set to "go to the next level" differs
from one set to "expand all down one level" only in `activeProjections` and
`expansionStates`. A bookmark omitting them leaves each matrix wherever the user
last drilled it, so the toggle switches visibility correctly and shows the wrong
view — which reads as a data problem, not a bookmark problem.

**Empty filter cards are not inert.** Most cards carry no `filter` key. That
records *the card exists and holds no selection*, and applying it **clears** a
filter the user set. Dropping the block is therefore not the conservative
choice; it is a different behaviour, and not the one Desktop produces.

**`filters` sits beside `singleVisual`, not inside it.** This is the one that
gets missed, and it gets missed twice: once when generating, and again when
verifying, because a diff loop written over `singleVisual` keys reports parity
across a subset and looks like parity overall. Compare whole containers.

Desktop also writes one empty Categorical card on the drilled hierarchy's top
level — a drill slot absent from `filterConfig`. It carries a fresh id in every
capture, so the id means nothing and generating one is as faithful as copying.

## Remap when carrying an existing toggle across

To move a working toggle onto a duplicated page, copy the bookmarks and swap
identities rather than regenerating. Generating reproduces the state the report
is *saved* with; a captured bookmark may hold something deliberate that was
never saved to the visual, and you cannot tell which by looking.

Remapping is a text substitution on the raw JSON, deliberately:

```python
text = text.replace(SRC_SECTION, DST_SECTION)
for src, dst in VISUALS.items():
    text = text.replace(src, dst)
```

These ids appear as object **keys**, inside `targetVisualNames`, and in
`activeSection`. A structural walk has to know all three places; a text swap
cannot miss one.

Map every visual the bookmark touches, not just the two being toggled — the
others carry state that must still point somewhere real.

## The navigator has two references

A `bookmarkNavigator` binds to a group through `visual.objects.bookmarks[0].properties`:

```
bookmarkGroup      → the group to show buttons for
selectedBookmark   → which one starts active
```

**Both** must be repointed. Fixing only `bookmarkGroup` leaves the navigator
naming a bookmark from the page it was copied from, which fails in a way that
looks like the toggle is merely mis-styled.

Register the group in `bookmarks/bookmarks.json`:

```json
{"name": "<groupId>", "displayName": "Scratch",
 "children": ["<summaryId>", "<breakdownId>"]}
```

Ids are 20 hex characters (`uuid.uuid4().hex[:20]`).

## Parse and set; never pattern-match the value

Editing the navigator with a regex silently matched nothing — the file is
indented and the pattern assumed compact JSON. It reported success and changed
nothing. Load the JSON, walk to the property, assign, write back.

The literal is quoted **inside** the string: `"Value": "'ef9a1f4b7d7b4cd7abac'"`.
Miss the inner quotes and the navigator binds to nothing.

## Verify

```bash
python ../powerbi-desktop-engine/scripts/pbircheck.py "<project>"
```

It catches a bookmark naming a visual that does not exist, which is the failure
this work creates. Then check no source identity survived:

```python
leaked = [v for v in SRC_IDS if v in open(new_bookmark).read()]
```

A leaked id is a bookmark that applies cleanly to the *wrong page's* visuals —
the exact symptom of a duplicated page whose toggle "does nothing".

Then diff whole containers against a known-good bookmark, if the report has one:

```python
gen[vid] == cap[vid]          # the container, not gen[vid]["singleVisual"]
```

Then reopen in Desktop and click it **through the navigator**. A bookmark
applied from the Bookmarks pane exercises the bookmark; only the navigator
exercises the wiring. Passing `pbircheck`, and even applying correctly from the
pane, says nothing about whether the navigator points at the group you wrote.

### Prove it by the query, not by looking

Eyeballing two renders is the weakest link in this whole procedure. A toggle's
correctness is exactly "does the visual issue the statement it issues in its
designed state", which is diffable — see *Proving a report edit by the query it
produces* in `powerbi-desktop-engine`:

```
Refresh visuals -> drill the matrix off its level -> click the bookmark
-> Refresh visuals -> export -> paquery.py baseline.json --compare after.json
```

```bash
python ../powerbi-desktop-engine/scripts/paquery.py base.json --compare after.json
```

Measured on this component: after drilling away and applying a generated
bookmark, the restored statement was byte-identical to the designed-state
baseline at 1,601 characters.

The perturbation is what makes the test mean anything — a toggle recorded from a
clean state emits no query at all, because the bookmark asserts the state the
visual is already in. The hidden visual is reported SILENT rather than passed,
since a hidden visual issues no query.
