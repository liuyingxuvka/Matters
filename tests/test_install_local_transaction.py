from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv
import zipfile

import pytest


pytestmark = [
    pytest.mark.release,
    pytest.mark.skipif(sys.platform != "win32", reason="Windows installer contract"),
]


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


def _wheel_bytes(version: str) -> dict[str, bytes]:
    package = {
        "matters/__init__.py": (
            f'VERSION = "{version}"\n'
        ).encode(),
        "matters/desktop.py": b"""\
import os

def application_icon_path():
    return os.environ["MATTERS_FAKE_ICON"]

def main():
    if os.environ.get("MATTERS_FAKE_FAIL_CHECK") == "1":
        return 19
    return 0
""",
        "matters/cli/__init__.py": b"",
        "matters/cli/main.py": b"def main():\n    return 0\n",
        "matters/api/__init__.py": b"",
        "matters/api/mcp/__init__.py": b"",
        "matters/api/mcp/stdio.py": b"""\
import json
import os
import sys

from matters import VERSION


def main():
    if os.environ.get("MATTERS_FAKE_FAIL_MCP") == "1":
        return 29
    initialized = False
    for line in sys.stdin:
        request = json.loads(line)
        method = request.get("method")
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "matters", "version": VERSION},
                },
            }
        elif method == "notifications/initialized":
            initialized = True
            continue
        elif method == "tools/list" and initialized:
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": [
                        {"name": "list_model_contracts"},
                        {"name": "get_situation_context"},
                        {"name": "record_user_observation"},
                    ]
                },
            }
        else:
            return 31
        print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0
""",
        "matters/assets/matters.ico": b"isolated-ico",
        "matters/assets/matters-icon.png": b"isolated-png",
    }
    dist_info = f"matters-{version}.dist-info"
    data_root = f"matters-{version}.data/data/share/matters/ui"
    plugin_root = f"matters-{version}.data/data/share/matters/plugins/matters"
    package.update(
        {
            f"{data_root}/index.html": b"<html></html>\n",
            f"{data_root}/styles.css": b"body {}\n",
            f"{data_root}/app.js": b"// isolated ui\n",
            f"{plugin_root}/.mcp.json": b'{"mcpServers": {}}\n',
            f"{plugin_root}/.codex-plugin/plugin.json": b'{"name": "matters"}\n',
            f"{plugin_root}/skills/matters/SKILL.md": b"---\nname: matters\n---\n",
            f"{plugin_root}/skills/matters/references/installation.md": b"# AI setup\n",
            f"{plugin_root}/skills/matters/references/service-contract.md": b"# Service\n",
        }
    )
    for skill_id in REQUIRED_SKILL_IDS:
        skill_root = f"matters/bundled_skills/{skill_id}"
        package.update(
            {
                f"{skill_root}/SKILL.md": f"---\nname: {skill_id}\n---\n".encode(),
                f"{skill_root}/agents/openai.yaml": b"interface: {}\n",
                f"{skill_root}/references/service-contract.md": b"# Contract\n",
                f"{skill_root}/scripts/invoke.py": b"raise SystemExit(0)\n",
            }
        )
    package.update(
        {
            f"{dist_info}/METADATA": (
                "Metadata-Version: 2.1\n"
                "Name: Matters\n"
                f"Version: {version}\n"
                "\n"
            ).encode(),
            f"{dist_info}/WHEEL": (
                "Wheel-Version: 1.0\n"
                "Generator: matters-transaction-test\n"
                "Root-Is-Purelib: true\n"
                "Tag: py3-none-any\n"
                "\n"
            ).encode(),
            f"{dist_info}/entry_points.txt": (
                "[console_scripts]\n"
                "matters = matters.cli.main:main\n"
                "matters-desktop = matters.desktop:main\n"
                "matters-mcp = matters.api.mcp.stdio:main\n"
            ).encode(),
        }
    )
    record_rows = []
    for name, content in sorted(package.items()):
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(content).digest()
        ).rstrip(b"=").decode()
        record_rows.append(f"{name},sha256={digest},{len(content)}")
    record_rows.append(f"{dist_info}/RECORD,,")
    package[f"{dist_info}/RECORD"] = ("\n".join(record_rows) + "\n").encode()
    return package


