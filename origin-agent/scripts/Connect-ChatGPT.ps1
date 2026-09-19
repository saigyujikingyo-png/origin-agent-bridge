param([Parameter(Mandatory=$true)][string]$TunnelId,
      [string]$TunnelClient = 'tunnel-client', [switch]$Run, [string]$StateRoot = '')
$ErrorActionPreference = 'Stop'
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Management\Microsoft.PowerShell.Management.psd1')
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
if ($TunnelId -notmatch '^tunnel_[a-f0-9]+$') { throw 'Provide the tunnel ID from OpenAI Platform tunnel settings.' }
if (-not $StateRoot) { $StateRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.origin-agent' }
$StateRoot = [IO.Path]::GetFullPath($StateRoot)
$install = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $StateRoot 'install.json') | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $install.executable -PathType Leaf)) { throw 'Install the Windows bundle first.' }
$previousHome = $env:ORIGIN_AGENT_HOME
try {
    $env:ORIGIN_AGENT_HOME = $StateRoot
    if ($Run) {
        $configPath = Join-Path $StateRoot 'cloud\runtime-config.json'
        $profilePath = Join-Path $StateRoot 'cloud\profiles\origin-agent.yaml'
        $profile = Get-Content -Raw -Encoding UTF8 -LiteralPath $profilePath | ConvertFrom-Json
        if ($profile.control_plane.tunnel_id -ne $TunnelId) {
            throw 'The requested tunnel does not match this account profile; its existing identity was preserved.'
        }
        if (Test-Path -LiteralPath $configPath -PathType Leaf) {
            if (-not $env:CONTROL_PLANE_API_KEY) { throw 'Set the existing runtime key locally; never put it in chat or source files.' }
            & $install.executable tunnel allow-start --config $configPath
            if ($LASTEXITCODE -ne 0) { throw 'The existing connector could not be enabled.' }
            & $install.executable tunnel run --config $configPath
            if ($LASTEXITCODE -ne 0) { throw 'The managed private connector did not start; check lifecycle status.' }
        } else {
            # Migrate the existing identity and DPAPI credential through the same
            # source-owned startup path; never call vendor connect independently.
            & $install.executable tunnel install-startup --start-now
            if ($LASTEXITCODE -ne 0) { throw 'The existing private connector could not be migrated and started.' }
        }
        return
    }
    if (-not $env:CONTROL_PLANE_API_KEY) { throw 'Set CONTROL_PLANE_API_KEY locally; do not put it in chat or source files.' }
    $resolvedClient = (Get-Command -Name $TunnelClient -CommandType Application -ErrorAction Stop).Source
    & $install.executable tunnel initialize --tunnel-id $TunnelId --tunnel-client $resolvedClient
    if ($LASTEXITCODE -ne 0) { throw 'Private connector initialization failed; existing account profiles were preserved.' }
} finally { $env:ORIGIN_AGENT_HOME = $previousHome }
