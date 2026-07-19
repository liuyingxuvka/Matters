"""C3: evidence qualification with precise version-bound anchors."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping

from matters.provenance.source_registry import SourceVersion


EVIDENCE_MODALITIES = {
    "observed",
    "reported",
    "planned",
    "inferred",
    "forecast",
}


@dataclass(frozen=True)
class EvidenceAnchor:
    evidence_id: str
    source_id: str
    source_version: int
    location: Mapping[str, Any]
    text: str
    modality: str
    current: bool = True


@dataclass(frozen=True)
class EvidenceGap:
    source_id: str
    reason: str
    claim: str = ""


class EvidenceQualifier:
    """The only owner allowed to promote source material to formal evidence."""

    def qualify(
        self,
        source: SourceVersion,
        *,
        text: str,
        location: Mapping[str, Any] | None,
        modality: str,
    ) -> EvidenceAnchor | EvidenceGap:
        if source.tombstone:
            return EvidenceGap(source.source_id, "source is tombstoned", text)
        if modality not in EVIDENCE_MODALITIES:
            return EvidenceGap(source.source_id, "unknown evidence modality", text)
        if not location or not any(
            key in location for key in ("field", "region", "page", "line")
        ):
            return EvidenceGap(source.source_id, "precise anchor missing", text)
        location_text = repr(sorted(dict(location).items()))
        digest = sha256(
            f"{location_text}\0{text}\0{modality}".encode("utf-8")
        ).hexdigest()[:24]
        evidence_id = f"evidence:{source.source_id}:{source.version}:{digest}"
        return EvidenceAnchor(
            evidence_id=evidence_id,
            source_id=source.source_id,
            source_version=source.version,
            location=dict(location),
            text=text,
            modality=modality,
        )

    @staticmethod
    def mark_stale(anchor: EvidenceAnchor) -> EvidenceAnchor:
        return EvidenceAnchor(
            evidence_id=anchor.evidence_id,
            source_id=anchor.source_id,
            source_version=anchor.source_version,
            location=anchor.location,
            text=anchor.text,
            modality=anchor.modality,
            current=False,
        )


__all__ = [
    "EVIDENCE_MODALITIES",
    "EvidenceAnchor",
    "EvidenceGap",
    "EvidenceQualifier",
]
