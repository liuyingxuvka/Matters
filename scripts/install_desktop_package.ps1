param(
    [Parameter(Mandatory = $true)][string]$PackageRoot,
    [string]$ManifestPath = "",
    [switch]$NoDesktopShortcut
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $PSScriptRoot "..")
)
$CandidateRoot = [System.IO.Path]::GetFullPath($PackageRoot)
$CandidateExecutable = Join-Path $CandidateRoot "Matters.exe"
if (-not (Test-Path -LiteralPath $CandidateExecutable -PathType Leaf)) {
    throw "The Matters desktop package does not contain Matters.exe."
}
$CandidateManifest = if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    Join-Path (Split-Path -Parent $CandidateRoot) "desktop-manifest.json"
} else {
    [System.IO.Path]::GetFullPath($ManifestPath)
}
if (-not (Test-Path -LiteralPath $CandidateManifest -PathType Leaf)) {
    throw "The Matters desktop package manifest is unavailable."
}
$PrivateRoot = if ([string]::IsNullOrWhiteSpace($env:MATTERS_HOME)) {
    Join-Path $env:USERPROFILE ".matters"
} else {
    [System.IO.Path]::GetFullPath($env:MATTERS_HOME)
}
$InstallRoot = Join-Path $PrivateRoot "install\desktop"
$VersionsRoot = Join-Path $InstallRoot "versions"
$TransactionsRoot = Join-Path $InstallRoot "transactions"
$ReceiptPath = Join-Path $InstallRoot "active-install.json"
$VersionSource = Get-Content -LiteralPath (Join-Path $RepositoryRoot "src\matters\_version.py") -Raw
$VersionMatch = [regex]::Match($VersionSource, 'VERSION\s*=\s*"([^"]+)"')
$Version = if ($VersionMatch.Success) { $VersionMatch.Groups[1].Value } else { "" }
if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "The Matters source version is unavailable."
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Save-FileState {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$SnapshotPath
    )
    $State = [ordered]@{
        path = $Path
        existed = $false
        snapshot_path = $SnapshotPath
        sha256 = ""
    }
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $State.existed = $true
        Copy-Item -LiteralPath $Path -Destination $SnapshotPath -Force
        $State.sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        $SnapshotHash = (Get-FileHash -LiteralPath $SnapshotPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($SnapshotHash -ne $State.sha256) {
            throw "A desktop install snapshot did not preserve its source identity."
        }
    }
    return [pscustomobject]$State
}

