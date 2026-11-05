# cttr-perf-log.ps1
# Samples the running moderngekko-run process once per second and writes a CSV:
# wall time, elapsed seconds, the game window title (ModernGekko puts its FPS
# counter in the title), whole-process CPU (percent of one core), working set,
# and per-thread CPU for the four busiest threads as "threadId:pct" pairs.
# The per-thread split is what separates a saturated game thread (recompiled
# code and the interpreter live there) from a saturated graphics thread
# (draw submission and the Vulkan driver) in the numbers afterwards.
#
# Run one tagged log per condition or area so the files label themselves:
#   .\cttr-perf-log.ps1 -Tag pad-hub
#   .\cttr-perf-log.ps1 -Tag nopad-race
#
# Optional bonus: while THIS window has focus, keys 1-4 drop markers into the
# CSV (1 tutorial, 2 hub, 3 race, 4 menu). The -Tag filename label is the
# primary labelling; markers only help inside a long mixed session.
#
# Stop with Ctrl+C, or just quit the game: the logger exits when the game does.

param(
    [string]$Tag = "session",
    [string]$OutDir = "C:\Games\CTTR\perf"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $OutDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$csvPath = Join-Path $OutDir "cttr-perf-$Tag-$stamp.csv"
"time,elapsed_s,marker,title,cpu_pct_one_core,working_set_mb,t1,t2,t3,t4" | Set-Content -Path $csvPath -Encoding UTF8

Write-Host "Log file: $csvPath"
Write-Host "Waiting for moderngekko-run to start..."
while (-not (Get-Process -Name moderngekko-run -ErrorAction SilentlyContinue)) {
    Start-Sleep -Milliseconds 500
}
$proc0 = Get-Process -Name moderngekko-run | Select-Object -First 1
$pid0 = $proc0.Id
Write-Host "Sampling moderngekko-run (PID $pid0) once per second. Ctrl+C stops."

$markers = @{ "1" = "tutorial"; "2" = "hub"; "3" = "race"; "4" = "menu" }
$start = Get-Date
$lastT = $start
$lastCpu = $proc0.TotalProcessorTime.TotalSeconds
$threadCpu = @{}
foreach ($t in $proc0.Threads) { $threadCpu[$t.Id] = $t.TotalProcessorTime.TotalSeconds }

while ($true) {
    Start-Sleep -Seconds 1
    $p = Get-Process -Id $pid0 -ErrorAction SilentlyContinue
    if (-not $p) { Write-Host "Game process exited; log complete."; break }
    $now = Get-Date
    $cpuNow = $p.TotalProcessorTime.TotalSeconds
    $dt = ($now - $lastT).TotalSeconds
    $cpuPct = 0
    if ($dt -gt 0) { $cpuPct = [math]::Round(100.0 * ($cpuNow - $lastCpu) / $dt, 1) }
    $lastT = $now
    $lastCpu = $cpuNow

    $marker = ""
    try {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true).KeyChar
            if ($markers.ContainsKey([string]$key)) { $marker = $markers[[string]$key] }
        }
    } catch { $marker = "" }

    $threadDeltas = @()
    $alive = @{}
    foreach ($t in $p.Threads) {
        $alive[$t.Id] = $true
        $tc = $t.TotalProcessorTime.TotalSeconds
        if ($threadCpu.ContainsKey($t.Id) -and $dt -gt 0) {
            $pct = [math]::Round(100.0 * ($tc - $threadCpu[$t.Id]) / $dt, 1)
            if ($pct -gt 0) { $threadDeltas += ,@($t.Id, $pct) }
        }
        $threadCpu[$t.Id] = $tc
    }
    foreach ($k in @($threadCpu.Keys)) { if (-not $alive.ContainsKey($k)) { $threadCpu.Remove($k) } }
    $top = @($threadDeltas | Sort-Object { $_[1] } -Descending | Select-Object -First 4)
    $tcols = @("", "", "", "")
    for ($i = 0; $i -lt $top.Count; $i++) { $tcols[$i] = "{0}:{1}" -f $top[$i][0], $top[$i][1] }

    $title = ""
    try { $title = ($p.MainWindowTitle -replace ",", ";") } catch { $title = "" }
    $elapsed = [int]($now - $start).TotalSeconds
    $ws = [math]::Round($p.WorkingSet64 / 1MB, 0)
    $row = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}" -f $now.ToString("HH:mm:ss"), $elapsed, $marker, $title, $cpuPct, $ws, $tcols[0], $tcols[1], $tcols[2], $tcols[3]
    Add-Content -Path $csvPath -Value $row -Encoding UTF8
    Write-Host $row
}
Write-Host "Saved: $csvPath"
