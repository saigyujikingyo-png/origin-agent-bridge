param([string]$PluginUrl = '', [switch]$RetireLocal, [switch]$NonInteractive)
$ErrorActionPreference = 'Stop'
$stateRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.origin-agent'
$install = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $stateRoot 'install.json') | ConvertFrom-Json
if (-not (Test-Path -LiteralPath $install.executable -PathType Leaf)) { throw 'Install Origin Companion first.' }
function Save-Connection([string]$Url, [bool]$Retire) {
    $arguments = @('connect-openai', '--url', $Url)
    if ($Retire) { $arguments += '--retire-local' }
    $output = & $install.executable @arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw ($output -join "`n") }
    return ($output | ConvertFrom-Json)
}
if ($NonInteractive) {
    if (-not $PluginUrl) { throw 'Provide your own plugin link with -PluginUrl.' }
    Save-Connection $PluginUrl $RetireLocal.IsPresent
    return
}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()
$form = New-Object Windows.Forms.Form
$form.Text = 'Origin Companion - one OpenAI connection'
$form.Size = New-Object Drawing.Size(720,390)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$heading = New-Object Windows.Forms.Label
$heading.Text = 'Use the same Origin Companion in Chat, Work and Codex.'
$heading.SetBounds(22,22,660,28)
$heading.Font = New-Object Drawing.Font('Segoe UI',12,[Drawing.FontStyle]::Bold)
$form.Controls.Add($heading)
$guide = New-Object Windows.Forms.Label
$guide.Text = "Open your personal plugins, connect Origin Companion, then copy its details-page link below. Use your existing connection; do not create another Origin plugin or API key."
$guide.SetBounds(22,65,660,48)
$form.Controls.Add($guide)
$directory = New-Object Windows.Forms.Button
$directory.Text = 'Open my plugins'
$directory.SetBounds(22,122,180,34)
$directory.Add_Click({ Start-Process 'https://chatgpt.com/plugins?view=personal' })
$form.Controls.Add($directory)
$connectionInput = New-Object Windows.Forms.TextBox
$connectionInput.SetBounds(22,173,660,28)
if ($PluginUrl) { $connectionInput.Text = $PluginUrl } else {
    $saved = & $install.executable connect-openai | ConvertFrom-Json
    if ($LASTEXITCODE -eq 0 -and $saved.configured) { $connectionInput.Text = $saved.plugin_url }
}
$form.Controls.Add($connectionInput)
$retire = New-Object Windows.Forms.CheckBox
$retire.Text = 'Retire the older local Origin Companion plugin entry (keeps the engine and data).'
$retire.SetBounds(22,214,660,28)
$retire.Checked = $true
$form.Controls.Add($retire)
$note = New-Object Windows.Forms.Label
$note.Text = 'Your licensed Windows computer and its private connection must be running. This does not add a new model subscription. Claude and WorkBuddy keep their own local MCP adapter.'
$note.SetBounds(22,250,660,40)
$form.Controls.Add($note)
$save = New-Object Windows.Forms.Button
$save.Text = 'Save and open Origin Companion'
$save.SetBounds(400,303,282,34)
$form.Tag = $null
$timer = New-Object Windows.Forms.Timer
$timer.Interval = 150
$timer.Add_Tick({
    $task = $form.Tag
    if (-not $task -or -not $task.Process.HasExited) { return }
    $timer.Stop()
    try {
        $output = $task.Output.GetAwaiter().GetResult()
        $errorText = $task.Error.GetAwaiter().GetResult()
        if ($task.Process.ExitCode -ne 0) { throw $errorText }
        $result = $output | ConvertFrom-Json
        Start-Process $result.plugin_url
        $form.Tag = $null
        $form.DialogResult = [Windows.Forms.DialogResult]::OK
        $form.Close()
    } catch {
        [Windows.Forms.MessageBox]::Show($_.Exception.Message,'Origin Companion') | Out-Null
    } finally {
        $task.Process.Dispose()
        $form.Tag = $null
        $save.Enabled = $true
        $save.Text = 'Save and open Origin Companion'
        $form.UseWaitCursor = $false
    }
})
$save.Add_Click({
    try {
        $text = $connectionInput.Text.Trim()
        $uri = [Uri]$text
        if ($uri.Scheme -ne 'https' -or $uri.Authority -ne 'chatgpt.com' -or
            $uri.AbsolutePath -notmatch '^/plugins/plugin_(asdk_app_[a-f0-9]{32})/?$') {
            throw 'Copy your Origin Companion details-page link from https://chatgpt.com/plugins.'
        }
        $canonicalUrl = 'https://chatgpt.com/plugins/plugin_' + $Matches[1]
        $start = New-Object Diagnostics.ProcessStartInfo
        $start.FileName = $install.executable
        $start.Arguments = 'connect-openai --url ' + $canonicalUrl
        if ($retire.Checked) { $start.Arguments += ' --retire-local' }
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $process = New-Object Diagnostics.Process
        $process.StartInfo = $start
        if (-not $process.Start()) { throw 'Could not start the connection check.' }
        $form.Tag = [pscustomobject]@{
            Process = $process
            Output = $process.StandardOutput.ReadToEndAsync()
            Error = $process.StandardError.ReadToEndAsync()
        }
        $save.Enabled = $false
        $save.Text = 'Checking the existing connection...'
        $form.UseWaitCursor = $true
        $timer.Start()
    } catch {
        [Windows.Forms.MessageBox]::Show($_.Exception.Message,'Origin Companion') | Out-Null
    }
})
$form.Add_FormClosing({
    if ($form.Tag) {
        $_.Cancel = $true
        $save.Text = 'Finishing the connection check...'
    }
})
$form.Controls.Add($save)
$form.AcceptButton = $save
$form.ShowDialog() | Out-Null
$timer.Dispose()
$form.Dispose()
