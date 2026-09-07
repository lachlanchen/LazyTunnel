# Source from a PowerShell profile. Only device-* peers use Git's SSH stack.
# Other existing SSH names keep Windows OpenSSH; no service or machine PATH change.
$global:DeviceSshDispatch = Join-Path $PSScriptRoot 'device-ssh-dispatch.sh'
$global:DeviceSshBash = Join-Path $env:ProgramFiles 'Git\bin\bash.exe'

function global:Invoke-DeviceSshTool {
    param([string]$Tool, [object[]]$ToolArguments)
    if (!(Test-Path $global:DeviceSshBash)) { throw 'Git for Windows Bash is required for device SSH' }
    $dispatchPath = $global:DeviceSshDispatch.Replace('\','/')
    & $global:DeviceSshBash --noprofile --norc $dispatchPath $Tool @ToolArguments
}

function global:ssh-device {
    param([Parameter(Mandatory=$true,Position=0)][ValidatePattern('^[a-zA-Z0-9-]+$')][string]$Name,
          [Parameter(ValueFromRemainingArguments=$true)][string[]]$RemoteCommand)
    Invoke-DeviceSshTool 'ssh' (@('device-'+$Name)+$RemoteCommand)
}

# Avoid replacing a user's own existing functions/aliases. A second source
# leaves our already installed functions in place (they use the refreshed paths).
if ((Get-Command ssh -ErrorAction SilentlyContinue).CommandType -eq 'Application') {
    function global:ssh {
        if (@($args | Where-Object { "$_" -match '^device-[A-Za-z0-9-]+(?=:|$)' }).Count) {
            Invoke-DeviceSshTool 'ssh' $args
        } else { & "$env:WINDIR\System32\OpenSSH\ssh.exe" @args }
    }
}
if ((Get-Command scp -ErrorAction SilentlyContinue).CommandType -eq 'Application') {
    function global:scp {
        if (@($args | Where-Object { "$_" -match '^device-[A-Za-z0-9-]+:' }).Count) {
            Invoke-DeviceSshTool 'scp' $args
        } else { & "$env:WINDIR\System32\OpenSSH\scp.exe" @args }
    }
}
if ((Get-Command sftp -ErrorAction SilentlyContinue).CommandType -eq 'Application') {
    function global:sftp {
        if (@($args | Where-Object { "$_" -match '^device-[A-Za-z0-9-]+(?=:|$)' }).Count) {
            Invoke-DeviceSshTool 'sftp' $args
        } else { & "$env:WINDIR\System32\OpenSSH\sftp.exe" @args }
    }
}
