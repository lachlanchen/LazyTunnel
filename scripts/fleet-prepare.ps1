param([Parameter(Mandatory=$true)][string]$Name)
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[a-z0-9][a-z0-9-]{0,19}$') { throw 'Invalid device name' }
$root = Join-Path $env:USERPROFILE '.config\lazytunnel-fleet'
New-Item -ItemType Directory -Force $root | Out-Null
$keys = @{}
foreach ($role in @('tunnel','jump','login')) {
    $key = Join-Path $root ($role+'_ed25519')
    if (!(Test-Path $key)) {
        if (Test-Path ($key+'.pub')) { throw 'Orphaned public key' }
        & "$env:WINDIR\System32\OpenSSH\ssh-keygen.exe" -q -t ed25519 -N '""' -C ('lazy-fleet-'+$Name+'-'+$role) -f $key
        if ($LASTEXITCODE) { throw 'Key generation failed' }
    }
    $keys[$role+'_key'] = ((& "$env:WINDIR\System32\OpenSSH\ssh-keygen.exe" -y -f $key).Trim() -split '\s+')[0..1] -join ' '
    if ($LASTEXITCODE) { throw 'Private key read failed' }
}
$keys.name=$Name; $keys.user=$env:USERNAME; $keys.home=$env:USERPROFILE.Replace('\','/')
$keys.platform='windows'; $keys.hostname=$env:COMPUTERNAME; $keys.ssh_port=22
$keys.host_key=((Get-Content "$env:ProgramData\ssh\ssh_host_ed25519_key.pub" -Raw).Trim() -split '\s+')[0..1] -join ' '
$keys | ConvertTo-Json -Compress
