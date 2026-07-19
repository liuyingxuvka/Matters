from __future__ import annotations

import pytest

from matters.providers.documents import (
    DocumentAdapter,
    DocumentAnchor,
    DocumentExtractionResult,
    DocumentSource,
)


def _source(**changes) -> DocumentSource:
    values = {
        "source_version_id": "source:synthetic:v1",
        "external_id": "synthetic.md",
        "media_type": "text/markdown",
        "content": b"first\nsecond",
        "tracking_disposition": "tracked",
    }
    values.update(changes)
    return DocumentSource(**values)


def test_plain_text_extraction_is_deterministic_and_precisely_anchored():
    adapter = DocumentAdapter()

    first = adapter.extract(_source())
    retry = adapter.extract(_source())

    assert first == retry
    assert first.status == "extracted"
    assert [anchor.text for anchor in first.anchors] == ["first", "second"]
    assert first.anchors[0].location == {
        "line_start": 1,
        "line_end": 1,
        "char_start": 0,
        "char_end": 5,
    }
    assert first.anchors[1].location["char_start"] == 6


def test_document_content_requires_tracking_and_unsupported_is_visible():
    adapter = DocumentAdapter()

    not_tracked = adapter.extract(
        _source(tracking_disposition="metadata_only")
    )
    unsupported = adapter.extract(
        _source(
            media_type="application/x-synthetic-unknown",
            external_id="synthetic.unknown",
        )
    )

    assert not_tracked.status == "not_tracked"
    assert unsupported.status == "unsupported"
    assert unsupported.gaps == ("safe_extractor_unavailable",)


def test_injected_spreadsheet_extractor_preserves_parent_and_range_anchor():
    class SpreadsheetExtractor:
        extractor_id = "synthetic.sheet:v1"
        media_types = frozenset(
            {"application/x-synthetic-spreadsheet"}
        )
        executes_active_content = False
        activates_external_data = False

        def extract(self, source, *, budget):
            return DocumentExtractionResult(
                "extracted",
                source.source_version_id,
                self.extractor_id,
                anchors=(
                    DocumentAnchor(
                        "sheet_range",
                        {"sheet": "Sheet1", "range": "A1:B2"},
                        "synthetic cells",
                    ),
                ),
                parent_source_version_id=source.parent_source_version_id,
            )

    adapter = DocumentAdapter((SpreadsheetExtractor(),))
    result = adapter.extract(
        _source(
            source_version_id="source:sheet:v1",
            external_id="synthetic.xlsx",
            media_type="application/x-synthetic-spreadsheet",
            parent_source_version_id="source:mail-attachment:v1",
        )
    )

    assert result.status == "extracted"
    assert result.extractor_id == "synthetic.sheet:v1"
    assert result.parent_source_version_id == "source:mail-attachment:v1"
    assert result.anchors[0].location["range"] == "A1:B2"


def test_active_content_or_external_data_extractors_are_rejected():
    class UnsafeExtractor:
        extractor_id = "synthetic.unsafe:v1"
        media_types = frozenset({"application/pdf"})
        executes_active_content = True
        activates_external_data = False

        def extract(self, source, *, budget):  # pragma: no cover
            raise AssertionError("unsafe extractor must never execute")

    with pytest.raises(ValueError, match="may not execute active content"):
        DocumentAdapter((UnsafeExtractor(),))
