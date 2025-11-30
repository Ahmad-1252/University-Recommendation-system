# University Recommendation System CLI Launcher
# This script activates the virtual environment and runs the CLI

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

Write-Host "Activating virtual environment..." -ForegroundColor Green
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

Write-Host "Starting University Recommendation System CLI..." -ForegroundColor Green
& python -m src.cli.commands @Args

Write-Host "`nCLI session ended." -ForegroundColor Yellow
Read-Host "Press Enter to exit"