param([string]$TunnelClient = '')
$ErrorActionPreference = 'Stop'
$stateRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.origin-agent'
$cloudRoot = Join-Path $stateRoot 'cloud'
New-Item -ItemType Directory -Path $cloudRoot -Force | Out-Null
$mutex = New-Object System.Threading.Mutex($false, ('Local\OriginCompanionTunnel-' + [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value))
$ownsMutex = $false
$exitCode = 0
try {
    try { $ownsMutex = $mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $ownsMutex = $true }
    if (-not $ownsMutex) { exit 0 }
    if (-not $TunnelClient) { $TunnelClient = Join-Path $stateRoot 'tunnel-client\v0.0.14\tunnel-client.exe' }
    if (-not (Test-Path -LiteralPath $TunnelClient -PathType Leaf)) { throw 'The configured tunnel-client is not installed.' }
    $failures = 0
    $retryDelays = @(5, 15, 30)
    while ($true) {
        try {
            $install = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $stateRoot 'install.json') | ConvertFrom-Json
            if (-not (Test-Path -LiteralPath $install.executable -PathType Leaf)) { throw 'Origin Companion is not installed.' }
            $profileDirectory = Join-Path $cloudRoot 'profiles'
            $profilePath = Join-Path $profileDirectory 'origin-agent.yaml'
            # The official managed connector writes JSON-compatible YAML. Keep the existing identity.
            $profile = Get-Content -Raw -Encoding UTF8 -LiteralPath $profilePath | ConvertFrom-Json
            $tunnelId = $profile.control_plane.tunnel_id
            if ($tunnelId -notmatch '^tunnel_[a-f0-9]+$') { throw 'No valid existing private tunnel profile was found.' }
            $secretFile = Join-Path $stateRoot 'secrets\tunnel-key.dpapi'
            $secureKey = ConvertTo-SecureString (Get-Content -Raw -LiteralPath $secretFile).Trim()
            $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
            try { $env:CONTROL_PLANE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer).Trim() }
            finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
            if ($env:CONTROL_PLANE_API_KEY -notmatch '^sk-') { throw 'The stored runtime key is invalid.' }
            $mcpCommand = '"' + $install.executable.Replace('\','/') + '" serve'
            $connectText = & $TunnelClient runtimes connect --json --alias origin-agent --profile origin-agent --profile-dir $profileDirectory --tunnel-id $tunnelId --mcp-command $mcpCommand --runtime-api-key env:CONTROL_PLANE_API_KEY
            if ($LASTEXITCODE -ne 0) { throw 'Managed tunnel connection failed.' }
            $statusText = & $TunnelClient runtimes status origin-agent --json
            if ($LASTEXITCODE -ne 0) { throw 'Managed tunnel status failed.' }
            $status = $statusText | ConvertFrom-Json
            if (-not $status.process_running -or -not $status.ready) { throw 'Managed tunnel was not ready.' }
            Remove-Item Env:CONTROL_PLANE_API_KEY -ErrorAction SilentlyContinue
            $secureKey.Dispose(); $secureKey = $null
            $tunnelProcess = Get-Process -Id $status.process.pid -ErrorAction Stop
            $processStarted = $tunnelProcess.StartTime
            [pscustomobject]@{startedUtc=[DateTime]::UtcNow.ToString('o');wrapperPid=$PID;tunnelPid=$tunnelProcess.Id;engineVersion=$install.version;recoveryAttempt=$failures;ready=$status.ready;healthy=$status.healthy} | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $cloudRoot 'background-status.json')
            $readyAt = [DateTime]::UtcNow
            # One Work acceptance task instance ended without its scheduled restart.
            # Supervise the actual child directly rather than infer the scheduler cause.
            while ($true) {
                Start-Sleep -Seconds 30
                $current = Get-Process -Id $tunnelProcess.Id -ErrorAction SilentlyContinue
                if (-not $current -or $current.StartTime -ne $processStarted) { throw 'The managed tunnel process stopped.' }
                if (([DateTime]::UtcNow - $readyAt).TotalSeconds -ge 300) { $failures = 0 }
            }
        } catch {
            $failures += 1
            $delay = if ($failures -le $retryDelays.Count) { $retryDelays[$failures - 1] } else { 0 }
            [pscustomobject]@{failedUtc=[DateTime]::UtcNow.ToString('o');error=$_.Exception.Message;consecutiveFailures=$failures;retryInSeconds=$delay} | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $cloudRoot 'background-error.json')
            if ($delay -eq 0) { throw }
            Start-Sleep -Seconds $delay
        } finally {
            Remove-Item Env:CONTROL_PLANE_API_KEY -ErrorAction SilentlyContinue
            if ($secureKey) { $secureKey.Dispose(); $secureKey = $null }
        }
    }
} catch {
    [pscustomobject]@{failedUtc=[DateTime]::UtcNow.ToString('o');error=$_.Exception.Message} | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $cloudRoot 'background-error.json')
    $exitCode = 1
} finally {
    Remove-Item Env:CONTROL_PLANE_API_KEY -ErrorAction SilentlyContinue
    if ($secureKey) { $secureKey.Dispose() }
    if ($ownsMutex) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
exit $exitCode