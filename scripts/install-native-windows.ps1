param([Parameter(Mandatory=$true)][string]$Bundle, [switch]$DesktopShortcut)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $Bundle).Path
if (-not (Test-Path -LiteralPath (Join-Path $source 'lazytunnel_app.exe')) -or
    -not (Test-Path -LiteralPath (Join-Path $source 'flutter_windows.dll'))) {
    throw 'Select the complete Windows Release directory, not just the EXE.'
}
$root = Join-Path $env:LOCALAPPDATA 'LazyTunnel\native'
$files = Get-ChildItem -LiteralPath $source -File -Recurse | Sort-Object FullName
if (Get-ChildItem -LiteralPath $source -Recurse | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
    throw 'Refusing links inside the release bundle.'
}
$hashes = ($files | ForEach-Object { $_.FullName.Substring($source.Length) + ':' + (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }) -join "`n"
$sha = [Security.Cryptography.SHA256]::Create()
try { $version = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($hashes)))).Replace('-','').Substring(0,16).ToLower() }
finally { $sha.Dispose() }
$destination = Join-Path $root "releases\$version"
if (Test-Path -LiteralPath $destination) {
    if ((Get-Content -LiteralPath (Join-Path $destination '.lazytunnel-native') -Raw).Trim() -ne $version) {
        throw 'Existing directory is not owned by this installer.'
    }
} else {
    New-Item -ItemType Directory -Force $destination | Out-Null
    Copy-Item -Path (Join-Path $source '*') -Destination $destination -Recurse
    Set-Content -LiteralPath (Join-Path $destination '.lazytunnel-native') -Value $version
}
$shell = New-Object -ComObject WScript.Shell
$locations = @([Environment]::GetFolderPath('Programs'))
if ($DesktopShortcut) { $locations += [Environment]::GetFolderPath('Desktop') }
foreach ($folder in $locations) {
    $link = Join-Path $folder 'LazyTunnel Native.lnk'
    $shortcut = $shell.CreateShortcut($link)
    if ((Test-Path -LiteralPath $link) -and -not $shortcut.TargetPath.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing to overwrite an unrelated shortcut.'
    }
    $shortcut.TargetPath = Join-Path $destination 'lazytunnel_app.exe'
    $shortcut.WorkingDirectory = $destination
    $shortcut.Description = 'Private computers, SSH terminals and desktop viewers'
    $shortcut.IconLocation = $shortcut.TargetPath + ',0'
    $shortcut.Save()
}
Write-Output "Native GUI installed: $destination"
Write-Output 'Open LazyTunnel Native from Start. SSH, remote desktops and existing windows were preserved.'
