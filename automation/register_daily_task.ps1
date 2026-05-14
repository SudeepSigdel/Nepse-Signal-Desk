param(
    [string]$TaskName = "NEPSE-Daily-Pipeline",
    [string]$ProjectRoot = "C:\Users\sudee\projects\Final Year Project",
    [string]$RunAt = "16:30",
    [string]$Source = "sharesansar",
    [double]$Delay = 0.2
)

$runner = Join-Path $ProjectRoot "automation\run_daily_pipeline.ps1"
if (-not (Test-Path $runner)) {
    throw "Runner script not found: $runner"
}

$psArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -ProjectRoot `"$ProjectRoot`" -Source `"$Source`" -Delay $Delay"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($RunAt, "HH:mm", $null))
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "Scheduled task '$TaskName' created/updated to run daily at $RunAt"
Write-Host "Test run command: powershell -ExecutionPolicy Bypass -File `"$runner`""
