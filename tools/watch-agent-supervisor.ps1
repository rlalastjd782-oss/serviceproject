param(
    [int]$IntervalSeconds = 30,
    [int]$StaleMinutes = 10,
    [switch]$Fix,
    [switch]$KillStaleCodex,
    [switch]$Once
)

$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
cmd /c chcp 65001 > $null

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AgentDir = Join-Path $ProjectRoot ".codex-agents"
$LogDir = Join-Path $AgentDir "logs"
$LockFile = Join-Path $AgentDir "pipeline.lock"
$SupervisorStatusFile = Join-Path $LogDir "supervisor-status.txt"
$StatusHeading = -join @("## ", [char]0xC0C1, [char]0xD0DC)

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Get-ActivePipelineProcesses {
    try {
        return @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -ieq "codex.exe" -and
            $_.CommandLine -match "exec --json" -and
            $_.CommandLine -like "*$ProjectRoot*"
        })
    }
    catch {
        return @()
    }
}

function Get-HandoffStatus {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -ne $StatusHeading) {
            continue
        }

        for ($j = $i + 1; $j -lt $lines.Count; $j++) {
            $candidate = $lines[$j].Trim()
            if ($candidate.StartsWith("## ")) {
                break
            }
            if ($candidate.StartsWith("- ")) {
                return $candidate.Substring(2).Trim()
            }
        }
    }

    return ""
}

function Get-LatestFile {
    param([string]$Pattern)

    return Get-ChildItem -LiteralPath $LogDir -File -Filter $Pattern -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Get-LatestProjectFile {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    return Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Get-FileStamp {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return "missing"
    }

    return (Get-Item -LiteralPath $Path).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
}

function Test-FileNewerThan {
    param(
        [string]$LeftPath,
        [string]$RightPath
    )

    if (-not (Test-Path -LiteralPath $LeftPath)) {
        return $false
    }

    if (-not (Test-Path -LiteralPath $RightPath)) {
        return $true
    }

    return ((Get-Item -LiteralPath $LeftPath).LastWriteTime -gt (Get-Item -LiteralPath $RightPath).LastWriteTime)
}

function Get-LastJsonEventText {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }

    try {
        $lastLine = Get-Content -LiteralPath $Path -Encoding UTF8 -Tail 1 -ErrorAction Stop
    }
    catch {
        return "log is being written by another process"
    }
    if (-not $lastLine -or -not $lastLine.StartsWith("{")) {
        return $lastLine
    }

    try {
        $event = $lastLine | ConvertFrom-Json
        if ($event.type -eq "item.completed" -and $event.item) {
            if ($event.item.type -eq "agent_message" -and $event.item.text) {
                $text = ($event.item.text -replace "`r?`n", " ").Trim()
                if ($text.Length -gt 140) {
                    $text = $text.Substring(0, 140) + "..."
                }
                return "agent_message: $text"
            }
            if ($event.item.command) {
                $command = ($event.item.command -replace "`r?`n", " ").Trim()
                if ($command.Length -gt 140) {
                    $command = $command.Substring(0, 140) + "..."
                }
                return "command: $command"
            }
            return "item.completed: $($event.item.type)"
        }

        return $event.type
    }
    catch {
        return $lastLine
    }
}

