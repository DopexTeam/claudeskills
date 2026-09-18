---
name: powerbi-bookmark-toggle
description: Toggle between two or more Power BI visuals in the same space using a bookmark group and a bookmark navigator, by editing PBIR directly. Use this whenever a page needs a summary/detail switch, tabbed views, or any control that swaps which visual is shown without changing the page; whenever a duplicated page's bookmark navigator does nothing; or whenever bookmarks need to be created or repointed in a .pbip without clicking through Desktop. Covers the display-hidden mechanism, remapping bookmarks between pages, and the second navigator reference that is easy to miss.
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

## Remap, never reconstruct

To give a duplicated page its own toggle, copy the working bookmarks and swap
identities. Do not write fresh ones.

A bookmark carries `filters`, `activeProjections`, `expansionStates` and
per-visual `objects` alongside the visibility flag. Anything omitted changes
behaviour silently *when the bookmark is applied* — not when it is written — so
the mistake surfaces later, in use.

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

Finally reopen in Desktop and click it. The file being valid is not the same as
the toggle behaving.
