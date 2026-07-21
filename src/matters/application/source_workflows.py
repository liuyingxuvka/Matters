"""Durable source runs from metadata inventory through bounded evidence.

Provider adapters deliberately stop before they own tracking, persistence, or
semantic-depth decisions.  This module is the application-level coordinator
that joins those independent owners without making a provider authoritative
for canonical Matters state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence
from uuid import uuid4

from matters.application.orchestrator import MatterService, SourceProcessingResult
from matters.application.content_selection import (
    ContentSelectionOwner,
    READABLE_CONTENT_SELECTION_MODES,
)
from matters.application.coverage_ledger import bounded_stage_output_set_ref
from matters.authorization.scopes import AuthorizationScope
from matters.inventory.owners import (
    CURRENT_TRACKING_POLICY_REVISION,
    CandidateScope,
    ChangeSet,
    InventoryOccurrence,
    InventorySnapshot,
    SourceDisposition,
    TrackingPolicy,
)
from matters.providers.base import ExternalReference, ProviderEnvelope
from matters.providers.codex import (
    CodexReadOnlyProvider,
    CodexRegistrationAdapter,
)
from matters.providers.documents import DocumentAdapter, DocumentSource
from matters.providers.filesystem import (
    FilesystemOccurrence,
    FilesystemReadOnlyAdapter,
)
from matters.providers.gmail import (
    GmailAuthorizedPage,
    GmailDiscoveryItem,
    GmailReadOnlyAdapter,
)
from matters.providers.images import ImageAdapter, ImageSource
from matters.provenance.evidence import EvidenceAnchor, EvidenceGap
from matters.provenance.source_registry import SourceVersion


IMAGE_SUFFIXES = frozenset(
    {
        ".avif",
        ".bmp",
        ".gif",
        ".heic",
        ".heif",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)
DOCUMENT_SUFFIXES = frozenset(
    {
        ".csv",
        ".doc",
        ".docx",
        ".epub",
        ".html",
        ".json",
        ".md",
        ".markdown",
        ".odt",
        ".pdf",
        ".ppt",
        ".pptx",
        ".rst",
        ".rtf",
        ".tex",
        ".tsv",
        ".txt",
        ".xls",
        ".xlsx",
        ".xml",
        ".yaml",
        ".yml",
    }
)


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _durable_payload(value: Any) -> Any:
    """Project tuples and dataclasses into the store's canonical JSON shape."""

    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
    )


def _filesystem_scope_id(root: Path) -> str:
    return "filesystem-scope:" + _digest(str(root.resolve()))[:24]


def _scoped_occurrence_id(scope_id: str, provider_occurrence_id: str) -> str:
    return "occurrence:" + _digest(
        f"{scope_id}\0{provider_occurrence_id}"
    )[:24]


def _source_version_ref(source: SourceVersion) -> str:
    return f"{source.source_id}:v{source.version}"


def _filesystem_kind(item: FilesystemOccurrence) -> str:
    if item.object_type != "file":
        return item.object_type
    suffix = PurePosixPath(item.external_id).suffix.casefold()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in DOCUMENT_SUFFIXES:
        return "document"
    return "file"


def _filesystem_recommendation(item: FilesystemOccurrence) -> str:
    return {
        "candidate": "tracked",
        "partition_boundary": "not_tracked",
        "hard_excluded": "hard_excluded",
        "excluded_sensitive": "hard_excluded",
        "quarantined": "hard_excluded",
        "inaccessible": "unavailable",
        "unsupported": "metadata_only",
        "cloud_placeholder": "metadata_only",
    }[item.outcome]


@dataclass(frozen=True)
class SourceRunSummary:
    provider: str
    scope_id: str
    inventory_revision: int
    discovered: int
    tracked: int
    hard_excluded: int
    metadata_only: int
    blocked: int
    unavailable: int
    not_tracked: int
    metadata_registered: int
    content_ingested: int
    evidence_anchors: int
    depth_sufficient: int
    depth_partial: int
    depth_blocked: int
    depth_stale: int
    depth_not_assessed: int
    terminal: bool
    gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceRunResult:
    summary: SourceRunSummary
    snapshot: InventorySnapshot
    changes: ChangeSet
    processed: tuple[SourceProcessingResult, ...] = ()


@dataclass(frozen=True)
class RegisteredFilesystemBatchResult:
    status: str
    requested_limit: int
    selected_count: int
    processed_count: int
    content_ingested: int
    evidence_anchors: int
    changed_count: int
    unavailable_count: int
    unsupported_count: int
    invalid_registration_count: int
    blocked_count: int
    remaining_count: int


@dataclass(frozen=True)
class GmailMetadataReconciliationResult:
    status: str
    scope_id: str
    requested_limit: int
    scanned_message_count: int
    eligible_message_count: int
    selected_count: int
    registered_count: int
    metadata_updated_count: int
    already_current_count: int
    preserved_body_count: int
    coverage_updated_count: int
    skipped_owner_mismatch_count: int
    remaining_count: int
    next_after_object_id: str


