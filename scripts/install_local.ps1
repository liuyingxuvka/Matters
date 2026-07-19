param(
    [string]$PythonPath = "python",
    [string]$WheelPath = "",
    [switch]$SkipBuild,
    [switch]$NoDesktopShortcut
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$PrivateRoot = Join-Path $env:USERPROFILE ".matters"
$DistRoot = Join-Path $RepositoryRoot "dist"

New-Item -ItemType Directory -Force -Path $PrivateRoot | Out-Null
[Environment]::SetEnvironmentVariable("MATTERS_HOME", $PrivateRoot, "User")
$env:MATTERS_HOME = $PrivateRoot

if (-not $SkipBuild) {
    New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null
    & $PythonPath -m pip wheel $RepositoryRoot --no-deps --wheel-dir $DistRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Matters wheel build failed."
    }
}

$Wheel = $null
if (-not [string]::IsNullOrWhiteSpace($WheelPath)) {
    $ResolvedWheel = Resolve-Path -LiteralPath $WheelPath -ErrorAction Stop
    $Wheel = Get-Item -LiteralPath $ResolvedWheel.Path
    if ($Wheel.Name -notlike "matters-0.2.0-*.whl") {
        throw "The explicit wheel is not a Matters 0.2.0 wheel."
    }
} else {
    $Wheel = Get-ChildItem -LiteralPath $DistRoot -Filter "matters-0.2.0-*.whl" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}
if ($null -eq $Wheel) {
    throw "The Matters 0.2.0 wheel is unavailable."
}

& $PythonPath -m pip install --upgrade --force-reinstall --no-deps $Wheel.FullName
if ($LASTEXITCODE -ne 0) {
    throw "Matters installation failed."
}

$SystemScriptsRoot = (& $PythonPath -c "import sysconfig; print(sysconfig.get_path('scripts'))").Trim()
$UserScriptsRoot = (& $PythonPath -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))").Trim()
$DesktopLauncher = @(
    (Join-Path $SystemScriptsRoot "matters-desktop.exe"),
    (Join-Path $UserScriptsRoot "matters-desktop.exe")
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ([string]::IsNullOrWhiteSpace($DesktopLauncher)) {
    throw "The installed Matters desktop launcher is unavailable."
}
$DesktopLauncher = (Resolve-Path -LiteralPath $DesktopLauncher).Path

& $DesktopLauncher --check
if ($LASTEXITCODE -ne 0) {
    throw "The installed Matters desktop currentness check failed."
}

$ShortcutRoot = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
New-Item -ItemType Directory -Force -Path $ShortcutRoot | Out-Null
$Shell = New-Object -ComObject WScript.Shell
$ShortcutPaths = @((Join-Path $ShortcutRoot "Matters.lnk"))
if (-not $NoDesktopShortcut) {
    $ShortcutPaths += (Join-Path ([Environment]::GetFolderPath("Desktop")) "Matters.lnk")
}
foreach ($ShortcutPath in $ShortcutPaths) {
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $DesktopLauncher
    $Shortcut.WorkingDirectory = $PrivateRoot
    $Shortcut.Description = "Matters private object browser"
    $Shortcut.Save()
}

$ReceiptRoot = Join-Path $PrivateRoot "install"
New-Item -ItemType Directory -Force -Path $ReceiptRoot | Out-Null
$Receipt = [ordered]@{
    schema = "matters.local-install-receipt.v1"
    matters_version = "0.2.0"
    wheel_sha256 = (Get-FileHash -LiteralPath $Wheel.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    launcher = $DesktopLauncher
    shortcuts = $ShortcutPaths
    private_root = $PrivateRoot
    installed_at = [DateTimeOffset]::UtcNow.ToString("o")
}
$Receipt | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $ReceiptRoot "install-receipt.json") -Encoding utf8

$Receipt | ConvertTo-Json -Depth 4
