param([string]$Destination = '', [string]$Hosts = '', [switch]$NonInteractive,
      [switch]$ConfigureClaude, [string]$StateRoot = '', [string]$UserHome = '',
      [string]$AppDataDirectory = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
$bundleRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
if (-not $UserHome) { $UserHome = [Environment]::GetFolderPath('UserProfile') }
if (-not $AppDataDirectory) { $AppDataDirectory = Join-Path $UserHome 'AppData\Roaming' }
if (-not $StateRoot) { $StateRoot = Join-Path $UserHome '.origin-agent' }
$StateRoot = [IO.Path]::GetFullPath($StateRoot)
if ($ConfigureClaude -and -not $Hosts) { $Hosts = 'claude' }
if (-not $NonInteractive -and -not $Hosts) {
    Write-Host 'Origin Companion - choose local agents (comma-separated):'
    Write-Host 'claude, workbuddy, codex  (Enter installs the engine and generated configurations only)'
    $Hosts = Read-Host 'Agents'
}
if ($Hosts -and ($Hosts.Split(',').Trim() | Where-Object { $_ -notin @('claude','workbuddy','codex') })) {
    throw 'Supported local hosts: claude, workbuddy, codex. ChatGPT uses Connect-ChatGPT.ps1.'
}
$checksums = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $bundleRoot 'checksums.json') | ConvertFrom-Json
function Test-Bundle([string]$Root) {
    $expected = @{}
    foreach ($entry in $checksums.PSObject.Properties) {
        if ($entry.Name -match '(^[/\\]|:|(^|[/\\])\.\.([/\\]|$))') { throw 'Invalid checksum path.' }
        $source = [IO.Path]::GetFullPath((Join-Path $Root $entry.Name))
        if (-not $source.StartsWith($Root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid checksum path.' }
        if (-not (Test-Path -LiteralPath $source -PathType Leaf) -or
            (Get-Item -LiteralPath $source).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint) -or
            (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant() -ne $entry.Value) {
            throw ('Integrity check failed: ' + $entry.Name)
        }
        $expected[$source] = $true
    }
    foreach ($item in Get-ChildItem -Force -Recurse -LiteralPath $Root) {
        if ($item.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)) { throw 'Links are not permitted in the release bundle.' }
        if (-not $item.PSIsContainer -and $item.FullName -ne (Join-Path $Root 'checksums.json') -and -not $expected.ContainsKey($item.FullName)) {
            throw ('Unexpected release file: ' + $item.Name)
        }
    }
}
Test-Bundle $bundleRoot
$appManifest = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $bundleRoot 'manifest.json') | ConvertFrom-Json
$version = $appManifest.version
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid release version.' }
if (-not $Destination) { $Destination = Join-Path $StateRoot ('app\' + $version) }
$Destination = [IO.Path]::GetFullPath($Destination).TrimEnd('\')
if ($Destination -eq $bundleRoot -or $Destination.StartsWith($bundleRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Choose an installation directory outside the extracted release folder.'
}
if (Test-Path -LiteralPath $Destination) {
    Test-Bundle $Destination
} else {
    $stage = $Destination + '.staging-' + [guid]::NewGuid().ToString('N')
    New-Item -ItemType Directory -Path $stage -Force | Out-Null
    foreach ($item in Get-ChildItem -Force -LiteralPath $bundleRoot) {
        Copy-Item -LiteralPath $item.FullName -Destination $stage -Recurse -Force
    }
    Test-Bundle $stage
    Move-Item -LiteralPath $stage -Destination $Destination
}
$executable = Join-Path $Destination 'server\origin-agent.exe'
$previousHome = $env:ORIGIN_AGENT_HOME
try {
    $env:ORIGIN_AGENT_HOME = $StateRoot
    Write-Host 'Checking the licensed Origin installation with a synthetic project...'
    $check = & $executable doctor --native
    if ($LASTEXITCODE -ne 0) { throw 'Origin self-check failed. The active installation and host settings were not changed.' }
    $checkResult = $check | ConvertFrom-Json
    if (-not $checkResult.native_readback) { throw 'Origin self-check did not return verified data.' }
    $arguments = @('integrate', $Destination, '--user-home', $UserHome, '--appdata', $AppDataDirectory)
    if ($Hosts) { $arguments += @('--hosts', $Hosts) }
    $result = & $executable @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Host configuration failed; see the installation receipt for rollback status.' }
    $result
    Write-Host ('Installed Origin Companion ' + $version + '. Restart selected agents to load the new tools.')
    Write-Host 'ChatGPT: reconnect the existing tunnel, or run Connect-ChatGPT.ps1 with your own account.'
} finally {
    $env:ORIGIN_AGENT_HOME = $previousHome
}