class SourceWorkflow:
    """Join read-only adapters to the durable application owners."""

    REGISTERED_FILESYSTEM_CLAIM_SIZE = 10
    REGISTERED_FILESYSTEM_LEASE_SECONDS = 300

    def __init__(
        self,
        service: MatterService,
        *,
        documents: DocumentAdapter | None = None,
        images: ImageAdapter | None = None,
    ) -> None:
        if service.store is None or service.inventory is None:
            raise RuntimeError("MATTERS_HOME is required for source workflows")
        self.service = service
        self.documents = documents or DocumentAdapter()
        self.images = images or ImageAdapter()

    def _scope(
        self,
        *,
        scope_id: str,
        provider: str,
        root_locator: str,
        object_types: Iterable[str],
    ) -> CandidateScope:
        assert self.service.store is not None
        prior = self.service.store.current("candidate_scope", scope_id)
        desired_types = tuple(sorted(set(object_types)))
        revision = 1
        if prior is not None:
            same = (
                str(prior.get("provider")) == provider
                and str(prior.get("root_locator")) == root_locator
                and tuple(prior.get("object_types", ())) == desired_types
                and not bool(prior.get("include_hidden", False))
                and not bool(prior.get("follow_links", False))
                and bool(prior.get("active", True))
            )
            revision = int(prior["revision"]) if same else int(prior["revision"]) + 1
        return CandidateScope(
            scope_id=scope_id,
            revision=revision,
            provider=provider,
            root_locator=root_locator,
            object_types=desired_types,
        )

    def _policy(self, policy_id: str) -> TrackingPolicy:
        assert self.service.store is not None
        prior = self.service.store.current("tracking_policy", policy_id)
        desired = TrackingPolicy(
            policy_id=policy_id,
            revision=CURRENT_TRACKING_POLICY_REVISION,
        )
        if prior is None or int(prior["revision"]) < desired.revision:
            return desired
        return TrackingPolicy(
            policy_id=str(prior["policy_id"]),
            revision=int(prior["revision"]),
            protected_classes=tuple(prior.get("protected_classes", ())),
            ignored_names=tuple(prior.get("ignored_names", ())),
            archive_size_limit=int(prior.get("archive_size_limit", 0)),
            changed_at=str(prior.get("changed_at", "")),
        )

    def retire_filesystem_scopes(
        self,
        *,
        root: Path,
        relative_paths: Iterable[str],
    ) -> Mapping[str, int]:
        """Retire only explicit former partition scopes under one private root."""

        assert self.service.store is not None
        root_path = Path(os.path.abspath(root))
        policy = self._policy("tracking-policy:default")
        retired_scope_count = 0
        retired_object_count = 0
        for relative_path in tuple(
            sorted(
                {
                    str(item)
                    for item in relative_paths
                    if str(item)
                }
            )
        ):
            normalized = PurePosixPath(relative_path)
            if (
                relative_path == "."
                or normalized.is_absolute()
                or any(part in {"", ".", ".."} for part in normalized.parts)
            ):
                continue
            scope_root = root_path.joinpath(*normalized.parts)
            scope_id = _filesystem_scope_id(scope_root)
            prior = self.service.store.current("candidate_scope", scope_id)
            if (
                prior is None
                or str(prior.get("provider", "")) != "filesystem"
                or not bool(prior.get("active", True))
                or Path(os.path.abspath(str(prior.get("root_locator", ""))))
                != scope_root
            ):
                continue
            scope = CandidateScope(
                scope_id=scope_id,
                revision=int(prior.get("revision", 1)) + 1,
                provider="filesystem",
                root_locator=str(scope_root),
                object_types=tuple(prior.get("object_types", ())),
                include_hidden=bool(prior.get("include_hidden", False)),
                follow_links=bool(prior.get("follow_links", False)),
                active=False,
            )
            _snapshot, changes = self.service.reconcile_inventory(
                scope=scope,
                policy=policy,
                occurrences=(),
                refresh_coverage_summary=False,
            )
            retired_scope_count += 1
            retired_object_count += len(changes.deleted)
        return {
            "retired_scope_count": retired_scope_count,
            "retired_object_count": retired_object_count,
        }

    @staticmethod
    def _authorization(
        *,
        scope_id: str,
        provider: str,
        occurrences: Sequence[InventoryOccurrence],
    ) -> AuthorizationScope:
        return AuthorizationScope(
            scope_id=f"authorization:{scope_id}",
            provider=provider,
            object_ids=frozenset(item.occurrence_id for item in occurrences),
            object_types=frozenset(
                {
                    "file",
                    "gmail_message",
                    "gmail_thread",
                    "gmail_attachment",
                }
            ),
        )

    @staticmethod
    def _disposition_map(
        snapshot: InventorySnapshot,
    ) -> dict[str, SourceDisposition]:
        return {item.occurrence_id: item for item in snapshot.dispositions}

    def _persist_anchor(self, anchor: EvidenceAnchor) -> None:
        self._persist_anchors((anchor,))

    def _persist_anchors(
        self,
        anchors: Sequence[EvidenceAnchor],
    ) -> None:
        assert self.service.store is not None
        self.service.store.append_content_addressed_many(
            (
                "evidence_anchor",
                anchor.evidence_id,
                asdict(anchor),
            )
            for anchor in anchors
        )

    def _persist_gap(self, gap: EvidenceGap) -> None:
        self._persist_gaps((gap,))

    def _persist_gaps(
        self,
        gaps: Sequence[EvidenceGap],
    ) -> None:
        assert self.service.store is not None
        self.service.store.append_content_addressed_many(
            (
                "evidence_gap",
                (
                    f"{gap.source_id}:gap:"
                    + _digest(f"{gap.reason}\0{gap.claim}")[:16]
                ),
                asdict(gap),
            )
            for gap in gaps
        )

    def _persist_extraction(
        self,
        *,
        owner: str,
        occurrence_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        assert self.service.store is not None
        current_payload = self.service.store.current(owner, occurrence_id)
        desired_payload = _durable_payload(dict(payload))
        if current_payload != desired_payload:
            self.service.store.append_next(
                owner,
                occurrence_id,
                desired_payload,
            )
        if (
            self.service.coverage_ledger is not None
            and self.service.coverage_ledger.current(occurrence_id) is not None
        ):
            raw_status = str(payload.get("status", ""))
            stage_status = (
                "current"
                if raw_status
                in {
                    "extracted",
                    "partial",
                    "metadata_only",
                    "analyzed",
                    "supported",
                }
                else (
                    "no_finding"
                    if raw_status in {"unsupported", "empty", "no_text"}
                    else "blocked"
                )
            )
            self.service.coverage_ledger.mark_stage(
                object_id=occurrence_id,
                stage_id="extraction",
                status=stage_status,
                input_fingerprint="sha256:" + _digest(repr(dict(payload))),
                output_ref=f"{owner}:{occurrence_id}",
                failure_class=(
                    "" if stage_status != "blocked" else raw_status or "extraction_failed"
                ),
                refresh_summary=False,
            )

    def _mark_evidence_and_analysis(
        self,
        *,
        occurrence_id: str,
        source: SourceVersion,
        anchors: Sequence[EvidenceAnchor],
        queued: bool,
    ) -> None:
        ledger = self.service.coverage_ledger
        if ledger is None or ledger.current(occurrence_id) is None:
            return
        fingerprint = "sha256:" + _digest(
            repr(
                (
                    _source_version_ref(source),
                    tuple(item.evidence_id for item in anchors),
                )
            )
        )
        ledger.mark_stage(
            object_id=occurrence_id,
            stage_id="evidence",
            status="current" if anchors else "no_finding",
            input_fingerprint=fingerprint,
            output_ref=(
                bounded_stage_output_set_ref(
                    "evidence_anchor",
                    _source_version_ref(source),
                    (item.evidence_id for item in anchors),
                )
                if anchors
                else "evidence:none"
            ),
            refresh_summary=False,
        )
        ledger.mark_stage(
            object_id=occurrence_id,
            stage_id="analysis",
            status="pending" if queued else "no_finding",
            input_fingerprint=fingerprint,
            output_ref=(
                f"analysis:{_source_version_ref(source)}"
                if queued
                else "analysis:not_applicable"
            ),
            refresh_summary=False,
        )

    def _mark_fresh(
        self,
        *,
        occurrence_id: str,
        inventory_revision: int,
        disposition: str,
    ) -> None:
        assert self.service.store is not None
        payload = _durable_payload({
            "occurrence_id": occurrence_id,
            "inventory_revision": inventory_revision,
            "status": "current",
            "disposition": disposition,
            "dependencies": (),
        })
        if (
            self.service.store.current(
                "dependency_freshness",
                occurrence_id,
            )
            != payload
        ):
            self.service.store.append_next(
                "dependency_freshness",
                occurrence_id,
                payload,
            )

    def _document_evidence(
        self,
        *,
        occurrence_id: str,
        source: SourceVersion,
        external_id: str,
        media_type: str,
        content: bytes,
        parent_source_version_id: str = "",
        source_context: Mapping[str, Any] | None = None,
        inventory_identity: str | None = None,
        stage_callback: (
            Callable[[str, Mapping[str, Any]], None] | None
        ) = None,
    ) -> tuple[tuple[EvidenceAnchor, ...], tuple[EvidenceGap, ...], str]:
        extraction = self.documents.extract(
            DocumentSource(
                source_version_id=_source_version_ref(source),
                external_id=external_id,
                media_type=media_type,
                content=content,
                tracking_disposition="tracked",
                parent_source_version_id=parent_source_version_id,
            )
        )
        self._persist_extraction(
            owner="document_extraction",
            occurrence_id=occurrence_id,
            payload=asdict(extraction),
        )
        if stage_callback is not None:
            stage_callback(
                "evidence",
                {"extraction_status": extraction.status},
            )
        anchors: list[EvidenceAnchor] = []
        gaps: list[EvidenceGap] = []
        for item in extraction.anchors:
            location = dict(item.location)
            if "line_start" in location:
                location["line"] = location["line_start"]
            qualified = self.service.evidence.qualify(
                source,
                text=item.text,
                location=location,
                modality=item.modality,
            )
            if isinstance(qualified, EvidenceAnchor):
                anchors.append(qualified)
            else:
                gaps.append(qualified)
        for reason in extraction.gaps:
            gap = EvidenceGap(source.source_id, reason)
            gaps.append(gap)
        self._persist_anchors(anchors)
        self._persist_gaps(gaps)
        if stage_callback is not None:
            stage_callback(
                "package",
                {
                    "anchor_count": len(anchors),
                    "gap_count": len(gaps),
                },
            )
        # Text, mail, office-document, and PDF screenshots are not Images
        # evidence and are not useful presentation assets.  Keep the exact
        # source at its provider and persist only the declared extraction and
        # evidence derivatives.
        queued = False
        if anchors:
            self.service.queue_source_understanding(
                source_revision=_source_version_ref(source),
                source_kind="document",
                anchors=tuple(anchors),
                source_context=source_context,
                inventory_identity=inventory_identity,
            )
            queued = True
        self._mark_evidence_and_analysis(
            occurrence_id=occurrence_id,
            source=source,
            anchors=anchors,
            queued=queued,
        )
        if stage_callback is not None:
            stage_callback(
                "coverage",
                {"queued": queued, "anchor_count": len(anchors)},
            )
        return tuple(anchors), tuple(gaps), extraction.status

    def _image_evidence(
        self,
        *,
        occurrence_id: str,
        source: SourceVersion,
        external_id: str,
        media_type: str,
        metadata: Mapping[str, Any],
        content: bytes | None = None,
        source_context: Mapping[str, Any] | None = None,
        inventory_identity: str | None = None,
        stage_callback: (
            Callable[[str, Mapping[str, Any]], None] | None
        ) = None,
    ) -> tuple[tuple[EvidenceAnchor, ...], tuple[EvidenceGap, ...], str]:
        image_source = ImageSource(
            source_version_id=_source_version_ref(source),
            external_id=external_id,
            media_type=media_type,
            width=int(metadata.get("width", 0) or 0),
            height=int(metadata.get("height", 0) or 0),
            metadata=metadata,
            tracking_disposition="tracked",
            content=content,
        )
        result = (
            self.images.analyze(image_source)
            if content is not None
            else self.images.inventory(image_source)
        )
        self._persist_extraction(
            owner="image_analysis",
            occurrence_id=occurrence_id,
            payload=asdict(result),
        )
        if stage_callback is not None:
            stage_callback(
                "evidence",
                {"extraction_status": result.status},
            )
        anchors: list[EvidenceAnchor] = []
        gaps: list[EvidenceGap] = []
        for item in result.observations:
            location = dict(item.anchor)
            if "metadata_field" in location:
                location["field"] = location["metadata_field"]
            qualified = self.service.evidence.qualify(
                source,
                text=item.text,
                location=location,
                modality=(
                    "observed"
                    if item.modality in {"metadata_derived", "exif_derived"}
                    else "inferred"
                ),
            )
            if isinstance(qualified, EvidenceAnchor):
                anchors.append(qualified)
            else:
                gaps.append(qualified)
        for reason in result.gaps:
            gap = EvidenceGap(source.source_id, reason)
            gaps.append(gap)
        self._persist_anchors(anchors)
        self._persist_gaps(gaps)
        if stage_callback is not None:
            stage_callback(
                "package",
                {
                    "anchor_count": len(anchors),
                    "gap_count": len(gaps),
                },
            )
        if content is not None and self.service.visuals is not None:
            try:
                self.service.visuals.register_image(
                    source_revision_id=_source_version_ref(source),
                    occurrence_id=occurrence_id,
                    content=content,
                    media_type=media_type,
                    evidence_ids=tuple(item.evidence_id for item in anchors),
                    photo=True,
                )
            except ValueError:
                gap = EvidenceGap(source.source_id, "visual_derivative_unavailable")
                self._persist_gap(gap)
                gaps.append(gap)
        queued = False
        if anchors:
            self.service.queue_source_understanding(
                source_revision=_source_version_ref(source),
                source_kind="image",
                anchors=tuple(anchors),
                source_context=source_context,
                inventory_identity=inventory_identity,
            )
            queued = True
        self._mark_evidence_and_analysis(
            occurrence_id=occurrence_id,
            source=source,
            anchors=anchors,
            queued=queued,
        )
        if stage_callback is not None:
            stage_callback(
                "coverage",
                {"queued": queued, "anchor_count": len(anchors)},
            )
        return tuple(anchors), tuple(gaps), result.status

    def _register_binary_source(
        self,
        *,
        authorization: AuthorizationScope,
        inventory_identity: str,
        occurrence: InventoryOccurrence,
        content: bytes,
        media_type: str,
    ) -> SourceProcessingResult:
        envelope = ProviderEnvelope(
            provider="filesystem",
            external_id=occurrence.occurrence_id,
            object_type=occurrence.object_type,
            payload={
                "display_name": str(
                    occurrence.metadata.get("display_name", "source")
                ),
                "media_type": media_type,
                "content_hash": "sha256:" + sha256(content).hexdigest(),
                "byte_length": len(content),
            },
            references=(
                ExternalReference(
                    "filesystem",
                    occurrence.occurrence_id,
                    occurrence.object_type,
                    occurrence.locator,
                ),
            ),
            metadata={
                "requires_private_runtime": True,
                "tracking_disposition": "tracked",
                "binary_content": True,
                **{
                    key: value
                    for key, value in occurrence.metadata.items()
                    if key
                    in {
                        "source_neighborhood_id",
                        "source_group_chain",
                        "source_group_labels",
                        "source_spatial_context_revision",
                        "path_depth",
                        "file_kind",
                        "file_identity",
                        "metadata_identity",
                    }
                },
            },
        )
        return self.service.process_envelope(
            scope=authorization,
            envelope=envelope,
            idempotency_key=(
                f"{inventory_identity}:{occurrence.occurrence_id}:binary"
            ),
            refresh_coverage_summary=False,
        )

    def _assess(
        self,
        *,
        occurrence_id: str,
        inventory_revision: int,
        disposition: str,
        coverage_terminal: bool = False,
        extraction_current: bool = False,
        evidence_anchored: bool = False,
        blocked_by: str = "",
    ) -> str:
        if disposition in {
            "not_tracked",
            "hard_excluded",
            "metadata_only",
            "unavailable",
        }:
            depth = self.service.assess_depth(
                occurrence_id=occurrence_id,
                inventory_revision=inventory_revision,
                criteria={},
            )
            self._mark_fresh(
                occurrence_id=occurrence_id,
                inventory_revision=inventory_revision,
                disposition=disposition,
            )
            return depth.state
        if disposition == "blocked" and not blocked_by:
            blocked_by = "source_disposition_blocked"
        depth = self.service.assess_depth(
            occurrence_id=occurrence_id,
            inventory_revision=inventory_revision,
            criteria={
                "coverage_terminal": coverage_terminal,
                "extraction_current": extraction_current,
                "analysis_terminal": self.service.research_status.current,
                "evidence_anchored": evidence_anchored,
                "owner_dispatch_terminal": False,
            },
            blocked_by=blocked_by,
        )
        if not blocked_by and extraction_current:
            self._mark_fresh(
                occurrence_id=occurrence_id,
                inventory_revision=inventory_revision,
                disposition=disposition,
            )
        return depth.state

    @staticmethod
    def _summary(
        *,
        provider: str,
        snapshot: InventorySnapshot,
        metadata_registered: int,
        content_ingested: int,
        evidence_anchors: int,
        depth_states: Sequence[str],
        terminal: bool,
        gaps: Sequence[str],
    ) -> SourceRunSummary:
        statuses = [item.status for item in snapshot.dispositions]
        return SourceRunSummary(
            provider=provider,
            scope_id=snapshot.scope_id,
            inventory_revision=snapshot.revision,
            discovered=len(snapshot.occurrences),
            tracked=statuses.count("tracked"),
            hard_excluded=statuses.count("hard_excluded"),
            metadata_only=statuses.count("metadata_only"),
            blocked=statuses.count("blocked"),
            unavailable=statuses.count("unavailable"),
            not_tracked=statuses.count("not_tracked"),
            metadata_registered=metadata_registered,
            content_ingested=content_ingested,
            evidence_anchors=evidence_anchors,
            depth_sufficient=depth_states.count("sufficient"),
            depth_partial=depth_states.count("partial"),
            depth_blocked=depth_states.count("blocked"),
            depth_stale=depth_states.count("stale"),
            depth_not_assessed=depth_states.count("not_assessed"),
            terminal=terminal,
            gaps=tuple(dict.fromkeys(gaps)),
        )

    @staticmethod
    def _registered_policy_path_prefix(
        occurrence: InventoryOccurrence,
    ) -> tuple[str, ...]:
        """Recover the partition prefix from persisted spatial metadata."""

        labels = tuple(
            str(item)
            for item in occurrence.metadata.get("source_group_labels", ())
        )
        parent = PurePosixPath(occurrence.locator).parent
        parent_parts = () if str(parent) == "." else parent.parts
        if not parent_parts:
            return labels
        if (
            len(labels) >= len(parent_parts)
            and labels[-len(parent_parts) :] == parent_parts
        ):
            return labels[: -len(parent_parts)]
        return ()

    @staticmethod
    def _registered_metadata_matches(
        occurrence: InventoryOccurrence,
        current: Mapping[str, Any],
    ) -> bool:
        """Require the content read to match the registered inventory row."""

        expected_identity = str(
            occurrence.metadata.get("metadata_identity", "")
        )
        current_identity = str(current.get("metadata_identity", ""))
        if expected_identity and current_identity:
            return expected_identity == current_identity
        stable_fields = ("file_identity", "size", "modified_ns")
        if not all(
            field in occurrence.metadata and field in current
            for field in stable_fields
        ):
            return False
        return all(
            occurrence.metadata[field] == current[field]
            for field in stable_fields
        )

    def _block_registered_filesystem_occurrence(
        self,
        *,
        occurrence_id: str,
        inventory_revision: int,
        failure_class: str,
    ) -> bool:
        """Record a visible source-version block without replacing content."""

        ledger = self.service.coverage_ledger
        if ledger is None:
            return False
        current = ledger.current(occurrence_id)
        if current is None or not current.active:
            return False
        ledger.mark_stage(
            object_id=occurrence_id,
            stage_id="source_version",
            status="blocked",
            input_fingerprint="sha256:"
            + _digest(
                f"{occurrence_id}\0{inventory_revision}\0{failure_class}"
            ),
            output_ref="source_version:blocked",
            failure_class=failure_class,
            refresh_summary=False,
        )
        self._assess(
            occurrence_id=occurrence_id,
            inventory_revision=inventory_revision,
            disposition="tracked",
            blocked_by=failure_class,
        )
        return True

    def _mark_registered_source_current(
        self,
        *,
        occurrence_id: str,
        source: SourceVersion,
    ) -> None:
        """Close a no-delta retry without changing downstream content depth."""

        ledger = self.service.coverage_ledger
        if ledger is None:
            return
        ledger.mark_stage(
            object_id=occurrence_id,
            stage_id="source_version",
            status="current",
            input_fingerprint="sha256:"
            + _digest(
                repr(
                    (
                        _source_version_ref(source),
                        source.content_hash,
                        source.metadata_hash,
                    )
                )
            ),
            output_ref=_source_version_ref(source),
            refresh_summary=False,
        )

    def run_codex(
        self,
        adapter: CodexRegistrationAdapter,
        *,
        user_intents: Mapping[str, str] | None = None,
        page_limit: int = 10_000,
    ) -> SourceRunResult:
        """Register explicit Codex workspaces/projects without copying content."""

        if page_limit <= 0:
            raise ValueError("page_limit must be positive")
        occurrences: list[InventoryOccurrence] = []
        cursor = ""
        terminal = False
        gaps: list[str] = []
        for _ in range(page_limit):
            page = adapter.discover(cursor=cursor)
            occurrences.extend(page.occurrences)
            terminal = page.coverage == "complete"
            if terminal:
                break
            if not page.next_cursor or page.next_cursor == cursor:
                gaps.append("codex_registration_cursor_did_not_progress")
                break
            cursor = page.next_cursor
        else:
            gaps.append("codex_registration_page_limit_exceeded")

        scope = adapter.candidate_scope()
        policy = self._policy("tracking-policy:default")
        snapshot, changes = self.service.reconcile_inventory(
            scope=scope,
            policy=policy,
            occurrences=tuple(occurrences),
            user_intents=user_intents,
            refresh_coverage_summary=False,
        )
        disposition_by_id = self._disposition_map(snapshot)
        selected = tuple(
            occurrence
            for occurrence in occurrences
            if disposition_by_id[occurrence.occurrence_id].status
            in {"tracked", "metadata_only"}
        )
        authorization = AuthorizationScope(
            scope_id=f"authorization:{scope.scope_id}",
            provider="codex",
            object_ids=frozenset(
                occurrence.occurrence_id for occurrence in selected
            ),
            object_types=frozenset(
                occurrence.object_type for occurrence in selected
            ),
        )
        provider = CodexReadOnlyProvider(adapter)
        metadata_registered = 0
        evidence_anchor_count = 0
        depth_states: list[str] = []
        for occurrence in selected:
            envelope = provider.read(
                object_ids=(occurrence.occurrence_id,)
            )[0]
            coverage = self.service.authorization.authorize_envelope(
                authorization,
                envelope,
            )
            registration = self.service.sources.register(
                envelope,
                idempotency_key=(
                    f"inventory:{scope.scope_id}:{snapshot.revision}:"
                    f"{occurrence.occurrence_id}"
                ),
            )
            source = registration.source_version
            if source is None:
                gaps.append(
                    "codex_source_registration_failed:"
                    f"{occurrence.occurrence_id}"
                )
                continue
            metadata_registered += 1
            self._mark_registered_source_current(
                occurrence_id=occurrence.occurrence_id,
                source=source,
            )
            self._persist_extraction(
                owner="codex_metadata_extraction",
                occurrence_id=occurrence.occurrence_id,
                payload={
                    "occurrence_id": occurrence.occurrence_id,
                    "source_revision": _source_version_ref(source),
                    "status": "metadata_only",
                    "coverage": coverage.status,
                    "source_in_place": True,
                    "copied_content": False,
                },
            )
            anchors: tuple[EvidenceAnchor, ...] = ()
            queued = False
            if occurrence.object_type == "codex_project":
                qualified = self.service.evidence.qualify(
                    source,
                    text=(
                        "Registered Codex project: "
                        + str(
                            occurrence.metadata.get(
                                "display_name",
                                "project",
                            )
                        )
                    ),
                    location={"field": "project_name"},
                    modality="observed",
                )
                if isinstance(qualified, EvidenceAnchor):
                    anchors = (qualified,)
                    self._persist_anchors(anchors)
                    self.service.queue_source_understanding(
                        source_revision=_source_version_ref(source),
                        source_kind="codex_project",
                        anchors=anchors,
                        source_context={
                            "provider": "codex",
                            "object_type": "codex_project",
                            "source_in_place": True,
                            "source_group_labels": tuple(
                                occurrence.metadata.get(
                                    "source_group_labels",
                                    (),
                                )
                            ),
                        },
                        inventory_identity=(
                            f"inventory:{scope.scope_id}:"
                            f"{snapshot.revision}"
                        ),
                    )
                    queued = True
                    evidence_anchor_count += 1
                else:
                    self._persist_gap(qualified)
            self._mark_evidence_and_analysis(
                occurrence_id=occurrence.occurrence_id,
                source=source,
                anchors=anchors,
                queued=queued,
            )
            disposition = disposition_by_id[
                occurrence.occurrence_id
            ].status
            depth_states.append(
                self._assess(
                    occurrence_id=occurrence.occurrence_id,
                    inventory_revision=snapshot.revision,
                    disposition=disposition,
                    coverage_terminal=coverage.status == "complete",
                    extraction_current=True,
                    evidence_anchored=bool(anchors),
                )
            )
        if self.service.coverage_ledger is not None:
            self.service.coverage_ledger.refresh_summary()
        summary = self._summary(
            provider="codex",
            snapshot=snapshot,
            metadata_registered=metadata_registered,
            content_ingested=0,
            evidence_anchors=evidence_anchor_count,
            depth_states=depth_states,
            terminal=terminal,
            gaps=gaps,
        )
        return SourceRunResult(summary, snapshot, changes)

    def run_filesystem(
        self,
        adapter: FilesystemReadOnlyAdapter,
        *,
        user_intents: Mapping[str, str] | None = None,
        content_limit: int | None = 0,
        page_limit: int = 10_000,
        refresh_coverage_summary: bool = True,
    ) -> SourceRunResult:
        """Inventory one authorized root, then read a bounded tracked subset."""

        if content_limit is not None and content_limit < 0:
            raise ValueError("content_limit cannot be negative")
        scope_id = _filesystem_scope_id(adapter.root)
        items: list[FilesystemOccurrence] = []
        cursor = ""
        terminal = False
        coverage_gaps: list[str] = []
        for _ in range(page_limit):
            page = adapter.discover(cursor=cursor)
            items.extend(page.items)
            coverage_gaps.extend(page.gaps)
            terminal = page.terminal
            if terminal:
                break
            if not page.next_cursor or page.next_cursor == cursor:
                coverage_gaps.append("filesystem_cursor_did_not_progress")
                break
            cursor = page.next_cursor
        else:
            coverage_gaps.append("filesystem_page_limit_exceeded")

        occurrences: list[InventoryOccurrence] = []
        provider_to_occurrence: dict[str, InventoryOccurrence] = {}
        policy = self._policy("tracking-policy:default")
        ignored_names = {
            str(name).casefold() for name in policy.ignored_names
        }
        for item in items:
            scoped_id = _scoped_occurrence_id(scope_id, item.occurrence_id)
            kind = _filesystem_kind(item)
            metadata = {
                **dict(item.metadata),
                "provider_occurrence_id": item.occurrence_id,
                "provider_external_id": item.external_id,
                "display_name": PurePosixPath(item.external_id).name,
                "recommended_disposition": _filesystem_recommendation(item),
                "disposition_reason": item.reason,
                "discovery_outcome": item.outcome,
            }
            policy_tokens = tuple(
                sorted(
                    {
                        part.casefold()
                        for part in (
                            *adapter.policy_path_prefix,
                            *PurePosixPath(item.external_id).parts,
                        )
                        if part.casefold() in ignored_names
                    }
                )
            )
            if policy_tokens:
                metadata["policy_path_tokens"] = policy_tokens
            if item.outcome == "excluded_sensitive":
                metadata["source_class"] = "credential"
                metadata["credential_like"] = True
            occurrence = InventoryOccurrence(
                occurrence_id=scoped_id,
                provider="filesystem",
                object_type=kind,
                locator=item.external_id,
                metadata=metadata,
                content_identity=str(item.metadata.get("file_identity", "")),
            )
            occurrences.append(occurrence)
            provider_to_occurrence[item.external_id] = occurrence

        scope = self._scope(
            scope_id=scope_id,
            provider="filesystem",
            root_locator=str(adapter.root),
            object_types=(item.object_type for item in occurrences),
        )
        snapshot, changes = self.service.reconcile_inventory(
            scope=scope,
            policy=policy,
            occurrences=tuple(occurrences),
            user_intents=user_intents,
            refresh_coverage_summary=refresh_coverage_summary,
        )
        selection_owner = ContentSelectionOwner(
            self.service.store,
            self.service.coverage_ledger,
        )
        selection_by_id = {
            plan.occurrence_id: plan
            for plan in selection_owner.plan_snapshot(snapshot)
        }
        if content_limit == 0:
            if (
                refresh_coverage_summary
                and self.service.coverage_ledger is not None
            ):
                self.service.coverage_ledger.refresh_summary()
            assert self.service.store is not None
            depth_states = tuple(
                str(row.get("state", "not_assessed"))
                if (
                    row := self.service.store.current(
                        "semantic_depth",
                        occurrence.occurrence_id,
                    )
                )
                else "not_assessed"
                for occurrence in occurrences
            )
            summary = self._summary(
                provider="filesystem",
                snapshot=snapshot,
                metadata_registered=0,
                content_ingested=0,
                evidence_anchors=0,
                depth_states=depth_states,
                terminal=terminal,
                gaps=coverage_gaps,
            )
            return SourceRunResult(summary, snapshot, changes)
        disposition_by_id = self._disposition_map(snapshot)
        authorization = self._authorization(
            scope_id=scope_id,
            provider="filesystem",
            occurrences=occurrences,
        )
        processed_results: list[SourceProcessingResult] = []
        depth_states: list[str] = []
        metadata_registered = 0
        content_ingested = 0
        evidence_count = 0

        source_by_occurrence: dict[str, SourceVersion] = {}
        for occurrence in occurrences:
            disposition = disposition_by_id[occurrence.occurrence_id]
            if disposition.status in {"hard_excluded", "not_tracked"}:
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition=disposition.status,
                    )
                )
                continue
            if (
                disposition.status == "tracked"
                and occurrence.object_type in {"document", "file"}
            ):
                # A successful tracked-content read is the authoritative
                # version for text-like files.  Register metadata only when
                # the read cannot produce stable content; otherwise every
                # repeat run would alternate metadata/content versions.
                continue
            metadata_envelope = ProviderEnvelope(
                provider="filesystem",
                external_id=occurrence.occurrence_id,
                object_type="file",
                payload={
                    "relative_path": occurrence.locator,
                    "metadata": dict(occurrence.metadata),
                },
                references=(
                    ExternalReference(
                        "filesystem",
                        occurrence.occurrence_id,
                        "file",
                        occurrence.locator,
                    ),
                ),
                metadata={
                    "metadata_only": True,
                    "requires_private_runtime": True,
                    "tracking_disposition": disposition.status,
                },
            )
            processing = self.service.process_envelope(
                scope=authorization,
                envelope=metadata_envelope,
                idempotency_key=(
                    f"{snapshot.snapshot_id}:{occurrence.occurrence_id}:metadata"
                ),
                refresh_coverage_summary=False,
            )
            processed_results.append(processing)
            if processing.registration and processing.registration.source_version:
                metadata_registered += int(
                    processing.registration.status != "no_delta"
                )
                source_by_occurrence[occurrence.occurrence_id] = (
                    processing.registration.source_version
                )
            if disposition.status != "tracked":
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition=disposition.status,
                        coverage_terminal=processing.terminal_status != "blocked",
                    )
                )

        tracked_files = [
            occurrence
            for occurrence in occurrences
            if disposition_by_id[occurrence.occurrence_id].status == "tracked"
            and occurrence.object_type in {"document", "file"}
            and selection_by_id[occurrence.occurrence_id].mode
            in READABLE_CONTENT_SELECTION_MODES
        ]
        if content_limit is not None:
            tracked_files = tracked_files[:content_limit]
        provider_dispositions = {
            occurrence.locator: "tracked" for occurrence in tracked_files
        }
        read_results = adapter.read_tracked(
            object_ids=tuple(occurrence.locator for occurrence in tracked_files),
            tracking_dispositions=provider_dispositions,
        )
        read_by_locator = {item.external_id: item for item in read_results}
        processed_ids: set[str] = set()
        for occurrence in tracked_files:
            result = read_by_locator[occurrence.locator]
            if not result.ingested or result.envelope is None:
                metadata_envelope = ProviderEnvelope(
                    provider="filesystem",
                    external_id=occurrence.occurrence_id,
                    object_type="file",
                    payload={
                        "relative_path": occurrence.locator,
                        "metadata": dict(occurrence.metadata),
                    },
                    references=(
                        ExternalReference(
                            "filesystem",
                            occurrence.occurrence_id,
                            "file",
                            occurrence.locator,
                        ),
                    ),
                    metadata={
                        "metadata_only": True,
                        "requires_private_runtime": True,
                        "tracking_disposition": "tracked",
                    },
                )
                metadata_processing = self.service.process_envelope(
                    scope=authorization,
                    envelope=metadata_envelope,
                    idempotency_key=(
                        f"{snapshot.snapshot_id}:"
                        f"{occurrence.occurrence_id}:metadata-fallback"
                    ),
                    refresh_coverage_summary=False,
                )
                processed_results.append(metadata_processing)
                metadata_registered += int(
                    metadata_processing.registration is not None
                    and metadata_processing.registration.status != "no_delta"
                )
                if (
                    metadata_processing.registration is not None
                    and metadata_processing.registration.source_version is not None
                ):
                    source_by_occurrence[occurrence.occurrence_id] = (
                        metadata_processing.registration.source_version
                    )
                if (
                    result.disposition == "unsupported"
                    and occurrence.object_type == "document"
                ):
                    continue
                processed_ids.add(occurrence.occurrence_id)
                blocked = (
                    result.reason
                    if result.disposition
                    in {"inaccessible", "changed_during_read"}
                    else ""
                )
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition="tracked",
                        blocked_by=blocked,
                    )
                )
                coverage_gaps.append(
                    f"filesystem_content:{result.disposition}"
                )
                continue
            processed_ids.add(occurrence.occurrence_id)
            original = result.envelope
            envelope = ProviderEnvelope(
                provider="filesystem",
                external_id=occurrence.occurrence_id,
                object_type="file",
                payload=dict(original.payload),
                coverage=original.coverage,
                cursor=original.cursor,
                denied_fields=original.denied_fields,
                references=(
                    ExternalReference(
                        "filesystem",
                        occurrence.occurrence_id,
                        "file",
                        occurrence.locator,
                    ),
                ),
                metadata={
                    **dict(original.metadata),
                    "requires_private_runtime": True,
                },
            )
            processing = self.service.process_envelope(
                scope=authorization,
                envelope=envelope,
                idempotency_key=(
                    f"{snapshot.snapshot_id}:{occurrence.occurrence_id}:content"
                ),
                refresh_coverage_summary=False,
            )
            processed_results.append(processing)
            source = (
                processing.registration.source_version
                if processing.registration is not None
                else source_by_occurrence.get(occurrence.occurrence_id)
            )
            anchors: tuple[EvidenceAnchor, ...] = ()
            extraction_status = "unsupported"
            if source is not None:
                content = str(envelope.payload.get("content", "")).encode("utf-8")
                media_type = (
                    mimetypes.guess_type(occurrence.locator)[0]
                    or "text/plain"
                )
                anchors, _gaps, extraction_status = self._document_evidence(
                    occurrence_id=occurrence.occurrence_id,
                    source=source,
                    external_id=occurrence.occurrence_id,
                    media_type=media_type,
                    content=content,
                    source_context=occurrence.metadata,
                    inventory_identity=snapshot.snapshot_id,
                )
            content_ingested += 1
            evidence_count += len(anchors)
            depth_states.append(
                self._assess(
                    occurrence_id=occurrence.occurrence_id,
                    inventory_revision=snapshot.revision,
                    disposition="tracked",
                    coverage_terminal=processing.terminal_status != "blocked",
                    extraction_current=extraction_status
                    in {"extracted", "partial"},
                    evidence_anchored=bool(anchors),
                    blocked_by=(
                        ""
                        if extraction_status
                        in {"extracted", "partial", "unsupported"}
                        else extraction_status
                    ),
                )
            )

        binary_candidates = [
            occurrence
            for occurrence in occurrences
            if disposition_by_id[occurrence.occurrence_id].status == "tracked"
            and occurrence.object_type in {"image", "document"}
            and occurrence.occurrence_id not in processed_ids
            and selection_by_id[occurrence.occurrence_id].mode
            in READABLE_CONTENT_SELECTION_MODES
        ]
        if content_limit is not None:
            remaining = max(0, content_limit - content_ingested)
            binary_candidates = binary_candidates[:remaining]
        binary_results = adapter.read_tracked_binary(
            object_ids=tuple(item.locator for item in binary_candidates),
            tracking_dispositions={
                item.locator: "tracked" for item in binary_candidates
            },
        )
        binary_by_locator = {
            item.external_id: item for item in binary_results
        }
        for occurrence in binary_candidates:
            result = binary_by_locator[occurrence.locator]
            if not result.ingested:
                processed_ids.add(occurrence.occurrence_id)
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition="tracked",
                        blocked_by=(
                            result.reason
                            if result.disposition
                            in {"inaccessible", "changed_during_read"}
                            else ""
                        ),
                    )
                )
                coverage_gaps.append(
                    f"filesystem_binary:{result.disposition}"
                )
                continue
            processing = self._register_binary_source(
                authorization=authorization,
                inventory_identity=snapshot.snapshot_id,
                occurrence=occurrence,
                content=result.content,
                media_type=result.media_type,
            )
            processed_results.append(processing)
            source = (
                processing.registration.source_version
                if processing.registration is not None
                else source_by_occurrence.get(occurrence.occurrence_id)
            )
            anchors: tuple[EvidenceAnchor, ...] = ()
            extraction_status = "unsupported"
            if source is not None and occurrence.object_type == "image":
                anchors, _gaps, extraction_status = self._image_evidence(
                    occurrence_id=occurrence.occurrence_id,
                    source=source,
                    external_id=str(
                        occurrence.metadata.get("display_name", "image")
                    ),
                    media_type=result.media_type,
                    metadata=occurrence.metadata,
                    content=result.content,
                    source_context=occurrence.metadata,
                    inventory_identity=snapshot.snapshot_id,
                )
            elif source is not None:
                anchors, _gaps, extraction_status = self._document_evidence(
                    occurrence_id=occurrence.occurrence_id,
                    source=source,
                    external_id=str(
                        occurrence.metadata.get("display_name", "document")
                    ),
                    media_type=result.media_type,
                    content=result.content,
                    source_context=occurrence.metadata,
                    inventory_identity=snapshot.snapshot_id,
                )
            processed_ids.add(occurrence.occurrence_id)
            content_ingested += 1
            evidence_count += len(anchors)
            depth_states.append(
                self._assess(
                    occurrence_id=occurrence.occurrence_id,
                    inventory_revision=snapshot.revision,
                    disposition="tracked",
                    coverage_terminal=processing.terminal_status != "blocked",
                    extraction_current=extraction_status
                    in {"extracted", "partial", "metadata_only", "analyzed"},
                    evidence_anchored=bool(anchors),
                    blocked_by=(
                        ""
                        if extraction_status
                        in {
                            "extracted",
                            "partial",
                            "metadata_only",
                            "analyzed",
                            "unsupported",
                        }
                        else extraction_status
                    ),
                )
            )

        for occurrence in occurrences:
            if (
                disposition_by_id[occurrence.occurrence_id].status != "tracked"
                or occurrence.occurrence_id in processed_ids
            ):
                continue
            source = source_by_occurrence.get(occurrence.occurrence_id)
            if occurrence.object_type == "image" and source is not None:
                media_type = (
                    mimetypes.guess_type(occurrence.locator)[0]
                    or "application/octet-stream"
                )
                anchors, _gaps, image_status = self._image_evidence(
                    occurrence_id=occurrence.occurrence_id,
                    source=source,
                    external_id=occurrence.occurrence_id,
                    media_type=media_type,
                    metadata=occurrence.metadata,
                    source_context=occurrence.metadata,
                    inventory_identity=snapshot.snapshot_id,
                )
                evidence_count += len(anchors)
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition="tracked",
                        coverage_terminal=True,
                        extraction_current=image_status
                        in {"metadata_only", "analyzed", "partial"},
                        evidence_anchored=bool(anchors),
                    )
                )
                continue
            depth_states.append(
                self._assess(
                    occurrence_id=occurrence.occurrence_id,
                    inventory_revision=snapshot.revision,
                    disposition="tracked",
                    coverage_terminal=source is not None,
                )
            )

        if refresh_coverage_summary and self.service.coverage_ledger is not None:
            self.service.coverage_ledger.refresh_summary()
        summary = self._summary(
            provider="filesystem",
            snapshot=snapshot,
            metadata_registered=metadata_registered,
            content_ingested=content_ingested,
            evidence_anchors=evidence_count,
            depth_states=depth_states,
            terminal=terminal,
            gaps=coverage_gaps,
        )
        return SourceRunResult(
            summary,
            snapshot,
            changes,
            tuple(processed_results),
        )

    def process_registered_filesystem_batch(
        self,
        *,
        limit: int,
    ) -> RegisteredFilesystemBatchResult:
        """Process a bounded batch through small recoverable claim pages."""

        assert self.service.store is not None
        with self.service.store.connection_session():
            requested_limit = limit
            selected_count = 0
            processed_count = 0
            content_ingested = 0
            evidence_anchors = 0
            changed_count = 0
            unavailable_count = 0
            unsupported_count = 0
            invalid_registration_count = 0
            blocked_count = 0
            remaining_count = 0
            while selected_count < requested_limit:
                worker_id = (
                    f"filesystem-worker:{os.getpid()}:{uuid4().hex}"
                )
                try:
                    page = self._process_registered_filesystem_batch(
                        limit=min(
                            self.REGISTERED_FILESYSTEM_CLAIM_SIZE,
                            requested_limit - selected_count,
                        ),
                        worker_id=worker_id,
                        refresh_coverage_summary=False,
                    )
                except BaseException:
                    self.service.store.abandon_filesystem_worker_claim(
                        worker_id=worker_id,
                        reason="worker_interrupted",
                    )
                    raise
                selected_count += page.selected_count
                processed_count += page.processed_count
                content_ingested += page.content_ingested
                evidence_anchors += page.evidence_anchors
                changed_count += page.changed_count
                unavailable_count += page.unavailable_count
                unsupported_count += page.unsupported_count
                invalid_registration_count += (
                    page.invalid_registration_count
                )
                blocked_count += page.blocked_count
                remaining_count = page.remaining_count
                if page.selected_count == 0:
                    break
            if self.service.coverage_ledger is not None:
                self.service.coverage_ledger.refresh_summary()
            return RegisteredFilesystemBatchResult(
                status=(
                    "idle"
                    if selected_count == 0
                    else (
                        "processed_with_blocks"
                        if blocked_count
                        else "processed"
                    )
                ),
                requested_limit=requested_limit,
                selected_count=selected_count,
                processed_count=processed_count,
                content_ingested=content_ingested,
                evidence_anchors=evidence_anchors,
                changed_count=changed_count,
                unavailable_count=unavailable_count,
                unsupported_count=unsupported_count,
                invalid_registration_count=invalid_registration_count,
                blocked_count=blocked_count,
                remaining_count=remaining_count,
            )

    def _process_registered_filesystem_batch(
        self,
        *,
        limit: int,
        worker_id: str,
        refresh_coverage_summary: bool,
    ) -> RegisteredFilesystemBatchResult:
        """Process registered filesystem content without rediscovery.

        Selection comes only from the materialized coverage-stage index.
        Private roots and relative locators are rehydrated from their current
        candidate scope and inventory snapshot, then remain inside the private
        runtime path.
        """

        assert self.service.store is not None
        claim = self.service.store.claim_registered_filesystem(
            worker_id=worker_id,
            limit=limit,
            lease_seconds=self.REGISTERED_FILESYSTEM_LEASE_SECONDS,
        )
        if claim is None:
            return RegisteredFilesystemBatchResult(
                status="idle",
                requested_limit=limit,
                selected_count=0,
                processed_count=0,
                content_ingested=0,
                evidence_anchors=0,
                changed_count=0,
                unavailable_count=0,
                unsupported_count=0,
                invalid_registration_count=0,
                blocked_count=0,
                remaining_count=0,
            )

        claim_id = str(claim["claim_id"])
        claim_token = str(claim["claim_token"])
        claimed_rows = self.service.store.filesystem_claim_occurrences(
            claim_id=claim_id,
            claim_token=claim_token,
        )
        object_ids = tuple(
            str(row["object_id"]) for row in claimed_rows
        )

        def checkpoint(
            object_id: str,
            stage: str,
            payload: Mapping[str, Any],
        ) -> None:
            self.service.store.update_filesystem_claim_checkpoint(
                claim_id=claim_id,
                claim_token=claim_token,
                object_id=object_id,
                stage=stage,
                checkpoint=dict(payload),
                extend_lease_seconds=(
                    self.REGISTERED_FILESYSTEM_LEASE_SECONDS
                ),
            )

        def complete(
            object_id: str,
            payload: Mapping[str, Any],
        ) -> None:
            self.service.store.complete_filesystem_claim_item(
                claim_id=claim_id,
                claim_token=claim_token,
                object_id=object_id,
                checkpoint=dict(payload),
            )

        coverage_payloads = self.service.store.current_many(
            "object_coverage",
            object_ids,
        )
        indexed_occurrences = (
            self.service.store.inventory_occurrences_by_object_ids(
                object_ids
            )
        )
        by_scope: dict[
            str,
            list[
                tuple[
                    Mapping[str, Any],
                    InventoryOccurrence,
                    int,
                ]
            ],
        ] = {}
        invalid_rows: list[tuple[str, int, str]] = []
        for claimed in claimed_rows:
            object_id = str(claimed["object_id"])
            coverage = coverage_payloads.get(object_id)
            if (
                coverage is None
                or not bool(coverage.get("active", True))
                or str(coverage.get("provider", "")) != "filesystem"
                or str(coverage.get("disposition", "")) != "tracked"
            ):
                invalid_rows.append(
                    (
                        object_id,
                        max(1, int(claimed["inventory_revision"])),
                        "filesystem_registration_not_current",
                    )
                )
                continue
            scope_id = str(claimed["scope_id"])
            inventory_revision = int(claimed["inventory_revision"])
            scope = self.service.store.current("candidate_scope", scope_id)
            occurrence_payload = dict(claimed["occurrence"])
            current_matches = tuple(
                row
                for row in indexed_occurrences.get(object_id, ())
                if str(row["scope_id"]) == scope_id
                and int(row["inventory_revision"]) == inventory_revision
                and str(row["provider"]) == "filesystem"
                and str(row["disposition"]) == "tracked"
                and dict(row["occurrence"]) == occurrence_payload
            )
            if (
                not scope_id
                or inventory_revision < 1
                or scope is None
                or not current_matches
                or str(scope.get("provider", "")) != "filesystem"
                or not bool(scope.get("active", True))
                or str(coverage.get("scope_id", "")) != scope_id
                or int(coverage.get("inventory_revision", 0) or 0)
                != inventory_revision
            ):
                invalid_rows.append(
                    (
                        object_id,
                        max(1, inventory_revision),
                        "filesystem_registration_not_current",
                    )
                )
                continue
            occurrence = InventoryOccurrence(**occurrence_payload)
            if (
                occurrence.provider != "filesystem"
                or occurrence.occurrence_id != object_id
            ):
                invalid_rows.append(
                    (
                        object_id,
                        inventory_revision,
                        "filesystem_occurrence_not_current",
                    )
                )
                continue
            by_scope.setdefault(scope_id, []).append(
                (scope, occurrence, inventory_revision)
            )

        processed_count = 0
        content_ingested = 0
        evidence_count = 0
        changed_count = 0
        unavailable_count = 0
        unsupported_count = 0
        invalid_count = 0
        blocked_count = 0

        for object_id, inventory_revision, failure_class in invalid_rows:
            invalid_count += 1
            blocked_count += int(
                self._block_registered_filesystem_occurrence(
                    occurrence_id=object_id,
                    inventory_revision=inventory_revision,
                    failure_class=failure_class,
                )
            )
            complete(
                object_id,
                {
                    "status": "blocked",
                    "failure_class": failure_class,
                },
            )

        for scope_id, scope_rows in by_scope.items():
            scope_payload = scope_rows[0][0]
            occurrences = tuple(row[1] for row in scope_rows)
            inventory_revision = int(scope_rows[0][2])
            inventory_identity = (
                f"inventory:{scope_id}:{inventory_revision}"
            )
            policy_prefix = self._registered_policy_path_prefix(
                occurrences[0]
            )
            try:
                adapter = FilesystemReadOnlyAdapter(
                    Path(str(scope_payload["root_locator"])),
                    policy_path_prefix=policy_prefix,
                )
            except (OSError, PermissionError, ValueError):
                for occurrence in occurrences:
                    unavailable_count += 1
                    blocked_count += int(
                        self._block_registered_filesystem_occurrence(
                            occurrence_id=occurrence.occurrence_id,
                            inventory_revision=inventory_revision,
                            failure_class="filesystem_scope_unavailable",
                        )
                    )
                    complete(
                        occurrence.occurrence_id,
                        {
                            "status": "blocked",
                            "failure_class": "filesystem_scope_unavailable",
                        },
                    )
                continue

            authorization = self._authorization(
                scope_id=scope_id,
                provider="filesystem",
                occurrences=occurrences,
            )

            def finish_block(
                occurrence_id: str,
                failure_class: str,
            ) -> int:
                blocked = int(
                    self._block_registered_filesystem_occurrence(
                        occurrence_id=occurrence_id,
                        inventory_revision=inventory_revision,
                        failure_class=failure_class,
                    )
                )
                complete(
                    occurrence_id,
                    {
                        "status": "blocked",
                        "failure_class": failure_class,
                    },
                )
                return blocked

            def stage_callback_for(
                occurrence_id: str,
            ) -> Callable[[str, Mapping[str, Any]], None]:
                return lambda stage, payload: checkpoint(
                    occurrence_id,
                    stage,
                    payload,
                )

            text_candidates = tuple(
                occurrence
                for occurrence in occurrences
                if occurrence.object_type in {"document", "file"}
            )
            text_results = adapter.read_tracked(
                object_ids=tuple(item.locator for item in text_candidates),
                tracking_dispositions={
                    item.locator: "tracked" for item in text_candidates
                },
            )
            text_by_locator = {
                item.external_id: item for item in text_results
            }
            binary_candidates: list[InventoryOccurrence] = [
                occurrence
                for occurrence in occurrences
                if occurrence.object_type == "image"
            ]

            for occurrence in text_candidates:
                result = text_by_locator[occurrence.locator]
                if (
                    result.disposition == "unsupported"
                    and occurrence.object_type == "document"
                ):
                    binary_candidates.append(occurrence)
                    continue
                if not result.ingested or result.envelope is None:
                    failure_class = {
                        "changed_during_read": "filesystem_content_changed",
                        "inaccessible": "filesystem_content_unavailable",
                    }.get(
                        result.disposition,
                        "filesystem_content_unsupported",
                    )
                    if result.disposition == "changed_during_read":
                        changed_count += 1
                    elif result.disposition == "inaccessible":
                        unavailable_count += 1
                    else:
                        unsupported_count += 1
                    blocked_count += finish_block(
                        occurrence.occurrence_id,
                        failure_class,
                    )
                    continue
                if not self._registered_metadata_matches(
                    occurrence,
                    result.envelope.metadata,
                ):
                    changed_count += 1
                    blocked_count += finish_block(
                        occurrence.occurrence_id,
                        "filesystem_inventory_stale",
                    )
                    continue

                original = result.envelope
                envelope = ProviderEnvelope(
                    provider="filesystem",
                    external_id=occurrence.occurrence_id,
                    object_type="file",
                    payload=dict(original.payload),
                    coverage=original.coverage,
                    cursor=original.cursor,
                    denied_fields=original.denied_fields,
                    references=(
                        ExternalReference(
                            "filesystem",
                            occurrence.occurrence_id,
                            "file",
                            occurrence.locator,
                        ),
                    ),
                    metadata={
                        **dict(original.metadata),
                        "requires_private_runtime": True,
                    },
                )
                processing = self.service.process_envelope(
                    scope=authorization,
                    envelope=envelope,
                    idempotency_key=(
                        f"{inventory_identity}:"
                        f"{occurrence.occurrence_id}:content"
                    ),
                    refresh_coverage_summary=False,
                )
                source = (
                    processing.registration.source_version
                    if processing.registration is not None
                    else None
                )
                if source is None or processing.terminal_status == "blocked":
                    blocked_count += finish_block(
                        occurrence.occurrence_id,
                        "filesystem_source_registration_blocked",
                    )
                    continue
                checkpoint(
                    occurrence.occurrence_id,
                    "extraction",
                    {"source_version_id": _source_version_ref(source)},
                )
                if processing.registration.status == "no_delta":
                    self._mark_registered_source_current(
                        occurrence_id=occurrence.occurrence_id,
                        source=source,
                    )
                content = str(
                    envelope.payload.get("content", "")
                ).encode("utf-8")
                media_type = (
                    mimetypes.guess_type(occurrence.locator)[0]
                    or "text/plain"
                )
                anchors, _gaps, extraction_status = self._document_evidence(
                    occurrence_id=occurrence.occurrence_id,
                    source=source,
                    external_id=occurrence.occurrence_id,
                    media_type=media_type,
                    content=content,
                    source_context=occurrence.metadata,
                    inventory_identity=inventory_identity,
                    stage_callback=stage_callback_for(
                        occurrence.occurrence_id
                    ),
                )
                processed_count += 1
                content_ingested += 1
                evidence_count += len(anchors)
                self._assess(
                    occurrence_id=occurrence.occurrence_id,
                    inventory_revision=inventory_revision,
                    disposition="tracked",
                    coverage_terminal=processing.terminal_status != "blocked",
                    extraction_current=extraction_status
                    in {"extracted", "partial"},
                    evidence_anchored=bool(anchors),
                    blocked_by=(
                        ""
                        if extraction_status
                        in {"extracted", "partial", "unsupported"}
                        else extraction_status
                    ),
                )
                complete(
                    occurrence.occurrence_id,
                    {
                        "status": "processed",
                        "extraction_status": extraction_status,
                        "anchor_count": len(anchors),
                    },
                )

            binary_results = adapter.read_tracked_binary(
                object_ids=tuple(item.locator for item in binary_candidates),
                tracking_dispositions={
                    item.locator: "tracked" for item in binary_candidates
                },
            )
            binary_by_locator = {
                item.external_id: item for item in binary_results
            }
            for occurrence in binary_candidates:
                result = binary_by_locator[occurrence.locator]
                if not result.ingested:
                    failure_class = {
                        "changed_during_read": "filesystem_content_changed",
                        "inaccessible": "filesystem_content_unavailable",
                    }.get(
                        result.disposition,
                        "filesystem_content_unsupported",
                    )
                    if result.disposition == "changed_during_read":
                        changed_count += 1
                    elif result.disposition == "inaccessible":
                        unavailable_count += 1
                    else:
                        unsupported_count += 1
                    blocked_count += finish_block(
                        occurrence.occurrence_id,
                        failure_class,
                    )
                    continue
                if not self._registered_metadata_matches(
                    occurrence,
                    result.metadata,
                ):
                    changed_count += 1
                    blocked_count += finish_block(
                        occurrence.occurrence_id,
                        "filesystem_inventory_stale",
                    )
                    continue

                processing = self._register_binary_source(
                    authorization=authorization,
                    inventory_identity=inventory_identity,
                    occurrence=occurrence,
                    content=result.content,
                    media_type=result.media_type,
                )
                source = (
                    processing.registration.source_version
                    if processing.registration is not None
                    else None
                )
                if source is None or processing.terminal_status == "blocked":
                    blocked_count += finish_block(
                        occurrence.occurrence_id,
                        "filesystem_source_registration_blocked",
                    )
                    continue
                checkpoint(
                    occurrence.occurrence_id,
                    "extraction",
                    {"source_version_id": _source_version_ref(source)},
                )
                if processing.registration.status == "no_delta":
                    self._mark_registered_source_current(
                        occurrence_id=occurrence.occurrence_id,
                        source=source,
                    )
                if occurrence.object_type == "image":
                    anchors, _gaps, extraction_status = self._image_evidence(
                        occurrence_id=occurrence.occurrence_id,
                        source=source,
                        external_id=str(
                            occurrence.metadata.get("display_name", "image")
                        ),
                        media_type=result.media_type,
                        metadata=occurrence.metadata,
                        content=result.content,
                        source_context=occurrence.metadata,
                        inventory_identity=inventory_identity,
                        stage_callback=stage_callback_for(
                            occurrence.occurrence_id
                        ),
                    )
                else:
                    anchors, _gaps, extraction_status = self._document_evidence(
                        occurrence_id=occurrence.occurrence_id,
                        source=source,
                        external_id=str(
                            occurrence.metadata.get("display_name", "document")
                        ),
                        media_type=result.media_type,
                        content=result.content,
                        source_context=occurrence.metadata,
                        inventory_identity=inventory_identity,
                        stage_callback=stage_callback_for(
                            occurrence.occurrence_id
                        ),
                    )
                processed_count += 1
                content_ingested += 1
                evidence_count += len(anchors)
                self._assess(
                    occurrence_id=occurrence.occurrence_id,
                    inventory_revision=inventory_revision,
                    disposition="tracked",
                    coverage_terminal=processing.terminal_status != "blocked",
                    extraction_current=extraction_status
                    in {"extracted", "partial", "metadata_only", "analyzed"},
                    evidence_anchored=bool(anchors),
                    blocked_by=(
                        ""
                        if extraction_status
                        in {
                            "extracted",
                            "partial",
                            "metadata_only",
                            "analyzed",
                            "unsupported",
                        }
                        else extraction_status
                    ),
                )
                complete(
                    occurrence.occurrence_id,
                    {
                        "status": "processed",
                        "extraction_status": extraction_status,
                        "anchor_count": len(anchors),
                    },
                )

        if (
            refresh_coverage_summary
            and self.service.coverage_ledger is not None
        ):
            self.service.coverage_ledger.refresh_summary()
        _remaining_ids, remaining_count = (
            self.service.store.registered_filesystem_source_page(limit=1)
        )
        return RegisteredFilesystemBatchResult(
            status=(
                "processed_with_blocks"
                if blocked_count
                else "processed"
            ),
            requested_limit=limit,
            selected_count=len(object_ids),
            processed_count=processed_count,
            content_ingested=content_ingested,
            evidence_anchors=evidence_count,
            changed_count=changed_count,
            unavailable_count=unavailable_count,
            unsupported_count=unsupported_count,
            invalid_registration_count=invalid_count,
            blocked_count=blocked_count,
            remaining_count=remaining_count,
        )

    def run_gmail(
        self,
        adapter: GmailReadOnlyAdapter,
        *,
        user_intents: Mapping[str, str] | None = None,
        auto_track_included: bool = True,
        content_limit: int | None = None,
        content_offset: int = 0,
        metadata_limit: int | None = None,
        metadata_offset: int = 0,
        page_limit: int = 10_000,
    ) -> SourceRunResult:
        """Run one bounded Gmail page with reusable short DB transactions."""

        assert self.service.store is not None
        with self.service.store.connection_session():
            return self._run_gmail(
                adapter,
                user_intents=user_intents,
                auto_track_included=auto_track_included,
                content_limit=content_limit,
                content_offset=content_offset,
                metadata_limit=metadata_limit,
                metadata_offset=metadata_offset,
                page_limit=page_limit,
            )

    def _run_gmail(
        self,
        adapter: GmailReadOnlyAdapter,
        *,
        user_intents: Mapping[str, str] | None = None,
        auto_track_included: bool = True,
        content_limit: int | None = None,
        content_offset: int = 0,
        metadata_limit: int | None = None,
        metadata_offset: int = 0,
        page_limit: int = 10_000,
    ) -> SourceRunResult:
        """Inventory authorized Gmail pages and read only tracked messages."""

        if (
            (content_limit is not None and content_limit < 0)
            or content_offset < 0
            or (metadata_limit is not None and metadata_limit < 0)
            or metadata_offset < 0
        ):
            raise ValueError("Gmail content bounds cannot be negative")
        pages: list[tuple[str, GmailAuthorizedPage, tuple[GmailDiscoveryItem, ...]]] = []
        cursor = ""
        terminal = False
        coverage_gaps: list[str] = []
        for _ in range(page_limit):
            authorized_page = adapter.authorized_page(cursor=cursor)
            discovery = adapter.accept_page(authorized_page, cursor=cursor)
            pages.append((cursor, authorized_page, discovery.items))
            coverage_gaps.extend(discovery.gaps)
            terminal = discovery.terminal
            if terminal:
                break
            if not discovery.next_cursor or discovery.next_cursor == cursor:
                coverage_gaps.append(
                    "gmail_partial_inventory_page"
                    if authorized_page.coverage == "partial"
                    else "gmail_cursor_did_not_progress"
                )
                break
            cursor = discovery.next_cursor
        else:
            coverage_gaps.append("gmail_page_limit_exceeded")

        item_by_id: dict[str, GmailDiscoveryItem] = {}
        for _cursor, _page, items in pages:
            for item in items:
                item_by_id[item.envelope.external_id] = item

        page_occurrences: list[InventoryOccurrence] = []
        for external_id in sorted(item_by_id):
            item = item_by_id[external_id]
            envelope = item.envelope
            category = str(envelope.payload.get("category", "")).casefold()
            recommended = item.recommended_disposition
            reason = item.reason
            if (
                not auto_track_included
                and envelope.object_type == "gmail_message"
                and recommended == "tracked"
                and category in adapter.manifest.included_categories
            ):
                recommended = "metadata_only"
                reason = "included_mailbox_content_read_disabled"
            object_type = {
                "gmail_message": "message",
                "gmail_thread": "thread",
                "gmail_attachment": "attachment",
            }.get(envelope.object_type, envelope.object_type)
            display_name = {
                "message": f"{category or 'mail'} message",
                "thread": "mail thread",
                "attachment": str(
                    envelope.payload.get("filename", "mail attachment")
                ),
            }.get(object_type, "mail item")
            thread_group_id = next(
                (
                    reference.external_id
                    for reference in envelope.references
                    if reference.object_type == "gmail_thread"
                ),
                (
                    external_id
                    if object_type == "thread"
                    else str(
                        envelope.metadata.get("parent_external_id", "")
                    )
                ),
            )
            page_occurrences.append(
                InventoryOccurrence(
                    occurrence_id=external_id,
                    provider="gmail",
                    object_type=object_type,
                    locator=external_id,
                    metadata={
                        "display_name": display_name,
                        "recommended_disposition": recommended,
                        "disposition_reason": reason,
                        "coverage": envelope.coverage,
                        "category": category,
                        "source_group_chain": (
                            (thread_group_id,) if thread_group_id else ()
                        ),
                        "source_group_labels": (
                            ("Gmail conversation",)
                            if thread_group_id
                            else ()
                        ),
                    },
                    content_identity=sha256(
                        repr(
                            (
                                envelope.object_type,
                                envelope.payload,
                                envelope.metadata,
                            )
                        ).encode("utf-8")
                    ).hexdigest(),
                    parent_occurrence_id=str(
                        envelope.metadata.get("parent_external_id", "")
                    ),
                )
            )

        scope_id = adapter.manifest.scope_id
        prior_snapshot = self.service.inventory.latest_snapshot(scope_id)
        occurrences_by_id = (
            {
                occurrence.occurrence_id: occurrence
                for occurrence in prior_snapshot.occurrences
            }
            if prior_snapshot is not None
            and any(page.coverage == "partial" for _, page, _ in pages)
            else {}
        )
        occurrences_by_id.update(
            {
                occurrence.occurrence_id: occurrence
                for occurrence in page_occurrences
            }
        )
        occurrences = tuple(occurrences_by_id.values())
        scope = self._scope(
            scope_id=scope_id,
            provider="gmail",
            root_locator=adapter.manifest.account_ref,
            object_types=(item.object_type for item in occurrences),
        )
        snapshot, changes = self.service.reconcile_inventory(
            scope=scope,
            policy=self._policy("tracking-policy:default"),
            occurrences=occurrences,
            user_intents=user_intents,
        )
        disposition_by_id = self._disposition_map(snapshot)
        authorization = self._authorization(
            scope_id=scope_id,
            provider="gmail",
            occurrences=occurrences,
        )
        processed_results: list[SourceProcessingResult] = []
        depth_states: list[str] = []
        metadata_registered = 0
        content_ingested = 0
        evidence_count = 0
        supplied_content_ids = {
            item.envelope.external_id
            for _page_cursor, authorized_page, page_items in pages
            for item in page_items
            if item.envelope.object_type == "gmail_message"
            and item.envelope.payload.get("provider_message_id")
            in {content.message_id for content in authorized_page.contents}
        }
        metadata_message_ids = sorted(
            occurrence.occurrence_id
            for occurrence in page_occurrences
            if occurrence.object_type == "message"
            and disposition_by_id[occurrence.occurrence_id].status
            == "metadata_only"
        )
        selected_metadata_ids = (
            metadata_message_ids[metadata_offset:]
            if metadata_limit is None
            else metadata_message_ids[
                metadata_offset : metadata_offset + metadata_limit
            ]
        )
        selected_metadata_id_set = set(selected_metadata_ids)
        metadata_remaining = max(
            0,
            len(metadata_message_ids)
            - metadata_offset
            - len(selected_metadata_ids),
        )
        if metadata_remaining:
            coverage_gaps.append(
                "gmail_metadata_owner_reconciliation_pending"
            )

        for occurrence in page_occurrences:
            disposition = disposition_by_id[occurrence.occurrence_id]
            if disposition.status in {"hard_excluded", "not_tracked"}:
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition=disposition.status,
                    )
                )
                continue
            if (
                disposition.status == "metadata_only"
                and occurrence.object_type == "message"
            ):
                if (
                    occurrence.occurrence_id
                    in selected_metadata_id_set
                ):
                    item = item_by_id[occurrence.occurrence_id]
                    result = self._register_gmail_metadata_owner(
                        item=item,
                        scope_id=scope_id,
                    )
                    metadata_registered += int(
                        result
                        in {
                            "registered",
                            "metadata_updated",
                        }
                    )
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition=disposition.status,
                    )
                )
                continue
            if disposition.status != "tracked":
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition=disposition.status,
                    )
                )
                continue
            if (
                occurrence.object_type == "message"
                and occurrence.occurrence_id in supplied_content_ids
            ):
                # The complete message envelope below is the authoritative
                # source version. Registering its metadata-only envelope first
                # would alternate a shallower version with the content version
                # on every bounded resume and regress current evidence.
                continue
            item = item_by_id[occurrence.occurrence_id]
            if occurrence.object_type == "message":
                source_id = self.service.sources.source_id(item.envelope)
                current_source = self.service.store.current(
                    "source_version",
                    source_id,
                )
                if (
                    current_source is not None
                    and "body_text_fingerprint"
                    in dict(current_source.get("content", {}))
                ):
                    # A later ID/metadata observation may refresh inventory,
                    # but it must never replace the current content-bearing
                    # source with a shallower metadata-only source version.
                    continue
            processing = self.service.process_envelope(
                scope=authorization,
                envelope=item.envelope,
                idempotency_key=(
                    f"{snapshot.snapshot_id}:{occurrence.occurrence_id}:metadata"
                ),
                refresh_coverage_summary=False,
            )
            processed_results.append(processing)
            metadata_registered += int(
                processing.registration is not None
                and processing.registration.status != "no_delta"
            )

        tracked_message_ids = [
            occurrence.occurrence_id
            for occurrence in page_occurrences
            if occurrence.object_type == "message"
            and disposition_by_id[occurrence.occurrence_id].status == "tracked"
        ]
        tracked_message_ids.sort(
            key=lambda occurrence_id: (
                occurrence_id not in supplied_content_ids,
                occurrence_id,
            )
        )
        if content_limit is not None:
            tracked_message_ids = tracked_message_ids[
                content_offset : content_offset + content_limit
            ]
        elif content_offset:
            tracked_message_ids = tracked_message_ids[content_offset:]
        selected_ids = set(tracked_message_ids)
        processed_ids: set[str] = set()
        dispositions = {
            occurrence.occurrence_id: disposition_by_id[
                occurrence.occurrence_id
            ].status
            for occurrence in page_occurrences
        }
        for page_cursor, authorized_page, page_items in pages:
            page_ids = {
                item.envelope.external_id
                for item in page_items
                if item.envelope.object_type == "gmail_message"
            }
            requested = selected_ids.intersection(page_ids)
            if not requested:
                continue
            results = adapter.read_page(
                authorized_page,
                tracking_dispositions=dispositions,
                cursor=page_cursor,
            )
            for result in results:
                if result.external_id not in requested:
                    continue
                processed_ids.add(result.external_id)
                if not result.ingested or result.envelope is None:
                    depth_states.append(
                        self._assess(
                            occurrence_id=result.external_id,
                            inventory_revision=snapshot.revision,
                            disposition="tracked",
                            blocked_by=(
                                result.reason
                                if result.disposition == "inaccessible"
                                else ""
                            ),
                        )
                    )
                    coverage_gaps.append(
                        f"gmail_content:{result.disposition}"
                    )
                    continue
                processing = self.service.process_envelope(
                    scope=authorization,
                    envelope=result.envelope,
                    idempotency_key=(
                        f"{snapshot.snapshot_id}:{result.external_id}:content"
                    ),
                    refresh_coverage_summary=False,
                )
                processed_results.append(processing)
                source = (
                    processing.registration.source_version
                    if processing.registration is not None
                    else None
                )
                anchors: tuple[EvidenceAnchor, ...] = ()
                extraction_status = "unsupported"
                if source is not None:
                    body = str(
                        result.envelope.payload.get("body_text", "")
                    ).encode("utf-8")
                    anchors, _gaps, extraction_status = (
                        self._document_evidence(
                            occurrence_id=result.external_id,
                            source=source,
                            external_id=result.external_id,
                            media_type="text/plain",
                            content=body,
                            inventory_identity=snapshot.snapshot_id,
                        )
                    )
                content_ingested += 1
                evidence_count += len(anchors)
                depth_states.append(
                    self._assess(
                        occurrence_id=result.external_id,
                        inventory_revision=snapshot.revision,
                        disposition="tracked",
                        coverage_terminal=processing.terminal_status != "blocked",
                        extraction_current=extraction_status
                        in {"extracted", "partial"},
                        evidence_anchored=bool(anchors),
                    )
                )

        for occurrence_id in tracked_message_ids:
            if occurrence_id in processed_ids:
                continue
            depth_states.append(
                self._assess(
                    occurrence_id=occurrence_id,
                    inventory_revision=snapshot.revision,
                    disposition="tracked",
                )
            )

        if self.service.coverage_ledger is not None:
            self.service.coverage_ledger.refresh_summary()
        summary = self._summary(
            provider="gmail",
            snapshot=snapshot,
            metadata_registered=metadata_registered,
            content_ingested=content_ingested,
            evidence_anchors=evidence_count,
            depth_states=depth_states,
            terminal=terminal,
            gaps=coverage_gaps,
        )
        return SourceRunResult(
            summary,
            snapshot,
            changes,
            tuple(processed_results),
        )

    def _gmail_metadata_owner_is_current(
        self,
        *,
        item: GmailDiscoveryItem,
        scope_id: str,
    ) -> bool:
        store = self.service.store
        ledger = self.service.coverage_ledger
        assert store is not None and ledger is not None
        external_id = item.envelope.external_id
        coverage = ledger.current(external_id)
        if (
            coverage is None
            or not coverage.active
            or coverage.scope_id != scope_id
            or coverage.provider != "gmail"
            or coverage.object_type != "message"
            or coverage.disposition != "metadata_only"
        ):
            return False
        matching = tuple(
            occurrence
            for occurrence in store.inventory_occurrences_by_object_ids(
                (external_id,)
            ).get(external_id, ())
            if occurrence["scope_id"] == scope_id
            and occurrence["inventory_revision"]
            == coverage.inventory_revision
            and occurrence["provider"] == "gmail"
            and occurrence["object_type"] == "message"
            and occurrence["disposition"] == "metadata_only"
        )
        return len(matching) == 1

    def _register_gmail_metadata_owner(
        self,
        *,
        item: GmailDiscoveryItem,
        scope_id: str,
    ) -> str:
        """Register only C2 metadata after exact current C1 owner checks."""

        if item.envelope.object_type != "gmail_message":
            raise ValueError("gmail_metadata_message_required")
        if not self._gmail_metadata_owner_is_current(
            item=item,
            scope_id=scope_id,
        ):
            raise ValueError("gmail_metadata_inventory_owner_not_current")
        source_id = self.service.sources.source_id(item.envelope)
        current = self.service.sources.current(source_id)
        if current is not None and not current.tombstone:
            if "body_text_fingerprint" in current.content:
                return "body_preserved"
        registration = self.service.sources.register(
            item.envelope,
            idempotency_key=(
                "gmail-metadata-owner-reconciliation:"
                f"{scope_id}:{item.envelope.external_id}:"
                f"{_digest(repr(dict(item.envelope.payload)))}:"
                f"{_digest(repr(dict(item.envelope.metadata)))}"
            ),
        )
        source = self.service.sources.current(source_id)
        if source is None or source.tombstone:
            raise RuntimeError("gmail_metadata_source_version_not_current")
        if "body_text_fingerprint" in source.content:
            raise RuntimeError("gmail_metadata_reconciliation_created_body")
        ledger = self.service.coverage_ledger
        assert ledger is not None
        before = ledger.current(item.envelope.external_id)
        assert before is not None
        fingerprint = "sha256:" + _digest(
            json.dumps(
                {
                    "source_ref": _source_version_ref(source),
                    "content_hash": source.content_hash,
                    "metadata_hash": source.metadata_hash,
                    "contract": "gmail-metadata-owner-reconciliation:v1",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        source_pointer = before.stages.get("source_version")
        if not (
            source_pointer is not None
            and source_pointer.status == "current"
            and source_pointer.input_fingerprint == fingerprint
            and source_pointer.output_ref == _source_version_ref(source)
            and not source_pointer.failure_class
        ):
            ledger.mark_stage(
                object_id=item.envelope.external_id,
                stage_id="source_version",
                status="current",
                input_fingerprint=fingerprint,
                output_ref=_source_version_ref(source),
                refresh_summary=False,
            )
        after = ledger.current(item.envelope.external_id)
        assert after is not None
        if registration.status == "no_delta":
            return "already_current"
        if current is None or current.tombstone:
            return "registered"
        return "metadata_updated"

    def reconcile_gmail_metadata_owners(
        self,
        adapter: GmailReadOnlyAdapter,
        *,
        after_object_id: str = "",
        limit: int = 500,
        page_limit: int = 10_000,
    ) -> GmailMetadataReconciliationResult:
        """Repair one bounded page of current metadata-only Gmail owners."""

        if limit < 1 or limit > 500 or page_limit < 1:
            raise ValueError("gmail_metadata_reconciliation_bounds_invalid")
        cursor = ""
        terminal = False
        item_by_id: dict[str, GmailDiscoveryItem] = {}
        for _ in range(page_limit):
            page = adapter.authorized_page(cursor=cursor)
            discovery = adapter.accept_page(page, cursor=cursor)
            for item in discovery.items:
                if item.envelope.object_type == "gmail_message":
                    item_by_id[item.envelope.external_id] = item
            terminal = discovery.terminal
            if terminal:
                break
            if not discovery.next_cursor or discovery.next_cursor == cursor:
                raise ValueError(
                    "gmail_metadata_reconciliation_cursor_not_terminal"
                )
            cursor = discovery.next_cursor
        if not terminal:
            raise ValueError(
                "gmail_metadata_reconciliation_inventory_not_terminal"
            )

        ordered_ids = tuple(
            object_id
            for object_id in sorted(item_by_id)
            if object_id > after_object_id
            and item_by_id[object_id].recommended_disposition
            == "metadata_only"
        )
        eligible_ids: list[str] = []
        skipped_owner_mismatch_count = 0
        for object_id in ordered_ids:
            if self._gmail_metadata_owner_is_current(
                item=item_by_id[object_id],
                scope_id=adapter.manifest.scope_id,
            ):
                eligible_ids.append(object_id)
            else:
                skipped_owner_mismatch_count += 1
        selected_ids = tuple(eligible_ids[:limit])

        registered_count = 0
        metadata_updated_count = 0
        already_current_count = 0
        preserved_body_count = 0
        coverage_updated_count = 0
        ledger = self.service.coverage_ledger
        assert ledger is not None
        for object_id in selected_ids:
            before = ledger.current(object_id)
            assert before is not None
            result = self._register_gmail_metadata_owner(
                item=item_by_id[object_id],
                scope_id=adapter.manifest.scope_id,
            )
            after = ledger.current(object_id)
            assert after is not None
            registered_count += int(result == "registered")
            metadata_updated_count += int(result == "metadata_updated")
            already_current_count += int(result == "already_current")
            preserved_body_count += int(result == "body_preserved")
            coverage_updated_count += int(after.revision != before.revision)

        if selected_ids and (
            registered_count
            or metadata_updated_count
            or coverage_updated_count
        ):
            ledger.refresh_summary()
        remaining_count = max(0, len(eligible_ids) - len(selected_ids))
        return GmailMetadataReconciliationResult(
            status=(
                "current"
                if (
                    registered_count
                    or metadata_updated_count
                    or coverage_updated_count
                )
                else "no_delta"
            ),
            scope_id=adapter.manifest.scope_id,
            requested_limit=limit,
            scanned_message_count=len(item_by_id),
            eligible_message_count=len(eligible_ids),
            selected_count=len(selected_ids),
            registered_count=registered_count,
            metadata_updated_count=metadata_updated_count,
            already_current_count=already_current_count,
            preserved_body_count=preserved_body_count,
            coverage_updated_count=coverage_updated_count,
            skipped_owner_mismatch_count=skipped_owner_mismatch_count,
            remaining_count=remaining_count,
            next_after_object_id=(
                selected_ids[-1]
                if remaining_count and selected_ids
                else ""
            ),
        )


__all__ = [
    "RegisteredFilesystemBatchResult",
    "GmailMetadataReconciliationResult",
    "SourceRunResult",
    "SourceRunSummary",
    "SourceWorkflow",
]
