from pathlib import Path

import pytest

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.providers.filesystem import FilesystemReadOnlyAdapter


def _input_dispositions(package):
    return [
        {
            "input_id": input_id,
            "disposition": "used",
            "reason": "bounded injected Codex execution",
        }
        for input_id in (
            *package.allowed_evidence_ids,
            *package.allowed_asset_ids,
        )
    ]


def test_private_profile_substitution_keeps_pending_package_identity(tmp_path: Path):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    documents = tmp_path / "documents"
    repository.mkdir()
    documents.mkdir()
    (documents / "plan.txt").write_text(
        "Prepare a launch plan",
        encoding="utf-8",
    )
    seen_targets = []

    def executor(package, entry):
        seen_targets.append((package.capability_role, entry.execution_target))
        if package.capability_role == "low_cost_annotator":
            return {
                "status": "passed",
                "input_dispositions": _input_dispositions(package),
                "findings": [
                    {
                        "finding_type": "source_annotation",
                        "owner_model_id": (
                            "A0_matters_source_analysis_operation"
                        ),
                        "statement": "A user launch plan",
                        "localized_statement": {
                            "en": "A user launch plan",
                            "zh-CN": "一项用户发布计划",
                        },
                        "semantic_revision": package.source_revision_ids[0],
                        "evidence_ids": [package.allowed_evidence_ids[0]],
                        "confidence": "bounded",
                        "modality": "observed",
                        "attributes": {
                            "content_kind": "user_plan",
                            "user_relevance": "likely_relevant",
                        },
                    }
                ],
                "resource_usage": {"input_count": 1},
            }
        return {
            "status": "passed",
            "input_dispositions": _input_dispositions(package),
            "findings": [],
            "resource_usage": {"input_count": 1},
        }

    service = MatterService(
        repository_root=repository,
        private_root=private,
        codex_executor=executor,
    )
    first_profile = service.activate_codex_execution_profile(
        (
            {
                "capability_role": "low_cost_annotator",
                "execution_target": "economy-model-a",
                "reasoning_level": "low",
            },
            {
                "capability_role": "matter_modeler",
                "execution_target": "reasoning-model-a",
                "reasoning_level": "high",
            },
        )
    )
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(documents),
        content_limit=20,
    )
    first_cycle = service.run_maintenance_cycle(limit=20)
    pending = service.pending_analysis_packages()
    assert pending["execution_profile_identity"] == first_profile[
        "profile_identity"
    ]
    semantic_package_id = pending["items"][0]["package_id"]
    semantic_fingerprint = pending["items"][0]["input_fingerprint"]

    second_profile = service.activate_codex_execution_profile(
        (
            {
                "capability_role": "low_cost_annotator",
                "execution_target": "economy-model-b",
                "reasoning_level": "minimal",
            },
            {
                "capability_role": "matter_modeler",
                "execution_target": "reasoning-model-b",
                "reasoning_level": "high",
            },
        )
    )
    unchanged_pending = service.pending_analysis_packages()["items"][0]
    assert service.pending_analysis_packages()[
        "execution_profile_identity"
    ] == second_profile["profile_identity"]
    second_cycle = service.run_maintenance_cycle(limit=20)
    semantic_result = service.operations.current_result(
        semantic_package_id
    )

    assert first_cycle["status"] == "progressed"
    assert second_cycle["status"] == "progressed"
    assert unchanged_pending["package_id"] == semantic_package_id
    assert unchanged_pending["input_fingerprint"] == semantic_fingerprint
    assert first_profile["profile_identity"] != second_profile["profile_identity"]
    assert seen_targets == [
        ("low_cost_annotator", "economy-model-a"),
        ("matter_modeler", "reasoning-model-b"),
    ]
    assert semantic_result.execution_profile_identity == (
        second_profile["profile_identity"]
    )
    assert semantic_result.concrete_execution_identity.startswith("execution:")
    assert service.pending_analysis_packages()["total_count"] == 0
    public_status = service.codex_execution_profile_status()
    assert "execution_target" not in public_status
    assert "economy-model-b" not in str(public_status)


def test_manual_result_uses_pending_envelope_profile_identity(tmp_path: Path):
    repository = tmp_path / "repository"
    private = tmp_path / "private"
    documents = tmp_path / "documents"
    repository.mkdir()
    documents.mkdir()
    (documents / "note.txt").write_text(
        "Keep this bounded note",
        encoding="utf-8",
    )
    service = MatterService(
        repository_root=repository,
        private_root=private,
    )
    profile = service.activate_codex_execution_profile(
        (
            {
                "capability_role": "low_cost_annotator",
                "execution_target": "economy-model",
                "reasoning_level": "low",
            },
        )
    )
    SourceWorkflow(service).run_filesystem(
        FilesystemReadOnlyAdapter(documents),
        content_limit=20,
    )
    pending = service.pending_analysis_packages()
    package = pending["items"][0]
    base_result = {
        "status": "passed",
        "input_dispositions": [
            {
                "input_id": input_id,
                "disposition": "insufficient",
                "reason": "No source-level claim is licensed.",
            }
            for input_id in (
                *package["allowed_evidence_ids"],
                *package["allowed_asset_ids"],
            )
        ],
        "findings": [],
        "concrete_execution_identity": "execution:manual-test",
        "resource_usage": {"input_count": 1},
    }

    stale = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result={
            **base_result,
            "execution_profile_identity": "execution-profile:stale",
        },
    )
    retry = service.pending_analysis_packages()
    accepted = service.import_autonomous_result(
        package_id=package["package_id"],
        provider_id=package["required_runner_id"],
        provider_version=package["required_runner_version"],
        result={
            **base_result,
            "execution_profile_identity": retry[
                "execution_profile_identity"
            ],
        },
    )

    assert pending["execution_profile_identity"] == profile["profile_identity"]
    assert stale["status"] == "blocked"
    assert retry["items"][0]["package_id"] == package["package_id"]
    assert retry["items"][0]["input_fingerprint"] == package[
        "input_fingerprint"
    ]
    assert accepted["status"] == "passed"


def test_private_profile_rejects_direct_provider_api_target(tmp_path: Path):
    repository = tmp_path / "repository"
    repository.mkdir()
    service = MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )
    with pytest.raises(ValueError, match="direct provider API"):
        service.activate_codex_execution_profile(
            (
                {
                    "capability_role": "low_cost_annotator",
                    "execution_target": "direct-api-with-api-key",
                    "reasoning_level": "low",
                },
            )
        )


@pytest.mark.parametrize(
    "target",
    (
        "openai_api",
        "OpenAI API",
        "provider_api",
        "https://api.openai.com/v1/responses",
    ),
)
def test_private_profile_rejects_equivalent_direct_api_spellings(
    tmp_path: Path,
    target: str,
):
    repository = tmp_path / "repository"
    repository.mkdir()
    service = MatterService(
        repository_root=repository,
        private_root=tmp_path / "private",
    )
    with pytest.raises(ValueError, match="direct provider API"):
        service.activate_codex_execution_profile(
            (
                {
                    "capability_role": "low_cost_annotator",
                    "execution_target": target,
                    "reasoning_level": "low",
                },
            )
        )
