"""Extract / replace the M body of a TMDL `expression` or `partition ... source =` block.

Handles both TMDL forms: plain (bare indented lines) and fenced (``` ... ```).
Power BI Desktop rewrites one into the other on save, so both must be read.
"""
import re


def find_body(text, header_re, tabs):
    """Return (start_line, end_line, body_lines, fenced) or None."""
    lines = text.split("\r\n")
    hi = None
    for i, l in enumerate(lines):
        if re.match(header_re, l):
            hi = i
            break
    if hi is None:
        return None
    fenced = lines[hi].rstrip().endswith("```")
    s = hi + 1
    if fenced:
        e = s
        while e < len(lines) and lines[e].strip() != "```":
            e += 1
        if e >= len(lines):
            return None
        return (s, e, lines[s:e], True)
    e = s
    pre = "\t" * tabs
    while e < len(lines) and (lines[e].startswith(pre) or lines[e].strip() == ""):
        e += 1
    while e > s and lines[e - 1].strip() == "":
        e -= 1
    return (s, e, lines[s:e], False)


def deindent(body_lines, tabs):
    pre = "\t" * tabs
    return "\n".join(l[len(pre):] if l.startswith(pre) else l for l in body_lines).rstrip()


def reindent(m, tabs):
    pre = "\t" * tabs
    return [(pre + l) if l.strip() else "" for l in m.split("\n")]


def splice(text, s, e, new_lines):
    lines = text.split("\r\n")
    return "\r\n".join(lines[:s] + new_lines + lines[e:])

# The points at which a TMDL table file splits into its parts. Lives here
# because it is TMDL structure, not anything to do with a particular
# report: both the compiler front-end and every consumer need it.
BLOCK = re.compile(r"(?m)^(?=\t(?:column|measure|partition|hierarchy|annotation)\b)")
