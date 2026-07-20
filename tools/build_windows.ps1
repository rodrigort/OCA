param(
    [string]$Python = "py"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if ($Python -eq "py") {
    & py -3 -m pip install -r requirements-dev.txt
    & py -3 tools/build_package.py
} else {
    & $Python -m pip install -r requirements-dev.txt
    & $Python tools/build_package.py
}

Write-Host "Application created under dist/OpenCANAnalyzer"
