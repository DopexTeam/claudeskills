# One-time setup for the procore-schema-lock skill.
#
#   powershell -ExecutionPolicy Bypass -File setup.ps1 [-Force] [-DataRoot <path>]
#
# Idempotent: safe to re-run, and re-runs after a Power BI Desktop upgrade are
# worth doing because the borrowed libraries move with it.
#
# Everything here exists because the two components that make this toolchain
# trustworthy belong to Microsoft and cannot be redistributed:
#
#   Microsoft.MashupEngine.dll         the M compiler Power BI itself uses. It
#                                      is the only thing that actually knows M's
#                                      grammar -- TMDL parsing validates
#                                      structure and treats the M inside an
#                                      expression as an opaque string
#   Microsoft.PowerBI.AdomdClient.dll  queries a running Desktop instance's DMVs
#                                      from a shell, which is what turns refresh
#                                      waiting from blind sleeps into a real
#                                      condition
#
# So setup finds the local install, copies one out, builds the parser against
# it, and PROVES both work rather than assuming.
param(
    [switch]$Force,
    [string]$DataRoot
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$scripts = Join-Path $root "scripts"
$mast = Join-Path $scripts "mast"
$fail = 0

$script:fixes = @()

function Step($n) { Write-Host "`n== $n" }
function Ok($m)   { Write-Host "   OK    $m" -ForegroundColor Green }

# Every failure carries what to DO about it. A setup that reports a missing
# dependency without saying where to get it just moves the search to the user.
function Bad($m, $fix) {
    Write-Host "   FAIL  $m" -ForegroundColor Red
    $script:fail++
    if ($fix) { $script:fixes += $fix }
}

Write-Host "procore-schema-lock setup"
Write-Host "   skill: $root"

# ---------------------------------------------------------------- prerequisites
Step "Prerequisites"

$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue) }
if ($py) {
    $v = & $py.Source --version 2>&1
    Ok "$v at $($py.Source)"
} else {
    Bad "Python is not on PATH. Every tool in this skill is Python." @"
Install Python 3.8 or newer:
    https://www.python.org/downloads/
  Tick "Add python.exe to PATH" in the installer, then open a new shell.
"@
}

# csc.exe ships with the .NET Framework; pick the newest v4 it offers.
$csc = Get-ChildItem "$env:WINDIR\Microsoft.NET\Framework64\v4*\csc.exe" -ErrorAction SilentlyContinue |
       Sort-Object FullName -Descending | Select-Object -First 1
if (-not $csc) {
    $csc = Get-ChildItem "$env:WINDIR\Microsoft.NET\Framework\v4*\csc.exe" -ErrorAction SilentlyContinue |
           Sort-Object FullName -Descending | Select-Object -First 1
}
if ($csc) { Ok "csc.exe at $($csc.FullName)" }
else {
    Bad "csc.exe not found. The M parser is a small C# program built against Power BI's engine." @"
Install the .NET Framework 4.x developer pack:
    https://dotnet.microsoft.com/download/dotnet-framework
  The compiler normally ships with Windows at
  %WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe -- if it is absent the
  framework has been removed or the feature is disabled.
"@
}

# -------------------------------------------------------- locate Power BI Desktop
Step "Power BI Desktop"

$candidates = @(
    "C:\Program Files\Microsoft Power BI Desktop\bin",
    "C:\Program Files (x86)\Microsoft Power BI Desktop\bin",
    "C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_*\bin"
)
$bin = $null
foreach ($c in $candidates) {
    $hit = Get-ChildItem -Path $c -Filter "Microsoft.MashupEngine.dll" -ErrorAction SilentlyContinue |
           Sort-Object FullName -Descending | Select-Object -First 1
    if ($hit) { $bin = $hit.Directory.FullName; break }
}
if ($bin) {
    Ok "bin at $bin"
} else {
    Bad "Power BI Desktop is not installed on this machine." @"
Install Power BI Desktop:
    https://powerbi.microsoft.com/desktop/
  or from the Microsoft Store:
    https://aka.ms/pbidesktopstore

  This skill is NOT optional about it. Two libraries ship only with Desktop and
  cannot be redistributed:
    Microsoft.MashupEngine.dll         the M compiler Power BI itself uses --
                                       the only thing that truly knows M's
                                       grammar. Without it, generated M is
                                       written to client reports unverified.
    Microsoft.PowerBI.AdomdClient.dll  queries a running model, which is how
                                       refresh waiting becomes a real condition
                                       rather than a guess.

  Having Power BI in the Service is not enough -- these are desktop libraries.

  Already installed somewhere unusual? Create scripts\pbi_paths.json with:
    { "bin": "<full path to the Desktop bin folder>" }
  and re-run. Searched:
    $($candidates -join "`n    ")
"@
}

