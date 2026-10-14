"""The PBIR schemas, taken from Power BI Desktop's own install.

Desktop validates report definitions when it saves them, so it carries the
schemas. They are embedded in Microsoft.PowerBI.ClientResources.dll as webpack
chunks -- `module.exports = JSON.parse('{...}')` -- one per document kind.

That matters because developer.microsoft.com publishes these too, but
publication LAGS Desktop. Of the five visualContainer versions in one real
corpus, 2.8.0 and 2.9.0 resolve on the web and 2.10.0, 2.11.0 and 2.12.0 return
404. The embedded copy has no such gap: it is by construction the schema the
installed Desktop actually enforces, it works offline, and it covers the newer
structures the published ones predate -- `visualGroup`, `parentGroupName` and
`isHidden` are all absent from published 2.9.0 and present here.

Same borrow as the mashup engine: read it out of the local install rather than
redistributing it. The cache is gitignored.

    python pbirschemas.py --extract    # refresh the cache
    python pbirschemas.py              # report what is cached
"""
import os
import re
import ast
import sys
import json
import glob
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbidesktop

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "pbir-schemas")
RESOURCE = "Microsoft.PowerBI.ClientResources.dll"

# The host prefix matters. The same schemas ship for DESKTOP, MOBILE,
# DESKTOPDIALOGHOST and REPORTSERVERHOSTMODERN; DESKTOP is the one that governs
# a .pbip written by Power BI Desktop.
PREFIX = "SCRIPTS/DESKTOP."

_PS = r"""
$ErrorActionPreference='Stop'
$a=[Reflection.Assembly]::LoadFrom('%s')
$out='%s'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$n=0
foreach ($r in $a.GetManifestResourceNames()) {
  if ($r -notlike '%s*SCHEMA*') { continue }
  $s=$a.GetManifestResourceStream($r)
  $rd=New-Object IO.StreamReader($s)
  $t=$rd.ReadToEnd(); $rd.Close()
  $f=Join-Path $out (($r -replace '^SCRIPTS/','') -replace '\.MIN\.JS$','.js')
  Set-Content -Path $f -Value $t -Encoding utf8
  $n++
}
Write-Output $n
"""


def _payloads(js):
    """Every JSON Schema in a webpack chunk, largest first.

    findall, not search. A webpack chunk bundles modules, and nothing guarantees
    one payload per chunk -- today each of these carries exactly one, which is
    luck rather than contract. Taking only the first would silently drop the
    rest, and a Desktop upgrade that bundles a second schema per chunk would
    look like nothing had changed.
    """
    out = []
    for raw in re.findall(r"JSON\.parse\('(.*?)'\)", js, re.S):
        # a JS single-quoted string literal; Python's literal parser handles the
        # same escape set, and is far safer than hand-rolling the unescaping
        for s in (lambda: ast.literal_eval("'" + raw + "'"),
                  lambda: raw.replace("\\'", "'")):
            try:
                out.append(json.loads(s()))
                break
            except Exception:
                continue
    return sorted(out, key=lambda d: -len(json.dumps(d)))


def _payload(js):
    got = _payloads(js)
    return got[0] if got else None


def extract():
    dll = pbidesktop.dll(RESOURCE)
    if not dll:
        raise SystemExit(
            "%s not found. Run setup.ps1, or install Power BI Desktop." % RESOURCE)
    os.makedirs(CACHE, exist_ok=True)
    ps = _PS % (dll.replace("'", "''"), CACHE.replace("'", "''"), PREFIX)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("extraction failed: %s" % (r.stderr or "")[:300])

    made, failed = 0, []
    for f in sorted(glob.glob(os.path.join(CACHE, "*.js"))):
        d = _payload(open(f, encoding="utf-8").read())
        # REPORTTHEMESCHEMA.JSON.js has no ".SCHEMA." separator, so a single
        # replace left it as reportthemeschema.json.json
        name = os.path.basename(f)[len("DESKTOP."):]
        for suffix in (".SCHEMA.JSON.js", ".JSON.js", ".js"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        if d is None:
            failed.append(name)
            continue
        json.dump(d, open(os.path.join(CACHE, name.lower() + ".json"), "w",
                          encoding="utf-8"), indent=1)
        made += 1
        os.remove(f)
    return made, failed


def _kind_of(name):
    return os.path.basename(name).replace(".json", "").lower()


def load_all():
    """{kind: schema}. Kinds are lowercase: visualcontainer, page, report, ..."""
    return {_kind_of(f): json.load(open(f, encoding="utf-8"))
            for f in glob.glob(os.path.join(CACHE, "*.json"))}


def available():
    return bool(glob.glob(os.path.join(CACHE, "*.json")))


if __name__ == "__main__":
    if "--extract" in sys.argv:
        made, failed = extract()
        print("  extracted %d schemas to %s" % (made, os.path.relpath(CACHE, HERE)))
        if failed:
            print("  FAILED to parse: %s" % ", ".join(failed))
            sys.exit(1)
    got = load_all()
    if not got:
        sys.exit("  no schemas cached -- run: python pbirschemas.py --extract")
    for k in sorted(got):
        d = got[k]
        print("  %-32s %d properties, %d definitions"
              % (k, len(d.get("properties", {})), len(d.get("definitions", {}))))
