param(
    [string]$ProjectRoot = "C:\Users\sudee\projects\Final Year Project",
    [string]$Source = "sharesansar",
    [double]$Delay = 0.2,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$pythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$runner = Join-Path $ProjectRoot "automation\daily_pipeline.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

if (-not (Test-Path $runner)) {
    throw "Runner script not found: $runner"
}

Set-Location $ProjectRoot
$cmdArgs = @($runner, "--source", $Source, "--delay", "$Delay")
if ($ExtraArgs -and $ExtraArgs.Count -gt 0) {
    $cmdArgs += $ExtraArgs
}

& $pythonExe @cmdArgs
exit $LASTEXITCODE
