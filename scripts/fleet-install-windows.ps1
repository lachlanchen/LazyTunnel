param([Parameter(Mandatory=$true)][string]$Bundle, [switch]$Apply)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$b=Get-Content -LiteralPath $Bundle -Raw | ConvertFrom-Json
$p=$b.peer; $root=Join-Path $env:USERPROFILE '.config\lazytunnel-fleet'
$ssh="$env:WINDIR\System32\OpenSSH\ssh.exe"
$utf8=New-Object Text.UTF8Encoding($false)
if ($p.home -cne $env:USERPROFILE.Replace('\','/') -or $p.user -ine $env:USERNAME) { throw 'Wrong endpoint user' }
if (!$Apply) { 'Plan: '+$p.name; return }
$previous=Join-Path $root 'bundle.json'
$prior=$null
if(Test-Path $previous) {
    $prior=Get-Content $previous -Raw|ConvertFrom-Json
    $oldAccount=if($prior.peer.account){$prior.peer.account}else{'default'}
    $newAccount=if($p.account){$p.account}else{'default'}
    if($oldAccount -cne $newAccount){throw 'Account transfer requires explicit identity migration'}
}
function Write-Owned([string]$Path,[string]$Text) {
    if (Test-Path $Path) {
        if ((Get-Item -LiteralPath $Path).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Refusing reparse point' }
        if ([IO.File]::ReadAllText($Path) -ceq $Text) { return }
        $back=Join-Path $root 'backups';New-Item -ItemType Directory -Force $back|Out-Null
        $copy=Join-Path $back ((Split-Path -Leaf $Path)+'.'+(Get-FileHash $Path -Algorithm SHA256).Hash.Substring(0,16))
        if (!(Test-Path $copy)) { Copy-Item -LiteralPath $Path $copy }
    }
    New-Item -ItemType Directory -Force (Split-Path $Path)|Out-Null
    # Write in place to retain restrictive administrator authorized_keys ACLs.
    $attributes=if(Test-Path $Path){[IO.File]::GetAttributes($Path)}else{$null}
    try {
        if ($null -ne $attributes -and ($attributes -band [IO.FileAttributes]::ReadOnly)) {
            [IO.File]::SetAttributes($Path,($attributes -band (-bnot [IO.FileAttributes]::ReadOnly)))
        }
        [IO.File]::WriteAllText($Path,$Text,$utf8)
    } finally {
        if ($null -ne $attributes) {[IO.File]::SetAttributes($Path,$attributes)}
    }
}
foreach ($role in @('tunnel','jump','login')) {
    $key=Join-Path $root ($role+'_ed25519')
    $actual=((& "$env:WINDIR\System32\OpenSSH\ssh-keygen.exe" -y -f $key).Trim() -split '\s+')[0..1] -join ' '
    if ($LASTEXITCODE -or $actual -cne $p.($role+'_key')) { throw 'Local identity mismatch' }
}
$hostkey=((Get-Content "$env:ProgramData\ssh\ssh_host_ed25519_key.pub" -Raw).Trim() -split '\s+')[0..1] -join ' '
if ($hostkey -cne $p.host_key) { throw 'Host identity mismatch' }
$carrier=Join-Path $root 'carrier.conf'
if ((Test-Path $carrier) -and [IO.File]::ReadAllText($carrier) -cne $b.files.'carrier.conf') { throw 'Carrier migration requires explicit stop and review' }
$candidate=Join-Path $root 'candidate.conf';Write-Owned $candidate $b.files.ssh_config
& $ssh -G -F $candidate ('lazy-'+$p.name)|Out-Null
if ($LASTEXITCODE) { throw 'Invalid candidate SSH configuration' }
foreach ($name in @('ssh_config','known_hosts','carrier.conf','carrier.ps1')) {
    Write-Owned (Join-Path $root $name) $b.files.$name
}
$isAdmin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$authorized=if ($isAdmin) { "$env:ProgramData\ssh\administrators_authorized_keys" } else { Join-Path $env:USERPROFILE '.ssh\authorized_keys' }
if ($isAdmin -and !(Test-Path $authorized)) { throw 'Review administrator key file ACL before creating it' }
$rows=[Collections.Generic.List[string]]::new()
if (Test-Path $authorized) { foreach ($line in ([IO.File]::ReadAllText($authorized) -split "`r?`n")) { if($line) {$rows.Add($line)} } }
if($prior) {
    $managed=@($prior.files.'authorized_keys.append' -split "`r?`n" | Where-Object {$_})
    for($i=$rows.Count-1;$i -ge 0;$i--) {
        if($managed -ccontains $rows[$i]){$rows.RemoveAt($i)}
    }
}
foreach ($line in ($b.files.'authorized_keys.append' -split "`n")) {
    if (!$line) { continue };$blob=($line -split '\s+')[1];$found=$false
    foreach($row in $rows) { if (($row -split '\s+') -contains $blob) { $found=$true;break } }
    if (!$found) {$rows.Add($line)}
}
Write-Owned $authorized (($rows -join "`n")+"`n")
$config=Join-Path $env:USERPROFILE '.ssh\config'
$old=if(Test-Path $config){[IO.File]::ReadAllText($config)}else{''}
$include='Include ~/.config/lazytunnel-fleet/ssh_config'
if (!(($old -split "`r?`n") -contains $include)) { Write-Owned $config ($include+"`nHost *`n`n"+$old) }
$bin=Join-Path $env:USERPROFILE '.local\bin'
$bash='C:\Program Files\Git\bin\bash.exe'
if (!(Test-Path $bash)) {$bash=Join-Path $env:USERPROFILE '.local\share\lazytunnel\ssh-runtime\usr\bin\bash.exe'}
$gitBackend=Test-Path $bash
if ($gitBackend) {
    Write-Owned (Join-Path $root 'ssh_config.git') ($b.files.ssh_config.Replace('"C:/Windows/System32/OpenSSH/ssh.exe"','/usr/bin/ssh'))
    $script='#!/bin/sh'+"`n"+'export SHELL=/usr/bin/bash'+"`n"+'exec /usr/bin/ssh -F "$USERPROFILE/.config/lazytunnel-fleet/ssh_config.git" "$@"'+"`n"
    Write-Owned (Join-Path $root 'fleet-ssh.sh') $script
    Write-Owned (Join-Path $root 'fleet-scp.sh') ($script.Replace('exec /usr/bin/ssh','exec /usr/bin/scp -S /usr/bin/ssh'))
    $invoke="& '$bash' '$root\fleet-ssh.sh'"
    $cmdInvoke='"'+$bash+'" "'+$root+'\fleet-ssh.sh"'
    $scpInvoke='"'+$bash+'" "'+$root+'\fleet-scp.sh"'
} else {
    $invoke="& '$ssh' -F '$root\ssh_config'"
    $cmdInvoke='"'+$ssh+'" -F "'+$root+'\ssh_config"'
    $scpInvoke='"'+$env:WINDIR+'\System32\OpenSSH\scp.exe" -F "'+$root+'\ssh_config"'
}
Write-Owned (Join-Path $root 'fleet-ssh.ps1') ($invoke+" @args`nexit `$LASTEXITCODE`n")
Write-Owned (Join-Path $bin 'scp-lazy.cmd') ("@echo off`r`n"+$scpInvoke+" %*`r`n")
# Per-device commands forward the complete command line, with no fixed arg limit.
foreach($alias in $b.aliases) {
    Write-Owned (Join-Path $bin ('ssh-lazy-'+$alias+'.cmd')) ("@echo off`r`n"+$cmdInvoke+" lazy-$alias %*`r`n")
}
$functions="function global:ssh-lazy { param([string]`$Device) $invoke ('lazy-'+`$Device) @args }`n"
foreach($alias in $b.aliases) { $functions+="function global:ssh-lazy-$alias { $invoke 'lazy-$alias' @args }`n" }
Write-Owned (Join-Path $root 'shell.ps1') $functions
$profilePath=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'WindowsPowerShell\Microsoft.PowerShell_profile.ps1'
$source=". '$root\shell.ps1'"
$profileOld=if(Test-Path $profilePath){[IO.File]::ReadAllText($profilePath)}else{''}
if (!(($profileOld -split "`r?`n") -contains $source)) {Write-Owned $profilePath ($profileOld+"`n"+$source+"`n")}
$userPath=[Environment]::GetEnvironmentVariable('Path','User')
if (!(($userPath -split ';') -contains $bin)) {[Environment]::SetEnvironmentVariable('Path',$bin+';'+$userPath,'User')}
if (!$p.external_carrier) {
    $taskName='LazyTunnel-Fleet'
    $action=New-ScheduledTaskAction -Execute "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument ('-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$root+'\carrier.ps1"')
    $principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType S4U -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -ErrorAction Stop
    $existing=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    $triggers=@((New-ScheduledTaskTrigger -AtStartup),
        (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5)))
    if (!$existing) {
        Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Settings $settings -Trigger $triggers -Description 'LazyTunnel outbound SSH; independent of UU desktop sessions' -ErrorAction Stop | Out-Null
    } elseif ($existing.Actions.Arguments -cne $action.Arguments) { throw 'Task changed outside installer; review required' }
    elseif (!(@($existing.Triggers | Where-Object {$_.Repetition.Interval -eq 'PT5M'}).Count)) {
        # Native scheduler retry after a prolonged outage, without spawning
        # another worker while the existing connection is running.
        Set-ScheduledTask -TaskName $taskName -Trigger $triggers -Settings $settings -ErrorAction Stop | Out-Null
    }
    if (!$existing -or $existing.State -ne 'Running') {Start-ScheduledTask -TaskName $taskName -ErrorAction Stop}
}
[ordered]@{installed=$p.name; commands=$b.aliases.Count;task=(Get-ScheduledTask -TaskName 'LazyTunnel-Fleet').State}|ConvertTo-Json -Compress