$engine = $null; $adomd = $null
if ($bin) {
    $engine = Join-Path $bin "Microsoft.MashupEngine.dll"
    $adomd  = Join-Path $bin "Microsoft.PowerBI.AdomdClient.dll"
    if (Test-Path $engine) { Ok "Microsoft.MashupEngine.dll" }
    else {
        Bad "Microsoft.MashupEngine.dll missing from $bin" @"
The Power BI Desktop install at
    $bin
  looks incomplete. Repair or reinstall it:
    https://powerbi.microsoft.com/desktop/
"@
    }
    if (Test-Path $adomd) { Ok "Microsoft.PowerBI.AdomdClient.dll" }
    else {
        Bad "Microsoft.PowerBI.AdomdClient.dll missing from $bin" @"
The Power BI Desktop install at
    $bin
  looks incomplete. Repair or reinstall it:
    https://powerbi.microsoft.com/desktop/
"@
    }
}

if ($fail -gt 0) {
    Write-Host "`n" ("-" * 72)
    Write-Host "Setup stopped: $fail prerequisite(s) missing. Nothing was changed." -ForegroundColor Red
    Write-Host ("-" * 72)
    foreach ($f in $script:fixes) { Write-Host "`n$f" }
    Write-Host ("-" * 72)
    Write-Host "Re-run this script once the above is resolved.`n"
    exit 1
}

# Record what we found so the tools do not have to probe, and so a
# non-standard install is honoured. Machine-specific -- gitignored.
$cfgPath = Join-Path $scripts "pbi_paths.json"
@{
    "bin" = $bin
    "Microsoft.MashupEngine.dll" = $engine
    "Microsoft.PowerBI.AdomdClient.dll" = $adomd
} | ConvertTo-Json | Set-Content -Path $cfgPath -Encoding utf8
Ok "recorded paths in scripts\pbi_paths.json"

# -------------------------------------------------------------- build the parser
Step "Build the M parser (mast.exe)"

New-Item -ItemType Directory -Force -Path $mast | Out-Null
$localDll = Join-Path $mast "Microsoft.MashupEngine.dll"
$exe = Join-Path $mast "mast.exe"

if ($Force -or -not (Test-Path $localDll) -or
    (Get-Item $engine).LastWriteTime -gt (Get-Item $localDll -ErrorAction SilentlyContinue).LastWriteTime) {
    Copy-Item $engine $localDll -Force
    Ok "copied the engine into scripts\mast"
} else {
    Ok "engine already present and current"
}

if ($Force -or -not (Test-Path $exe) -or
    (Get-Item (Join-Path $mast "MAst.cs")).LastWriteTime -gt (Get-Item $exe).LastWriteTime) {
    # The quotes must survive INTO csc's argv rather than being eaten by
    # PowerShell. csc treats a comma inside /r: as a reference separator, so any
    # install path containing a comma -- a company name ending in ", LLC" is the
    # common case -- splits into two bogus references and the build dies with
    # CS0006 reporting half a path. Spaces alone are fine; the comma is the trap.
    $cscArgs = @("/nologo", "/target:exe", "/out:`"$exe`"",
                 "`"$(Join-Path $mast 'MAst.cs')`"", "/r:`"$localDll`"")
    $out = & $csc.FullName $cscArgs 2>&1
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) {
        Bad "csc failed:`n$out" @"
The C# compiler rejected the build. If the paths above look split at a comma or
a space, that is the cause -- report the path you installed this skill to.
"@
    } else { Ok "built mast.exe" }
} else {
    Ok "mast.exe already current"
}

