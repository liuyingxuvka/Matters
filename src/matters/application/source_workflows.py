"""Durable source runs from metadata inventory through bounded evidence.

Provider adapters deliberately stop before they own tracking, persistence, or
semantic-depth decisions.  This module is the application-level coordinator
that joins those independent owners without making a provider authoritative
for canonical Matters state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import mimetypes
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from matters.application.orchestrator import MatterService, SourceProcessingResult
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


class SourceWorkflow:
    """Join read-only adapters to the durable application owners."""

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
        assert self.service.store is not None
        self.service.store.append(
            "evidence_anchor",
            anchor.evidence_id,
            self.service.store.next_revision(
                "evidence_anchor",
                anchor.evidence_id,
            ),
            asdict(anchor),
        )

    def _persist_gap(self, gap: EvidenceGap) -> None:
        assert self.service.store is not None
        gap_id = (
            f"{gap.source_id}:gap:"
            + _digest(f"{gap.reason}\0{gap.claim}")[:16]
        )
        self.service.store.append(
            "evidence_gap",
            gap_id,
            self.service.store.next_revision("evidence_gap", gap_id),
            asdict(gap),
        )

    def _persist_extraction(
        self,
        *,
        owner: str,
        occurrence_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        assert self.service.store is not None
        self.service.store.append(
            owner,
            occurrence_id,
            self.service.store.next_revision(owner, occurrence_id),
            dict(payload),
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
                ",".join(item.evidence_id for item in anchors)
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
        self.service.store.append(
            "dependency_freshness",
            occurrence_id,
            self.service.store.next_revision(
                "dependency_freshness",
                occurrence_id,
            ),
            {
                "occurrence_id": occurrence_id,
                "inventory_revision": inventory_revision,
                "status": "current",
                "disposition": disposition,
                "dependencies": (),
            },
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
                self._persist_anchor(qualified)
                anchors.append(qualified)
            else:
                self._persist_gap(qualified)
                gaps.append(qualified)
        for reason in extraction.gaps:
            gap = EvidenceGap(source.source_id, reason)
            self._persist_gap(gap)
            gaps.append(gap)
        if (
            self.service.visuals is not None
            and extraction.anchors
            and extraction.status in {"extracted", "partial"}
        ):
            self.service.visuals.register_document_preview(
                source_revision_id=_source_version_ref(source),
                occurrence_id=occurrence_id,
                title=PurePosixPath(external_id).name or "Document",
                text="\n".join(item.text for item in extraction.anchors[:16]),
                evidence_ids=tuple(item.evidence_id for item in anchors),
            )
        queued = False
        if anchors:
            self.service.queue_source_understanding(
                source_revision=_source_version_ref(source),
                source_kind="document",
                anchors=tuple(anchors),
            )
            queued = True
        self._mark_evidence_and_analysis(
            occurrence_id=occurrence_id,
            source=source,
            anchors=anchors,
            queued=queued,
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
                self._persist_anchor(qualified)
                anchors.append(qualified)
            else:
                self._persist_gap(qualified)
                gaps.append(qualified)
        for reason in result.gaps:
            gap = EvidenceGap(source.source_id, reason)
            self._persist_gap(gap)
            gaps.append(gap)
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
            )
            queued = True
        self._mark_evidence_and_analysis(
            occurrence_id=occurrence_id,
            source=source,
            anchors=anchors,
            queued=queued,
        )
        return tuple(anchors), tuple(gaps), result.status

    def _register_binary_source(
        self,
        *,
        authorization: AuthorizationScope,
        snapshot: InventorySnapshot,
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
                ),
            ),
            metadata={
                "requires_private_runtime": True,
                "tracking_disposition": "tracked",
                "binary_content": True,
            },
        )
        return self.service.process_envelope(
            scope=authorization,
            envelope=envelope,
            idempotency_key=(
                f"{snapshot.snapshot_id}:{occurrence.occurrence_id}:binary"
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

    def run_filesystem(
        self,
        adapter: FilesystemReadOnlyAdapter,
        *,
        user_intents: Mapping[str, str] | None = None,
        content_limit: int | None = None,
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
        if content_limit == 0:
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
                snapshot=snapshot,
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

    def run_gmail(
        self,
        adapter: GmailReadOnlyAdapter,
        *,
        user_intents: Mapping[str, str] | None = None,
        auto_track_included: bool = True,
        content_limit: int | None = None,
        page_limit: int = 10_000,
    ) -> SourceRunResult:
        """Inventory authorized Gmail pages and read only tracked messages."""

        if content_limit is not None and content_limit < 0:
            raise ValueError("content_limit cannot be negative")
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
                coverage_gaps.append("gmail_cursor_did_not_progress")
                break
            cursor = discovery.next_cursor
        else:
            coverage_gaps.append("gmail_page_limit_exceeded")

        item_by_id: dict[str, GmailDiscoveryItem] = {}
        for _cursor, _page, items in pages:
            for item in items:
                item_by_id[item.envelope.external_id] = item

        occurrences: list[InventoryOccurrence] = []
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
            occurrences.append(
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
        scope = self._scope(
            scope_id=scope_id,
            provider="gmail",
            root_locator=adapter.manifest.account_ref,
            object_types=(item.object_type for item in occurrences),
        )
        snapshot, changes = self.service.reconcile_inventory(
            scope=scope,
            policy=self._policy("tracking-policy:default"),
            occurrences=tuple(occurrences),
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
            if disposition.status != "tracked":
                depth_states.append(
                    self._assess(
                        occurrence_id=occurrence.occurrence_id,
                        inventory_revision=snapshot.revision,
                        disposition=disposition.status,
                    )
                )
                continue
            item = item_by_id[occurrence.occurrence_id]
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

        supplied_content_ids = {
            item.envelope.external_id
            for _page_cursor, authorized_page, page_items in pages
            for item in page_items
            if item.envelope.object_type == "gmail_message"
            and item.envelope.payload.get("provider_message_id")
            in {content.message_id for content in authorized_page.contents}
        }
        tracked_message_ids = [
            occurrence.occurrence_id
            for occurrence in occurrences
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
            tracked_message_ids = tracked_message_ids[:content_limit]
        selected_ids = set(tracked_message_ids)
        processed_ids: set[str] = set()
        dispositions = {
            occurrence.occurrence_id: disposition_by_id[
                occurrence.occurrence_id
            ].status
            for occurrence in occurrences
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


__all__ = [
    "SourceRunResult",
    "SourceRunSummary",
    "SourceWorkflow",
]
