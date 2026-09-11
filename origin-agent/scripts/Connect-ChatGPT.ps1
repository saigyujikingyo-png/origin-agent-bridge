param([Parameter(Mandatory=$true)][string]$TunnelId,
      [string]$TunnelClient = 'tunnel-client', [switch]$Run)
$ErrorActionPreference = 'Stop'
if ($TunnelId -notmatch '^tunnel_[a-f0-9]+$') { throw 'Provide the tunnel ID from OpenAI Platform tunnel settings.' }
$stateRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.origin-agent'
$install = Get-Content -Raw -LiteralPath (Join-Path $stateRoot 'install.json') | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $install.executable)) { throw 'Install the Windows bundle first.' }
if (-not $env:CONTROL_PLANE_API_KEY) { throw 'Set CONTROL_PLANE_API_KEY locally; do not put it in chat or source files.' }
# The tunnel client's command parser treats backslashes as escapes, even on Windows.
$mcpCommand = '"' + $install.executable.Replace('\','/') + '" serve'
& $TunnelClient init --sample sample_mcp_stdio_local --profile origin-agent --tunnel-id $TunnelId --mcp-command $mcpCommand
if ($LASTEXITCODE -ne 0) { throw 'Tunnel profile setup failed.' }
& $TunnelClient doctor --profile origin-agent --explain
if ($LASTEXITCODE -ne 0) { throw 'Tunnel diagnostics failed.' }
if ($Run) { & $TunnelClient run --profile origin-agent }