function Restore-FileState {
    param([Parameter(Mandatory = $true)]$State)
    if ($State.existed) {
        Copy-Item -LiteralPath $State.snapshot_path -Destination $State.path -Force
        $RestoredHash = (Get-FileHash -LiteralPath $State.path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($RestoredHash -ne $State.sha256) {
            throw "A desktop install rollback did not restore the prior file identity."
        }
    }
    elseif (Test-Path -LiteralPath $State.path -PathType Leaf) {
        Remove-Item -LiteralPath $State.path -Force
    }
    if (-not $State.existed -and (Test-Path -LiteralPath $State.path -PathType Leaf)) {
        throw "A desktop install rollback left a file that did not previously exist."
    }
}

function Assert-ShortcutCurrent {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "A Matters desktop shortcut was not published."
    }
    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($Path)
    if (
        -not [string]::Equals(
            [System.IO.Path]::GetFullPath($Shortcut.TargetPath),
            [System.IO.Path]::GetFullPath($Target),
            [System.StringComparison]::OrdinalIgnoreCase
        ) -or
        -not [string]::Equals(
            [System.IO.Path]::GetFullPath($Shortcut.WorkingDirectory),
            [System.IO.Path]::GetFullPath($WorkingDirectory),
            [System.StringComparison]::OrdinalIgnoreCase
        ) -or
        -not [string]::Equals(
            [string]$Shortcut.IconLocation,
            "$Target,0",
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "A Matters desktop shortcut does not target the active package."
    }
}

$env:PYTHONPATH = Join-Path $RepositoryRoot "src"
$CandidateVerificationLines = @(
    python scripts\build_desktop_manifest.py `
        --package-root $CandidateRoot `
        --manifest $CandidateManifest `
        --verify
)
if ($LASTEXITCODE -ne 0 -or $CandidateVerificationLines.Count -eq 0) {
    throw "The Matters desktop package manifest is not current."
}
$CandidateVerification = (
    [string]::Join([Environment]::NewLine, $CandidateVerificationLines) |
        ConvertFrom-Json
)
$VerifiedManifest = $CandidateVerification.manifest
if ([string]$VerifiedManifest.matters_version -ne $Version) {
    throw "The Matters desktop package version does not match the installer."
}
$PackageHash = ([string]$VerifiedManifest.package_sha256).Substring(7)
$TransactionId = [guid]::NewGuid().ToString("N")
$TransactionRoot = Join-Path $TransactionsRoot $TransactionId
$StageRoot = Join-Path $TransactionRoot "candidate"
$PriorRoot = Join-Path $TransactionRoot "prior"
$ActivationRoot = Join-Path $VersionsRoot ("$Version-" + $PackageHash.Substring(0, 16))
$ActivationExistedBefore = Test-Path -LiteralPath $ActivationRoot
$InstallPrefix = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
) + [System.IO.Path]::DirectorySeparatorChar
foreach ($OwnedPath in @($TransactionRoot, $StageRoot, $ActivationRoot)) {
    $ResolvedOwnedPath = [System.IO.Path]::GetFullPath($OwnedPath)
    if (-not $ResolvedOwnedPath.StartsWith(
        $InstallPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "A desktop installation path escapes the private install root."
    }
}

$ShortcutRoot = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$ShortcutPaths = @((Join-Path $ShortcutRoot "Matters.lnk"))
if (-not $NoDesktopShortcut) {
    $ShortcutPaths += (Join-Path ([Environment]::GetFolderPath("Desktop")) "Matters.lnk")
}
$ShortcutStates = @()
$ReceiptState = $null
$EnvironmentChanged = $false
$FinalReceiptJson = ""
$PriorUserMattersHome = [Environment]::GetEnvironmentVariable("MATTERS_HOME", "User")
try {
    New-Item -ItemType Directory -Force -Path $StageRoot, $PriorRoot, $VersionsRoot | Out-Null
    Get-ChildItem -LiteralPath $CandidateRoot -Force |
        Copy-Item -Destination $StageRoot -Recurse -Force

    $ReceiptState = Save-FileState `
        -Path $ReceiptPath `
        -SnapshotPath (Join-Path $PriorRoot "active-install.json")
    $PriorPackageIdentity = ""
    if ($ReceiptState.existed) {
        $ExistingReceipt = (
            Get-Content -LiteralPath $ReceiptPath -Raw -Encoding UTF8 |
                ConvertFrom-Json
        )
        if ($ExistingReceipt.package_sha256 -match '^sha256:[0-9a-f]{64}$') {
            $PriorPackageIdentity = [string]$ExistingReceipt.package_sha256
        }
    }

    $PlanPath = Join-Path $TransactionRoot "desktop-install-plan.json"
    python scripts\build_desktop_manifest.py `
        --package-root $StageRoot `
        --manifest $CandidateManifest `
        --verify `
        --plan $PlanPath `
        --transaction-id $TransactionId `
        --prior-install-identity $PriorPackageIdentity
    if ($LASTEXITCODE -ne 0) {
        throw "The staged Matters desktop package identity changed."
    }
    $VerifiedPlan = Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    $ExpectedInstallStages = @(
        "snapshot_prior_install",
        "stage_candidate_package",
        "verify_staged_package",
        "activate_candidate",
        "verify_installed_currentness",
        "publish_application_shortcuts",
        "publish_install_receipt"
    )
    $ExpectedRollbackStages = @(
        "remove_failed_candidate",
        "restore_prior_package",
        "restore_prior_shortcuts",
        "restore_prior_install_receipt",
        "verify_restored_identity"
    )
    if (
        [string]$VerifiedPlan.transaction_id -ne $TransactionId -or
        [string]$VerifiedPlan.candidate_manifest_fingerprint -ne [string]$VerifiedManifest.manifest_fingerprint -or
        [string]$VerifiedPlan.prior_install_identity -ne $PriorPackageIdentity -or
        $VerifiedPlan.rollback_required_after_activation -ne $true -or
        [string]::Join("|", @($VerifiedPlan.stages)) -ne [string]::Join("|", $ExpectedInstallStages) -or
        [string]::Join("|", @($VerifiedPlan.rollback_stages)) -ne [string]::Join("|", $ExpectedRollbackStages)
    ) {
        throw "The desktop install transaction plan is not bound to this candidate."
    }

    for ($Index = 0; $Index -lt $ShortcutPaths.Count; $Index++) {
        $ShortcutStates += Save-FileState `
            -Path $ShortcutPaths[$Index] `
            -SnapshotPath (Join-Path $PriorRoot ("shortcut-{0}.lnk" -f $Index))
    }

    if (-not (Test-Path -LiteralPath $ActivationRoot)) {
        Move-Item -LiteralPath $StageRoot -Destination $ActivationRoot
    } else {
        python scripts\build_desktop_manifest.py `
            --package-root $ActivationRoot `
            --manifest $CandidateManifest `
            --verify
        if ($LASTEXITCODE -ne 0) {
            throw "The existing desktop activation has a different identity."
        }
    }
    $InstalledExecutable = Join-Path $ActivationRoot "Matters.exe"
    $InstalledExecutableSha256 = "sha256:" + (
        Get-FileHash -LiteralPath $InstalledExecutable -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if (
        $InstalledExecutableSha256 -ne
        [string]$VerifiedManifest.executable_sha256
    ) {
        throw "The installed Matters desktop executable identity changed."
    }
    $InstalledSelfTestStdoutPath = Join-Path $TransactionRoot "installed-self-test.stdout.json"
    $InstalledSelfTestStderrPath = Join-Path $TransactionRoot "installed-self-test.stderr.txt"
    $InstalledSelfTestProcess = Start-Process `
        -FilePath $InstalledExecutable `
        -ArgumentList "--self-test" `
        -Wait `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $InstalledSelfTestStdoutPath `
        -RedirectStandardError $InstalledSelfTestStderrPath
    $SelfTestOutput = if (Test-Path -LiteralPath $InstalledSelfTestStdoutPath -PathType Leaf) {
        Get-Content -LiteralPath $InstalledSelfTestStdoutPath -Raw -Encoding UTF8
    } else {
        ""
    }
    if (
        $InstalledSelfTestProcess.ExitCode -ne 0 -or
        [string]::IsNullOrWhiteSpace($SelfTestOutput)
    ) {
        throw "The installed Matters desktop package currentness check failed."
    }
    $SelfTest = $SelfTestOutput | ConvertFrom-Json
    if (
        $SelfTest.ok -ne $true -or
        [string]$SelfTest.result.matters_version -ne $Version -or
        [string]$SelfTest.result.shell_kind -ne "packaged_windows_webview" -or
        $SelfTest.result.loopback_only -ne $true -or
        $SelfTest.result.owns_application_window -ne $true -or
        $SelfTest.result.packaged_ui -ne $true -or
        $SelfTest.result.private_shell_profile -ne $true -or
        $SelfTest.result.persists_locale_density_window_state -ne $true -or
        $SelfTest.result.startup_health_gate -ne $true -or
        $SelfTest.result.in_shell_recovery_surface -ne $true -or
        $SelfTest.result.clean_owned_process_shutdown -ne $true -or
        @($SelfTest.result.available_locales) -notcontains "en" -or
        @($SelfTest.result.available_locales) -notcontains "zh-CN"
    ) {
        throw "The installed Matters desktop package self-test gates are incomplete."
    }
    New-Item -ItemType Directory -Force -Path $ShortcutRoot | Out-Null
    $Shell = New-Object -ComObject WScript.Shell
    foreach ($ShortcutPath in $ShortcutPaths) {
        $Shortcut = $Shell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = $InstalledExecutable
        $Shortcut.WorkingDirectory = $PrivateRoot
        $Shortcut.Description = "Matters private object browser"
        $Shortcut.IconLocation = "$InstalledExecutable,0"
        $Shortcut.Save()
        Assert-ShortcutCurrent `
            -Path $ShortcutPath `
            -Target $InstalledExecutable `
            -WorkingDirectory $PrivateRoot
    }
    $Receipt = [ordered]@{
        schema = "matters.desktop-install-receipt.v1"
        matters_version = $Version
        package_sha256 = "sha256:$PackageHash"
        executable_sha256 = $InstalledExecutableSha256
        build_toolchain_sha256 = $VerifiedManifest.build_toolchain_sha256
        manifest_fingerprint = $VerifiedManifest.manifest_fingerprint
        transaction_plan_fingerprint = $VerifiedPlan.plan_fingerprint
        ui_bundle_sha256 = $VerifiedManifest.ui_bundle_sha256
        icon_sha256 = $VerifiedManifest.icon_sha256
        skill_pack_identity = $VerifiedManifest.skill_pack_identity
        service_contract_identity = $VerifiedManifest.service_contract_identity
        worker_contract_identity = $VerifiedManifest.worker_contract_identity
        installed_root = $ActivationRoot
        launcher = $InstalledExecutable
        shortcuts = $ShortcutPaths
        private_root = $PrivateRoot
        transaction_id = $TransactionId
        installed_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    $ReceiptCandidatePath = Join-Path $TransactionRoot "active-install.candidate.json"
    Write-Utf8NoBom -Path $ReceiptCandidatePath -Content (($Receipt | ConvertTo-Json -Depth 4) + [Environment]::NewLine)
    $CandidateReceipt = Get-Content -LiteralPath $ReceiptCandidatePath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    if (
        [string]$CandidateReceipt.package_sha256 -ne [string]$VerifiedManifest.package_sha256 -or
        [string]$CandidateReceipt.manifest_fingerprint -ne [string]$VerifiedManifest.manifest_fingerprint -or
        [string]$CandidateReceipt.executable_sha256 -ne [string]$VerifiedManifest.executable_sha256 -or
        [string]$CandidateReceipt.build_toolchain_sha256 -ne [string]$VerifiedManifest.build_toolchain_sha256 -or
        [string]$CandidateReceipt.transaction_plan_fingerprint -ne [string]$VerifiedPlan.plan_fingerprint -or
        [string]$CandidateReceipt.installed_root -ne $ActivationRoot -or
        [string]$CandidateReceipt.launcher -ne $InstalledExecutable
    ) {
        throw "The desktop install receipt candidate is not bound to the installed package."
    }
    if (Test-Path -LiteralPath $ReceiptPath -PathType Leaf) {
        $ReceiptReplaceBackupPath = Join-Path $TransactionRoot "active-install.replace-backup.json"
        [System.IO.File]::Replace(
            $ReceiptCandidatePath,
            $ReceiptPath,
            $ReceiptReplaceBackupPath
        )
    } else {
        [System.IO.File]::Move($ReceiptCandidatePath, $ReceiptPath)
    }
    $InstalledReceipt = Get-Content -LiteralPath $ReceiptPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    if (
        [string]$InstalledReceipt.manifest_fingerprint -ne [string]$VerifiedManifest.manifest_fingerprint -or
        [string]$InstalledReceipt.executable_sha256 -ne [string]$VerifiedManifest.executable_sha256 -or
        [string]$InstalledReceipt.build_toolchain_sha256 -ne [string]$VerifiedManifest.build_toolchain_sha256 -or
        [string]$InstalledReceipt.transaction_plan_fingerprint -ne [string]$VerifiedPlan.plan_fingerprint
    ) {
        throw "The published desktop install receipt identity is not current."
    }
    if (
        $null -ne $ReceiptReplaceBackupPath -and
        (Test-Path -LiteralPath $ReceiptReplaceBackupPath -PathType Leaf)
    ) {
        Remove-Item -LiteralPath $ReceiptReplaceBackupPath -Force
    }
    [Environment]::SetEnvironmentVariable("MATTERS_HOME", $PrivateRoot, "User")
    $EnvironmentChanged = $true
    $FinalReceiptJson = $Receipt | ConvertTo-Json -Depth 4
    if (Test-Path -LiteralPath $TransactionRoot) {
        Remove-Item -LiteralPath $TransactionRoot -Recurse -Force
    }
}
catch {
    $Failure = $_
    $RollbackErrors = [System.Collections.Generic.List[string]]::new()
    foreach ($ShortcutState in $ShortcutStates) {
        try {
            Restore-FileState -State $ShortcutState
        }
        catch {
            $RollbackErrors.Add($_.Exception.Message)
        }
    }
    if ($null -ne $ReceiptState) {
        try {
            Restore-FileState -State $ReceiptState
            if ($ReceiptState.existed -and $PriorPackageIdentity) {
                $RestoredReceipt = Get-Content -LiteralPath $ReceiptPath -Raw -Encoding UTF8 |
                    ConvertFrom-Json
                if (
                    [string]$RestoredReceipt.package_sha256 -ne $PriorPackageIdentity -or
                    -not (Test-Path -LiteralPath ([string]$RestoredReceipt.installed_root) -PathType Container) -or
                    -not (Test-Path -LiteralPath ([string]$RestoredReceipt.launcher) -PathType Leaf)
                ) {
                    throw "The prior desktop activation identity was not restored."
                }
            }
        }
        catch {
            $RollbackErrors.Add($_.Exception.Message)
        }
    }
    if (
        -not $ActivationExistedBefore -and
        (Test-Path -LiteralPath $ActivationRoot)
    ) {
        try {
            Remove-Item -LiteralPath $ActivationRoot -Recurse -Force
        }
        catch {
            $RollbackErrors.Add($_.Exception.Message)
        }
    }
    if ($EnvironmentChanged) {
        try {
            [Environment]::SetEnvironmentVariable("MATTERS_HOME", $PriorUserMattersHome, "User")
        }
        catch {
            $RollbackErrors.Add($_.Exception.Message)
        }
    }
    if (Test-Path -LiteralPath $TransactionRoot) {
        try {
            Remove-Item -LiteralPath $TransactionRoot -Recurse -Force
        }
        catch {
            $RollbackErrors.Add($_.Exception.Message)
        }
    }
    if ($RollbackErrors.Count -gt 0) {
        throw (
            "Matters desktop installation failed and rollback was incomplete: " +
            $Failure.Exception.Message + "; " +
            [string]::Join("; ", $RollbackErrors)
        )
    }
    throw $Failure
}
$FinalReceiptJson
