param([string]$ConfigPath = '')
$ErrorActionPreference = 'Stop'
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Management\Microsoft.PowerShell.Management.psd1')
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
if (-not $ConfigPath) { $ConfigPath = Join-Path $PSScriptRoot 'runtime-config.json' }
$ConfigPath = [IO.Path]::GetFullPath($ConfigPath)
$config = Get-Content -Raw -Encoding UTF8 -LiteralPath $ConfigPath | ConvertFrom-Json
$install = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $config.state_root 'install.json') | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $install.executable -PathType Leaf)) { throw 'Origin Companion is not installed.' }
# Stop records explicit user intent and reconciles only the selected account scope.
# Never use Stop-Process by executable name or Stop-ScheduledTask on an entire tree.
$previousHome = $env:ORIGIN_AGENT_HOME
try {
    $env:ORIGIN_AGENT_HOME = $config.state_root
    & $install.executable tunnel stop --config $ConfigPath
    if ($LASTEXITCODE -ne 0) { throw 'Private connector stop is not confirmed; unrelated processes were preserved.' }
    & $install.executable tunnel disable-startup --config $ConfigPath
    if ($LASTEXITCODE -ne 0) { throw 'The connector is stopped but disabling its startup registration was not confirmed.' }
} finally { $env:ORIGIN_AGENT_HOME = $previousHome }
