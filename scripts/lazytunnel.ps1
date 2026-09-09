param([Parameter(Position=0)][ValidateSet('install','update','prepare','login','sync','status','devices','boot','ssh','web')][string]$Command='status',
      [string]$Name, [string]$Bundle, [string]$Source=$PSScriptRoot,
      [string]$Device, [string]$Output, [int]$Port=0, [int]$LocalPort=0, [string]$Path='/',
      [switch]$NoLauncher,
      [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$state=Join-Path $env:USERPROFILE '.config\lazytunnel-fleet'
$code=Join-Path $env:USERPROFILE '.local\share\lazytunnel\client\code'
$ssh="$env:WINDIR\System32\OpenSSH\ssh.exe"
$utf8=New-Object Text.UTF8Encoding($false)
if($Command -in @('install','update')) {
    New-Item -ItemType Directory -Force $code|Out-Null
    foreach($file in @('lazytunnel.ps1','fleet-prepare.ps1','fleet-install-windows.ps1')) {
        $from=Join-Path $Source $file;$to=Join-Path $code $file
        if($from -ne $to) {Copy-Item -LiteralPath $from -Destination $to -Force}
    }
    if(!$NoLauncher) {
        $bin=Join-Path $env:USERPROFILE '.local\bin';New-Item -ItemType Directory -Force $bin|Out-Null
        [IO.File]::WriteAllText((Join-Path $bin 'lazytunnel.cmd'),('@echo off'+"`r`n"+'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "'+$code+'\lazytunnel.ps1" %*'+"`r`n"),$utf8)
    }
    'Client code installed; private identity and active task unchanged.';return
}
if($Command -eq 'prepare') {
    $text=(& (Join-Path $PSScriptRoot 'fleet-prepare.ps1') -Name $Name)-join "`n"
    if($Output){[IO.File]::WriteAllText($Output,$text,$utf8)}else{$text};return
}
if($Command -in @('login','sync')) {
    if($Command -eq 'sync') {
        $text=(& $ssh -F "$state\ssh_config" lazy-fleet-registry) -join "`n"
        if($LASTEXITCODE){throw 'Registry connection failed; current configuration retained'}
        $null=$text|ConvertFrom-Json
        $Bundle=Join-Path $state 'candidate.json';[IO.File]::WriteAllText($Bundle,$text,$utf8)
    }
    & (Join-Path $PSScriptRoot 'fleet-install-windows.ps1') -Bundle $Bundle -Apply
    if($LASTEXITCODE){throw 'Client activation failed'}
    if($Bundle -ne (Join-Path $state 'bundle.json')) {Copy-Item $Bundle (Join-Path $state 'bundle.json') -Force}
    'Client enrolled; aliases synchronized.';return
}
$b=Get-Content "$state\bundle.json" -Raw|ConvertFrom-Json
if($Command -eq 'boot') {
    $t=Get-ScheduledTask -TaskName LazyTunnel-Fleet
    Enable-ScheduledTask -TaskName LazyTunnel-Fleet|Out-Null
    if($t.State -ne 'Running'){Start-ScheduledTask -TaskName LazyTunnel-Fleet}
    'Boot task enabled; existing desktop unchanged.';return
}
if($Command -eq 'status') {[ordered]@{device=$b.peer.name;user=$b.peer.user;privateState=$state;task=[string](Get-ScheduledTask -TaskName LazyTunnel-Fleet).State}|ConvertTo-Json;return}
if($Command -eq 'devices') {$b.aliases|ForEach-Object{'ssh-lazy-'+$_};return}
if($b.aliases -notcontains $Device){throw 'Unknown enrolled device'}
if($Command -eq 'ssh') {& "$state\fleet-ssh.ps1" ('lazy-'+$Device) @Rest;exit $LASTEXITCODE}
if(!$LocalPort){$LocalPort=$Port}
if($Port -lt 1 -or $Port -gt 65535 -or $LocalPort -lt 1024 -or $LocalPort -gt 65535){throw 'Invalid port'}
if(Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue){throw 'Local port occupied; choose -LocalPort'}
'Open on THIS computer: http://127.0.0.1:'+$LocalPort+$Path
& "$state\fleet-ssh.ps1" -NT -o ExitOnForwardFailure=yes -L ('127.0.0.1:'+$LocalPort+':127.0.0.1:'+$Port) ('lazy-'+$Device)
exit $LASTEXITCODE