def _write_wheel(
    root: Path,
    version: str,
    *,
    drop: tuple[str, ...] = (),
) -> Path:
    wheel = root / f"matters-{version}-py3-none-any.whl"
    package = _wheel_bytes(version)
    for path in drop:
        package.pop(path)
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in package.items():
            archive.writestr(name, content)
    return wheel


def _powershell() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    assert executable is not None
    return executable


def _run(
    command: list[str],
    *,
    env: dict[str, str],
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        env=env,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def _installed_version(python: Path, env: dict[str, str]) -> str:
    result = _run(
        [
            str(python),
            "-c",
            "import importlib.metadata as m; print(m.version('matters'))",
        ],
        env=env,
        check=True,
    )
    return result.stdout.strip()


def _create_shortcut(
    path: Path,
    target: Path,
    *,
    env: dict[str, str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    shortcut_env = dict(env)
    shortcut_env["MATTERS_TEST_SHORTCUT"] = str(path)
    shortcut_env["MATTERS_TEST_TARGET"] = str(target)
    script = r"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($env:MATTERS_TEST_SHORTCUT)
$shortcut.TargetPath = $env:MATTERS_TEST_TARGET
$shortcut.WorkingDirectory = Split-Path -Parent $env:MATTERS_TEST_TARGET
$shortcut.Description = "prior Matters shortcut"
$shortcut.Save()
"""
    _run(
        [_powershell(), "-NoProfile", "-Command", script],
        env=shortcut_env,
        check=True,
    )


def _installer_command(
    script: Path,
    python: Path,
    candidate_wheel: Path,
) -> list[str]:
    return [
        _powershell(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-PythonPath",
        str(python),
        "-WheelPath",
        str(candidate_wheel),
        "-SkipBuild",
        "-NoDesktopShortcut",
    ]


def _prepare_private_state(
    root: Path,
    *,
    old_launcher: Path,
    base_env: dict[str, str],
) -> tuple[dict[str, str], Path, bytes, Path, bytes]:
    root.mkdir(parents=True, exist_ok=True)
    private_root = root / "private"
    appdata = root / "appdata"
    icon = root / "icon.ico"
    icon.write_bytes(b"isolated-icon")
    receipt = private_root / "install" / "install-receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    prior_receipt = b'{"schema":"prior-isolated-receipt"}\n'
    receipt.write_bytes(prior_receipt)
    shortcut = (
        appdata
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Matters.lnk"
    )
    env = dict(base_env)
    env.update(
        {
            "MATTERS_HOME": str(private_root),
            "APPDATA": str(appdata),
            "MATTERS_FAKE_ICON": str(icon),
        }
    )
    _create_shortcut(shortcut, old_launcher, env=env)
    prior_shortcut = shortcut.read_bytes()
    return env, receipt, prior_receipt, shortcut, prior_shortcut


def _assert_prior_state_restored(
    *,
    python: Path,
    env: dict[str, str],
    receipt: Path,
    prior_receipt: bytes,
    shortcut: Path,
    prior_shortcut: bytes,
) -> None:
    assert _installed_version(python, env) == "0.2.0"
    assert receipt.read_bytes() == prior_receipt
    assert shortcut.read_bytes() == prior_shortcut
    wheels = receipt.parent / "wheels"
    assert not wheels.exists() or not any(wheels.iterdir())
    transactions = receipt.parent / "transactions"
    assert not transactions.exists() or not any(transactions.iterdir())


def _patched_installer(
    root: Path,
    *,
    source: Path,
    replacement_target: str,
    replacement: str,
) -> Path:
    repository = root / "repo"
    scripts = repository / "scripts"
    version_root = repository / "src" / "matters"
    scripts.mkdir(parents=True)
    version_root.mkdir(parents=True)
    installer = source.read_text(encoding="utf-8")
    assert replacement_target in installer
    (scripts / "install_local.ps1").write_text(
        installer.replace(replacement_target, replacement, 1),
        encoding="utf-8",
    )
    (version_root / "_version.py").write_text(
        'VERSION = "0.3.1"\n',
        encoding="utf-8",
    )
    return scripts / "install_local.ps1"


def test_installer_transaction_blocks_or_restores_every_post_activation_stage(
    tmp_path: Path,
) -> None:
    root = tmp_path
    wheel_root = root / "wheels"
    wheel_root.mkdir()
    prior_wheel = _write_wheel(wheel_root, "0.2.0")
    candidate_wheel = _write_wheel(wheel_root, "0.3.1")
    environment_root = root / "venv"
    venv.EnvBuilder(with_pip=True).create(environment_root)
    python = environment_root / "Scripts" / "python.exe"
    base_env = dict(os.environ)
    base_env.pop("MATTERS_FAKE_FAIL_CHECK", None)
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-deps",
            str(prior_wheel),
        ],
        env=base_env,
        check=True,
    )
    old_launcher = environment_root / "Scripts" / "matters-desktop.exe"
    assert old_launcher.is_file()
    source_installer = Path("scripts/install_local.ps1").resolve()

    # A same-version filename and valid METADATA are insufficient. Missing
    # MCP transport must fail before candidate activation.
    invalid_wheel_root = root / "invalid-wheels"
    invalid_wheel_root.mkdir()
    invalid_wheel = _write_wheel(
        invalid_wheel_root,
        "0.3.1",
        drop=("matters/api/mcp/stdio.py",),
    )
    invalid_root = root / "invalid-wheel"
    invalid = _prepare_private_state(
        invalid_root,
        old_launcher=old_launcher,
        base_env=base_env,
    )
    invalid_result = _run(
        _installer_command(source_installer, python, invalid_wheel),
        env=invalid[0],
    )
    assert invalid_result.returncode != 0
    assert "missing required package files" in (
        invalid_result.stdout + invalid_result.stderr
    )
    _assert_prior_state_restored(
        python=python,
        env=invalid[0],
        receipt=invalid[1],
        prior_receipt=invalid[2],
        shortcut=invalid[3],
        prior_shortcut=invalid[4],
    )

    # A non-file in the exact installed RECORD inventory makes restoration
    # unprovable, so the candidate must never activate.
    blocked_root = root / "blocked"
    blocked = _prepare_private_state(
        blocked_root,
        old_launcher=old_launcher,
        base_env=base_env,
    )
    installed_init = environment_root / "Lib" / "site-packages" / "matters" / "__init__.py"
    prior_init = installed_init.read_bytes()
    installed_init.unlink()
    installed_init.mkdir()
    blocked_result = _run(
        _installer_command(source_installer, python, candidate_wheel),
        env=blocked[0],
    )
    assert blocked_result.returncode != 0
    assert "non-file path" in (blocked_result.stdout + blocked_result.stderr)
    installed_init.rmdir()
    installed_init.write_bytes(prior_init)
    _assert_prior_state_restored(
        python=python,
        env=blocked[0],
        receipt=blocked[1],
        prior_receipt=blocked[2],
        shortcut=blocked[3],
        prior_shortcut=blocked[4],
    )

    # Launcher currentness failure happens after candidate activation.
    launcher_root = root / "launcher-failure"
    launcher = _prepare_private_state(
        launcher_root,
        old_launcher=old_launcher,
        base_env=base_env,
    )
    launcher[0]["MATTERS_FAKE_FAIL_CHECK"] = "1"
    launcher_result = _run(
        _installer_command(source_installer, python, candidate_wheel),
        env=launcher[0],
    )
    assert launcher_result.returncode != 0
    assert "desktop currentness check failed" in (
        launcher_result.stdout + launcher_result.stderr
    )
    _assert_prior_state_restored(
        python=python,
        env=launcher[0],
        receipt=launcher[1],
        prior_receipt=launcher[2],
        shortcut=launcher[3],
        prior_shortcut=launcher[4],
    )

    # Icon validation failure also restores the package before returning.
    icon_root = root / "icon-failure"
    icon = _prepare_private_state(
        icon_root,
        old_launcher=old_launcher,
        base_env=base_env,
    )
    icon[0]["MATTERS_FAKE_ICON"] = str(icon_root / "missing.ico")
    icon_result = _run(
        _installer_command(source_installer, python, candidate_wheel),
        env=icon[0],
    )
    assert icon_result.returncode != 0
    assert "application icon is unavailable" in (
        icon_result.stdout + icon_result.stderr
    )
    _assert_prior_state_restored(
        python=python,
        env=icon[0],
        receipt=icon[1],
        prior_receipt=icon[2],
        shortcut=icon[3],
        prior_shortcut=icon[4],
    )

    # MCP protocol failure happens after candidate activation and exact
    # distribution-contract validation, and must restore the whole prior state.
    mcp_root = root / "mcp-failure"
    mcp = _prepare_private_state(
        mcp_root,
        old_launcher=old_launcher,
        base_env=base_env,
    )
    mcp[0]["MATTERS_FAKE_FAIL_MCP"] = "1"
    mcp_result = _run(
        _installer_command(source_installer, python, candidate_wheel),
        env=mcp[0],
    )
    assert mcp_result.returncode != 0
    assert "MCP currentness check failed" in (
        mcp_result.stdout + mcp_result.stderr
    )
    _assert_prior_state_restored(
        python=python,
        env=mcp[0],
        receipt=mcp[1],
        prior_receipt=mcp[2],
        shortcut=mcp[3],
        prior_shortcut=mcp[4],
    )

    # Mutation-testing copies inject a failure immediately after the real
    # shortcut save and after the real receipt publication. The production
    # catch/rollback path is otherwise byte-identical.
    shortcut_script = _patched_installer(
        root / "shortcut-script",
        source=source_installer,
        replacement_target="        $Shortcut.Save()\n",
        replacement=(
            "        $Shortcut.Save()\n"
            '        throw "isolated shortcut validation failure"\n'
        ),
    )
    shortcut_root = root / "shortcut-failure"
    shortcut = _prepare_private_state(
        shortcut_root,
        old_launcher=old_launcher,
        base_env=base_env,
    )
    shortcut_result = _run(
        _installer_command(shortcut_script, python, candidate_wheel),
        env=shortcut[0],
    )
    assert shortcut_result.returncode != 0
    assert "validation failure" in (
        shortcut_result.stdout + shortcut_result.stderr
    )
    _assert_prior_state_restored(
        python=python,
        env=shortcut[0],
        receipt=shortcut[1],
        prior_receipt=shortcut[2],
        shortcut=shortcut[3],
        prior_shortcut=shortcut[4],
    )

    receipt_script = _patched_installer(
        root / "receipt-script",
        source=source_installer,
        replacement_target=(
            "    $PublishedReceipt = Get-Content -LiteralPath $ReceiptPath"
        ),
        replacement=(
            '    throw "isolated receipt publication failure"\n'
            "    $PublishedReceipt = Get-Content -LiteralPath $ReceiptPath"
        ),
    )
    receipt_root = root / "receipt-failure"
    receipt = _prepare_private_state(
        receipt_root,
        old_launcher=old_launcher,
        base_env=base_env,
    )
    receipt_result = _run(
        _installer_command(receipt_script, python, candidate_wheel),
        env=receipt[0],
    )
    assert receipt_result.returncode != 0
    assert "publication failure" in (
        receipt_result.stdout + receipt_result.stderr
    )
    _assert_prior_state_restored(
        python=python,
        env=receipt[0],
        receipt=receipt[1],
        prior_receipt=receipt[2],
        shortcut=receipt[3],
        prior_shortcut=receipt[4],
    )

    # The same isolated environment can finally commit the candidate.
    success_root = root / "success"
    success = _prepare_private_state(
        success_root,
        old_launcher=old_launcher,
        base_env=base_env,
    )
    success_result = _run(
        _installer_command(source_installer, python, candidate_wheel),
        env=success[0],
    )
    assert success_result.returncode == 0, (
        success_result.stdout + success_result.stderr
    )
    assert _installed_version(python, success[0]) == "0.3.1"
    installed_receipt = json.loads(success[1].read_text(encoding="utf-8"))
    assert installed_receipt["matters_version"] == "0.3.1"
    assert Path(installed_receipt["mcp_launcher"]).is_file()
    assert installed_receipt["wheel_contents_fingerprint"].startswith("sha256:")
    assert installed_receipt["skill_pack_identity"].startswith("sha256:")
    assert Path(installed_receipt["wheel_archive"]).is_file()
    assert success[3].read_bytes() != success[4]
