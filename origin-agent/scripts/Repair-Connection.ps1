param([string]$ConfigPath = '', [switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
foreach ($module in @('Management','Utility','Security')) {
    Import-Module ($PSHOME + '\Modules\Microsoft.PowerShell.' + $module + '\Microsoft.PowerShell.' + $module + '.psd1')
}
Import-Module ($PSHOME + '\Modules\CimCmdlets\CimCmdlets.psd1')
Import-Module ($PSHOME + '\Modules\ScheduledTasks\ScheduledTasks.psd1')
if (-not $ConfigPath) { $ConfigPath = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.origin-agent\cloud\runtime-config.json' }
if (-not [IO.Path]::IsPathRooted($ConfigPath)) { throw 'Use an absolute connection configuration path.' }
$ConfigPath = [IO.Path]::GetFullPath($ConfigPath)
$config = Get-Content -Raw -Encoding UTF8 -LiteralPath $ConfigPath | ConvertFrom-Json
foreach ($path in @($config.state_root,$config.secret_file,$config.cloud_root)) {
    if (-not [IO.Path]::IsPathRooted($path)) { throw 'Use an existing installed connection.' }
}
$root = [IO.Path]::GetFullPath($config.state_root).TrimEnd('\')
$secret = [IO.Path]::GetFullPath($config.secret_file)
$cloud = [IO.Path]::GetFullPath($config.cloud_root)
if ($config.schema_version -ne 2 -or -not $secret.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase) -or
    -not ($cloud.Equals($root + '\cloud', [StringComparison]::OrdinalIgnoreCase) -or
        $cloud.StartsWith($root + '\cloud\accounts\', [StringComparison]::OrdinalIgnoreCase)) -or
    -not $ConfigPath.Equals((Join-Path $cloud 'runtime-config.json'), [StringComparison]::OrdinalIgnoreCase) -or
    -not (Test-Path -LiteralPath $secret -PathType Leaf)) { throw 'Use an existing installed connection.' }
foreach ($target in @($secret,$cloud,$ConfigPath)) {
    $item = Get-Item -LiteralPath $target
    while ($item) {
        if ($item.Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)) { throw 'Connection paths must not be redirected.' }
        $item = if ($item -is [IO.FileInfo]) { $item.Directory } else { $item.Parent }
    }
}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$form = New-Object Windows.Forms.Form
$form.Text = 'Origin Companion - connection credential'
$form.Size = New-Object Drawing.Size(650,375)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$guide = New-Object Windows.Forms.Label
$guide.SetBounds(20,20,600,92)
$guide.Text = "Connection: $($config.alias)`r`nThe service rejected this connection's credential. Use a valid restricted tunnel key from the same OpenAI project. Your plugin and tunnel identity stay the same. Paste the key only in this local window."
$form.Controls.Add($guide)
$open = New-Object Windows.Forms.Button
$open.Text = 'Open OpenAI key settings'
$open.SetBounds(20,113,240,32)
$open.Add_Click({ Start-Process 'https://platform.openai.com/api-keys' })
$form.Controls.Add($open)
$credentialInput = New-Object Windows.Forms.TextBox
$credentialInput.UseSystemPasswordChar = $true
$credentialInput.SetBounds(20,160,600,27)
$form.Controls.Add($credentialInput)
$save = New-Object Windows.Forms.Button
$save.Text = 'Save credential and resume connection'
$save.SetBounds(20,201,350,34)
$form.Controls.Add($save)
$feedback = New-Object Windows.Forms.Label
$feedback.SetBounds(20,248,600,70)
$feedback.Text = 'Encrypted for your Windows user. No key is sent to chat or written to logs.'
$form.Controls.Add($feedback)
$save.Add_Click({
    $secure = $null
    $pending = $null
    try {
        $key = $credentialInput.Text.Trim()
        if ($key -notmatch '^sk-[A-Za-z0-9_-]{20,}$') { throw 'Enter a valid OpenAI connection key.' }
        $secure = ConvertTo-SecureString $key -AsPlainText -Force
        $key = $null
        $encrypted = ConvertFrom-SecureString $secure
        $pending = $secret + '.pending-' + [guid]::NewGuid().ToString('N')
        [IO.File]::WriteAllText($pending, $encrypted, (New-Object Text.UTF8Encoding($false)))
        [IO.File]::Replace($pending, $secret, ($secret + '.backup-' + [guid]::NewGuid().ToString('N')))
        $pending = $null
        $encrypted = $null
        $credentialInput.Clear()
        $intent = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $cloud 'intent.json') | ConvertFrom-Json
        if ($intent.enabled -and -not $intent.stop_requested) {
            Start-ScheduledTask -TaskName $config.task_name -TaskPath $config.task_path
            $feedback.Text = 'Saved. The background connection is checking the credential. This window will show the result.'
        } else {
            $feedback.Text = 'Saved. This connection remains stopped because its startup preference is disabled.'
        }
    } catch {
        $feedback.Text = 'Could not save or start the connection. Check the key and your connection settings. No key is included in diagnostics.'
    } finally {
        $key = $null
        $encrypted = $null
        if ($secure) { $secure.Dispose() }
        if ($pending -and (Test-Path -LiteralPath $pending)) { Remove-Item -LiteralPath $pending -Force }
    }
})
$timer = New-Object Windows.Forms.Timer
$timer.Interval = 3000
$timer.Add_Tick({
    try {
        $state = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $cloud 'supervisor-state.json') | ConvertFrom-Json
        $now = ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0)
        if ($state.ready -and $state.observed_epoch -and $now - $state.observed_epoch -ge 0 -and
            $now - $state.observed_epoch -lt 40 -and $state.remote_reachability -eq 'online') {
            $feedback.Text = 'Connection online. Return to your agent and use @Origin Companion.'
        } elseif ($state.state -eq 'blocked' -and $state.reason -eq 'authentication_required') {
            $feedback.Text = 'The service rejected the credential. Check that the key belongs to this connection and has tunnel permissions.'
        }
    } catch { }
})
try {
    if ($ValidateOnly) {
        [pscustomobject]@{password_masked=$credentialInput.UseSystemPasswordChar;save_button=$save.Text;secret_written=$false} | ConvertTo-Json -Compress
    } else {
        $timer.Start()
        $form.ShowDialog() | Out-Null
    }
} finally {
    $credentialInput.Clear()
    $timer.Stop()
    $timer.Dispose()
    $form.Dispose()
}
