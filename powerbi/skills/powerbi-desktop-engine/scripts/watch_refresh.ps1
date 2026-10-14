# Wait for a Power BI Desktop refresh to finish, and say which way it went.
#
#   powershell -NoProfile -File watch_refresh.ps1 -Port 55955 [-TimeoutMin 60]
#
# Exits when the refresh reaches a terminal state, so a background shell can
# block on it instead of sleeping blind. Prints ONE line.
#
# The engine is only reachable through ADOMD, and Power BI Desktop ships it:
# bin\Microsoft.PowerBI.AdomdClient.dll. Note the assembly is named
# Microsoft.PowerBI.AdomdClient while its types live in the
# Microsoft.AnalysisServices.AdomdClient namespace.
#
# Terminal states, because silence is not success:
#   DONE    every partition Ready AND the newest RefreshedTime moved past the
#           baseline taken at start -- that second clause is what distinguishes
#           a genuine re-run from the previous refresh's cached data
#   FAILED  a refresh was seen in progress and then everything settled back with
#           RefreshedTime unmoved. Desktop rolls the model back on failure, so
#           partition ErrorMessage is usually empty and the only evidence is the
#           rollback itself
#   ERROR   a partition reported an ErrorMessage
#   TIMEOUT / GONE
param(
    [Parameter(Mandatory = $true)][int]$Port,
    [int]$TimeoutMin = 60,
    [int]$IntervalSec = 20
)

# Resolved the same way the Python side does: setup.ps1 records what it found
# in pbi_paths.json, and we probe as a fallback so this still works without it.
$cfg = Join-Path $PSScriptRoot "pbi_paths.json"
$dll = $null
if (Test-Path $cfg) {
    $j = Get-Content -Raw $cfg | ConvertFrom-Json
    $v = $j.'Microsoft.PowerBI.AdomdClient.dll'
    if ($v -and (Test-Path $v)) { $dll = $v }
}
if (-not $dll) {
    foreach ($p in @("C:\Program Files\Microsoft Power BI Desktop\bin",
                     "C:\Program Files (x86)\Microsoft Power BI Desktop\bin",
                     "C:\Program Files\WindowsApps\Microsoft.MicrosoftPowerBIDesktop_*\bin")) {
        $hit = Get-ChildItem -Path $p -Filter "Microsoft.PowerBI.AdomdClient.dll" -ErrorAction SilentlyContinue |
               Select-Object -First 1
        if ($hit) { $dll = $hit.FullName; break }
    }
}
if (-not $dll) { "GONE  Microsoft.PowerBI.AdomdClient.dll not found -- run setup.ps1"; exit 3 }
[void][Reflection.Assembly]::LoadFrom($dll)

function Get-State([int]$p) {
    $c = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$p")
    $c.Open()
    try {
        $cmd = $c.CreateCommand()
        $cmd.CommandText = "SELECT [State], [RefreshedTime], [ErrorMessage] FROM `$SYSTEM.TMSCHEMA_PARTITIONS"
        $r = $cmd.ExecuteReader()
        $tot = 0; $ready = 0; $err = ""; $max = [datetime]::MinValue
        while ($r.Read()) {
            $tot++
            if ([int]$r[0] -eq 1) { $ready++ }
            if ($r[1] -ne [DBNull]::Value -and [datetime]$r[1] -gt $max) { $max = [datetime]$r[1] }
            if ($r[2] -ne [DBNull]::Value -and "$($r[2])".Trim().Length -gt 0 -and $err -eq "") { $err = "$($r[2])" }
        }
        $r.Close()
        return @{ total = $tot; ready = $ready; max = $max; err = $err }
    } finally { $c.Close() }
}

function Get-RunTimes([int]$p, [datetime]$after) {
    $c = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$p")
    $c.Open()
    try {
        $cmd = $c.CreateCommand()
        $cmd.CommandText = "SELECT [RefreshedTime] FROM `$SYSTEM.TMSCHEMA_PARTITIONS"
        $r = $cmd.ExecuteReader()
        $out = @()
        while ($r.Read()) {
            if ($r[0] -ne [DBNull]::Value -and [datetime]$r[0] -gt $after) { $out += [datetime]$r[0] }
        }
        $r.Close()
        return $out
    } finally { $c.Close() }
}

try { $base = Get-State $Port } catch { "GONE  cannot reach localhost:$Port -- $($_.Exception.Message)"; exit 3 }
$baseMax = $base.max
$sawPending = ($base.ready -lt $base.total)
$deadline = (Get-Date).AddMinutes($TimeoutMin)

# A failed refresh leaves the model PARTIALLY loaded -- Evaluations sat at
# 24/120 afterwards -- so "every partition settled" never arrives and waiting
# for it would report nothing but TIMEOUT. Stalling is therefore its own
# terminal state: no movement in either the ready count or RefreshedTime for
# StallPolls consecutive checks, having seen movement earlier.
$StallPolls = 9
$lastSig = "$($base.ready)|$($base.max.Ticks)"
$stall = 0
$sawMovement = $false
$s = $base

while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds $IntervalSec
    try { $s = Get-State $Port } catch { "GONE  instance closed or unreachable during refresh"; exit 3 }

    if ($s.err -ne "") { "ERROR  $($s.err.Substring(0, [Math]::Min(300, $s.err.Length)))"; exit 2 }

    $sig = "$($s.ready)|$($s.max.Ticks)"
    if ($sig -eq $lastSig) { $stall++ } else { $stall = 0; $sawMovement = $true; $lastSig = $sig }

    if ($s.ready -eq $s.total -and $s.max -gt $baseMax) {
        # Duration is measured across the partitions that refreshed in THIS run,
        # i.e. those stamped after the baseline. Subtracting the baseline itself
        # would report the gap since the PREVIOUS refresh -- on Evaluations that
        # read 1380s for a run that actually took 563s.
        $run = Get-RunTimes $Port $baseMax
        $d = if ($run.Count -gt 1) {
            [int](($run | Measure-Object -Maximum).Maximum - ($run | Measure-Object -Minimum).Minimum).TotalSeconds
        } else { 0 }
        "DONE  $($s.ready)/$($s.total) ready, $($run.Count) partitions refreshed, took ${d}s (ended $($s.max.ToString('HH:mm:ss')))"
        exit 0
    }
    if ($s.ready -lt $s.total) { $sawPending = $true }

    if ($sawMovement -and $stall -ge $StallPolls -and $s.max -le $baseMax) {
        "FAILED  $($s.ready)/$($s.total) ready and unchanged for $($StallPolls * $IntervalSec)s; RefreshedTime never moved past $($baseMax.ToString('HH:mm:ss')) -- refresh did not land"
        exit 1
    }
    if ($sawPending -and $s.ready -eq $s.total -and $s.max -le $baseMax) {
        "FAILED  all partitions settled but RefreshedTime never moved past $($baseMax.ToString('HH:mm:ss')) -- refresh rolled back"
        exit 1
    }
}
"TIMEOUT  after $TimeoutMin min; ready $($s.ready)/$($s.total), newest $($s.max.ToString('HH:mm:ss'))"
exit 4
