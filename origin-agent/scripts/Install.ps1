param([string]$Destination = '', [switch]$ConfigureClaude)
$ErrorActionPreference = 'Stop'
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
$bundleRoot = [IO.Path]::GetFullPath($PSScriptRoot)
if (-not (Test-Path -LiteralPath (Join-Path $bundleRoot 'server\origin-agent.exe'))) {
    throw 'Run this installer from the extracted Windows release ZIP.'
}
$appManifest = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $bundleRoot 'manifest.json') | ConvertFrom-Json
$version = $appManifest.version
$stateRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.origin-agent'
if (-not $Destination) { $Destination = Join-Path $stateRoot ('app\' + $version) }
$Destination = [IO.Path]::GetFullPath($Destination)
if ($Destination -eq $bundleRoot -or $Destination.StartsWith($bundleRoot + [IO.Path]::DirectorySeparatorChar)) {
    throw 'Choose an installation directory outside the extracted release folder.'
}
$checksumFile = Join-Path $bundleRoot 'checksums.json'
$checksums = Get-Content -Raw -Encoding UTF8 -LiteralPath $checksumFile | ConvertFrom-Json
foreach ($entry in $checksums.PSObject.Properties) {
    $source = [IO.Path]::GetFullPath((Join-Path $bundleRoot $entry.Name))
    if (-not $source.StartsWith($bundleRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Invalid checksum path.' }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant() -ne $entry.Value) {
        throw ('Integrity check failed: ' + $entry.Name)
    }
}
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
foreach ($item in Get-ChildItem -Force -Recurse -File -LiteralPath $bundleRoot) {
    $relative = $item.FullName.Substring($bundleRoot.Length + 1)
    $target = Join-Path $Destination $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    if ((Test-Path -LiteralPath $target) -and
        ((Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash -eq (Get-FileHash -Algorithm SHA256 -LiteralPath $item.FullName).Hash)) { continue }
    Copy-Item -LiteralPath $item.FullName -Destination $target -Force
}
$executable = Join-Path $Destination 'server\origin-agent.exe'
$env:ORIGIN_AGENT_HOME = $stateRoot
$statusText = & $executable status
if ($LASTEXITCODE -ne 0) { throw 'Installed executable failed its self-check.' }
$status = $statusText | ConvertFrom-Json
$hostConfig = @{mcpServers=@{'origin-agent'=@{type='stdio';command=$executable;args=@('serve');env=@{ORIGIN_AGENT_HOME=$stateRoot}}}}
$hostDirectory = Join-Path $Destination 'host-configs'
New-Item -ItemType Directory -Path $hostDirectory -Force | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
$json = $hostConfig | ConvertTo-Json -Depth 10
foreach ($name in @('claude-desktop.json','workbuddy.json','generic-mcp.json')) {
    [IO.File]::WriteAllText((Join-Path $hostDirectory $name),$json,$utf8)
}
# Local manifests get absolute paths generated on this computer, never a developer's home path.
foreach ($name in @('.mcp.json','mcp.json')) {
    $content = $json
    if ($name -eq 'mcp.json') {
        $portableConfig = @{'$schema'='https://agent-plugins.org/schemas/1.0.0/mcp.schema.json';mcpServers=$hostConfig.mcpServers}
        $content = $portableConfig | ConvertTo-Json -Depth 10
    }
    [IO.File]::WriteAllText((Join-Path $Destination $name),$content,$utf8)
}
[IO.File]::WriteAllText((Join-Path $Destination 'workbuddy\mcp.json'),$json,$utf8)
Copy-Item -LiteralPath (Join-Path $Destination 'skills') -Destination (Join-Path $Destination 'workbuddy') -Recurse -Force
Compress-Archive -Path (Join-Path $Destination 'workbuddy\*') -DestinationPath (Join-Path $hostDirectory 'workbuddy-connector.zip') -Force
New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $stateRoot 'install.json'),(@{version=$version;executable=$executable;root=$Destination}|ConvertTo-Json),$utf8)
if ($ConfigureClaude) {
    $claudeConfig = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
    New-Item -ItemType Directory -Path (Split-Path -Parent $claudeConfig) -Force | Out-Null
    $existing = if (Test-Path -LiteralPath $claudeConfig) { Get-Content -Raw -Encoding UTF8 -LiteralPath $claudeConfig | ConvertFrom-Json } else { [pscustomobject]@{} }
    if (-not $existing.PSObject.Properties['mcpServers']) { $existing | Add-Member mcpServers ([pscustomobject]@{}) }
    if (Test-Path -LiteralPath $claudeConfig) {
        $backup = $claudeConfig + '.origin-agent.' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.bak'
        Copy-Item -LiteralPath $claudeConfig -Destination $backup
    }
    $existing.mcpServers | Add-Member -NotePropertyName 'origin-agent' -NotePropertyValue $hostConfig.mcpServers.'origin-agent' -Force
    [IO.File]::WriteAllText($claudeConfig,($existing|ConvertTo-Json -Depth 50),$utf8)
}
Write-Output ('Installed Origin Companion ' + $version + ' at ' + $Destination)
Write-Output ('Host configuration: ' + $hostDirectory)
Write-Output ('Origin detected: ' + $status.native_ready_to_probe)
Write-Output 'Each computer needs its own installed and activated Origin. Restart the host to load new MCP tools.'
