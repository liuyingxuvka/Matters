"""Pure extraction helpers; they never admit evidence or canonical state."""

from __future__ import annotations

from typing import Any, Mapping


def source_assertions(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    assertions: list[dict[str, Any]] = []
    summary = payload.get("summary")
    if summary:
        assertions.append(
            {
                "text": str(summary),
                "anchor": {"field": "summary"},
                "modality": "reported",
            }
        )
    resolution = payload.get("resolution")
    if resolution:
        assertions.append(
            {
                "text": str(resolution),
                "anchor": {"field": "resolution"},
                "modality": "reported",
            }
        )
    for index, comment in enumerate(payload.get("comments", ())):
        if isinstance(comment, Mapping) and comment.get("body"):
            assertions.append(
                {
                    "text": str(comment["body"]),
                    "anchor": {"field": "comments", "index": index},
                    "modality": "reported",
                    "language": str(comment.get("language", "")),
                }
            )
    for index, attachment in enumerate(payload.get("attachments", ())):
        if not isinstance(attachment, Mapping):
            continue
        region = attachment.get("region") or attachment.get("ocr_region")
        if region:
            assertions.append(
                {
                    "text": str(
                        attachment.get("ocr_text")
                        or attachment.get("name")
                        or "attachment region"
                    ),
                    "anchor": {
                        "field": "attachments",
                        "index": index,
                        "region": list(region),
                        "page": attachment.get("page"),
                    },
                    "modality": "observed",
                }
            )
        elif attachment.get("content_hash"):
            assertions.append(
                {
                    "text": str(attachment.get("name") or "result attachment"),
                    "anchor": {
                        "field": "attachments",
                        "index": index,
                        "content_hash": str(attachment["content_hash"]),
                    },
                    "modality": "observed",
                }
            )
    return tuple(assertions)


__all__ = ["source_assertions"]
