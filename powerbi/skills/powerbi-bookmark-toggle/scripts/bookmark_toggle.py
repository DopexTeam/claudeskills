"""Create a visual-toggle bookmark group in a PBIP report, from scratch.

    python bookmark_toggle.py "<project>" --page <pageId> --group "Views" \
        --view "Summary=<visualId>" --view "Breakdown=<visualId>" \
        [--navigator <visualId>] [--apply]

Each --view names one visual that is VISIBLE in that view; every other targeted
visual is hidden. Two views over two visuals is the summary/detail switch.

Desktop must be closed.

Why this exists alongside remapping
-----------------------------------
Remapping an existing toggle is the right move when the report already has one,
because a bookmark Desktop wrote carries captured state -- filters, objects,
orderBy, expansionStates -- and dropping it changes behaviour on apply. But on a
report with no toggle anywhere there is nothing to copy, and clicking one
together in Desktop just to clone it is a poor trade.

So this writes the schema minimum:

    required        $schema, name, displayName, explorationState
    explorationState  version, activeSection, sections
    section         visualContainers
    display         mode            ("hidden"; showing means OMITTING display)

plus each target's DRILL STATE, which is not optional and is the part that is
easy to miss. A matrix's drill level lives in `activeProjections`, and its
expand-all/pinning in `expansionStates`. A bookmark that omits them leaves the
visual wherever the user last drilled it, so a toggle built without them looks
correct on the first click and diverges from the designed view thereafter.

plus each target's FILTER CARDS, which live on the container beside
`singleVisual` rather than inside it -- the level at which they are easiest to
overlook, including when diffing against a captured bookmark.

All of it is read off the target's own visual.json: `activeProjections` is the
projections whose `active` is not false, `expansionStates` copies across, and
`filterConfig.filters` transforms into `filters.byExpr`. So the state the report
was saved with is the state the bookmark restores, and nothing has to be
captured by clicking through Desktop.

`options.applyOnlyToTargetVisuals` is what makes this safe: the bookmark is
applied to the named visuals only, so it cannot reset a slicer it says nothing
about. Without it, a bookmark this size is genuinely dangerous -- it would
restore every visual on the page to a state it does not describe.
"""
import os
import re
import sys
import json
import uuid
import glob
import argparse

SCHEMA_BOOKMARK = ("https://developer.microsoft.com/json-schemas/fabric/item/"
                   "report/definition/bookmark/2.1.0/schema.json")
VERSION = "1.3"


def definition_dir(project):
    if os.path.isdir(os.path.join(project, "pages")):
        return project
    hits = glob.glob(os.path.join(project, "*.Report", "definition"))
    if not hits:
        sys.exit("no PBIR definition under %s" % project)
    return hits[0]


def newid():
    return uuid.uuid4().hex[:20]


DRILL_ROLES = ("Rows", "Columns")


def load_visual(d, page, vid):
    path = os.path.join(d, "pages", page, "visuals", vid, "visual.json")
    return json.load(open(path, encoding="utf-8-sig"))


def visual_state(container):
    """The part of a visual's saved state a bookmark must restore.

    Drill level and expansion are properties of the VISUAL, and a bookmark that
    does not mention them lets the user's own drilling persist through a toggle.
    Reading them here means the bookmark restores what the report was saved
    with, which is what the page author chose.
    """
    vis = container["visual"]
    sv = {"visualType": vis.get("visualType")}

    qs = vis.get("query", {}).get("queryState", {})
    active = {}
    for role in DRILL_ROLES:
        projections = qs.get(role, {}).get("projections", [])
        fields = [p["field"] for p in projections if p.get("active", True)]
        if fields:
            active[role] = fields
    if active:
        sv["activeProjections"] = active

    exp = vis.get("expansionStates")
    if exp:
        # visual.json writes `root: {}`, bookmarks write `root:
        # {"identityValues": []}` -- the same "no rows individually expanded"
        exp = json.loads(json.dumps(exp))
        for e in exp:
            if not e.get("root"):
                e["root"] = {"identityValues": []}
        sv["expansionStates"] = exp
    return sv


def visual_filters(container):
    """The visual's filter cards, in the shape a bookmark stores them.

    `filters` sits beside `singleVisual` on the container, NOT inside it, which
    is how it gets missed. Cards with no `filter` key are empty -- the bookmark
    records that the card exists and holds no selection, which is what lets
    applying it CLEAR a filter the user set. Omit the block and a toggle leaves
    the user's filtering in place instead of restoring the designed view.

        field                ->  expression
        howCreated "User"    ->  1,  absent -> 0
        ordinal, objects     ->  dropped
        filter               ->  kept verbatim where present
    """
    cards = []
    for f in container.get("filterConfig", {}).get("filters", []):
        card = {"name": f["name"], "type": f["type"],
                "expression": f["field"],
                "howCreated": 1 if f.get("howCreated") == "User" else 0}
        if "filter" in f:
            card["filter"] = f["filter"]
        cards.append(card)

    # Desktop also stores one empty Categorical card on the drilled hierarchy's
    # top level -- the drill slot. It is not in the visual's filterConfig, and
    # Desktop mints a fresh id for it in every capture, so the id carries no
    # identity and generating one is as faithful as copying one.
    v = container["visual"]
    if v.get("expansionStates"):
        rows = v.get("query", {}).get("queryState", {}).get("Rows", {})
        top = rows.get("projections", [])
        if top:
            cards.append({"name": newid(), "type": "Categorical",
                          "expression": top[0]["field"], "howCreated": 0})
    return {"byExpr": cards} if cards else None


