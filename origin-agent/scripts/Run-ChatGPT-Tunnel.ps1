param([string]$ConfigPath = '')
$ErrorActionPreference = 'Stop'
# Codex may inherit PowerShell 7 module paths; use this interpreter's built-ins.
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Management\Microsoft.PowerShell.Management.psd1')
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1')
Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1')
$secureKey = $null
$previousKey = $env:CONTROL_PLANE_API_KEY
$previousHome = $env:ORIGIN_AGENT_HOME
$exitCode = 1
try {
    if (-not $ConfigPath) { $ConfigPath = Join-Path $PSScriptRoot 'runtime-config.json' }
    if (-not [IO.Path]::IsPathRooted($ConfigPath)) { throw 'The private connector configuration path must be absolute.' }
    $ConfigPath = [IO.Path]::GetFullPath($ConfigPath)
    $config = Get-Content -Raw -Encoding UTF8 -LiteralPath $ConfigPath | ConvertFrom-Json
    if ($config.schema_version -ne 1 -or -not [IO.Path]::IsPathRooted($config.state_root) -or
        -not [IO.Path]::IsPathRooted($config.secret_file)) { throw 'The private connector configuration is invalid.' }
    $install = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $config.state_root 'install.json') | ConvertFrom-Json
    if (-not [IO.Path]::IsPathRooted($install.executable) -or
        -not (Test-Path -LiteralPath $install.executable -PathType Leaf)) { throw 'Origin Companion is not installed.' }
    # DPAPI stays in this Windows adapter. No key is passed in argv or printed.
    $secureKey = ConvertTo-SecureString (Get-Content -Raw -LiteralPath $config.secret_file).Trim()
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try { $env:CONTROL_PLANE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer).Trim() }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
    if ($env:CONTROL_PLANE_API_KEY -notmatch '^sk-') { throw 'The stored runtime key is invalid.' }
    $env:ORIGIN_AGENT_HOME = $config.state_root
    & $install.executable tunnel run --config $ConfigPath
    $exitCode = $LASTEXITCODE
} catch {
    # Do not expose raw credential-bearing subprocess responses in scheduler output.
    Write-Error 'Origin Companion private connector could not start. Check its lifecycle status and installation receipt.' -ErrorAction Continue
    $exitCode = 1
} finally {
    $env:CONTROL_PLANE_API_KEY = $previousKey
    $env:ORIGIN_AGENT_HOME = $previousHome
    if ($secureKey) { $secureKey.Dispose() }
}
exit $exitCode
