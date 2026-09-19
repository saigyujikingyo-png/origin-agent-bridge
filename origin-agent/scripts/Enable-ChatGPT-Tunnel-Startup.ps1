param([switch]$StartNow, [string]$ProfileSource = '', [string]$StateRoot = '')
$ErrorActionPreference = 'Stop'
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Management\Microsoft.PowerShell.Management.psd1')
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
if (-not $StateRoot) { $StateRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.origin-agent' }
$StateRoot = [IO.Path]::GetFullPath($StateRoot)
$install = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $StateRoot 'install.json') | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $install.executable -PathType Leaf)) { throw 'Install Origin Companion first.' }
if (-not $ProfileSource -and -not (Test-Path -LiteralPath (Join-Path $StateRoot 'cloud\profiles\origin-agent.yaml'))) {
    $legacyProfile = Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'tunnel-client\origin-agent.yaml'
    if (Test-Path -LiteralPath $legacyProfile -PathType Leaf) { $ProfileSource = $legacyProfile }
}
$arguments = @('tunnel', 'install-startup')
if ($ProfileSource) { $arguments += @('--profile-source', [IO.Path]::GetFullPath($ProfileSource)) }
if ($StartNow) { $arguments += '--start-now' }
$previousHome = $env:ORIGIN_AGENT_HOME
try {
    $env:ORIGIN_AGENT_HOME = $StateRoot
    & $install.executable @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Private connector setup failed. The installation receipt records rollback status.' }
} finally { $env:ORIGIN_AGENT_HOME = $previousHome }
