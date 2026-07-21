"""Strict private-manifest Gmail body continuation import.

This leaf accepts already-read connector results.  It has no connector, model,
API-key, mailbox mutation, or semantic Matter authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any, TYPE_CHECKING

from matters.application.coverage_ledger import (
    bounded_stage_output_set_ref,
)
from matters.provenance.evidence import EvidenceAnchor
from matters.provenance.source_registry import SourceVersion
from matters.providers.base import ProviderEnvelope
from matters.providers.documents import DocumentAdapter, DocumentSource

if TYPE_CHECKING:
    from matters.application.orchestrator import MatterService
    from matters.application.coverage_ledger import ObjectCoverageRow


ARTIFACT_TYPE = "gmail_body_continuation"
MAX_BATCH_MESSAGES = 20
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_BODY_BYTES = 4 * 1024 * 1024
MAX_BATCH_BODY_BYTES = 16 * 1024 * 1024
_MANIFEST_ROW_KEYS = frozenset(
    {
        "message_id",
        "source_page_identity",
        "batch_number",
        "prior_body_fingerprint",
    }
)
_RESULT_KEYS = frozenset(
    {"artifact_type", "manifest_sha256", "batch_number", "messages"}
)
_AVAILABLE_MESSAGE_KEYS = frozenset(
    {"message_id", "body", "content_status"}
)
_NO_TEXT_MESSAGE_KEYS = frozenset(
    {
        "message_id",
        "body",
        "content_status",
        "raw_recovery_proof_identity",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PROOF_IDENTITY_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_NO_TEXT_PROOF_DOMAIN = (
    b"matters.gmail.raw-mime-recovery.no-text-body.v1\x00"
)


def _digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def gmail_no_text_raw_recovery_proof_identity(
    message_id: str,
) -> str:
    """Derive the auditable identity of one canonical no-text recovery row."""

    if not isinstance(message_id, str) or not message_id:
        raise ValueError("gmail_body_message_identity_invalid")
    canonical_row = {
        "message_id": message_id,
        "body": "",
        "content_status": "no_text_body",
        "disposition": "no_text_body",
    }
    encoded = json.dumps(
        canonical_row,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + sha256(
        _NO_TEXT_PROOF_DOMAIN + encoded
    ).hexdigest()


def _source_ref(source: SourceVersion) -> str:
    return f"{source.source_id}:v{source.version}"


def _positive_int(value: object, error: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(error)
    return value


def _exact_keys(
    value: object,
    expected: frozenset[str],
    error: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(error)
    normalized = {str(key): item for key, item in value.items()}
    if set(normalized) != expected:
        raise ValueError(error)
    return normalized


@dataclass(frozen=True)
class GmailBodyManifestRow:
    message_id: str
    source_page_identity: str
    batch_number: int
    prior_body_fingerprint: str


@dataclass(frozen=True)
class GmailBodyMessage:
    message_id: str
    body: str
    body_bytes: bytes
    content_status: str
    raw_recovery_proof_identity: str = ""


@dataclass(frozen=True)
class GmailBodyContinuationContract:
    manifest_sha256: str
    manifest_identity: str
    batch_number: int
    batch_numbers: tuple[int, ...]
    rows: tuple[GmailBodyManifestRow, ...]
    messages: tuple[GmailBodyMessage, ...]


@dataclass(frozen=True)
class GmailBodyContinuationResult:
    status: str
    batch_number: int
    expected_count: int
    imported_count: int
    already_current_count: int
    evidence_anchor_count: int
    receipt_updated_count: int
    no_text_body_count: int
    content_disposition_updated_count: int
    next_batch_number: int | None
    has_more: bool
    manifest_status: str = "matched"


@dataclass(frozen=True)
class _OwnerBinding:
    row: GmailBodyManifestRow
    message: GmailBodyMessage
    source: SourceVersion
    coverage: "ObjectCoverageRow"
    body_already_current: bool
    extracted_anchors: tuple[tuple[Mapping[str, object], str], ...]


def parse_gmail_body_continuation(
    manifest_bytes: bytes,
    connector_result: Mapping[str, Any],
) -> GmailBodyContinuationContract:
    """Validate the entire exact batch without reading or writing runtime state."""

    if not isinstance(manifest_bytes, bytes):
        raise ValueError("gmail_body_manifest_bytes_required")
    if not manifest_bytes or len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise ValueError("gmail_body_manifest_size_invalid")
    manifest_sha256 = _digest_bytes(manifest_bytes)
    try:
        manifest_payload = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("gmail_body_manifest_json_invalid") from exc
    if not isinstance(manifest_payload, list) or not manifest_payload:
        raise ValueError("gmail_body_manifest_rows_required")

    rows: list[GmailBodyManifestRow] = []
    seen_ids: set[str] = set()
    batch_sizes: dict[int, int] = {}
    for raw_row in manifest_payload:
        row = _exact_keys(
            raw_row,
            _MANIFEST_ROW_KEYS,
            "gmail_body_manifest_row_projection_invalid",
        )
        message_id = row["message_id"]
        page_identity = row["source_page_identity"]
        prior_body_fingerprint = row["prior_body_fingerprint"]
        if (
            not isinstance(message_id, str)
            or not message_id
            or not isinstance(page_identity, str)
            or not page_identity
            or not isinstance(prior_body_fingerprint, str)
            or (
                prior_body_fingerprint
                and _PROOF_IDENTITY_RE.fullmatch(
                    prior_body_fingerprint
                )
                is None
            )
        ):
            raise ValueError("gmail_body_manifest_row_identity_invalid")
        if message_id in seen_ids:
            raise ValueError("gmail_body_manifest_message_duplicate")
        seen_ids.add(message_id)
        batch_number = _positive_int(
            row["batch_number"],
            "gmail_body_manifest_batch_invalid",
        )
        batch_sizes[batch_number] = batch_sizes.get(batch_number, 0) + 1
        if batch_sizes[batch_number] > MAX_BATCH_MESSAGES:
            raise ValueError("gmail_body_batch_budget_exceeded")
        rows.append(
            GmailBodyManifestRow(
                message_id,
                page_identity,
                batch_number,
                prior_body_fingerprint,
            )
        )
    batch_numbers = tuple(sorted(batch_sizes))

    result = _exact_keys(
        connector_result,
        _RESULT_KEYS,
        "gmail_body_result_projection_invalid",
    )
    if result["artifact_type"] != ARTIFACT_TYPE:
        raise ValueError("gmail_body_result_artifact_type_invalid")
    observed_sha256 = result["manifest_sha256"]
    if (
        not isinstance(observed_sha256, str)
        or _SHA256_RE.fullmatch(observed_sha256) is None
        or observed_sha256 != manifest_sha256
    ):
        raise ValueError("gmail_body_manifest_hash_mismatch")
    batch_number = _positive_int(
        result["batch_number"],
        "gmail_body_result_batch_invalid",
    )
    if batch_number not in batch_sizes:
        raise ValueError("gmail_body_result_batch_not_in_manifest")
    raw_messages = result["messages"]
    if not isinstance(raw_messages, list):
        raise ValueError("gmail_body_result_messages_invalid")
    if (
        not raw_messages
        or len(raw_messages) > MAX_BATCH_MESSAGES
        or len(raw_messages) != batch_sizes[batch_number]
    ):
        raise ValueError("gmail_body_result_batch_membership_invalid")

    selected_rows = tuple(
        row for row in rows if row.batch_number == batch_number
    )
    expected_ids = {row.message_id for row in selected_rows}
    by_id: dict[str, GmailBodyMessage] = {}
    total_body_bytes = 0
    for raw_message in raw_messages:
        if not isinstance(raw_message, Mapping):
            raise ValueError("gmail_body_message_projection_invalid")
        content_status = raw_message.get("content_status")
        if content_status == "available":
            message = _exact_keys(
                raw_message,
                _AVAILABLE_MESSAGE_KEYS,
                "gmail_body_message_projection_invalid",
            )
        elif content_status == "no_text_body":
            if "raw_recovery_proof_identity" not in raw_message:
                raise ValueError(
                    "gmail_no_text_raw_recovery_proof_required"
                )
            message = _exact_keys(
                raw_message,
                _NO_TEXT_MESSAGE_KEYS,
                "gmail_body_message_projection_invalid",
            )
        else:
            raise ValueError("gmail_body_content_unavailable")
        message_id = message["message_id"]
        body = message["body"]
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("gmail_body_message_identity_invalid")
        if message_id in by_id:
            raise ValueError("gmail_body_result_message_duplicate")
        if message_id not in expected_ids:
            raise ValueError(
                "gmail_body_result_batch_membership_invalid"
            )
        proof_identity = ""
        if content_status == "available":
            if not isinstance(body, str) or not body.strip():
                raise ValueError("gmail_body_content_empty")
        else:
            if body != "":
                raise ValueError("gmail_no_text_body_must_be_empty")
            proof_identity = message["raw_recovery_proof_identity"]
            if (
                not isinstance(proof_identity, str)
                or _PROOF_IDENTITY_RE.fullmatch(proof_identity) is None
            ):
                raise ValueError(
                    "gmail_no_text_raw_recovery_proof_invalid"
                )
            if proof_identity != (
                gmail_no_text_raw_recovery_proof_identity(message_id)
            ):
                raise ValueError(
                    "gmail_no_text_raw_recovery_proof_mismatch"
                )
        try:
            body_bytes = body.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("gmail_body_content_encoding_invalid") from exc
        if len(body_bytes) > MAX_BODY_BYTES:
            raise ValueError("gmail_body_content_budget_exceeded")
        total_body_bytes += len(body_bytes)
        if total_body_bytes > MAX_BATCH_BODY_BYTES:
            raise ValueError("gmail_body_batch_content_budget_exceeded")
        by_id[message_id] = GmailBodyMessage(
            message_id,
            body,
            body_bytes,
            content_status,
            proof_identity,
        )
    if set(by_id) != expected_ids:
        raise ValueError("gmail_body_result_batch_membership_invalid")

    return GmailBodyContinuationContract(
        manifest_sha256=manifest_sha256,
        manifest_identity=f"gmail-body-manifest:{manifest_sha256[:24]}",
        batch_number=batch_number,
        batch_numbers=batch_numbers,
        rows=selected_rows,
        messages=tuple(by_id[row.message_id] for row in selected_rows),
    )


class GmailBodyContinuationImporter:
    """C1/C2/C3/M0 continuation leaf over already-current Gmail metadata."""

    def __init__(
        self,
        service: "MatterService",
        *,
        documents: DocumentAdapter | None = None,
    ) -> None:
        if (
            service.store is None
            or service.coverage_ledger is None
            or service.inventory is None
        ):
            raise RuntimeError(
                "MATTERS_HOME is required for Gmail body continuation"
            )
        self.service = service
        self.documents = documents or DocumentAdapter()

    def _bind_current_owners(
        self,
        contract: GmailBodyContinuationContract,
    ) -> tuple[_OwnerBinding, ...]:
        store = self.service.store
        assert store is not None
        grouped = store.current_gmail_message_sources_by_provider_ids(
            message.message_id for message in contract.messages
        )
        bindings: list[_OwnerBinding] = []
        for row, message in zip(
            contract.rows,
            contract.messages,
            strict=True,
        ):
            payloads = grouped.get(message.message_id, ())
            if len(payloads) != 1:
                raise ValueError("gmail_body_metadata_owner_not_current")
            source_id = str(payloads[0].get("source_id", ""))
            source = self.service.sources.current(source_id)
            if (
                source is None
                or source.tombstone
                or source.provider != "gmail"
                or source.external_reference.provider != "gmail"
                or source.external_reference.object_type != "gmail_message"
                or source.content.get("provider_message_id")
                != message.message_id
            ):
                raise ValueError("gmail_body_metadata_owner_not_current")
            external_id = source.external_reference.external_id
            coverage = self.service.coverage_ledger.current(external_id)
            if (
                coverage is None
                or not coverage.active
                or coverage.provider != "gmail"
                or coverage.object_type != "message"
                or coverage.disposition not in {"tracked", "metadata_only"}
            ):
                raise ValueError("gmail_body_coverage_owner_not_current")
            occurrences = store.inventory_occurrences_by_object_ids(
                (external_id,)
            ).get(external_id, ())
            if not any(
                occurrence["scope_id"] == coverage.scope_id
                and occurrence["inventory_revision"]
                == coverage.inventory_revision
                and occurrence["provider"] == "gmail"
                and occurrence["object_type"] == "message"
                and occurrence["disposition"]
                in {"tracked", "metadata_only"}
                for occurrence in occurrences
            ):
                raise ValueError("gmail_body_inventory_owner_not_current")

            current_body_fingerprint = str(
                source.content.get("body_text_fingerprint", "")
            )
            current_body_length = source.content.get(
                "body_text_byte_length"
            )
            if message.content_status == "no_text_body":
                if (
                    current_body_length is not None
                    and int(current_body_length) > 0
                ):
                    raise ValueError(
                        "gmail_no_text_body_current_content_conflict"
                    )
                if row.prior_body_fingerprint != current_body_fingerprint:
                    raise ValueError(
                        "gmail_body_current_content_conflict"
                    )
                body_already_current = False
                extracted_anchors = ()
            else:
                expected_body_fingerprint = (
                    "sha256:" + _digest_bytes(message.body_bytes)
                )
                body_already_current = (
                    current_body_fingerprint == expected_body_fingerprint
                    and int(current_body_length or 0)
                    == len(message.body_bytes)
                )
                if (
                    not body_already_current
                    and row.prior_body_fingerprint
                    != current_body_fingerprint
                ):
                    raise ValueError(
                        "gmail_body_current_content_conflict"
                    )
                extraction = self.documents.extract(
                    DocumentSource(
                        source_version_id="gmail-body-preflight",
                        external_id=external_id,
                        media_type="text/plain",
                        content=message.body_bytes,
                        tracking_disposition="tracked",
                    )
                )
                extracted_anchors = tuple(
                    (dict(anchor.location), anchor.text)
                    for anchor in extraction.anchors
                    if anchor.text.strip()
                )
                if (
                    extraction.status != "extracted"
                    or extraction.gaps
                    or not extracted_anchors
                ):
                    raise ValueError(
                        "gmail_body_exact_extraction_unavailable"
                    )
            bindings.append(
                _OwnerBinding(
                    row,
                    message,
                    source,
                    coverage,
                    body_already_current,
                    extracted_anchors,
                )
            )
        return tuple(bindings)

    def _current_body_source(
        self,
        binding: _OwnerBinding,
        contract: GmailBodyContinuationContract,
    ) -> tuple[SourceVersion, bool]:
        if binding.body_already_current:
            return binding.source, False
        body_digest = _digest_bytes(binding.message.body_bytes)
        content = {
            **dict(binding.source.content),
            "body_text": binding.message.body,
            "body_content_status": "available",
        }
        envelope = ProviderEnvelope(
            provider="gmail",
            external_id=binding.source.external_reference.external_id,
            object_type="gmail_message",
            payload=content,
            coverage="partial",
            references=(binding.source.external_reference,),
            metadata={
                "requires_private_runtime": True,
                "private_payload": True,
                "gmail_body_continuation": True,
                "manifest_identity": contract.manifest_identity,
            },
        )
        registration = self.service.sources.register(
            envelope,
            idempotency_key=(
                "gmail-body-continuation:"
                f"{contract.manifest_sha256}:{contract.batch_number}:"
                f"{binding.source.source_id}:{body_digest}"
            ),
        )
        current = self.service.sources.current(binding.source.source_id)
        expected_fingerprint = "sha256:" + body_digest
        if (
            current is None
            or current.tombstone
            or current.content.get("body_text_fingerprint")
            != expected_fingerprint
            or int(current.content.get("body_text_byte_length", -1))
            != len(binding.message.body_bytes)
        ):
            raise RuntimeError("gmail_body_source_version_not_current")
        return (
            registration.source_version or current,
            registration.status != "no_delta",
        )

    def _qualify_anchors(
        self,
        source: SourceVersion,
        binding: _OwnerBinding,
    ) -> tuple[EvidenceAnchor, ...]:
        anchors: list[EvidenceAnchor] = []
        for raw_location, text in binding.extracted_anchors:
            location = dict(raw_location)
            if "line_start" in location:
                location["line"] = location["line_start"]
            qualified = self.service.evidence.qualify(
                source,
                text=text,
                location=location,
                modality="reported",
            )
            if not isinstance(qualified, EvidenceAnchor):
                raise RuntimeError("gmail_body_evidence_anchor_not_qualified")
            anchors.append(qualified)
        return tuple(anchors)

    @staticmethod
    def _pointer_is_current(
        coverage: "ObjectCoverageRow",
        *,
        stage_id: str,
        status: str,
        input_fingerprint: str,
        output_ref: str,
    ) -> bool:
        pointer = coverage.stages.get(stage_id)
        return (
            pointer is not None
            and pointer.status == status
            and pointer.input_fingerprint == input_fingerprint
            and pointer.output_ref == output_ref
            and not pointer.failure_class
        )

    def _mark_coverage(
        self,
        *,
        object_id: str,
        source: SourceVersion,
        anchors: tuple[EvidenceAnchor, ...],
    ) -> bool:
        ledger = self.service.coverage_ledger
        assert ledger is not None
        source_ref = _source_ref(source)
        fingerprint = _fingerprint(
            {
                "source_ref": source_ref,
                "content_hash": source.content_hash,
                "metadata_hash": source.metadata_hash,
                "evidence_ids": tuple(
                    anchor.evidence_id for anchor in anchors
                ),
                "contract": "gmail-body-continuation:v1",
            }
        )
        evidence_ref = bounded_stage_output_set_ref(
            "evidence_anchor",
            source_ref,
            (anchor.evidence_id for anchor in anchors),
        )
        stages = (
            ("source_version", "current", source_ref),
            (
                "extraction",
                "current",
                f"gmail_body_extraction:{source_ref}",
            ),
            ("evidence", "current", evidence_ref),
            ("analysis", "pending", f"analysis:{source_ref}"),
        )
        changed = False
        for stage_id, status, output_ref in stages:
            coverage = ledger.current(object_id)
            if coverage is None:
                raise RuntimeError("gmail_body_coverage_owner_missing")
            if self._pointer_is_current(
                coverage,
                stage_id=stage_id,
                status=status,
                input_fingerprint=fingerprint,
                output_ref=output_ref,
            ):
                continue
            ledger.mark_stage(
                object_id=object_id,
                stage_id=stage_id,
                status=status,
                input_fingerprint=fingerprint,
                output_ref=output_ref,
                refresh_summary=False,
            )
            changed = True
        return changed

    def _persist_body_receipt(
        self,
        *,
        contract: GmailBodyContinuationContract,
        binding: _OwnerBinding,
        source: SourceVersion,
        anchors: tuple[EvidenceAnchor, ...],
    ) -> bool:
        store = self.service.store
        assert store is not None
        source_ref = _source_ref(source)
        desired = {
            "artifact_type": "gmail_message_body",
            "source_id": source.source_id,
            "source_version_ref": source_ref,
            "manifest_identity": contract.manifest_identity,
            "manifest_sha256": contract.manifest_sha256,
            "batch_number": contract.batch_number,
            "source_page_identity_digest": _fingerprint(
                binding.row.source_page_identity
            ),
            "body_digest": "sha256:"
            + _digest_bytes(binding.message.body_bytes),
            "body_byte_count": len(binding.message.body_bytes),
            "content_status": "available",
            "evidence_set_ref": bounded_stage_output_set_ref(
                "evidence_anchor",
                source_ref,
                (anchor.evidence_id for anchor in anchors),
            ),
        }
        result = store.compare_current_and_append(
            "gmail_message_body",
            source.source_id,
            is_equivalent=lambda current: current == desired,
            payload_factory=lambda _revision, _current: desired,
        )
        return result["status"] == "appended"

    def _persist_no_text_disposition(
        self,
        *,
        contract: GmailBodyContinuationContract,
        binding: _OwnerBinding,
    ) -> bool:
        store = self.service.store
        assert store is not None
        desired = {
            "artifact_type": "gmail_message_content_disposition",
            "source_id": binding.source.source_id,
            "source_version_ref": _source_ref(binding.source),
            "manifest_identity": contract.manifest_identity,
            "manifest_sha256": contract.manifest_sha256,
            "batch_number": contract.batch_number,
            "source_page_identity_digest": _fingerprint(
                binding.row.source_page_identity
            ),
            "content_status": "no_text_body",
            "body_present": False,
            "raw_recovery_proof_identity": (
                binding.message.raw_recovery_proof_identity
            ),
            "extraction_disposition": "not_applicable",
            "evidence_disposition": "not_applicable",
        }
        result = store.compare_current_and_append(
            "gmail_message_content_disposition",
            binding.source.source_id,
            is_equivalent=lambda current: current == desired,
            payload_factory=lambda _revision, _current: desired,
        )
        return result["status"] == "appended"

    def _mark_no_text_coverage(
        self,
        *,
        binding: _OwnerBinding,
    ) -> bool:
        ledger = self.service.coverage_ledger
        assert ledger is not None
        source = binding.source
        source_ref = _source_ref(source)
        disposition_ref = (
            "gmail_message_content_disposition:"
            f"{source.source_id}:no_text_body"
        )
        fingerprint = _fingerprint(
            {
                "source_ref": source_ref,
                "content_hash": source.content_hash,
                "metadata_hash": source.metadata_hash,
                "content_status": "no_text_body",
                "raw_recovery_proof_identity": (
                    binding.message.raw_recovery_proof_identity
                ),
                "contract": "gmail-body-continuation:v2",
            }
        )
        stages = (
            ("source_version", "current", source_ref),
            ("extraction", "not_applicable", disposition_ref),
            ("evidence", "not_applicable", disposition_ref),
            ("analysis", "not_applicable", disposition_ref),
        )
        changed = False
        for stage_id, status, output_ref in stages:
            coverage = ledger.current(
                source.external_reference.external_id
            )
            if coverage is None:
                raise RuntimeError("gmail_body_coverage_owner_missing")
            if self._pointer_is_current(
                coverage,
                stage_id=stage_id,
                status=status,
                input_fingerprint=fingerprint,
                output_ref=output_ref,
            ):
                continue
            ledger.mark_stage(
                object_id=source.external_reference.external_id,
                stage_id=stage_id,
                status=status,
                input_fingerprint=fingerprint,
                output_ref=output_ref,
                refresh_summary=False,
            )
            changed = True
        return changed

    def import_batch(
        self,
        *,
        manifest_bytes: bytes,
        connector_result: Mapping[str, Any],
    ) -> GmailBodyContinuationResult:
        """Validate all identities first, then idempotently advance each message."""

        contract = parse_gmail_body_continuation(
            manifest_bytes,
            connector_result,
        )
        bindings = self._bind_current_owners(contract)
        store = self.service.store
        ledger = self.service.coverage_ledger
        assert store is not None and ledger is not None

        imported_count = 0
        already_current_count = 0
        evidence_anchor_count = 0
        receipt_updated_count = 0
        no_text_body_count = 0
        content_disposition_updated_count = 0
        any_change = False
        for binding in bindings:
            if binding.message.content_status == "no_text_body":
                no_text_body_count += 1
                disposition_changed = self._persist_no_text_disposition(
                    contract=contract,
                    binding=binding,
                )
                content_disposition_updated_count += int(
                    disposition_changed
                )
                any_change = any_change or disposition_changed
                any_change = (
                    self._mark_no_text_coverage(binding=binding)
                    or any_change
                )
                continue

            source, source_changed = self._current_body_source(
                binding,
                contract,
            )
            imported_count += int(source_changed)
            already_current_count += int(binding.body_already_current)
            any_change = any_change or source_changed

            anchors = self._qualify_anchors(source, binding)
            inserted = store.append_content_addressed_many(
                (
                    "evidence_anchor",
                    anchor.evidence_id,
                    asdict(anchor),
                )
                for anchor in anchors
            )
            evidence_anchor_count += len(anchors)
            any_change = any_change or bool(inserted)

            receipt_changed = self._persist_body_receipt(
                contract=contract,
                binding=binding,
                source=source,
                anchors=anchors,
            )
            receipt_updated_count += int(receipt_changed)
            any_change = any_change or receipt_changed
            any_change = (
                self._mark_coverage(
                    object_id=source.external_reference.external_id,
                    source=source,
                    anchors=anchors,
                )
                or any_change
            )

        if any_change:
            ledger.refresh_summary()
        next_batch = next(
            (
                number
                for number in contract.batch_numbers
                if number > contract.batch_number
            ),
            None,
        )
        return GmailBodyContinuationResult(
            status="current" if any_change else "no_delta",
            batch_number=contract.batch_number,
            expected_count=len(bindings),
            imported_count=imported_count,
            already_current_count=already_current_count,
            evidence_anchor_count=evidence_anchor_count,
            receipt_updated_count=receipt_updated_count,
            no_text_body_count=no_text_body_count,
            content_disposition_updated_count=(
                content_disposition_updated_count
            ),
            next_batch_number=next_batch,
            has_more=next_batch is not None,
        )


__all__ = [
    "ARTIFACT_TYPE",
    "GmailBodyContinuationContract",
    "GmailBodyContinuationImporter",
    "GmailBodyContinuationResult",
    "MAX_BATCH_MESSAGES",
    "gmail_no_text_raw_recovery_proof_identity",
    "parse_gmail_body_continuation",
]
