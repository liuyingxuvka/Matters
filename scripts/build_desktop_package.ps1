param(
    [string]$OutputRoot = "dist\desktop"
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$OutputPath = [System.IO.Path]::GetFullPath(
    (Join-Path $RepositoryRoot $OutputRoot)
)
$WorkPath = Join-Path $RepositoryRoot "build\desktop"
$SpecPath = Join-Path $RepositoryRoot "build\desktop-spec"
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
        --icon "src\matters\assets\matters.ico" `
        --paths "src" `
        --collect-all "webview" `
        --collect-data "matters" `
        --add-data "ui;ui" `
        --distpath $OutputPath `
        --workpath $WorkPath `
        --specpath $SpecPath `
        "scripts\matters_desktop_entry.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Matters desktop package build failed."
    }
    $Executable = Join-Path $OutputPath "Matters\Matters.exe"
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Matters desktop executable was not produced."
    }
    $SelfTestPath = Join-Path $OutputPath "desktop-self-test.json"
    $SelfTestLines = @(& $Executable --self-test)
    if ($LASTEXITCODE -ne 0 -or $SelfTestLines.Count -eq 0) {
        throw "Matters packaged desktop self-test failed."
    }
    [System.IO.File]::WriteAllText(
        $SelfTestPath,
        (
            [string]::Join([Environment]::NewLine, $SelfTestLines) +
            [Environment]::NewLine
        ),
        [System.Text.UTF8Encoding]::new($false)
    )
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