# ------------------------------------------------------------------- data root
Step "Data root"

if (-not $DataRoot) {
    $DataRoot = $env:PROCORE_LOCK_DATA
    if (-not $DataRoot) { $DataRoot = Join-Path $env:USERPROFILE ".procore-schema-lock" }
}
foreach ($k in @("calcdep", "required", "derived", "backup")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $DataRoot $k) | Out-Null
}
Ok "$DataRoot"
Write-Host "         Deliberately OUTSIDE this folder: captures, contracts and backups are"
Write-Host "         client data -- whole semantic models, column names, share tokens. Set"
Write-Host "         PROCORE_LOCK_DATA to move it."

# --------------------------------------------------------------------- prove it
Step "Verify"

# The parser must not merely run; it must return a tree. Repeated literals are
# the specific thing to check -- the engine interns them, and a cycle guard
# scoped to the whole tree instead of the current path silently drops every
# repeat, which would make a column named twice invisible the second time.
$probe = @'
import sys, os
sys.path.insert(0, os.path.abspath("scripts"))
import astm, mcompile
if not astm.available():
    print("FAIL  mast.exe or the engine dll is missing"); sys.exit(1)
a = astm.parse_many({"t": 'let a = Table.SelectColumns(x, {"dup"}), b = Table.SelectColumns(y, {"dup"}) in b'})[0]["t"]
lits = [astm.text_of(arg) for _, args in astm.invocations(a) for arg in args]
if lits.count(["dup"]) != 2:
    print("FAIL  parser dropped a repeated literal:", lits); sys.exit(1)
print("OK    parser returns a tree, repeated literals intact")
import tempfile
with tempfile.TemporaryDirectory() as t:
    good = mcompile.compile_all({"ok": "let x = 1 in x"}, t)
    bad  = mcompile.compile_all({"bad": "let f = (optional as list) => 1 in f"}, t)
if not good[0][1]:
    print("FAIL  compiler rejected valid M:", good); sys.exit(1)
if bad[0][1]:
    print("FAIL  compiler ACCEPTED a reserved word as a parameter -- the gate is not real"); sys.exit(1)
print("OK    compiler accepts valid M and rejects `optional` as a parameter")
'@
Push-Location $root
try {
    $probe | & $py.Source -
    if ($LASTEXITCODE -ne 0) { Bad "verification failed" }
} finally { Pop-Location }

# ADOMD only proves out against a running instance; absence of one is not a failure.
$probe2 = @'
$cfg = Get-Content -Raw "scripts\pbi_paths.json" | ConvertFrom-Json
[void][Reflection.Assembly]::LoadFrom($cfg.'Microsoft.PowerBI.AdomdClient.dll')
[void][Microsoft.AnalysisServices.AdomdClient.AdomdConnection]
'@
Push-Location $root
try {
    Invoke-Expression $probe2
    Ok "ADOMD client loads (namespace Microsoft.AnalysisServices.AdomdClient)"
} catch {
    Bad "ADOMD client did not load: $($_.Exception.Message)"
} finally { Pop-Location }

# ----------------------------------------------------------------------- done
if ($fail -gt 0) {
    Write-Host "`n" ("-" * 72)
    Write-Host "Setup finished with $fail problem(s)." -ForegroundColor Red
    Write-Host ("-" * 72)
    foreach ($f in $script:fixes) { Write-Host "`n$f" }
    if (-not $script:fixes) {
        Write-Host "`nNo automatic remediation for the above. The build or verification step"
        Write-Host "failed against a Power BI Desktop install that was found -- re-run with"
        Write-Host "-Force to rebuild from scratch, and check the error text above."
    }
    Write-Host ("-" * 72) "`n"
    exit 1
}
Write-Host "`nReady. Start with SKILL.md; the workflow begins by capturing"
Write-Host "INFO.CALCDEPENDENCY from an open, refreshed model.`n"
exit 0
