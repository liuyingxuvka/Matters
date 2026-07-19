import json
import os
from pathlib import Path

import pytest

from matters.application.orchestrator import MatterService
from matters.application.partitioned_filesystem import PartitionedFilesystemRunner
from matters.authorization.coverage import AuthorizationCoverage, AuthorizationError
from matters.authorization.scopes import AuthorizationScope, opaque_reference
from matters.providers.base import ProviderEnvelope
from matters.infrastructure.capability_status.status import validate_private_root


def _envelope(**changes):
    values = {
        "provider": "fake",
        "external_id": "one",
        "object_type": "object",
        "payload": {"value": 1},
    }
    values.update(changes)
    return ProviderEnvelope(**values)


def test_active_scope_and_explicit_partial_coverage():
    owner = AuthorizationCoverage()
    scope = AuthorizationScope("s", "fake", frozenset({"one"}))
    assert owner.authorize_envelope(scope, _envelope()).complete
    partial = owner.authorize_envelope(
        scope,
        _envelope(coverage="complete", denied_fields=("secret",)),
    )
    assert partial.status == "partial"


def test_outside_and_revoked_scopes_fail_before_fetch():
    owner = AuthorizationCoverage()
    outside = AuthorizationScope("s", "fake", frozenset({"other"}))
    try:
        owner.authorize_envelope(outside, _envelope())
    except AuthorizationError as exc:
        assert str(exc) == "outside_scope"
    else:
        raise AssertionError("outside scope was accepted")
    revoked = AuthorizationScope("s", "fake", frozenset({"one"}), active=False)
    try:
        owner.authorize_envelope(revoked, _envelope())
    except AuthorizationError as exc:
        assert str(exc) == "authorization_revoked"
    else:
        raise AssertionError("revoked scope was accepted")


def test_private_root_must_be_outside_git(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    assert validate_private_root(repository / "runtime", repository).status == "blocked"
    assert validate_private_root(tmp_path / "private", repository).status == "active"


def test_explicit_live_read_boundary_is_owned_and_enforced_by_c1():
    owner = AuthorizationCoverage()
    scope = AuthorizationScope(
        scope_id="scope",
        provider="jira",
        object_ids=frozenset({"ISSUE-1"}),
        instance_ref_hash=opaque_reference("https://synthetic.invalid"),
        project_ref_hashes=frozenset({opaque_reference("PROJECT")}),
        object_types=frozenset({"issue", "comment"}),
        time_start="2026-01-01T00:00:00+00:00",
        time_end="2026-12-31T23:59:59+00:00",
        permission_fingerprint=opaque_reference("permission-set"),
        expires_at="2099-01-01T00:00:00+00:00",
    )
    owner.assert_read_allowed(
        scope,
        provider="jira",
        object_ids=("ISSUE-1",),
        object_types=("issue",),
        instance_ref_hash=scope.instance_ref_hash,
        require_explicit_boundary=True,
    )
    with pytest.raises(AuthorizationError, match="object_type_outside_scope"):
        owner.assert_read_allowed(
            scope,
            provider="jira",
            object_ids=("ISSUE-1",),
            object_types=("worklog",),
            instance_ref_hash=scope.instance_ref_hash,
            require_explicit_boundary=True,
        )


def test_large_root_is_durably_partitioned_without_terminal_content_claim(
    tmp_path: Path,
):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    source = tmp_path / "source"
    repository.mkdir()
    source.mkdir()
    (source / "root.txt").write_text("root", encoding="utf-8")
    wide = source / "wide"
    wide.mkdir()
    (wide / "own.txt").write_text("own", encoding="utf-8")
    for name, count in (("first", 3), ("second", 2)):
        child = wide / name
        child.mkdir()
        for index in range(count):
            (child / f"{index}.txt").write_text(str(index), encoding="utf-8")
    small = source / "small"
    small.mkdir()
    (small / "only.txt").write_text("only", encoding="utf-8")
    manifest_path = private / "runs" / "partition.json"
    runner = PartitionedFilesystemRunner(
        MatterService(repository_root=repository, private_root=private),
        manifest_path=manifest_path,
        max_entries=4,
        content_limit=0,
    )

    result = runner.run(source)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["ok"]
    assert result["delegating_partition_count"] == 2
    assert result["complete_partition_count"] == 3
    assert result["terminal_coverage"] == "not_claimed"
    assert all(
        node["status"] in {"complete", "partitioned"}
        for node in manifest["nodes"].values()
    )


def test_partition_checkpoint_retries_transient_windows_destination_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    source = tmp_path / "source"
    repository.mkdir()
    source.mkdir()
    (source / "one.txt").write_text("one", encoding="utf-8")
    runner = PartitionedFilesystemRunner(
        MatterService(repository_root=repository, private_root=private),
        manifest_path=private / "runs" / "partition.json",
        max_entries=10,
        content_limit=0,
    )
    original_replace = os.replace
    attempts = 0

    def transient_replace(source_path, destination_path):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("synthetic destination lock")
        return original_replace(source_path, destination_path)

    monkeypatch.setattr(
        "matters.application.partitioned_filesystem.os.replace",
        transient_replace,
    )

    assert runner.run(source)["ok"]
    assert attempts >= 2
