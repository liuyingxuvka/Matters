import json
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

import pytest

from matters.infrastructure.capability_status.status import validate_private_root
from scripts.jira_slice_preflight import build_preflight
import scripts.check_public_boundary as public_boundary
from scripts.check_public_boundary import _git_executable, _scan_text, check


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + sha256(value).hexdigest()


def _desktop_manifest(files: dict[str, bytes], toolchain: bytes) -> bytes:
    rows = [
        f"{path.removeprefix('Matters/')}\t{sha256(content).hexdigest()}"
        for path, content in sorted(files.items())
    ]
    payload = {
        "application_id": "matters.desktop",
        "matters_version": "0.3.0",
        "shell_kind": "packaged_windows_webview",
        "package_sha256": _sha256_bytes("\n".join(rows).encode("utf-8")),
        "executable_sha256": _sha256_bytes(files["Matters/Matters.exe"]),
        "build_toolchain_sha256": _sha256_bytes(toolchain),
        "ui_bundle_sha256": _sha256_bytes(b"synthetic-ui"),
        "icon_sha256": _sha256_bytes(b"synthetic-icon"),
        "service_contract_identity": "matters.service.contract:0.3.0",
        "worker_contract_identity": "matters.worker.contract:0.3.0",
        "skill_pack_identity": "matters.skill-pack.synthetic",
        "available_locales": ["en", "zh-CN"],
        "loopback_only": True,
        "owns_application_window": True,
        "packaged_ui": True,
        "private_shell_profile": True,
        "persists_locale_density_window_state": True,
        "startup_health_gate": True,
        "in_shell_recovery_surface": True,
        "clean_owned_process_shutdown": True,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    payload["manifest_fingerprint"] = _sha256_bytes(canonical)
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


def test_private_roots_must_be_external_and_public_inventory_is_clean():
    repository = Path(".").resolve()
    inside = validate_private_root(repository / "runtime", repository)
    outside = validate_private_root(repository.parent / "MATTERS_HOME", repository)
    assert inside.status == "blocked"
    assert outside.status == "active"
    report = check(
        repository,
        repository / "docs/security/public-file-policy.json",
    )
    assert report["ok"], report["findings"]


def test_jira_preflight_has_no_read_without_external_authorization(tmp_path):
    repository = Path(".").resolve()
    result = build_preflight(
        repository_root=repository,
        slice_id="J1",
        g8_current=True,
    )
    assert not result["read_allowed"]
    assert result["real_jira_access"] == "not_run"
    assert result["blockers"] == ["explicit_authorization_missing"]

    inside = repository / "synthetic-authorization.json"
    inside.write_text("{}", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="outside Git"):
            build_preflight(
                repository_root=repository,
                slice_id="J1",
                g8_current=True,
                authorization_path=inside,
            )
    finally:
        inside.unlink()


def _write_boundary_fixture(root: Path, *, ignore_required: bool) -> None:
    (root / "src").mkdir()
    (root / "evidence").mkdir()
    (root / "src/app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "src/required.py").write_text("REQUIRED = True\n", encoding="utf-8")
    (root / "evidence/receipt.json").write_text("{}\n", encoding="utf-8")
    ignore_lines = ["__pycache__/"]
    if ignore_required:
        ignore_lines.append("src/required.py")
    (root / ".gitignore").write_text("\n".join(ignore_lines) + "\n", encoding="utf-8")
    inventory = {
        "schema": "matters.required-public-inventory.v1",
        "authority": "test",
        "required_singletons": [".gitignore", "inventory.json", "policy.json"],
        "required_trees": ["evidence", "src"],
        "excluded_patterns": ["**/__pycache__/**", "**/*.pyc"],
        "fingerprint_excluded_patterns": ["evidence/**"],
        "package_projection": [
            {
                "source_prefix": "src/",
                "source_pattern": "src/**",
                "wheel_prefix": "",
            }
        ],
        "release_required_singletons": [],
    }
    policy = {
        "schema": "matters.public-file-policy.v1",
        "required_public_inventory": "inventory.json",
        "allowed_paths": [
            ".gitignore",
            "evidence/**",
            "inventory.json",
            "policy.json",
            "src/**",
        ],
        "forbidden_paths": ["runtime/**"],
        "external_private_roots": [
            {
                "id": "PRIVATE_TEST_ROOT",
                "relative_path": "../private-test-root",
                "acl_disposition": "user_review_required",
                "encryption_disposition": "user_review_required",
                "cloud_sync_disposition": "user_review_required",
            }
        ],
        "maximum_public_file_bytes": 100000,
    }
    (root / "inventory.json").write_text(
        json.dumps(inventory),
        encoding="utf-8",
    )
    (root / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
    subprocess.run(
        (_git_executable(), "init", "--quiet"),
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_decoded_json_yaml_and_encoded_home_paths_are_rejected(tmp_path):
    private_roots = (("PRIVATE_TEST_ROOT", tmp_path / "private-test-root"),)
    windows_path = "C:" + "\\\\" + "Users" + "\\\\" + "synthetic-user" + "\\\\" + "file.txt"
    json_payload = json.dumps({"path": windows_path})
    json_findings = _scan_text(
        "synthetic.json",
        json_payload,
        ".json",
        private_roots,
    )
    assert {row["code"] for row in json_findings} == {"absolute_home_path_leak"}

    encoded_posix = "%2F" + "home" + "%2Fsynthetic-user%2Ffile.txt"
    yaml_payload = "path: " + json.dumps(encoded_posix)
    yaml_findings = _scan_text(
        "synthetic.yaml",
        yaml_payload,
        ".yaml",
        private_roots,
    )
    assert {row["code"] for row in yaml_findings} == {"absolute_home_path_leak"}


def test_private_email_and_opaque_gmail_identifiers_are_rejected(tmp_path):
    private_roots = (("PRIVATE_TEST_ROOT", tmp_path / "private-test-root"),)
    nonreserved_address = "private-person@" + "nonreserved" + "." + "synthetic"
    private_payload = json.dumps(
        {
            "from": nonreserved_address,
            "message_id": "18f4abcde1234567",
        }
    )
    findings = _scan_text(
        "private-mail.json",
        private_payload,
        ".json",
        private_roots,
    )
    assert {row["code"] for row in findings} >= {
        "personal_email_identifier_leak",
        "gmail_identifier_leak",
    }

    synthetic_payload = json.dumps(
        {
            "from": "synthetic@example.invalid",
            "message_id": "synthetic-message-001",
        }
    )
    assert not _scan_text(
        "synthetic-mail.json",
        synthetic_payload,
        ".json",
        private_roots,
    )


def test_required_ignored_source_fails_and_cache_does_not_change_fingerprint(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=True)
    policy = tmp_path / "policy.json"
    blocked = check(tmp_path, policy)
    assert not blocked["ok"]
    assert {
        (row["code"], row["path"])
        for row in blocked["findings"]
    } >= {("required_public_file_ignored", "src/required.py")}

    (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    clean = check(tmp_path, policy)
    assert clean["ok"], clean["findings"]
    before = clean["required_public_inventory"]["required_fingerprint"]

    cache = tmp_path / "src/__pycache__"
    cache.mkdir()
    (cache / "noise.pyc").write_bytes(b"not-a-real-bytecode-file")
    after_report = check(tmp_path, policy)
    assert after_report["ok"], after_report["findings"]
    assert after_report["required_public_inventory"]["required_fingerprint"] == before

    (tmp_path / "evidence/receipt.json").write_text(
        '{"status":"regenerated"}\n',
        encoding="utf-8",
    )
    regenerated = check(tmp_path, policy)
    assert regenerated["ok"], regenerated["findings"]
    assert regenerated["required_public_inventory"]["required_fingerprint"] == before


def test_no_commit_and_missing_release_inputs_are_visible_with_portable_paths(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    report = check(tmp_path, tmp_path / "policy.json")
    assert report["ok"], report["findings"]
    assert report["root"] == "repo://"
    assert report["policy"] == "repo://policy.json"
    assert report["inventories"]["tracked"]["status"] == "not_available"
    assert report["inventories"]["tracked"]["reason"] == "repository_has_no_commit"
    assert report["inventories"]["clean_clone"]["status"] == "not_available"
    assert report["inventories"]["package"]["status"] == "not_run"
    serialized = json.dumps(report, sort_keys=True)
    assert str(tmp_path) not in serialized


def test_existing_release_metadata_is_admitted_before_release_gate(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    inventory_path = tmp_path / "inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["release_required_singletons"] = ["CHANGELOG.md"]
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    policy_path = tmp_path / "policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["allowed_paths"].append("CHANGELOG.md")
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# Changes\n", encoding="utf-8")

    routine = check(tmp_path, policy_path)

    assert routine["ok"], routine["findings"]
    assert not any(
        row["code"] == "public_candidate_not_in_required_inventory"
        and row["path"] == "CHANGELOG.md"
        for row in routine["findings"]
    )


def test_link_clean_clone_and_package_inventory_mismatches_fail_closed(
    tmp_path,
    monkeypatch,
):
    repository = tmp_path / "repository"
    repository.mkdir()
    _write_boundary_fixture(repository, ignore_required=False)
    policy = repository / "policy.json"

    linked = repository / "src/linked.py"
    linked.write_text("LINKED = True\n", encoding="utf-8")
    real_link_check = public_boundary._is_link_or_junction
    monkeypatch.setattr(
        public_boundary,
        "_is_link_or_junction",
        lambda path: path == linked or real_link_check(path),
    )
    linked_report = check(repository, policy)
    assert {
        (row["code"], row["path"])
        for row in linked_report["findings"]
    } >= {("required_public_link_forbidden", "src/linked.py")}

    monkeypatch.setattr(public_boundary, "_is_link_or_junction", real_link_check)
    clean_clone = tmp_path / "clean-clone"
    shutil.copytree(repository, clean_clone)
    (clean_clone / "src/required.py").unlink()

    wheel = tmp_path / "matters-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("app.py", "VALUE = 1\n")
    mismatch = check(
        repository,
        policy,
        clean_clone_root=clean_clone,
        package_artifacts=(wheel,),
    )
    assert {
        row["code"] for row in mismatch["findings"]
    } >= {"clean_clone_inventory_mismatch", "package_inventory_mismatch"}


def test_package_inventory_rejects_stale_or_unexpected_runtime_payload(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    inventory_path = tmp_path / "inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["wheel_data_projection"] = []
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    wheel = tmp_path / "matters-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("app.py", "VALUE = 1\n")
        archive.writestr("required.py", "REQUIRED = True\n")
        archive.writestr("stale/private-copy.py", "SHOULD_NOT_SHIP = True\n")
        archive.writestr(
            "matters-0.0.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: matters\nVersion: 0.0.0\n",
        )

    report = check(
        tmp_path,
        tmp_path / "policy.json",
        package_artifacts=(wheel,),
    )

    package = report["inventories"]["package"]
    assert package["status"] == "fail"
    assert package["artifacts"][0]["unexpected_public"] == [
        "stale/private-copy.py"
    ]
    assert {
        row["code"] for row in report["findings"]
    } >= {"package_inventory_mismatch"}


def test_sdist_excludes_control_receipts_and_rejects_their_return(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    inventory_path = tmp_path / "inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["sdist_excluded_patterns"] = ["evidence/**"]
    inventory["package_forbidden_patterns"] = ["evidence/**"]
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    clean_sdist = tmp_path / "matters-0.0.0.tar.gz"
    with tarfile.open(clean_sdist, "w:gz") as archive:
        for relative in (
            ".gitignore",
            "inventory.json",
            "policy.json",
            "src/app.py",
            "src/required.py",
        ):
            archive.add(
                tmp_path / relative,
                arcname=f"matters-0.0.0/{relative}",
            )

    clean = check(
        tmp_path,
        tmp_path / "policy.json",
        package_artifacts=(clean_sdist,),
    )
    assert clean["inventories"]["package"]["status"] == "pass"

    leaky_sdist = tmp_path / "matters-0.0.0-leaky.tar.gz"
    with tarfile.open(leaky_sdist, "w:gz") as archive:
        for relative in (
            ".gitignore",
            "evidence/receipt.json",
            "inventory.json",
            "policy.json",
            "src/app.py",
            "src/required.py",
        ):
            archive.add(
                tmp_path / relative,
                arcname=f"matters-0.0.0/{relative}",
            )

    leaky = check(
        tmp_path,
        tmp_path / "policy.json",
        package_artifacts=(leaky_sdist,),
    )
    artifact = leaky["inventories"]["package"]["artifacts"][0]
    assert artifact["status"] == "fail"
    assert artifact["forbidden_payload"] == ["evidence/receipt.json"]


def test_generated_package_text_is_scanned_for_private_home_paths(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    inventory_path = tmp_path / "inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["wheel_data_projection"] = []
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    wheel = tmp_path / "matters-0.0.0-py3-none-any.whl"
    private_path = (
        "C:" + "\\\\" + "Users" + "\\\\private-user\\\\record.txt"
    )
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "app.py",
            f"PRIVATE_PATH = {private_path!r}\n",
        )
        archive.writestr("required.py", "REQUIRED = True\n")
        archive.writestr(
            "matters-0.0.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: matters\nVersion: 0.0.0\n",
        )

    report = check(
        tmp_path,
        tmp_path / "policy.json",
        package_artifacts=(wheel,),
    )

    assert report["inventories"]["package"]["status"] == "fail"
    assert any(
        row["code"] == "absolute_home_path_leak"
        and row["path"].startswith("package://matters-0.0.0")
        for row in report["findings"]
    )


def test_desktop_zip_has_its_own_inventory_and_vendor_metadata_boundary(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    executable = b"\0synthetic-windows-executable"
    vendor_metadata = (
        "Author-email: dependency-author@" + "vendor.invalid\n"
    ).encode("utf-8")
    files = {
        "Matters/Matters.exe": executable,
        "Matters/_internal/pywebview-1.0.dist-info/METADATA": vendor_metadata,
    }
    toolchain = b'{"schema":"synthetic.desktop-toolchain"}\n'
    desktop_zip = tmp_path / "Matters-0.3.0-windows-x64.zip"
    with zipfile.ZipFile(desktop_zip, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
        archive.writestr("README.md", "# Matters\n")
        archive.writestr("AI-SETUP.md", "# AI setup\n")
        archive.writestr("desktop-build-toolchain.json", toolchain)
        archive.writestr(
            "desktop-manifest.json",
            _desktop_manifest(files, toolchain),
        )

    report = check(
        tmp_path,
        tmp_path / "policy.json",
        package_artifacts=(desktop_zip,),
    )

    artifact = report["inventories"]["package"]["artifacts"][0]
    assert artifact["kind"] == "desktop"
    assert artifact["status"] == "pass"
    assert not artifact["missing_required"]
    assert not artifact["unexpected_public"]
    assert not artifact["privacy_findings"]


def test_desktop_zip_rejects_self_test_and_machine_local_direct_url(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    executable = b"\0synthetic-windows-executable"
    private_path = (
        "C:" + "\\\\" + "Users" + "\\\\private-user\\\\wheel.whl"
    )
    files = {
        "Matters/Matters.exe": executable,
        "Matters/_internal/matters-0.3.0.dist-info/direct_url.json": (
            json.dumps({"url": "file:///" + private_path}).encode("utf-8")
        ),
    }
    toolchain = b'{"schema":"synthetic.desktop-toolchain"}\n'
    desktop_zip = tmp_path / "Matters-0.3.0-windows-x64.zip"
    with zipfile.ZipFile(desktop_zip, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
        archive.writestr("desktop-build-toolchain.json", toolchain)
        archive.writestr(
            "desktop-manifest.json",
            _desktop_manifest(files, toolchain),
        )
        archive.writestr(
            "desktop-self-test.json",
            json.dumps({"application_icon": private_path}),
        )

    report = check(
        tmp_path,
        tmp_path / "policy.json",
        package_artifacts=(desktop_zip,),
    )

    artifact = report["inventories"]["package"]["artifacts"][0]
    assert artifact["kind"] == "desktop"
    assert artifact["status"] == "fail"
    assert any("direct_url.json" in row for row in artifact["package_errors"])
    assert any("desktop-self-test.json" in row for row in artifact["package_errors"])
    assert {
        row["code"] for row in artifact["privacy_findings"]
    } >= {"absolute_home_path_leak"}


def test_desktop_vendor_exemptions_are_narrow(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    executable = b"\0synthetic-windows-executable"
    portable_example = "/" + "home" + "/" + "user/file.txt"
    private_example = "/" + "home" + "/" + "private-person/records.txt"
    files = {
        "Matters/Matters.exe": executable,
        "Matters/_internal/webview/platforms/gtk.py": (
            f"# portable example: {portable_example}\n"
            f"PRIVATE = '{private_example}'\n"
        ).encode("utf-8"),
    }
    toolchain = b'{"schema":"synthetic.desktop-toolchain"}\n'
    desktop_zip = tmp_path / "Matters-0.3.0-windows-x64.zip"
    with zipfile.ZipFile(desktop_zip, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
        archive.writestr("desktop-build-toolchain.json", toolchain)
        archive.writestr(
            "desktop-manifest.json",
            _desktop_manifest(files, toolchain),
        )

    report = check(
        tmp_path,
        tmp_path / "policy.json",
        package_artifacts=(desktop_zip,),
    )

    assert any(
        row["code"] == "absolute_home_path_leak"
        and row["path"].endswith("webview/platforms/gtk.py")
        for row in report["inventories"]["package"]["artifacts"][0][
            "privacy_findings"
        ]
    )


def test_desktop_matters_metadata_and_manifest_hashes_fail_closed(tmp_path):
    _write_boundary_fixture(tmp_path, ignore_required=False)
    private_address = "private-person@" + "nonreserved" + ".synthetic"
    executable = b"\0synthetic-windows-executable"
    matters_metadata = f"Author-email: {private_address}\n".encode("utf-8")
    original_files = {
        "Matters/Matters.exe": executable,
        "Matters/_internal/matters-0.3.0.dist-info/METADATA": matters_metadata,
    }
    original_toolchain = b'{"schema":"synthetic.desktop-toolchain"}\n'
    desktop_zip = tmp_path / "Matters-0.3.0-windows-x64.zip"
    with zipfile.ZipFile(desktop_zip, "w") as archive:
        archive.writestr("Matters/Matters.exe", executable + b"-changed")
        archive.writestr(
            "Matters/_internal/matters-0.3.0.dist-info/METADATA",
            matters_metadata,
        )
        archive.writestr(
            "desktop-build-toolchain.json",
            original_toolchain + b" ",
        )
        archive.writestr(
            "desktop-manifest.json",
            _desktop_manifest(original_files, original_toolchain),
        )

    report = check(
        tmp_path,
        tmp_path / "policy.json",
        package_artifacts=(desktop_zip,),
    )

    artifact = report["inventories"]["package"]["artifacts"][0]
    assert {
        "desktop_package_sha256_stale",
        "desktop_executable_sha256_stale",
        "desktop_build_toolchain_sha256_stale",
    } <= set(artifact["package_errors"])
    assert any(
        row["code"] == "personal_email_identifier_leak"
        and row["path"].endswith("matters-0.3.0.dist-info/METADATA")
        for row in artifact["privacy_findings"]
    )


def test_release_manifest_prunes_receipts_and_wheel_carries_standard_plugin():
    manifest = Path("MANIFEST.in").read_text(encoding="utf-8")
    inventory = json.loads(
        Path("docs/security/required-public-inventory.json").read_text(
            encoding="utf-8"
        )
    )
    projected = {
        row["source_path"]: row["wheel_data_path"]
        for row in inventory["wheel_data_projection"]
    }

    assert "graft .agents" not in manifest
    assert "graft .codex" not in manifest
    assert "graft .flowguard" not in manifest
    assert "prune .agents" in manifest
    assert "prune .codex" in manifest
    assert "prune .flowguard" in manifest
    assert "graft synthetic_fixtures" in manifest
    assert projected["plugins/matters/.mcp.json"] == (
        "share/matters/plugins/matters/.mcp.json"
    )
    assert projected["plugins/matters/.codex-plugin/plugin.json"] == (
        "share/matters/plugins/matters/.codex-plugin/plugin.json"
    )
    assert projected[
        "plugins/matters/skills/matters/references/installation.md"
    ] == (
        "share/matters/plugins/matters/skills/matters/references/installation.md"
    )
    assert {".agents/**", ".codex/**", ".flowguard/**"} <= set(
        inventory["sdist_excluded_patterns"]
    )
    assert {".agents/**", ".codex/**", ".flowguard/**"} <= set(
        inventory["package_forbidden_patterns"]
    )
    assert {
        ".flowguard/evidence/ui/screenshots/**",
        ".flowguard/evidence/ui/**/screenshots/**",
    } <= set(inventory["excluded_patterns"])
