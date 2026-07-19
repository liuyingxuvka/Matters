from __future__ import annotations

import pytest

from matters.providers.images import (
    ImageAdapter,
    ImageObservation,
    ImageSource,
)


def _image(**changes) -> ImageSource:
    values = {
        "source_version_id": "source:image:v1",
        "external_id": "synthetic.png",
        "media_type": "image/png",
        "width": 100,
        "height": 50,
        "metadata": {
            "exif.capture_time": "2026-01-01T12:00:00Z",
            "width": 100,
        },
        "tracking_disposition": "tracked",
        "content": b"synthetic-image-bytes",
    }
    values.update(changes)
    return ImageSource(**values)


def test_image_inventory_is_metadata_only_and_never_event_or_identity_proof():
    result = ImageAdapter().inventory(_image(content=None))

    assert result.status == "metadata_only"
    exif = next(
        item for item in result.observations if item.modality == "exif_derived"
    )
    assert not exif.event_proof
    assert not exif.identity_proof
    assert exif.anchor == {"metadata_field": "exif.capture_time"}


def test_image_analysis_requires_tracking_and_visible_runner():
    adapter = ImageAdapter()

    not_tracked = adapter.analyze(
        _image(tracking_disposition="review_required")
    )
    unsupported = adapter.analyze(_image())

    assert not_tracked.status == "not_tracked"
    assert unsupported.status == "unsupported"
    assert "ocr_or_visual_runner_unavailable" in unsupported.gaps


def test_injected_ocr_runner_preserves_region_confidence_and_uncertainty():
    class SyntheticOCR:
        runner_id = "synthetic.ocr:v1"
        modalities = frozenset({"ocr_derived"})

        def analyze(self, source, *, budget):
            return (
                ImageObservation(
                    "ocr_derived",
                    {"region": (5, 5, 30, 20)},
                    "SYNTH?TIC",
                    0.61,
                    self.runner_id,
                    gaps=("ambiguous_character",),
                ),
            )

    adapter = ImageAdapter((SyntheticOCR(),))
    first = adapter.analyze(_image())
    retry = adapter.analyze(_image())

    assert first == retry
    assert first.status == "analyzed"
    ocr = next(
        item for item in first.observations if item.modality == "ocr_derived"
    )
    assert ocr.confidence == 0.61
    assert ocr.gaps == ("ambiguous_character",)
    assert not ocr.event_proof
    assert not ocr.identity_proof


def test_image_adapter_rejects_claimed_event_or_identity_proof():
    with pytest.raises(ValueError, match="not event or identity proof"):
        ImageObservation(
            "visual_inference",
            {"region": (0, 0, 1, 1)},
            "synthetic person",
            0.5,
            "synthetic.vision:v1",
            event_proof=True,
        )
