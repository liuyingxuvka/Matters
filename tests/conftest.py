from __future__ import annotations

import json
from pathlib import Path

import pytest

from matters.application.orchestrator import MatterService
from matters.authorization.scopes import AuthorizationScope
from matters.providers.base import ProviderEnvelope


@pytest.fixture
def synthetic_rows() -> dict[str, dict]:
    payload = json.loads(
        Path("tests/fixtures/jira_synthetic/J1-J10.json").read_text(
            encoding="utf-8"
        )
    )
    return {row["scenario_id"]: row for row in payload["scenarios"]}


def envelope_for(row: dict) -> ProviderEnvelope:
    data = dict(row["provider_envelope"])
    external_id = str(data.pop("external_id"))
    object_type = str(data.pop("object_type"))
    denied = []
    if data.get("private_comments_access") == "denied":
        denied.append("private_comments")
    if data.get("attachment_access") == "denied":
        denied.append("attachments")
    return ProviderEnvelope(
        provider="jira",
        external_id=external_id,
        object_type=object_type,
        payload=data,
        coverage="partial" if denied else "complete",
        denied_fields=tuple(denied),
    )


def scope_for(envelope: ProviderEnvelope, *, active: bool = True) -> AuthorizationScope:
    return AuthorizationScope(
        scope_id=f"scope:{envelope.external_id}",
        provider=envelope.provider,
        object_ids=frozenset({envelope.external_id}),
        active=active,
    )


def process_source(service: MatterService, row: dict):
    envelope = envelope_for(row)
    return service.process_envelope(
        scope=scope_for(envelope),
        envelope=envelope,
        idempotency_key=f"key:{row['scenario_id']}",
    )


@pytest.fixture
def service(tmp_path: Path) -> MatterService:
    repository = tmp_path / "repository"
    repository.mkdir()
    return MatterService(
        private_root=tmp_path / "private",
        repository_root=repository,
    )
