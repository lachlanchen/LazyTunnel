# Run with Windows PowerShell 5.1: powershell -NoProfile -File tests/windows-release.ps1
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$repo=Split-Path $PSScriptRoot -Parent
$saved=$env:USERPROFILE
$temp=Join-Path $env:TEMP ('lazytunnel-install-test-'+[guid]::NewGuid().ToString('N'))
$utf8=New-Object Text.UTF8Encoding($false)
try {
    $env:USERPROFILE=$temp
    $state=Join-Path $temp '.config\lazytunnel-fleet'
    New-Item -ItemType Directory $state -Force|Out-Null
    $bundle=Join-Path $state 'bundle.json'
    [IO.File]::WriteAllText($bundle,'{"peer":{"name":"test","user":"test"},"aliases":["test"]}',$utf8)
    $before=(Get-FileHash -LiteralPath $bundle).Hash
    $code=Join-Path $temp '.local\share\lazytunnel\client\code'
    New-Item -ItemType Directory $code -Force|Out-Null
    [IO.File]::WriteAllText((Join-Path $code 'lazytunnel.ps1'),"'legacy marker'",$utf8)
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'scripts\lazytunnel.ps1') install -NoLauncher
    if($LASTEXITCODE){throw 'Initial installation failed'}
    $base=Split-Path $code -Parent
    $revision=[IO.File]::ReadAllText((Join-Path $base 'current.txt')).Trim()
    $release=Join-Path $base ('releases\'+$revision)
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $code 'lazytunnel.ps1') update -Source $release -NoLauncher
    if($LASTEXITCODE){throw 'Installed updater failed'}
    $devices=& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $code 'lazytunnel.ps1') devices
    if($LASTEXITCODE -or $devices -notcontains 'ssh-lazy-test'){throw 'Installed CLI unusable'}
    if([IO.File]::ReadAllText((Join-Path $base 'legacy-client-before-update.ps1')) -ne "'legacy marker'"){throw 'Legacy backup overwritten'}
    if((Get-FileHash -LiteralPath $bundle).Hash -ne $before){throw 'Identity modified'}
    $bad=Join-Path $temp 'bad';New-Item -ItemType Directory $bad|Out-Null
    Copy-Item -Path (Join-Path $release '*.ps1') -Destination $bad
    [IO.File]::WriteAllText((Join-Path $bad 'fleet-prepare.ps1'),'function broken {',$utf8)
    try {
        $ErrorActionPreference='Continue'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $code 'lazytunnel.ps1') update -Source $bad -NoLauncher 2>$null
        $failed=$LASTEXITCODE
    } finally {$ErrorActionPreference='Stop'}
    if(!$failed){throw 'Invalid candidate accepted'}
    if([IO.File]::ReadAllText((Join-Path $base 'current.txt')).Trim() -ne $revision){throw 'Failed candidate replaced current'}
    'PASS: Windows install, self-update, legacy backup, identity preservation and invalid candidate rejection'
} finally {
    $env:USERPROFILE=$saved
    if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force}
}
