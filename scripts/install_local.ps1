param(
    [string]$PythonPath = "python",
    [string]$WheelPath = "",
    [switch]$SkipBuild,
    [switch]$NoDesktopShortcut
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$PrivateRootWasExplicit = -not [string]::IsNullOrWhiteSpace($env:MATTERS_HOME)
$PrivateRoot = if ($PrivateRootWasExplicit) {
    [System.IO.Path]::GetFullPath($env:MATTERS_HOME)
} else {
    Join-Path $env:USERPROFILE ".matters"
}
$DistRoot = Join-Path $RepositoryRoot "dist"
$VersionSource = Join-Path $RepositoryRoot "src\matters\_version.py"

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

function Remove-RepositoryBuildResidue {
    $RepositoryPrefix = $RepositoryRoot.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + [System.IO.Path]::DirectorySeparatorChar
    $BuildResiduePaths = @(
        (Join-Path $RepositoryRoot "build"),
        (Join-Path $RepositoryRoot "src\matters.egg-info")
    )
    foreach ($BuildResiduePath in $BuildResiduePaths) {
        $FullPath = [System.IO.Path]::GetFullPath($BuildResiduePath)
        if (-not $FullPath.StartsWith($RepositoryPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "A Matters build-residue path escapes the repository: $FullPath"
        }
        if (-not (Test-Path -LiteralPath $FullPath)) {
            continue
        }
        $Item = Get-Item -LiteralPath $FullPath -Force
        if (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "A Matters build-residue path is a link or junction: $FullPath"
        }
        Remove-Item -LiteralPath $FullPath -Recurse -Force
    }
}

function Get-InstalledMattersDistribution {
    $DistributionIdentityScript = @"
# matters-installed-distribution-identity-v1
import importlib.metadata as metadata
import json
import pathlib

try:
    distribution = metadata.distribution("matters")
except metadata.PackageNotFoundError:
    print(json.dumps({"present": False, "version": None, "files": []}, sort_keys=True))
else:
    files = distribution.files
    if files is None:
        raise SystemExit("The installed Matters distribution has no recoverable RECORD inventory.")
    resolved_files = sorted(
        {
            str(pathlib.Path(distribution.locate_file(entry)).resolve())
            for entry in files
        }
    )
    print(
        json.dumps(
            {
                "present": True,
                "version": distribution.version,
                "files": resolved_files,
            },
            sort_keys=True,
        )
    )
"@
    $DistributionJsonLines = @($DistributionIdentityScript | & $PythonPath -)
    if ($LASTEXITCODE -ne 0) {
        throw "The installed Matters distribution identity could not be frozen."
    }
    $DistributionJson = [string]::Join([Environment]::NewLine, $DistributionJsonLines)
    if ([string]::IsNullOrWhiteSpace($DistributionJson)) {
        throw "The installed Matters distribution identity is empty."
    }
    return ($DistributionJson | ConvertFrom-Json)
}

function New-DistributionSnapshot {
    param(
        [Parameter(Mandatory = $true)][string]$TransactionRoot
    )

    $Identity = Get-InstalledMattersDistribution
    $SnapshotRoot = Join-Path $TransactionRoot "prior-distribution"
    $SnapshotFilesRoot = Join-Path $SnapshotRoot "files"
    New-Item -ItemType Directory -Force -Path $SnapshotFilesRoot | Out-Null

    $Entries = @()
    $Index = 0
    foreach ($DestinationPath in @($Identity.files)) {
        $Index += 1
        $Exists = Test-Path -LiteralPath $DestinationPath -PathType Leaf
        if ((Test-Path -LiteralPath $DestinationPath) -and -not $Exists) {
            throw "The installed Matters distribution inventory contains a non-file path: $DestinationPath"
        }

        $StagedPath = $null
        $Sha256 = $null
        if ($Exists) {
            $StagedPath = Join-Path $SnapshotFilesRoot ("{0:D6}.bin" -f $Index)
            Copy-Item -LiteralPath $DestinationPath -Destination $StagedPath -Force
            $Sha256 = (Get-FileHash -LiteralPath $DestinationPath -Algorithm SHA256).Hash.ToLowerInvariant()
            $StagedSha256 = (Get-FileHash -LiteralPath $StagedPath -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($StagedSha256 -ne $Sha256) {
                throw "The prior Matters distribution staging copy is not byte-identical: $DestinationPath"
            }
        }

        $Entries += [ordered]@{
            destination = $DestinationPath
            existed = $Exists
            staged_path = $StagedPath
            sha256 = $Sha256
        }
    }

    if ($Identity.present -and $Entries.Count -eq 0) {
        throw "The installed Matters distribution has no recoverable files."
    }

    $Snapshot = [ordered]@{
        schema = "matters.installed-distribution-snapshot.v1"
        present = [bool]$Identity.present
        version = $Identity.version
        entries = $Entries
    }
    $SnapshotPath = Join-Path $SnapshotRoot "snapshot.json"
    Write-Utf8NoBom -Path $SnapshotPath -Content (($Snapshot | ConvertTo-Json -Depth 6) + [Environment]::NewLine)
    return [pscustomobject]$Snapshot
}

function Save-FileState {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$StateRoot,
        [Parameter(Mandatory = $true)][string]$StateName
    )

    $Exists = Test-Path -LiteralPath $Path -PathType Leaf
    if ((Test-Path -LiteralPath $Path) -and -not $Exists) {
        throw "A transactional file target is not a regular file: $Path"
    }
    $StagedPath = $null
    $Sha256 = $null
    if ($Exists) {
        New-Item -ItemType Directory -Force -Path $StateRoot | Out-Null
        $StagedPath = Join-Path $StateRoot "$StateName.bin"
        Copy-Item -LiteralPath $Path -Destination $StagedPath -Force
        $Sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
        $StagedSha256 = (Get-FileHash -LiteralPath $StagedPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($StagedSha256 -ne $Sha256) {
            throw "A transactional file staging copy is not byte-identical: $Path"
        }
    }
    return [pscustomobject]@{
        path = $Path
        existed = $Exists
        staged_path = $StagedPath
        sha256 = $Sha256
    }
}

function Restore-FileState {
    param(
        [Parameter(Mandatory = $true)]$State
    )

    if ($State.existed) {
        $Parent = Split-Path -Parent $State.path
        New-Item -ItemType Directory -Force -Path $Parent | Out-Null
        Copy-Item -LiteralPath $State.staged_path -Destination $State.path -Force
        $RestoredSha256 = (Get-FileHash -LiteralPath $State.path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($RestoredSha256 -ne $State.sha256) {
            throw "A transactional file was not restored byte-for-byte: $($State.path)"
        }
    } elseif (Test-Path -LiteralPath $State.path) {
        if (-not (Test-Path -LiteralPath $State.path -PathType Leaf)) {
            throw "A transactional file target became a non-file path: $($State.path)"
        }
        Remove-Item -LiteralPath $State.path -Force
    }
}

function Restore-DistributionSnapshot {
    param(
        [Parameter(Mandatory = $true)]$Snapshot
    )

    & $PythonPath -m pip uninstall --yes matters
    if ($LASTEXITCODE -ne 0) {
        throw "The failed Matters candidate could not be removed during rollback."
    }

    if (-not $Snapshot.present) {
        $CurrentIdentity = Get-InstalledMattersDistribution
        if ($CurrentIdentity.present) {
            throw "Rollback did not restore the prior clean-machine package state."
        }
        return
    }

    foreach ($Entry in @($Snapshot.entries)) {
        if ($Entry.existed) {
            $Parent = Split-Path -Parent $Entry.destination
            New-Item -ItemType Directory -Force -Path $Parent | Out-Null
            Copy-Item -LiteralPath $Entry.staged_path -Destination $Entry.destination -Force
        } elseif (Test-Path -LiteralPath $Entry.destination -PathType Leaf) {
            Remove-Item -LiteralPath $Entry.destination -Force
        }
    }

    $RestoredIdentity = Get-InstalledMattersDistribution
    if (-not $RestoredIdentity.present -or $RestoredIdentity.version -ne $Snapshot.version) {
        throw "Rollback did not restore the prior Matters distribution identity."
    }
    foreach ($Entry in @($Snapshot.entries)) {
        if ($Entry.existed) {
            if (-not (Test-Path -LiteralPath $Entry.destination -PathType Leaf)) {
                throw "Rollback did not restore a prior Matters distribution file: $($Entry.destination)"
            }
            $RestoredSha256 = (Get-FileHash -LiteralPath $Entry.destination -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($RestoredSha256 -ne $Entry.sha256) {
                throw "Rollback restored a different Matters distribution file: $($Entry.destination)"
            }
        } elseif (Test-Path -LiteralPath $Entry.destination) {
            throw "Rollback did not restore a previously absent Matters distribution path: $($Entry.destination)"
        }
    }
}

$ExpectedVersionScript = @"
import ast
import pathlib
import sys

tree = ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
for node in tree.body:
    if (
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "VERSION" for target in node.targets)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ):
        print(node.value.value)
        break
else:
    raise SystemExit("Matters VERSION authority is unavailable.")
"@
$ExpectedVersionLines = @($ExpectedVersionScript | & $PythonPath - $VersionSource)
$ExpectedVersion = ($ExpectedVersionLines -join "`n").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($ExpectedVersion)) {
    throw "The Matters source version authority is unavailable."
}
$ExpectedWheelPattern = "matters-$ExpectedVersion-*.whl"

New-Item -ItemType Directory -Force -Path $PrivateRoot | Out-Null
$env:MATTERS_HOME = $PrivateRoot

if (-not $SkipBuild) {
    # Setuptools reuses build/lib across invocations. Retired package files can
    # otherwise survive source deletion and reappear in a new wheel.
    Remove-RepositoryBuildResidue
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
    if ($Wheel.Name -notlike $ExpectedWheelPattern) {
        throw "The explicit wheel is not a Matters $ExpectedVersion wheel."
    }
} else {
    $Wheel = Get-ChildItem -LiteralPath $DistRoot -Filter $ExpectedWheelPattern |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}
if ($null -eq $Wheel) {
    throw "The Matters $ExpectedVersion wheel is unavailable."
}

$WheelIdentityScript = @"
# matters-wheel-identity-v2
import configparser
import email
import hashlib
import json
import sys
import zipfile

REQUIRED_SKILL_IDS = (
    "matters-source-governance",
    "matters-inventory-reconciliation",
    "matters-freshness-maintenance",
    "matters-model-depth-maintenance",
    "matters-human-correction",
    "matters-model-miss-review",
    "matters-skill-runtime",
    "matters-research-orchestration",
    "matters-semantic-understanding",
    "matters-autonomous-maintenance",
    "matters-hero-image-generation",
)
RETIRED_SKILL_IDS = (
    "matters-card-visual-curation",
    "matters-generated-hero",
)
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/service-contract.md",
    "scripts/invoke.py",
)
EXPECTED_CONSOLE_SCRIPTS = {
    "matters": "matters.cli.main:main",
    "matters-desktop": "matters.desktop:main",
    "matters-mcp": "matters.api.mcp.stdio:main",
}


def fingerprint(rows):
    payload = "\n".join(rows).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()

wheel_path, expected_version = sys.argv[1:3]
with zipfile.ZipFile(wheel_path) as archive:
    names = tuple(archive.namelist())
    name_set = set(names)
    metadata_paths = [
        path
        for path in names
        if path.endswith(".dist-info/METADATA")
    ]
    if len(metadata_paths) != 1:
        raise SystemExit("The wheel must contain exactly one METADATA file.")
    message = email.message_from_bytes(archive.read(metadata_paths[0]))
    entry_point_paths = [
        path for path in names if path.endswith(".dist-info/entry_points.txt")
    ]
    if len(entry_point_paths) != 1:
        raise SystemExit("The wheel must contain exactly one entry_points.txt file.")
    parser = configparser.ConfigParser()
    parser.read_string(archive.read(entry_point_paths[0]).decode("utf-8"))
    console_scripts = dict(parser.items("console_scripts"))
    if console_scripts != EXPECTED_CONSOLE_SCRIPTS:
        raise SystemExit("The wheel console-script contract is incomplete or unexpected.")

    required_package_files = {
        "matters/api/mcp/stdio.py",
        "matters/assets/matters.ico",
        "matters/assets/matters-icon.png",
    }
    missing_package_files = sorted(required_package_files - name_set)
    if missing_package_files:
        raise SystemExit(
            "The wheel is missing required package files: "
            + ", ".join(missing_package_files)
        )
    required_ui_suffixes = {
        "/share/matters/ui/index.html",
        "/share/matters/ui/styles.css",
        "/share/matters/ui/app.js",
    }
    missing_ui = sorted(
        suffix for suffix in required_ui_suffixes
        if not any(path.endswith(suffix) for path in names)
    )
    if missing_ui:
        raise SystemExit(
            "The wheel is missing required UI files: " + ", ".join(missing_ui)
        )

    skill_prefix = "matters/bundled_skills/"
    discovered_skill_ids = {
        path[len(skill_prefix):].split("/", 1)[0]
        for path in names
        if path.startswith(skill_prefix)
        and "/" in path[len(skill_prefix):]
        and "__pycache__" not in path
        and not path.endswith((".pyc", ".pyo", ".log"))
    }
    if discovered_skill_ids != set(REQUIRED_SKILL_IDS):
        raise SystemExit(
            "The wheel bundled-skill authority is not the exact required eleven-skill pack."
        )
    retired_hits = sorted(
        path for path in names if any(retired in path for retired in RETIRED_SKILL_IDS)
    )
    if retired_hits:
        raise SystemExit("The wheel contains retired Matters skill authority.")
    required_skill_paths = {
        f"{skill_prefix}{skill_id}/{relative}"
        for skill_id in REQUIRED_SKILL_IDS
        for relative in REQUIRED_SKILL_FILES
    }
    missing_skill_paths = sorted(required_skill_paths - name_set)
    if missing_skill_paths:
        raise SystemExit(
            "The wheel is missing required bundled-skill files: "
            + ", ".join(missing_skill_paths)
        )
    skill_rows = [
        f"{path}\t{hashlib.sha256(archive.read(path)).hexdigest()}"
        for path in sorted(required_skill_paths)
    ]
    content_rows = [
        f"{path}\t{hashlib.sha256(archive.read(path)).hexdigest()}"
        for path in sorted(path for path in names if not path.endswith("/"))
    ]
name = (message.get("Name") or "").strip().lower().replace("_", "-")
version = (message.get("Version") or "").strip()
if name != "matters" or version != expected_version:
    raise SystemExit("The wheel metadata does not match the frozen Matters source version.")
print(
    json.dumps(
        {
            "name": name,
            "version": version,
            "wheel_contents_fingerprint": fingerprint(content_rows),
            "skill_pack_identity": fingerprint(skill_rows),
        },
        sort_keys=True,
    )
)
"@
$WheelIdentityLines = @(
    $WheelIdentityScript | & $PythonPath - ([string]$Wheel.FullName) $ExpectedVersion
)
if ($LASTEXITCODE -ne 0 -or $WheelIdentityLines.Count -eq 0) {
    throw "The candidate Matters wheel identity could not be verified."
}
$WheelIdentityJson = [string]::Join([Environment]::NewLine, $WheelIdentityLines)
$WheelIdentity = $WheelIdentityJson | ConvertFrom-Json
if (
    $WheelIdentity.version -ne $ExpectedVersion -or
    [string]::IsNullOrWhiteSpace($WheelIdentity.wheel_contents_fingerprint) -or
    [string]::IsNullOrWhiteSpace($WheelIdentity.skill_pack_identity)
) {
    throw "The candidate Matters wheel contract identity is incomplete."
}

$SystemScriptsRoot = (& $PythonPath -c "import sysconfig; print(sysconfig.get_path('scripts'))").Trim()
$UserScriptsRoot = (& $PythonPath -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($SystemScriptsRoot)) {
    throw "The Matters launcher installation roots are unavailable."
}

$ShortcutRoot = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$ShortcutPaths = @((Join-Path $ShortcutRoot "Matters.lnk"))
if (-not $NoDesktopShortcut) {
    $ShortcutPaths += (Join-Path ([Environment]::GetFolderPath("Desktop")) "Matters.lnk")
}
$ReceiptRoot = Join-Path $PrivateRoot "install"
$ReceiptPath = Join-Path $ReceiptRoot "install-receipt.json"
New-Item -ItemType Directory -Force -Path $ReceiptRoot | Out-Null
$TransactionRoot = Join-Path $ReceiptRoot ("transactions\" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $TransactionRoot | Out-Null

$PriorDistribution = $null
$ReceiptState = $null
$ShortcutStates = @()
$WheelArchiveCreated = $false
$WheelArchivePath = $null
$ActivationStarted = $false
$Committed = $false

try {
    # No package mutation is allowed until every prior state has a byte-identical staging copy.
    $PriorDistribution = New-DistributionSnapshot -TransactionRoot $TransactionRoot
    $StateRoot = Join-Path $TransactionRoot "prior-files"
    $ReceiptState = Save-FileState -Path $ReceiptPath -StateRoot $StateRoot -StateName "install-receipt"
    $ShortcutIndex = 0
    foreach ($ShortcutPath in $ShortcutPaths) {
        $ShortcutIndex += 1
        $ShortcutStates += Save-FileState `
            -Path $ShortcutPath `
            -StateRoot $StateRoot `
            -StateName ("shortcut-{0:D2}" -f $ShortcutIndex)
    }

    $WheelSha256 = (Get-FileHash -LiteralPath $Wheel.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $WheelArchiveRoot = Join-Path $ReceiptRoot "wheels"
    New-Item -ItemType Directory -Force -Path $WheelArchiveRoot | Out-Null
    $WheelArchivePath = Join-Path $WheelArchiveRoot ("$WheelSha256-$($Wheel.Name)")
    if (Test-Path -LiteralPath $WheelArchivePath -PathType Leaf) {
        $ArchivedSha256 = (Get-FileHash -LiteralPath $WheelArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($ArchivedSha256 -ne $WheelSha256) {
            throw "The existing rollback wheel archive has a different identity."
        }
    } else {
        Copy-Item -LiteralPath $Wheel.FullName -Destination $WheelArchivePath
        $WheelArchiveCreated = $true
        $ArchivedSha256 = (Get-FileHash -LiteralPath $WheelArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($ArchivedSha256 -ne $WheelSha256) {
            throw "The candidate rollback wheel archive is not byte-identical."
        }
    }

    $ActivationStarted = $true
    & $PythonPath -m pip install --upgrade --force-reinstall --no-deps $Wheel.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Matters installation failed."
    }

    $InstalledIdentity = Get-InstalledMattersDistribution
    if (-not $InstalledIdentity.present -or $InstalledIdentity.version -ne $ExpectedVersion) {
        throw "The installed Matters distribution does not match the candidate version."
    }

    $InstalledContractScript = @"
# matters-installed-contract-identity-v1
import hashlib
import importlib.metadata as metadata
import json
import pathlib
import sys

REQUIRED_SKILL_IDS = (
    "matters-source-governance",
    "matters-inventory-reconciliation",
    "matters-freshness-maintenance",
    "matters-model-depth-maintenance",
    "matters-human-correction",
    "matters-model-miss-review",
    "matters-skill-runtime",
    "matters-research-orchestration",
    "matters-semantic-understanding",
    "matters-autonomous-maintenance",
    "matters-hero-image-generation",
)
RETIRED_SKILL_IDS = (
    "matters-card-visual-curation",
    "matters-generated-hero",
)
REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/service-contract.md",
    "scripts/invoke.py",
)
EXPECTED_CONSOLE_SCRIPTS = {
    "matters": "matters.cli.main:main",
    "matters-desktop": "matters.desktop:main",
    "matters-mcp": "matters.api.mcp.stdio:main",
}


def fingerprint(rows):
    payload = "\n".join(rows).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


expected_version, expected_skill_pack = sys.argv[1:3]
distribution = metadata.distribution("matters")
if distribution.version != expected_version:
    raise SystemExit("The installed Matters version does not match the candidate.")
files = tuple(distribution.files or ())
normalized = {str(path).replace("\\", "/"): path for path in files}
required_package_files = {
    "matters/api/mcp/stdio.py",
    "matters/assets/matters.ico",
    "matters/assets/matters-icon.png",
}
missing_package_files = sorted(required_package_files - set(normalized))
if missing_package_files:
    raise SystemExit(
        "The installed distribution is missing required package files: "
        + ", ".join(missing_package_files)
    )
for path in sorted(required_package_files):
    resolved = pathlib.Path(distribution.locate_file(normalized[path])).resolve()
    if not resolved.is_file():
        raise SystemExit(f"An installed required package file is unavailable: {path}")
required_ui_suffixes = {
    "/share/matters/ui/index.html",
    "/share/matters/ui/styles.css",
    "/share/matters/ui/app.js",
}
ui_paths = {
    suffix: next(
        (path for path in normalized if path.endswith(suffix)),
        None,
    )
    for suffix in required_ui_suffixes
}
if any(path is None for path in ui_paths.values()):
    raise SystemExit("The installed distribution is missing required UI files.")
for suffix, path in ui_paths.items():
    resolved = pathlib.Path(distribution.locate_file(normalized[path])).resolve()
    if not resolved.is_file():
        raise SystemExit(f"An installed required UI file is unavailable: {suffix}")
console_scripts = {
    entry.name: entry.value
    for entry in distribution.entry_points
    if entry.group == "console_scripts"
}
if console_scripts != EXPECTED_CONSOLE_SCRIPTS:
    raise SystemExit(
        "The installed Matters console-script contract is incomplete or unexpected."
    )
skill_prefix = "matters/bundled_skills/"
discovered_skill_ids = {
    path[len(skill_prefix):].split("/", 1)[0]
    for path in normalized
    if path.startswith(skill_prefix)
    and "/" in path[len(skill_prefix):]
    and "__pycache__" not in path
    and not path.endswith((".pyc", ".pyo", ".log"))
}
if discovered_skill_ids != set(REQUIRED_SKILL_IDS):
    raise SystemExit(
        "The installed bundled-skill authority is not the exact required eleven-skill pack."
    )
if any(
    retired in path
    for path in normalized
    for retired in RETIRED_SKILL_IDS
):
    raise SystemExit("The installed distribution contains retired Matters skill authority.")
required_skill_paths = {
    f"{skill_prefix}{skill_id}/{relative}"
    for skill_id in REQUIRED_SKILL_IDS
    for relative in REQUIRED_SKILL_FILES
}
missing_skill_paths = sorted(required_skill_paths - set(normalized))
if missing_skill_paths:
    raise SystemExit(
        "The installed distribution is missing required bundled-skill files: "
        + ", ".join(missing_skill_paths)
    )
skill_rows = []
for path in sorted(required_skill_paths):
    resolved = pathlib.Path(distribution.locate_file(normalized[path])).resolve()
    if not resolved.is_file():
        raise SystemExit(f"An installed bundled-skill file is unavailable: {path}")
    skill_rows.append(f"{path}\t{hashlib.sha256(resolved.read_bytes()).hexdigest()}")
skill_pack_identity = fingerprint(skill_rows)
if skill_pack_identity != expected_skill_pack:
    raise SystemExit("The installed skill pack is not byte-identical to the candidate wheel.")
print(
    json.dumps(
        {
            "version": distribution.version,
            "skill_pack_identity": skill_pack_identity,
            "stdio_sha256": hashlib.sha256(
                pathlib.Path(
                    distribution.locate_file(normalized["matters/api/mcp/stdio.py"])
                ).read_bytes()
            ).hexdigest(),
        },
        sort_keys=True,
    )
)
"@
    $InstalledContractLines = @(
        $InstalledContractScript |
            & $PythonPath - $ExpectedVersion ([string]$WheelIdentity.skill_pack_identity)
    )
    if ($LASTEXITCODE -ne 0 -or $InstalledContractLines.Count -eq 0) {
        throw "The installed Matters distribution contract could not be verified."
    }
    $InstalledContractJson = [string]::Join(
        [Environment]::NewLine,
        $InstalledContractLines
    )
    $InstalledContract = $InstalledContractJson | ConvertFrom-Json
    if (
        $InstalledContract.version -ne $ExpectedVersion -or
        $InstalledContract.skill_pack_identity -ne $WheelIdentity.skill_pack_identity
    ) {
        throw "The installed Matters distribution contract identity is incomplete."
    }

    $McpLauncher = @(
        (Join-Path $SystemScriptsRoot "matters-mcp.exe"),
        (Join-Path $UserScriptsRoot "matters-mcp.exe")
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($McpLauncher)) {
        throw "The installed Matters MCP launcher is unavailable."
    }
    $McpLauncher = (Resolve-Path -LiteralPath $McpLauncher).Path
    $McpValidationScript = @"
import json
import subprocess
import sys

launcher, expected_version = sys.argv[1:3]
requests = (
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "matters-installer", "version": "1"},
        },
    },
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
)
payload = "".join(
    json.dumps(request, separators=(",", ":")) + "\n"
    for request in requests
)
result = subprocess.run(
    [launcher],
    input=payload,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="strict",
    timeout=30,
    check=False,
)
if result.returncode != 0:
    raise SystemExit(
        "The installed Matters MCP launcher exited unsuccessfully: "
        + result.stderr.strip()
    )
responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
if len(responses) != 2:
    raise SystemExit("The installed Matters MCP launcher emitted unexpected stdout.")
initialize = responses[0].get("result", {})
if (
    initialize.get("protocolVersion") != "2025-11-25"
    or initialize.get("serverInfo", {}).get("version") != expected_version
):
    raise SystemExit("The installed Matters MCP initialize identity is stale.")
tool_names = {
    tool.get("name")
    for tool in responses[1].get("result", {}).get("tools", ())
}
required_tools = {
    "list_model_contracts",
    "get_situation_context",
    "record_user_observation",
}
if not required_tools.issubset(tool_names):
    raise SystemExit("The installed Matters MCP tool contract is incomplete.")
"@
    $McpValidationScript | & $PythonPath - $McpLauncher $ExpectedVersion
    if ($LASTEXITCODE -ne 0) {
        throw "The installed Matters MCP currentness check failed."
    }

    $DesktopLauncher = @(
        (Join-Path $SystemScriptsRoot "matters-desktop.exe"),
        (Join-Path $UserScriptsRoot "matters-desktop.exe")
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($DesktopLauncher)) {
        throw "The installed Matters desktop launcher is unavailable."
    }
    $DesktopLauncher = (Resolve-Path -LiteralPath $DesktopLauncher).Path

    & $DesktopLauncher --check
    if ($LASTEXITCODE -ne 0) {
        throw "The installed Matters desktop currentness check failed."
    }
    $IconPath = (& $PythonPath -c "from matters.desktop import application_icon_path; print(application_icon_path())").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($IconPath) -or -not (Test-Path -LiteralPath $IconPath -PathType Leaf)) {
        throw "The installed Matters application icon is unavailable."
    }
    $IconPath = (Resolve-Path -LiteralPath $IconPath).Path

    New-Item -ItemType Directory -Force -Path $ShortcutRoot | Out-Null
    $Shell = New-Object -ComObject WScript.Shell
    foreach ($ShortcutPath in $ShortcutPaths) {
        $Shortcut = $Shell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = $DesktopLauncher
        $Shortcut.WorkingDirectory = $PrivateRoot
        $Shortcut.Description = "Matters private object browser"
        $Shortcut.IconLocation = "$IconPath,0"
        $Shortcut.Save()

        $VerifiedShortcut = $Shell.CreateShortcut($ShortcutPath)
        if (
            -not (Test-Path -LiteralPath $ShortcutPath -PathType Leaf) -or
            [System.IO.Path]::GetFullPath($VerifiedShortcut.TargetPath) -ne [System.IO.Path]::GetFullPath($DesktopLauncher) -or
            [System.IO.Path]::GetFullPath($VerifiedShortcut.WorkingDirectory) -ne [System.IO.Path]::GetFullPath($PrivateRoot) -or
            -not $VerifiedShortcut.IconLocation.StartsWith($IconPath, [System.StringComparison]::OrdinalIgnoreCase)
        ) {
            throw "The installed Matters shortcut currentness check failed: $ShortcutPath"
        }
    }

    $Receipt = [ordered]@{
        schema = "matters.local-install-receipt.v1"
        matters_version = $ExpectedVersion
        wheel_sha256 = $WheelSha256
        wheel_archive = $WheelArchivePath
        launcher = $DesktopLauncher
        mcp_launcher = $McpLauncher
        wheel_contents_fingerprint = $WheelIdentity.wheel_contents_fingerprint
        skill_pack_identity = $WheelIdentity.skill_pack_identity
        application_icon = $IconPath
        shortcuts = $ShortcutPaths
        private_root = $PrivateRoot
        installed_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $ReceiptCandidatePath = Join-Path $TransactionRoot "candidate-install-receipt.json"
    $ReceiptJson = ($Receipt | ConvertTo-Json -Depth 4) + [Environment]::NewLine
    Write-Utf8NoBom -Path $ReceiptCandidatePath -Content $ReceiptJson
    $VerifiedReceipt = Get-Content -LiteralPath $ReceiptCandidatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (
        $VerifiedReceipt.schema -ne "matters.local-install-receipt.v1" -or
        $VerifiedReceipt.matters_version -ne $ExpectedVersion -or
        $VerifiedReceipt.wheel_sha256 -ne $WheelSha256 -or
        $VerifiedReceipt.wheel_archive -ne $WheelArchivePath -or
        $VerifiedReceipt.mcp_launcher -ne $McpLauncher -or
        $VerifiedReceipt.wheel_contents_fingerprint -ne $WheelIdentity.wheel_contents_fingerprint -or
        $VerifiedReceipt.skill_pack_identity -ne $WheelIdentity.skill_pack_identity
    ) {
        throw "The Matters install receipt candidate failed currentness validation."
    }
    Move-Item -LiteralPath $ReceiptCandidatePath -Destination $ReceiptPath -Force
    $PublishedReceipt = Get-Content -LiteralPath $ReceiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (
        $PublishedReceipt.matters_version -ne $ExpectedVersion -or
        $PublishedReceipt.wheel_sha256 -ne $WheelSha256 -or
        $PublishedReceipt.launcher -ne $DesktopLauncher -or
        $PublishedReceipt.mcp_launcher -ne $McpLauncher -or
        $PublishedReceipt.wheel_contents_fingerprint -ne $WheelIdentity.wheel_contents_fingerprint -or
        $PublishedReceipt.skill_pack_identity -ne $WheelIdentity.skill_pack_identity
    ) {
        throw "The published Matters install receipt failed currentness validation."
    }

    if (-not $PrivateRootWasExplicit) {
        [Environment]::SetEnvironmentVariable("MATTERS_HOME", $PrivateRoot, "User")
    }
    $Committed = $true
} catch {
    $InstallFailure = $_
    $RollbackErrors = [System.Collections.Generic.List[string]]::new()

    if ($ActivationStarted -and $null -ne $PriorDistribution) {
        try {
            Restore-DistributionSnapshot -Snapshot $PriorDistribution
        } catch {
            $RollbackErrors.Add("package: $($_.Exception.Message)")
        }
    }
    foreach ($ShortcutState in $ShortcutStates) {
        try {
            Restore-FileState -State $ShortcutState
        } catch {
            $RollbackErrors.Add("shortcut: $($_.Exception.Message)")
        }
    }
    if ($null -ne $ReceiptState) {
        try {
            Restore-FileState -State $ReceiptState
        } catch {
            $RollbackErrors.Add("receipt: $($_.Exception.Message)")
        }
    }
    if ($WheelArchiveCreated -and -not [string]::IsNullOrWhiteSpace($WheelArchivePath)) {
        try {
            Remove-Item -LiteralPath $WheelArchivePath -Force
        } catch {
            $RollbackErrors.Add("wheel archive: $($_.Exception.Message)")
        }
    }

    if ($RollbackErrors.Count -gt 0) {
        throw "Matters installation failed and rollback is incomplete. Recovery staging remains at $TransactionRoot. Cause: $($InstallFailure.Exception.Message). Rollback errors: $([string]::Join('; ', $RollbackErrors))"
    }

    Remove-Item -LiteralPath $TransactionRoot -Recurse -Force
    throw "Matters installation failed; the prior package, shortcuts, and receipt were restored. Cause: $($InstallFailure.Exception.Message)"
} finally {
    if ($Committed -and (Test-Path -LiteralPath $TransactionRoot)) {
        Remove-Item -LiteralPath $TransactionRoot -Recurse -Force
    }
}

$Receipt | ConvertTo-Json -Depth 4
