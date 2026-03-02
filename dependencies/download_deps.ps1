param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$wheelhouse = Join-Path $PSScriptRoot "wheelhouse"

New-Item -ItemType Directory -Force -Path $wheelhouse | Out-Null

& $Python -m pip download -r (Join-Path $root "requirements.txt") -d $wheelhouse
Write-Host "Downloaded dependencies to $wheelhouse"