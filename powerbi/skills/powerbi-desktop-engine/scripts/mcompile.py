"""Compile generated M with Power BI's own mashup engine.

Microsoft.Mashup.Engine1.Library.Modules.Compile(string) is the parser Power BI
itself uses. It is the only thing in this toolchain that actually knows M's
grammar.

This exists because hand-rolled validation gave false confidence twice:

  * `mlint` checks let-body structure but has no grammar, so it passed
    `optional as list` -- `optional` is a reserved word and the model would not
    open.
  * `ConnectFolder` returns success on a model whose M is syntactically invalid:
    TMDL parsing validates STRUCTURE, and the M inside an expression is an
    opaque string to it. Only the mashup engine compiles it.

"TMDL parses" is therefore not "the model loads". Use this before writing any
generated M to a report.
"""
import os
import re
import sys
import json
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbidesktop

# Resolved, never hardcoded. A default MSI install lands in Program Files, but
# the Store build sits under a versioned WindowsApps folder and an enterprise
# install can be anywhere; setup.ps1 records whatever it found.
DLL = pbidesktop.mashup_engine() or ""

_PS = r"""
$ErrorActionPreference='Stop'
$a=[Reflection.Assembly]::LoadFrom('%s')
$m=$a.GetType('Microsoft.Mashup.Engine1.Library.Modules').GetMethod('Compile',[Type[]]@([string]))
$docs = Get-Content -Raw -Encoding UTF8 '%s' | ConvertFrom-Json
$out = @()
foreach ($d in $docs) {
  try { $null=$m.Invoke($null,@([string]$d.doc)); $out += [pscustomobject]@{name=$d.name; ok=$true; error=''} }
  catch { $e=$_.Exception; while($e.InnerException){$e=$e.InnerException}
          $out += [pscustomobject]@{name=$d.name; ok=$false; error=$e.Message} }
}
$out | ConvertTo-Json -Compress -Depth 3
"""


def available():
    return os.path.exists(DLL)


def compile_all(named_expressions, tmp_dir):
    """named_expressions: {name: m_text}. Returns [(name, ok, error)].

    Each expression is wrapped in a minimal section document, which is how
    Power BI stores them, so what is compiled matches what ships.
    """
    docs = []
    for name, m in named_expressions.items():
        ident = name if re.fullmatch(r"[A-Za-z_]\w*", name) else '#"%s"' % name
        docs.append({"name": name,
                     "doc": "section S;\nshared %s = %s;" % (ident, m.rstrip().rstrip(";"))})
    jf = os.path.join(tmp_dir, "_mcompile.json")
    with open(jf, "w", encoding="utf-8") as fh:
        json.dump(docs, fh)
    ps = _PS % (DLL.replace("'", "''"), jf.replace("'", "''"))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True)
    txt = (r.stdout or "").strip()
    if not txt:
        return [("<compiler>", False, (r.stderr or "no output").strip()[:400])]
    data = json.loads(txt)
    if isinstance(data, dict):
        data = [data]
    return [(d["name"], bool(d["ok"]), d.get("error") or "") for d in data]


def m_sources(model_def_dir):
    """Only genuine M: {name -> expression text}.

    Skips what is not M, because feeding it to the compiler produces false
    failures that are worse than no check:
      * calculated tables / calc groups -- their partition source is DAX
      * expressions whose body is empty after extraction
    Handles single-line expressions (`expression X = "lit" meta [...]`), whose
    body sits on the header line rather than below it.
    """
    import glob
    from mbody import find_body, deindent
    from mbody import BLOCK

    out = {}
    ef = os.path.join(model_def_dir, "expressions.tmdl")
    if os.path.exists(ef):
        t = open(ef, encoding="utf-8", newline="").read()
        for b in re.split(r"(?m)^(?=expression )", t):
            m = re.match(r"expression\s+(?:'([^']+)'|(\S+))\s*=(.*)", b)
            if not m:
                continue
            name = m.group(1) or m.group(2)
            inline = (m.group(3) or "").strip()
            if inline and inline != "```":
                out["expr:" + name] = inline            # single-line form
                continue
            r = find_body(b, r"^expression\s", 2)
            body = deindent(r[2], 2) if r else ""
            if body.strip():
                out["expr:" + name] = body
    td = os.path.join(model_def_dir, "tables")
    for f in sorted(glob.glob(os.path.join(td, "*.tmdl"))):
        t = open(f, encoding="utf-8", errors="replace", newline="").read()
        for blk in BLOCK.split(t):
            if not blk.startswith("\tpartition"):
                continue
            head = blk.split("\n", 1)[0]
            if not re.search(r"=\s*m\s*$", head.strip()):
                break                                    # calculated / other: not M
            r = find_body(blk, r"^\t\tsource =", 4)
            body = deindent(r[2], 4) if r else ""
            if body.strip():
                out[os.path.basename(f)[:-5]] = body
            break
    return out
