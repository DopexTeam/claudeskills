"""Turn an HTML design's CSS custom properties into a Power BI theme.

    python theme_from_css.py <design.html> [-o theme.json] [--name NAME]

The bridge problem this solves: AI writes a beautiful HTML artifact in minutes
because the training data is overwhelmingly web, and the same design then takes
days to reproduce by hand in Power BI. The *design language* is the reusable
part, and in a well-built HTML artifact it is already isolated in `:root` as
custom properties.

A Power BI theme absorbs almost all of it, and the mapping is unusually direct
because both are doing the same job:

    --ok / --alert / --warn     good / bad / neutral
    --r2 .. --r5 (a ramp)       minimum / center / maximum
    --ink / --ink2 / --muted    firstLevel .. fourthLevelElements
    --page / --surface          background / secondaryBackground
    --accent                    accent, tableAccent, hyperlink
    font families               textClasses

What does NOT cross, and should not be forced:

  * generated narrative prose -- the sentences an LLM wrote about THIS data are
    analysis, not formatting. A DAX text measure can approximate a couple of
    them and will be brittle.
  * rotated column headers, precise document typography, pagination
  * a dark-mode toggle -- a report carries one theme at a time

So this does not port a document. It ports the design language, so that what is
built in Power BI looks like it belongs to the same family, and so that a design
decision is made once.

Validated against the theme schema Desktop itself ships (pbirschemas).
"""
import os
import re
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbirschemas
import jsonschema_min

HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

# token name -> theme properties it feeds. First match wins, so order matters.
MAP = [
    (("page", "bg", "background"), ["background"]),
    (("surface", "card", "panel"), ["secondaryBackground"]),
    (("ink", "text", "fg", "foreground"), ["foreground", "firstLevelElements"]),
    (("ink2", "text2", "muted2"), ["secondLevelElements"]),
    (("muted", "subtle"), ["thirdLevelElements"]),
    (("line", "border", "rule"), ["fourthLevelElements"]),
    (("accent", "primary", "brand"), ["accent", "tableAccent", "hyperlink"]),
    (("ok", "good", "success", "pass"), ["good"]),
    (("alert", "bad", "danger", "error", "fail"), ["bad"]),
    (("warn", "caution"), ["neutral"]),
]


def tokens(html):
    """CSS custom properties from the FIRST :root block.

    The first block only: a design with a dark mode redefines the same names
    under a media query, and merging the two yields a palette that is neither.
    """
    m = re.search(r":root\s*\{(.*?)\}", html, re.S)
    if not m:
        return {}
    out = {}
    for name, value in re.findall(r"--([a-zA-Z0-9-]+)\s*:\s*([^;]+);", m.group(1)):
        out[name.strip()] = value.strip()
    return out


def fonts(html):
    fams = re.findall(r"family=([A-Za-z0-9+]+)", html)
    return [f.replace("+", " ") for f in dict.fromkeys(fams)]


def ramp(toks):
    """A numbered colour ramp (--r2..--r5) -> the conditional-formatting scale."""
    steps = sorted(((k, v) for k, v in toks.items()
                    if re.fullmatch(r"r[0-9]+", k) and HEX.match(v)),
                   key=lambda kv: int(kv[0][1:]))
    if len(steps) < 2:
        return {}
    lo, hi = steps[0][1], steps[-1][1]
    mid = steps[len(steps) // 2][1]
    return {"minimum": lo, "center": mid, "maximum": hi}


def build(html, name):
    toks = tokens(html)
    colours = {k: v for k, v in toks.items() if HEX.match(v)}
    theme = {"name": name}
    used = {}

    for keys, targets in MAP:
        for key in keys:
            if key in colours:
                for t in targets:
                    theme.setdefault(t, colours[key])
                    used.setdefault(t, key)
                break

    theme.update(ramp(colours))

    # dataColors: the accent first, then every other colour that is not already
    # doing a semantic job, so a chart drawn with this theme stays in family
    taken = {v for k, v in theme.items() if isinstance(v, str) and HEX.match(v)}
    series = [theme[k] for k in ("accent",) if k in theme]
    for k, v in colours.items():
        if v not in taken and v not in series and not re.fullmatch(r"r[0-9]+", k):
            series.append(v)
    if series:
        theme["dataColors"] = series[:12]

    fs = fonts(html)
    if fs:
        body = fs[-1]
        head = fs[0]
        theme["textClasses"] = {
            "title": {"fontFace": head, "fontSize": 14},
            "header": {"fontFace": head, "fontSize": 12},
            "label": {"fontFace": body, "fontSize": 10},
            "callout": {"fontFace": head, "fontSize": 28},
        }
    return theme, toks, used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("-o", "--out")
    ap.add_argument("--name")
    a = ap.parse_args()

    html = open(a.html, encoding="utf-8", errors="replace").read()
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    name = a.name or (title.group(1).strip() if title else os.path.basename(a.html))
    theme, toks, used = build(html, name)

    print("  %d custom properties found, %d are colours"
          % (len(toks), sum(1 for v in toks.values() if HEX.match(v))))
    print("  mapped:")
    for t in sorted(used):
        print("    %-22s <- --%-14s %s" % (t, used[t], theme[t]))
    for extra in ("minimum", "center", "maximum"):
        if extra in theme:
            print("    %-22s <- ramp           %s" % (extra, theme[extra]))
    if "dataColors" in theme:
        print("    %-22s %d series colours" % ("dataColors", len(theme["dataColors"])))
    if "textClasses" in theme:
        print("    %-22s %s" % ("textClasses", fonts(html)))

    unmapped = [k for k, v in toks.items() if HEX.match(v)
                and v not in {x for x in theme.values() if isinstance(x, str)}
                and v not in theme.get("dataColors", [])]
    if unmapped:
        print("  NOT mapped (no theme property does this job): %s"
              % ", ".join("--" + u for u in unmapped[:10]))

    if pbirschemas.available():
        reg = pbirschemas.load_all()
        schema = reg.get("reportthemeschema")
        if schema:
            errs = jsonschema_min.validate(theme, schema, registry=reg)
            print("  schema: %s" % ("valid against Desktop's theme schema" if not errs
                                    else "%d problem(s): %s" % (len(errs), errs[:3])))
    else:
        print("  schema: not cached -- run pbirschemas.py --extract to validate")

    out = a.out or os.path.splitext(a.html)[0] + ".theme.json"
    json.dump(theme, open(out, "w", encoding="utf-8"), indent=2)
    print("  wrote %s" % out)


if __name__ == "__main__":
    main()
