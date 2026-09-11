param([switch]$StartNow, [string]$ProfileSource = '')
$ErrorActionPreference = 'Stop'
$stateRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.origin-agent'
$cloudRoot = Join-Path $stateRoot 'cloud'
$source = Join-Path $PSScriptRoot 'Run-ChatGPT-Tunnel.ps1'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw 'Run-ChatGPT-Tunnel.ps1 must be beside this script.' }
if (-not (Test-Path -LiteralPath (Join-Path $stateRoot 'secrets\tunnel-key.dpapi'))) { throw 'Set up this user private tunnel first.' }
New-Item -ItemType Directory -Path $cloudRoot -Force | Out-Null
# Avoid MSIX AppData redirection: background Windows tasks need a shared per-user path.
$profileDirectory = Join-Path $cloudRoot 'profiles'
$profileDestination = Join-Path $profileDirectory 'origin-agent.yaml'
if (-not (Test-Path -LiteralPath $profileDestination)) {
    if (-not $ProfileSource) { $ProfileSource = Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'tunnel-client\origin-agent.yaml' }
    $profileText = Get-Content -Raw -Encoding UTF8 -LiteralPath $ProfileSource
    $profile = $profileText | ConvertFrom-Json
    if ($profile.control_plane.tunnel_id -notmatch '^tunnel_[a-f0-9]+$') { throw 'The existing tunnel profile is invalid.' }
    if ($profile.control_plane.api_key -ne 'env:CONTROL_PLANE_API_KEY') { throw 'Use an environment reference for the existing runtime key before enabling startup.' }
    New-Item -ItemType Directory -Path $profileDirectory -Force | Out-Null
    [System.IO.File]::WriteAllText($profileDestination,$profileText,[System.Text.UTF8Encoding]::new($false))
}
$destination = Join-Path $cloudRoot 'Run-ChatGPT-Tunnel.ps1'
$taskPrefix = 'Origin Companion Private Tunnel'
$userSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskName = $taskPrefix + '-' + $userSid
# Preserve this user's already installed legacy task, without colliding with other Windows accounts.
$legacy = Get-ScheduledTask -TaskName $taskPrefix -ErrorAction SilentlyContinue
$expectedArguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $destination + '"'
if ($legacy -and $legacy.Actions.Arguments -contains $expectedArguments) { $taskName = $taskPrefix }
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.Actions.Arguments -notcontains ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $destination + '"')) { throw 'An unrelated task uses this name; no changes made.' }
    Export-ScheduledTask -TaskName $taskName | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $cloudRoot ('task-backup-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '.xml'))
}
if (Test-Path -LiteralPath $destination) { Copy-Item -LiteralPath $destination -Destination (Join-Path $cloudRoot ('launcher-backup-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '.ps1')) }
Copy-Item -LiteralPath $source -Destination $destination -Force
$windowsPowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $destination + '"'
$userName = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $windowsPowerShell -Argument $arguments -WorkingDirectory $stateRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $userName
$principal = New-ScheduledTaskPrincipal -UserId $userName -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Keep the existing private Origin Companion cloud connection available while this user is logged in, independently of Codex.' -Force | Out-Null
if ($StartNow) { Start-ScheduledTask -TaskName $taskName }
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State,@{Name='RunLevel';Expression={$_.Principal.RunLevel}},@{Name='LogonType';Expression={$_.Principal.LogonType}}