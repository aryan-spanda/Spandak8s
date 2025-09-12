# Spandak8s CLI Wrapper with Auto-Backend Start
# Usage: .\spandak8s-with-backend.ps1 modules enable minio --tier bronze

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$CliArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnsureBackendScript = Join-Path $ScriptDir "ensure-backend.ps1"
$CliScript = Join-Path $ScriptDir "spandak8s"

# Ensure backend is running
& $EnsureBackendScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Backend is not available. Cannot proceed with CLI command." -ForegroundColor Red
    exit 1
}

# Execute the CLI command
if ($CliArgs.Count -gt 0) {
    $CommandLine = ($CliArgs -join ' ')
    Write-Host "🎯 Executing: spandak8s $CommandLine" -ForegroundColor Cyan
    python $CliScript @CliArgs
} else {
    Write-Host "💡 Usage: .\spandak8s-with-backend.ps1 <command> [args...]" -ForegroundColor Yellow
    Write-Host "   Example: .\spandak8s-with-backend.ps1 modules enable minio --tier bronze" -ForegroundColor Yellow
}
