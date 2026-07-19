from matters.providers.base import ProviderEnvelope
from matters.provenance.evidence import EvidenceAnchor, EvidenceGap, EvidenceQualifier
from matters.provenance.source_registry import SourceRegistry


def _source():
    result = SourceRegistry().register(
        ProviderEnvelope("fake", "one", "object", {"title": "x"}),
        idempotency_key="a",
    )
    return result.source_version


def test_precise_anchor_modality_gap_and_staleness():
    owner = EvidenceQualifier()
    source = _source()
    anchor = owner.qualify(
        source,
        text="work is planned",
        location={"field": "body", "line": 3},
        modality="planned",
    )
    gap = owner.qualify(
        source,
        text="detailed claim",
        location=None,
        modality="reported",
    )
    assert isinstance(anchor, EvidenceAnchor)
    assert anchor.modality == "planned"
    assert isinstance(gap, EvidenceGap)
    assert not owner.mark_stale(anchor).current
    image = owner.qualify(
        source,
        text="value in image",
        location={"field": "attachments", "region": [1, 2, 3, 4]},
        modality="observed",
    )
    assert isinstance(image, EvidenceAnchor)
