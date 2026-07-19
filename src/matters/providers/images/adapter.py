"""Metadata-first image inventory with injectable OCR/vision runners."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol


IMAGE_STATUSES = frozenset(
    {
        "metadata_only",
        "analyzed",
        "partial",
        "not_tracked",
        "unsupported",
        "resource_exhausted",
    }
)
IMAGE_MODALITIES = frozenset(
    {
        "metadata_derived",
        "exif_derived",
        "ocr_derived",
        "visual_inference",
    }
)


@dataclass(frozen=True)
class ImageBudget:
    max_bytes: int = 32 * 1024 * 1024
    max_pixels: int = 40_000_000
    max_observations: int = 10_000

    def __post_init__(self) -> None:
        if min(self.max_bytes, self.max_pixels, self.max_observations) < 1:
            raise ValueError("image analysis budgets must be positive")


@dataclass(frozen=True)
class ImageSource:
    source_version_id: str
    external_id: str
    media_type: str
    width: int
    height: int
    metadata: Mapping[str, object]
    tracking_disposition: str
    content: bytes | None = None

    def __post_init__(self) -> None:
        if not self.source_version_id or not self.external_id or not self.media_type:
            raise ValueError(
                "source_version_id, external_id, and media_type are required"
            )
        if self.width < 0 or self.height < 0:
            raise ValueError("image dimensions cannot be negative")
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.content is not None:
            object.__setattr__(self, "content", bytes(self.content))


@dataclass(frozen=True)
class ImageObservation:
    modality: str
    anchor: Mapping[str, object]
    text: str
    confidence: float
    runner_id: str
    gaps: tuple[str, ...] = ()
    event_proof: bool = False
    identity_proof: bool = False

    def __post_init__(self) -> None:
        if self.modality not in IMAGE_MODALITIES:
            raise ValueError(f"unsupported image modality: {self.modality}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("image confidence must be between 0 and 1")
        if self.event_proof or self.identity_proof:
            raise ValueError(
                "image adapter observations are candidates, not event or identity proof"
            )
        anchor = dict(self.anchor)
        if "metadata_field" not in anchor and "region" not in anchor:
            raise ValueError(
                "image observation requires a metadata field or pixel region"
            )
        object.__setattr__(self, "anchor", anchor)
        object.__setattr__(self, "gaps", tuple(self.gaps))


@dataclass(frozen=True)
class ImageAnalysisResult:
    status: str
    source_version_id: str
    observations: tuple[ImageObservation, ...] = ()
    gaps: tuple[str, ...] = ()
    runner_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in IMAGE_STATUSES:
            raise ValueError(f"unsupported image status: {self.status}")
        object.__setattr__(self, "observations", tuple(self.observations))
        object.__setattr__(self, "gaps", tuple(self.gaps))
        object.__setattr__(self, "runner_ids", tuple(self.runner_ids))


class ImageRunner(Protocol):
    """A versioned OCR or vision runner injected by the private runtime."""

    runner_id: str
    modalities: frozenset[str]

    def analyze(
        self,
        source: ImageSource,
        *,
        budget: ImageBudget,
    ) -> Sequence[ImageObservation]:
        """Return bounded observations for exactly this source."""


class ImageAdapter:
    """Preserve metadata/OCR/visual modalities and uncertainty separately."""

    provider_id = "images"

    def __init__(
        self,
        runners: Sequence[ImageRunner] = (),
        *,
        budget: ImageBudget | None = None,
    ):
        self._budget = budget or ImageBudget()
        seen_ids: set[str] = set()
        validated: list[ImageRunner] = []
        for runner in runners:
            if not runner.runner_id or runner.runner_id in seen_ids:
                raise ValueError("image runner ids must be unique and non-empty")
            if not runner.modalities or not runner.modalities.issubset(
                {"ocr_derived", "visual_inference"}
            ):
                raise ValueError("image runner modalities must be OCR or visual")
            seen_ids.add(runner.runner_id)
            validated.append(runner)
        self._runners = tuple(validated)

    @staticmethod
    def _metadata_observations(
        source: ImageSource,
    ) -> tuple[ImageObservation, ...]:
        observations: list[ImageObservation] = []
        for key in sorted(source.metadata):
            value = source.metadata[key]
            modality = (
                "exif_derived"
                if str(key).casefold().startswith("exif")
                else "metadata_derived"
            )
            observations.append(
                ImageObservation(
                    modality=modality,
                    anchor={"metadata_field": str(key)},
                    text=str(value),
                    confidence=1.0,
                    runner_id="matters.image-metadata:v1",
                    gaps=(
                        "metadata_does_not_prove_event_or_identity",
                    ),
                )
            )
        return tuple(observations)

    def inventory(self, source: ImageSource) -> ImageAnalysisResult:
        """Inventory metadata without requiring or reading image bytes."""

        return ImageAnalysisResult(
            "metadata_only",
            source.source_version_id,
            observations=self._metadata_observations(source),
            gaps=("pixel_content_not_assessed",),
            runner_ids=("matters.image-metadata:v1",),
        )

    def _validate_region(
        self,
        source: ImageSource,
        observation: ImageObservation,
    ) -> None:
        if "region" not in observation.anchor:
            return
        region = observation.anchor["region"]
        if (
            not isinstance(region, (tuple, list))
            or len(region) != 4
            or any(not isinstance(value, int) for value in region)
        ):
            raise ValueError("image region must be four integer coordinates")
        left, top, right, bottom = region
        if not (
            0 <= left < right <= source.width
            and 0 <= top < bottom <= source.height
        ):
            raise ValueError("image region lies outside the source dimensions")

    def analyze(self, source: ImageSource) -> ImageAnalysisResult:
        if source.tracking_disposition != "tracked":
            return ImageAnalysisResult(
                "not_tracked",
                source.source_version_id,
                gaps=("current_tracked_disposition_required",),
            )
        if source.content is None:
            return ImageAnalysisResult(
                "metadata_only",
                source.source_version_id,
                observations=self._metadata_observations(source),
                gaps=("stable_image_content_unavailable",),
                runner_ids=("matters.image-metadata:v1",),
            )
        if len(source.content) > self._budget.max_bytes:
            return ImageAnalysisResult(
                "resource_exhausted",
                source.source_version_id,
                observations=self._metadata_observations(source),
                gaps=("image_byte_budget_exceeded",),
                runner_ids=("matters.image-metadata:v1",),
            )
        if source.width * source.height > self._budget.max_pixels:
            return ImageAnalysisResult(
                "resource_exhausted",
                source.source_version_id,
                observations=self._metadata_observations(source),
                gaps=("image_pixel_budget_exceeded",),
                runner_ids=("matters.image-metadata:v1",),
            )
        if not self._runners:
            return ImageAnalysisResult(
                "unsupported",
                source.source_version_id,
                observations=self._metadata_observations(source),
                gaps=("ocr_or_visual_runner_unavailable",),
                runner_ids=("matters.image-metadata:v1",),
            )

        observations = list(self._metadata_observations(source))
        runner_ids = ["matters.image-metadata:v1"]
        gaps: list[str] = []
        for runner in self._runners:
            runner_ids.append(runner.runner_id)
            try:
                returned = tuple(
                    runner.analyze(source, budget=self._budget)
                )
            except Exception:
                gaps.append(f"image_runner_failed:{runner.runner_id}")
                break
            if len(observations) + len(returned) > self._budget.max_observations:
                gaps.append("image_observation_budget_exceeded")
                remaining = self._budget.max_observations - len(observations)
                returned = returned[: max(0, remaining)]
            for observation in returned:
                if observation.runner_id != runner.runner_id:
                    raise ValueError("image runner identity changed during analysis")
                if observation.modality not in runner.modalities:
                    raise ValueError("image runner returned an undeclared modality")
                self._validate_region(source, observation)
                observations.append(observation)
            if gaps:
                break
        return ImageAnalysisResult(
            "partial" if gaps else "analyzed",
            source.source_version_id,
            observations=tuple(observations),
            gaps=tuple(gaps),
            runner_ids=tuple(runner_ids),
        )


__all__ = [
    "IMAGE_MODALITIES",
    "IMAGE_STATUSES",
    "ImageAdapter",
    "ImageAnalysisResult",
    "ImageBudget",
    "ImageObservation",
    "ImageRunner",
    "ImageSource",
]
