import json
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

from matters.infrastructure.capability_status.status import validate_private_root
from scripts.jira_slice_preflight import build_preflight
import scripts.check_public_boundary as public_boundary
from scripts.check_public_boundary import _git_executable, _scan_text, check


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
