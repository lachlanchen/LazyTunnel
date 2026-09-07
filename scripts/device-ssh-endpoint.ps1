param([switch]$Prepare, [string]$Name, [string]$Bundle)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Join-Path $env:USERPROFILE '.ssh'
$utf8 = New-Object System.Text.UTF8Encoding($false)
New-Item -ItemType Directory -Force -Path $root | Out-Null

function Write-Reviewed([string]$Path, [string]$Text) {
    if (Test-Path $Path) {
        if ([IO.File]::ReadAllText($Path) -ceq $Text) { return }
        $backupDir = Join-Path $root 'device-ssh-backups'
        New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
        $hash = (Get-FileHash -Algorithm SHA256 $Path).Hash.Substring(0,16)
        $backup = Join-Path $backupDir ((Split-Path -Leaf $Path)+'.'+$hash)
        if (!(Test-Path $backup)) { Copy-Item -LiteralPath $Path -Destination $backup }
    }
    [IO.File]::WriteAllText($Path, $Text, $utf8)
}

if ($Prepare) {
    if ($Name -notmatch '^[a-z0-9][a-z0-9-]{0,40}$') { throw 'Invalid device name' }
    $pubs = @{}
    foreach ($suffix in @('', '_hop')) {
        $key = Join-Path $root ('id_ed25519_devices'+$suffix)
        if (!(Test-Path $key)) {
            if (Test-Path ($key+'.pub')) { throw 'Public key exists without private key' }
            & ssh-keygen.exe -q -t ed25519 -N '""' -C ('device-ssh-'+$Name+$suffix) -f $key
            if ($LASTEXITCODE -ne 0) { throw 'Key generation failed' }
        }
        $pubs[$suffix] = (& ssh-keygen.exe -y -f $key).Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Key read failed' }
    }
    [ordered]@{name=$Name; hostname=$env:COMPUTERNAME; home=$env:USERPROFILE;
        public_key=$pubs['']; hop_public_key=$pubs['_hop'];
        host_key=(Get-Content "$env:ProgramData\ssh\ssh_host_ed25519_key.pub" -Raw).Trim()
    } | ConvertTo-Json -Compress
    exit
}
if (!$Bundle) { throw 'Specify -Prepare -Name device or -Bundle reviewed.json' }
$b = Get-Content -LiteralPath $Bundle -Raw | ConvertFrom-Json
if (!$b.config.StartsWith("# Managed device SSH peers`n")) { throw 'Unreviewed configuration' }
foreach ($key in $b.authorized_keys) {
    if ($key -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+(?: .*)?$') { throw 'Invalid public key' }
}
$candidate = Join-Path $root 'devices-candidate.conf'
[IO.File]::WriteAllText($candidate, $b.config, $utf8)
& ssh.exe -G -F $candidate device-server | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Candidate SSH configuration failed validation' }

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
# Microsoft OpenSSH's standard administrator key file, preserving its ACL.
$authorized = if ($admin) { "$env:ProgramData\ssh\administrators_authorized_keys" } else { Join-Path $root 'authorized_keys' }
if ($admin -and !(Test-Path $authorized)) { throw 'Review administrator authorized_keys ACL before creating it' }
$old = if (Test-Path $authorized) { [IO.File]::ReadAllText($authorized) } else { '' }
$lines = [System.Collections.Generic.List[string]]::new()
foreach ($line in ($old -split "`r?`n")) { if ($line) { $lines.Add($line) } }
foreach ($key in $b.authorized_keys) {
    $fields = $key -split '\s+'
    $blob = $fields[1]
    $found = $false
    foreach ($line in $lines) { if (($line -split '\s+') -contains $blob) { $found = $true; break } }
    if (!$found) { $lines.Add($fields[0]+' '+$blob+' device-ssh') }
}
Write-Reviewed $authorized (($lines -join "`n")+"`n")
Write-Reviewed (Join-Path $root 'devices_known_hosts') $b.known_hosts
Write-Reviewed (Join-Path $root 'devices.conf') $b.config
$configPath = Join-Path $root 'config'
$oldConfig = if (Test-Path $configPath) { [IO.File]::ReadAllText($configPath) } else { '' }
$include = 'Include ~/.ssh/devices.conf'
if (!(($oldConfig -split "`r?`n") -contains $include)) {
    Write-Reviewed $configPath ($include+"`nHost *`n`n"+$oldConfig)
}
& ssh.exe -G device-server | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Installed SSH configuration failed validation' }
[ordered]@{installed=$true; home=$env:USERPROFILE; keys=$b.authorized_keys.Count; authorized_keys=$authorized} | ConvertTo-Json -Compress