def make_bookmark(d, page, label, visible, targets):
    """One view: `visible` shown, every other target hidden."""
    containers = {}
    for v in targets:
        vis = load_visual(d, page, v)
        sv = visual_state(vis)
        if v != visible:
            sv["display"] = {"mode": "hidden"}
        container = {"singleVisual": sv}
        filters = visual_filters(vis)
        if filters:
            container["filters"] = filters
        containers[v] = container
    return {
        "$schema": SCHEMA_BOOKMARK,
        "name": newid(),
        "displayName": label,
        "options": {
            "applyOnlyToTargetVisuals": True,
            "targetVisualNames": list(targets),
            "suppressActiveSection": True,
        },
        "explorationState": {
            "version": VERSION,
            "activeSection": page,
            "sections": {page: {"visualContainers": containers}},
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--page", required=True)
    ap.add_argument("--group", required=True)
    ap.add_argument("--view", action="append", required=True,
                    help='"Label=visualId", repeatable')
    ap.add_argument("--navigator", help="bookmarkNavigator visual to repoint")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    d = definition_dir(a.project)
    views = []
    for v in a.view:
        if "=" not in v:
            sys.exit("--view wants Label=visualId, got %r" % v)
        label, vid = v.split("=", 1)
        views.append((label.strip(), vid.strip()))
    targets = [vid for _, vid in views]

    # every target must exist on that page, or the bookmark applies to nothing
    present = {os.path.basename(os.path.dirname(f))
               for f in glob.glob(os.path.join(d, "pages", a.page, "visuals",
                                               "*", "visual.json"))}
    if not present:
        sys.exit("page %s has no visuals -- wrong page id?" % a.page)
    missing = [v for v in targets if v not in present]
    if missing:
        sys.exit("not on page %s: %s\n(a bookmark naming a visual that is not "
                 "there applies cleanly and does nothing, which is the hardest "
                 "version of this bug to see)" % (a.page, ", ".join(missing)))

    books = [(make_bookmark(d, a.page, label, vid, targets), label)
             for label, vid in views]
    gid = newid()

    print("  page      %s" % a.page)
    for b, label in books:
        vcs = b["explorationState"]["sections"][a.page]["visualContainers"]
        hidden = [v for v, o in vcs.items() if "display" in o["singleVisual"]]
        print("  %-10s %s  shows %s  hides %s"
              % (label, b["name"], dict(views)[label], hidden))
        for v, o in vcs.items():
            sv = o["singleVisual"]
            drill = {r: len(f) for r, f in sv.get("activeProjections", {}).items()}
            cards = o.get("filters", {}).get("byExpr", [])
            print("      %s  %-12s drill=%s expansion=%d filters=%d (%d set)"
                  % (v, sv.get("visualType"), drill or "-",
                     len(sv.get("expansionStates", [])), len(cards),
                     sum(1 for c in cards if "filter" in c)))
    print("  group     %s  %r" % (gid, a.group))
    if a.navigator:
        print("  navigator %s" % a.navigator)
    if not a.apply:
        print("  DRY RUN")
        return 0

    bdir = os.path.join(d, "bookmarks")
    os.makedirs(bdir, exist_ok=True)
    for b, _ in books:
        with open(os.path.join(bdir, b["name"] + ".bookmark.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(b, fh, indent=2)

    meta_path = os.path.join(bdir, "bookmarks.json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8-sig"))
    else:
        meta = {"$schema": SCHEMA_BOOKMARK.replace("bookmark/2.1.0",
                                                   "bookmarksMetadata/1.0.0"),
                "items": []}
    items = meta.setdefault("items", [])
    # re-running with the same group name replaces it rather than leaving a
    # second group of the same name behind, which renders as a duplicate
    # navigator entry and is confusing to diagnose
    for old in [i for i in items if i.get("displayName") == a.group]:
        for child in old.get("children", []):
            stale = os.path.join(bdir, child + ".bookmark.json")
            if os.path.exists(stale):
                os.remove(stale)
        items.remove(old)
    items.append({"name": gid, "displayName": a.group,
                  "children": [b["name"] for b, _ in books]})
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    if a.navigator:
        nav_path = os.path.join(d, "pages", a.page, "visuals", a.navigator,
                                "visual.json")
        nav = json.load(open(nav_path, encoding="utf-8-sig"))
        # parse and SET -- a regex over this file matches nothing when it is
        # indented, and reports success while changing nothing
        props = nav["visual"]["objects"]["bookmarks"][0]["properties"]
        props["bookmarkGroup"]["expr"]["Literal"]["Value"] = "'%s'" % gid
        if "selectedBookmark" in props:
            props["selectedBookmark"]["expr"]["Literal"]["Value"] = \
                "'%s'" % books[0][0]["name"]
        with open(nav_path, "w", encoding="utf-8") as fh:
            json.dump(nav, fh, indent=2)

    print("  APPLIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
