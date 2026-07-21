param(
    [string]$OutputRoot = "dist\desktop"
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$OutputPath = if ([System.IO.Path]::IsPathRooted($OutputRoot)) {
    [System.IO.Path]::GetFullPath($OutputRoot)
} else {
    [System.IO.Path]::GetFullPath(
        (Join-Path $RepositoryRoot $OutputRoot)
    )
}
$WorkPath = Join-Path $RepositoryRoot "build\desktop"
$SpecPath = Join-Path $RepositoryRoot "build\desktop-spec"
$IconPath = Join-Path $RepositoryRoot "src\matters\assets\matters.ico"
$SourcePath = Join-Path $RepositoryRoot "src"
$BundledSkillsPath = Join-Path $SourcePath "matters\bundled_skills"
$UiPath = Join-Path $RepositoryRoot "ui"
$ReadmePath = Join-Path $RepositoryRoot "README.md"
$AiSetupPath = Join-Path $RepositoryRoot "plugins\matters\skills\matters\references\installation.md"
$EntryPath = Join-Path $RepositoryRoot "scripts\matters_desktop_entry.py"
$VersionPath = Join-Path $SourcePath "matters\_version.py"
$VersionSource = Get-Content -LiteralPath $VersionPath -Raw -Encoding UTF8
$VersionMatch = [regex]::Match($VersionSource, 'VERSION\s*=\s*"([^"]+)"')
if (-not $VersionMatch.Success) {
    throw "Matters version authority is unavailable."
}
$MattersVersion = $VersionMatch.Groups[1].Value
$PreviousPythonPath = $env:PYTHONPATH

Push-Location $RepositoryRoot
try {
    New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
    $ToolchainPath = Join-Path $OutputPath "desktop-build-toolchain.json"
    python scripts\build_desktop_toolchain.py --output $ToolchainPath
    if ($LASTEXITCODE -ne 0) {
        throw "Matters desktop build toolchain identity could not be frozen."
    }
    python -m PyInstaller `
        --noconfirm `
        --clean `
        --name Matters `
        --windowed `
        --icon $IconPath `
        --paths $SourcePath `
        --hidden-import "webview.platforms.winforms" `
        --hidden-import "webview.platforms.edgechromium" `
        --exclude-module "webview.platforms.android" `
        --exclude-module "webview.platforms.cef" `
        --exclude-module "webview.platforms.cocoa" `
        --exclude-module "webview.platforms.gtk" `
        --exclude-module "webview.platforms.qt" `
        --exclude-module "torch" `
        --exclude-module "torchvision" `
        --exclude-module "torchaudio" `
        --exclude-module "tensorflow" `
        --exclude-module "jax" `
        --exclude-module "jaxlib" `
        --exclude-module "pandas" `
        --exclude-module "scipy" `
        --exclude-module "matplotlib" `
        --exclude-module "sympy" `
        --exclude-module "numba" `
        --exclude-module "llvmlite" `
        --exclude-module "sklearn" `
        --exclude-module "pytest" `
        --exclude-module "IPython" `
        --collect-data "matters" `
        --add-data "$BundledSkillsPath;matters\bundled_skills" `
        --add-data "$UiPath;ui" `
        --distpath $OutputPath `
        --workpath $WorkPath `
        --specpath $SpecPath `
        $EntryPath
    if ($LASTEXITCODE -ne 0) {
        throw "Matters desktop package build failed."
    }
    $Executable = Join-Path $OutputPath "Matters\Matters.exe"
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Matters desktop executable was not produced."
    }
    $PackageRoot = Join-Path $OutputPath "Matters"
    Copy-Item -LiteralPath $ReadmePath -Destination (Join-Path $OutputPath "README.md") -Force
    Copy-Item -LiteralPath $AiSetupPath -Destination (Join-Path $OutputPath "AI-SETUP.md") -Force
    $DirectUrlReceipts = @(
        Get-ChildItem -LiteralPath $PackageRoot -Recurse -File `
            -Filter "direct_url.json" -ErrorAction Stop
    )
    if ($DirectUrlReceipts.Count -gt 0) {
        $DirectUrlReceipts | Remove-Item -Force
    }
    if (
        Get-ChildItem -LiteralPath $PackageRoot -Recurse -File `
            -Filter "direct_url.json" -ErrorAction Stop
    ) {
        throw "Matters desktop package retained a machine-local direct_url receipt."
    }
    $SelfTestPath = Join-Path $OutputPath "desktop-self-test.json"
    $SelfTestStdoutPath = Join-Path $OutputPath "desktop-self-test.stdout.tmp"
    $SelfTestStderrPath = Join-Path $OutputPath "desktop-self-test.stderr.tmp"
    $SelfTestProcess = Start-Process `
        -FilePath $Executable `
        -ArgumentList "--self-test" `
        -Wait `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $SelfTestStdoutPath `
        -RedirectStandardError $SelfTestStderrPath
    $SelfTestOutput = if (Test-Path -LiteralPath $SelfTestStdoutPath -PathType Leaf) {
        Get-Content -LiteralPath $SelfTestStdoutPath -Raw -Encoding UTF8
    } else {
        ""
    }
    if ($SelfTestProcess.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($SelfTestOutput)) {
        $SelfTestError = if (Test-Path -LiteralPath $SelfTestStderrPath -PathType Leaf) {
            (Get-Content -LiteralPath $SelfTestStderrPath -Raw -Encoding UTF8).Trim()
        } else {
            ""
        }
        throw "Matters packaged desktop self-test failed."
    }
    [System.IO.File]::WriteAllText(
        $SelfTestPath,
        ($SelfTestOutput.TrimEnd() + [Environment]::NewLine),
        [System.Text.UTF8Encoding]::new($false)
    )
    Remove-Item -LiteralPath $SelfTestStdoutPath, $SelfTestStderrPath -Force
    $ManifestPath = Join-Path $OutputPath "desktop-manifest.json"
    $env:PYTHONPATH = Join-Path $RepositoryRoot "src"
    python scripts\build_desktop_manifest.py `
        --package-root (Join-Path $OutputPath "Matters") `
        --manifest $ManifestPath `
        --self-test $SelfTestPath `
        --toolchain $ToolchainPath
    if ($LASTEXITCODE -ne 0) {
        throw "Matters desktop manifest build failed."
    }
    $ReleaseArchivePath = Join-Path $OutputPath (
        "Matters-{0}-windows-x64.zip" -f $MattersVersion
    )
    python scripts\build_desktop_release_archive.py `
        --desktop-root $OutputPath `
        --output $ReleaseArchivePath
    if ($LASTEXITCODE -ne 0) {
        throw "Matters desktop release archive build failed."
    }
    Write-Output $Executable
    Write-Output $ManifestPath
    Write-Output $ToolchainPath
    Write-Output $ReleaseArchivePath
}
finally {
    if ($null -eq $PreviousPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $PreviousPythonPath
    }
    Pop-Location
}
