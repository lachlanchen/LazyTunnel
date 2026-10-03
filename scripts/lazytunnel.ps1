param([Parameter(Position=0)][ValidateSet('install','update','prepare','login','sync','status','devices','boot','ssh','web')][string]$Command='status',
      [string]$Name, [string]$Bundle, [string]$Source,
      [string]$Device, [string]$Output, [int]$Port=0, [int]$LocalPort=0, [string]$Path='/',
      [switch]$NoLauncher,
      [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
if(!$Source){$Source=$PSScriptRoot}
$state=Join-Path $env:USERPROFILE '.config\lazytunnel-fleet'
$code=Join-Path $env:USERPROFILE '.local\share\lazytunnel\client\code'
$ssh="$env:WINDIR\System32\OpenSSH\ssh.exe"
$utf8=New-Object Text.UTF8Encoding($false)
if($Command -in @('install','update')) {
    $base=Split-Path $code -Parent
    New-Item -ItemType Directory -Force $base|Out-Null
    $lock=[IO.File]::Open((Join-Path $base '.update.lock'),'OpenOrCreate','ReadWrite','None')
    try {
        $files=@('lazytunnel.ps1','fleet-prepare.ps1','fleet-install-windows.ps1')
        $hashes=@()
        foreach($file in $files) {
            $from=Join-Path $Source $file
            $tokens=$null;$errors=$null
            $null=[Management.Automation.Language.Parser]::ParseFile($from,[ref]$tokens,[ref]$errors)
            if($errors.Count){throw ('Candidate syntax check failed: '+$file)}
            $hashes+=($file+':'+(Get-FileHash -LiteralPath $from -Algorithm SHA256).Hash)
        }
        $sha=[Security.Cryptography.SHA256]::Create()
        try {$digest=([BitConverter]::ToString($sha.ComputeHash($utf8.GetBytes(($hashes -join "`n"))))).Replace('-','').ToLower()}
        finally {$sha.Dispose()}
        $release=Join-Path $base ('releases\'+$digest)
        if(Test-Path -LiteralPath $release) {
            foreach($file in $files) {
                if((Get-FileHash -LiteralPath (Join-Path $release $file)).Hash -ne (Get-FileHash -LiteralPath (Join-Path $Source $file)).Hash){throw 'Existing release differs; refusing overwrite'}
            }
        } else {
            $stage=Join-Path $base ('.candidate-'+[guid]::NewGuid().ToString('N'))
            New-Item -ItemType Directory $stage|Out-Null
            try {
                foreach($file in $files){Copy-Item -LiteralPath (Join-Path $Source $file) -Destination (Join-Path $stage $file)}
                New-Item -ItemType Directory -Force (Split-Path $release -Parent)|Out-Null
                Move-Item -LiteralPath $stage -Destination $release
            } finally {if(Test-Path -LiteralPath $stage){Remove-Item -LiteralPath $stage -Recurse -Force}}
        }
        $pointer=Join-Path $base 'current.txt'
        $pending=Join-Path $base ('.current-'+[guid]::NewGuid().ToString('N'))
        [IO.File]::WriteAllText($pending,$digest,$utf8)
        if(Test-Path -LiteralPath $pointer) {
            if([IO.File]::ReadAllText($pointer).Trim() -ne $digest) {
                [IO.File]::Replace($pending,$pointer,(Join-Path $base 'previous.txt'))
            } else {Remove-Item -LiteralPath $pending}
        } else {[IO.File]::Move($pending,$pointer)}
        New-Item -ItemType Directory -Force $code|Out-Null
        $shim=@'
# Managed by LazyTunnel immutable Windows client
$ErrorActionPreference='Stop'
$base=Split-Path $PSScriptRoot -Parent
$revision=[IO.File]::ReadAllText((Join-Path $base 'current.txt')).Trim()
if($revision -notmatch '^[a-f0-9]{64}$'){throw 'Invalid LazyTunnel release pointer'}
& (Join-Path $base ('releases\'+$revision+'\lazytunnel.ps1')) @args
if($null -ne $LASTEXITCODE){exit $LASTEXITCODE}
'@
        $compat=Join-Path $code 'lazytunnel.ps1'
        $legacy=Join-Path $base 'legacy-client-before-update.ps1'
        if((Test-Path -LiteralPath $compat) -and !(Test-Path -LiteralPath $legacy)) {
            Copy-Item -LiteralPath $compat -Destination $legacy
        }
        $pending=Join-Path $code ('.shim-'+[guid]::NewGuid().ToString('N'))
        [IO.File]::WriteAllText($pending,$shim,$utf8)
        if(Test-Path -LiteralPath $compat){
            # Windows PowerShell 5.1 can coerce a null backup path to an invalid
            # empty string. Use an explicit temporary backup, then remove it.
            $replaced=Join-Path $code ('.replaced-'+[guid]::NewGuid().ToString('N'))
            [IO.File]::Replace($pending,$compat,$replaced)
            Remove-Item -LiteralPath $replaced
        }
        else {[IO.File]::Move($pending,$compat)}
        if(!$NoLauncher) {
            $bin=Join-Path $env:USERPROFILE '.local\bin';New-Item -ItemType Directory -Force $bin|Out-Null
            [IO.File]::WriteAllText((Join-Path $bin 'lazytunnel.cmd'),('@echo off'+"`r`n"+'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "'+$code+'\lazytunnel.ps1" %*'+"`r`n"),$utf8)
        }
        'Client code installed: '+$digest+'; private identity and active task unchanged.';return
    } finally {$lock.Dispose()}
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
