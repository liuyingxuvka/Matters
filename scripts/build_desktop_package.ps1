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
$EntryPath = Join-Path $RepositoryRoot "scripts\matters_desktop_entry.py"
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
        --collect-all "webview" `
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
    Write-Output $Executable
    Write-Output $ManifestPath
    Write-Output $ToolchainPath
}
finally {
    if ($null -eq $PreviousPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $PreviousPythonPath
    }
    Pop-Location
}