function Write-SupervisorSnapshot {
    $now = Get-Date
    $activeProcesses = Get-ActivePipelineProcesses
    $latestEvents = Get-LatestFile -Pattern "*-events.jsonl"
    $latestMessage = Get-LatestFile -Pattern "*-last-message.md"
    $latestError = Get-LatestFile -Pattern "*-pipeline-error.txt"
    $latestStderr = Get-LatestFile -Pattern "*-stderr.log"

    $lockExists = Test-Path -LiteralPath $LockFile
    $lockAgeMinutes = 0.0
    $lockContent = ""
    if ($lockExists) {
        $lockItem = Get-Item -LiteralPath $LockFile
        $lockAgeMinutes = ($now - $lockItem.LastWriteTime).TotalMinutes
        $lockContent = (Get-Content -LiteralPath $LockFile -Encoding UTF8 -ErrorAction SilentlyContinue) -join " | "
    }

    $latestEventAgeMinutes = $null
    if ($latestEvents) {
        $latestEventAgeMinutes = ($now - $latestEvents.LastWriteTime).TotalMinutes
    }

    $logStale = $false
    if ($latestEvents -and $latestEventAgeMinutes -ge $StaleMinutes) {
        $logStale = $true
    }

    $lockStale = $lockExists -and $lockAgeMinutes -ge $StaleMinutes
    $activeCount = @($activeProcesses).Count

    if ($Fix -and $lockExists -and $activeCount -eq 0 -and $lockStale) {
        Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
        $lockExists = $false
        $lockContent = "stale lock removed by supervisor"
    }

    if ($Fix -and $KillStaleCodex -and $lockExists -and $activeCount -gt 0 -and $logStale) {
        foreach ($process in $activeProcesses) {
            Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
        $activeCount = 0
        $lockExists = $false
        $lockContent = "stale Codex process and lock removed by supervisor"
    }

    $handoffs = @(
        [pscustomobject]@{ Name = "Planning -> Design"; Path = Join-Path $ProjectRoot "handoff\planning-to-design.md"; Next = Join-Path $ProjectRoot "handoff\design-to-dev.md" },
        [pscustomobject]@{ Name = "Design -> Dev"; Path = Join-Path $ProjectRoot "handoff\design-to-dev.md"; Next = Join-Path $ProjectRoot "handoff\dev-to-qa.md" },
        [pscustomobject]@{ Name = "Dev -> QA"; Path = Join-Path $ProjectRoot "handoff\dev-to-qa.md"; Next = Join-Path $ProjectRoot "handoff\qa-to-final.md" },
        [pscustomobject]@{ Name = "QA -> Final"; Path = Join-Path $ProjectRoot "handoff\qa-to-final.md"; Next = Join-Path $ProjectRoot "handoff\final-to-git.md" },
        [pscustomobject]@{ Name = "Final -> PlanningFinal"; Path = Join-Path $ProjectRoot "handoff\final-to-git.md"; Next = Join-Path $ProjectRoot "handoff\planning-final-to-git.md" },
        [pscustomobject]@{ Name = "PlanningFinal -> Git"; Path = Join-Path $ProjectRoot "handoff\planning-final-to-git.md"; Next = "" }
    )

    $latestSpec = Get-LatestProjectFile -Path (Join-Path $ProjectRoot "docs\specs")
    $planningHandoffPath = Join-Path $ProjectRoot "handoff\planning-to-design.md"

    $lines = New-Object System.Collections.ArrayList
    [void]$lines.Add("Codex Pipeline Supervisor")
    [void]$lines.Add("Project: $ProjectRoot")
    [void]$lines.Add("Updated: $($now.ToString('yyyy-MM-dd HH:mm:ss'))")
    [void]$lines.Add("Fix mode: $Fix / Kill stale Codex: $KillStaleCodex")
    [void]$lines.Add("")
    [void]$lines.Add("Lock")
    if ($lockExists) {
        [void]$lines.Add("  ACTIVE, age=$([Math]::Round($lockAgeMinutes, 1)) minutes")
        [void]$lines.Add("  $lockContent")
    }
    else {
        [void]$lines.Add("  NO_LOCK")
        if ($lockContent) {
            [void]$lines.Add("  $lockContent")
        }
    }
    [void]$lines.Add("")
    [void]$lines.Add("Process")
    [void]$lines.Add("  active Codex pipeline processes: $activeCount")
    foreach ($process in $activeProcesses) {
        [void]$lines.Add("  PID $($process.ProcessId)")
    }
    [void]$lines.Add("")
    [void]$lines.Add("Latest Logs")
    if ($latestEvents) {
        [void]$lines.Add("  events: $($latestEvents.Name), age=$([Math]::Round($latestEventAgeMinutes, 1)) minutes")
        [void]$lines.Add("  last event: $(Get-LastJsonEventText -Path $latestEvents.FullName)")
    }
    if ($latestMessage) {
        [void]$lines.Add("  last message: $($latestMessage.Name), updated=$($latestMessage.LastWriteTime.ToString('HH:mm:ss'))")
    }
    if ($latestError) {
        [void]$lines.Add("  last pipeline error: $($latestError.Name), updated=$($latestError.LastWriteTime.ToString('HH:mm:ss'))")
    }
    if ($latestStderr -and $latestStderr.Length -gt 0) {
        [void]$lines.Add("  last stderr: $($latestStderr.Name), $($latestStderr.Length) bytes")
    }
    [void]$lines.Add("")
    [void]$lines.Add("Handoff")
    foreach ($handoff in $handoffs) {
        [void]$lines.Add("  $($handoff.Name): $(Get-HandoffStatus -Path $handoff.Path) / updated $(Get-FileStamp -Path $handoff.Path)")
    }
    [void]$lines.Add("")
    [void]$lines.Add("Freshness")
    if ($latestSpec) {
        $specStamp = $latestSpec.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        if (Test-FileNewerThan -LeftPath $latestSpec.FullName -RightPath $planningHandoffPath) {
            [void]$lines.Add("  Planning spec newer than handoff: $($latestSpec.Name) / updated $specStamp")
            [void]$lines.Add("  Action: planning must update handoff\planning-to-design.md")
        }
        else {
            [void]$lines.Add("  Planning spec is covered by handoff: $($latestSpec.Name) / updated $specStamp")
        }
    }
    foreach ($handoff in $handoffs) {
        if ($handoff.Next -and (Test-FileNewerThan -LeftPath $handoff.Path -RightPath $handoff.Next)) {
            [void]$lines.Add("  $($handoff.Name): upstream handoff is newer. Next stage should rerun.")
        }
    }
    [void]$lines.Add("")

    $scanLock = $lockExists -and $activeCount -eq 0 -and $lockContent.Contains("Role: PipelineScan")

    if ($lockExists -and $activeCount -eq 0 -and $lockStale -and -not $scanLock) {
        [void]$lines.Add("Decision: stale lock. Run with -Fix to remove it.")
    }
    elseif ($scanLock) {
        [void]$lines.Add("Decision: pipeline is checking ready stages.")
    }
    elseif ($lockExists -and $activeCount -gt 0 -and $logStale) {
        [void]$lines.Add("Decision: Codex process looks stalled. Run with -Fix -KillStaleCodex to stop only this project's stale Codex exec.")
    }
    elseif ($lockExists) {
        [void]$lines.Add("Decision: pipeline appears active.")
    }
    else {
        [void]$lines.Add("Decision: pipeline is free.")
    }

    $text = $lines -join [Environment]::NewLine
    $text | Set-Content -LiteralPath $SupervisorStatusFile -Encoding UTF8
    Write-Host $text
}

Write-Host "Watching Codex pipeline supervisor."
Write-Host "Project: $ProjectRoot"
Write-Host "Interval: $IntervalSeconds seconds"
Write-Host "Stale threshold: $StaleMinutes minutes"
Write-Host "Status file: .codex-agents\logs\supervisor-status.txt"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

while ($true) {
    Write-SupervisorSnapshot
    if ($Once) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}
