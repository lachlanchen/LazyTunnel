param([string]$Flutter = 'flutter.bat')
$ErrorActionPreference = 'Stop'
$nativeRoot = Split-Path -Parent $PSScriptRoot
$version = (& $Flutter --version | Select-Object -First 1)
if ($version -notmatch '^Flutter 3\.47\.2 ') { throw 'Use the pinned Flutter 3.47.2 SDK.' }
Push-Location (Join-Path $nativeRoot 'apps\lazytunnel')
try {
    & $Flutter pub get --enforce-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Dependency resolution failed' }
    & $Flutter analyze
    if ($LASTEXITCODE -ne 0) { throw 'Analysis failed' }
    & $Flutter test
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    & $Flutter build windows --release
    if ($LASTEXITCODE -ne 0) { throw 'Windows build failed' }
} finally { Pop-Location }
