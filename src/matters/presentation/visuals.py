"""C2/C3/C12 representative-visual assets and card display decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from matters.infrastructure.blobs.store import BlobStore
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.presentation.localization import DEFAULT_LOCALE_REGISTRY


ASSET_KINDS = frozenset({"photo", "existing_image", "document_preview"})
SELECTION_MODES = frozenset(
    {"user_override", "ai_recommendation", "deterministic_fallback", "placeholder"}
)
SAFE_IMAGE_MEDIA_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)


def _opaque(prefix: str, *parts: str, length: int = 32) -> str:
    digest = sha256("\0".join(parts).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}:{digest}"


@dataclass(frozen=True)
class VisualAsset:
    asset_id: str
    source_revision_id: str
    occurrence_id: str
    kind: str
    media_type: str
    original_blob_ref: str
    hero_blob_ref: str
    thumbnail_blob_ref: str
    preview_token: str
    width: int
    height: int
    current: bool
    display_allowed: bool
    evidence_ids: tuple[str, ...]
    localized_alt: Mapping[str, str]
    localized_reason: Mapping[str, str]
    derivation_id: str

    def __post_init__(self) -> None:
        if self.kind not in ASSET_KINDS:
            raise ValueError("unsupported visual asset kind")
        if self.media_type not in SAFE_IMAGE_MEDIA_TYPES:
            raise ValueError("unsafe visual media type")
        locales = set(DEFAULT_LOCALE_REGISTRY.available_locales)
        if set(self.localized_alt) != locales or set(self.localized_reason) != locales:
            raise ValueError("visual asset localization is incomplete")
        if min(self.width, self.height) < 1:
            raise ValueError("visual dimensions must be positive")


@dataclass(frozen=True)
class CardVisualDecision:
    matter_id: str
    decision_revision: int
    asset_id: str
    preview_token: str
    selection_mode: str
    status: str
    semantic_revision: str
    localized_alt: Mapping[str, str]
    localized_reason: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.selection_mode not in SELECTION_MODES:
            raise ValueError("unsupported visual selection mode")
        if self.status not in {"current", "stale", "missing"}:
            raise ValueError("unsupported visual decision status")


class VisualAssetOwner:
    """Persist private derivatives and publish path-free visual decisions."""

    def __init__(
        self,
        *,
        store: SQLiteStore,
        blob_store: BlobStore,
    ) -> None:
        self.store = store
        self.blobs = blob_store

    @staticmethod
    def _localized(en: str, zh_cn: str) -> dict[str, str]:
        return {"en": en, "zh-CN": zh_cn}

    @staticmethod
    def _encode(image: Image.Image, *, size: tuple[int, int]) -> bytes:
        normalized = ImageOps.exif_transpose(image).convert("RGB")
        normalized.thumbnail(size, Image.Resampling.LANCZOS)
        output = BytesIO()
        normalized.save(
            output,
            format="JPEG",
            quality=86,
            optimize=True,
            progressive=True,
        )
        return output.getvalue()

    def register_image(
        self,
        *,
        source_revision_id: str,
        occurrence_id: str,
        content: bytes,
        media_type: str,
        evidence_ids: Sequence[str] = (),
        photo: bool = True,
    ) -> VisualAsset:
        if media_type not in SAFE_IMAGE_MEDIA_TYPES:
            raise ValueError("browser-safe image media type required")
        try:
            with Image.open(BytesIO(content)) as opened:
                opened.verify()
            with Image.open(BytesIO(content)) as opened:
                width, height = opened.size
                hero = self._encode(opened, size=(1440, 900))
            with Image.open(BytesIO(content)) as opened:
                thumbnail = self._encode(opened, size=(720, 450))
        except (OSError, UnidentifiedImageError) as exc:
            raise ValueError("image content is not decodable") from exc
        original_ref = self.blobs.put(content)
        hero_ref = self.blobs.put(hero)
        thumbnail_ref = self.blobs.put(thumbnail)
        kind = "photo" if photo else "existing_image"
        asset_id = _opaque(
            "visual",
            source_revision_id,
            occurrence_id,
            kind,
            original_ref,
        )
        token = _opaque("preview", asset_id, thumbnail_ref, length=40)
        asset = VisualAsset(
            asset_id=asset_id,
            source_revision_id=source_revision_id,
            occurrence_id=occurrence_id,
            kind=kind,
            media_type="image/jpeg",
            original_blob_ref=original_ref,
            hero_blob_ref=hero_ref,
            thumbnail_blob_ref=thumbnail_ref,
            preview_token=token,
            width=int(width),
            height=int(height),
            current=True,
            display_allowed=True,
            evidence_ids=tuple(dict.fromkeys(str(item) for item in evidence_ids)),
            localized_alt=self._localized(
                "Representative source image",
                "来源中的代表图片",
            ),
            localized_reason=self._localized(
                "Selected from an authorized image source",
                "选自已授权的图片来源",
            ),
            derivation_id="matters.visual.image-derivative:v1",
        )
        self._persist_asset(asset)
        return asset

    def register_document_preview(
        self,
        *,
        source_revision_id: str,
        occurrence_id: str,
        title: str,
        text: str,
        evidence_ids: Sequence[str] = (),
    ) -> VisualAsset:
        """Render a bounded excerpt from real document evidence as a safe preview."""

        normalized_title = " ".join(title.split())[:80] or "Document"
        normalized_text = "\n".join(
            line.strip()[:96] for line in text.splitlines() if line.strip()
        )[:900]
        canvas = Image.new("RGB", (1200, 750), "#f4f1e9")
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle(
            (38, 28, 1162, 722),
            radius=18,
            fill="#ffffff",
            outline="#d8d2c5",
            width=2,
        )
        try:
            title_font = ImageFont.truetype("DejaVuSans.ttf", 38)
            body_font = ImageFont.truetype("DejaVuSans.ttf", 24)
        except OSError:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
        draw.text((72, 58), normalized_title, font=title_font, fill="#242424")
        for index, line in enumerate(normalized_text.splitlines()[:10]):
            draw.text(
                (72, 126 + index * 42),
                line,
                font=body_font,
                fill="#242424",
            )
        draw.rounded_rectangle(
            (72, 668, 282, 678),
            radius=5,
            fill="#dc2626",
        )
        original = BytesIO()
        canvas.save(original, format="PNG", optimize=True)
        hero = self._encode(canvas, size=(1440, 900))
        thumbnail = self._encode(canvas, size=(720, 450))
        original_ref = self.blobs.put(original.getvalue())
        hero_ref = self.blobs.put(hero)
        thumbnail_ref = self.blobs.put(thumbnail)
        asset_id = _opaque(
            "visual",
            source_revision_id,
            occurrence_id,
            "document_preview",
            original_ref,
        )
        token = _opaque("preview", asset_id, thumbnail_ref, length=40)
        asset = VisualAsset(
            asset_id=asset_id,
            source_revision_id=source_revision_id,
            occurrence_id=occurrence_id,
            kind="document_preview",
            media_type="image/jpeg",
            original_blob_ref=original_ref,
            hero_blob_ref=hero_ref,
            thumbnail_blob_ref=thumbnail_ref,
            preview_token=token,
            width=1200,
            height=750,
            current=True,
            display_allowed=True,
            evidence_ids=tuple(dict.fromkeys(str(item) for item in evidence_ids)),
            localized_alt=self._localized(
                f"Preview of {normalized_title}",
                f"{normalized_title} 的文档预览",
            ),
            localized_reason=self._localized(
                "Generated from the document's anchored text",
                "根据文档中已定位的文字生成",
            ),
            derivation_id="matters.visual.document-preview:v1",
        )
        self._persist_asset(asset)
        return asset

    def _persist_asset(self, asset: VisualAsset) -> None:
        self.store.append(
            "visual_asset",
            asset.asset_id,
            self.store.next_revision("visual_asset", asset.asset_id),
            asdict(asset),
        )
        self.store.append(
            "visual_preview_token",
            asset.preview_token,
            self.store.next_revision("visual_preview_token", asset.preview_token),
            {
                "preview_token": asset.preview_token,
                "asset_id": asset.asset_id,
                "thumbnail_blob_ref": asset.thumbnail_blob_ref,
                "hero_blob_ref": asset.hero_blob_ref,
                "media_type": asset.media_type,
                "current": asset.current,
                "display_allowed": asset.display_allowed,
            },
        )

    def assets_for_occurrence(self, occurrence_id: str) -> tuple[VisualAsset, ...]:
        assets = []
        for payload in self.store.iter_current("visual_asset"):
            if str(payload.get("occurrence_id")) != occurrence_id:
                continue
            asset = VisualAsset(**dict(payload))
            if asset.current and asset.display_allowed:
                assets.append(asset)
        return tuple(sorted(assets, key=lambda item: item.asset_id))

    def decide(
        self,
        *,
        matter_id: str,
        semantic_revision: str,
        occurrence_ids: Sequence[str] = (),
        recommended_asset_id: str = "",
    ) -> CardVisualDecision:
        prior_override = self.store.current("card_visual_override", matter_id)
        allowed = tuple(
            asset
            for occurrence_id in occurrence_ids
            for asset in self.assets_for_occurrence(occurrence_id)
        )
        by_id = {asset.asset_id: asset for asset in allowed}
        selected: VisualAsset | None = None
        mode = "placeholder"
        if prior_override and bool(prior_override.get("active", False)):
            selected = by_id.get(str(prior_override.get("asset_id", "")))
            mode = "user_override" if selected is not None else "placeholder"
        if selected is None and recommended_asset_id:
            selected = by_id.get(recommended_asset_id)
            mode = "ai_recommendation" if selected is not None else "placeholder"
        if selected is None and allowed:
            priority = {"photo": 0, "existing_image": 1, "document_preview": 2}
            selected = sorted(
                allowed,
                key=lambda asset: (priority[asset.kind], asset.asset_id),
            )[0]
            mode = "deterministic_fallback"
        revision = self.store.next_revision("card_visual_decision", matter_id)
        if selected is None:
            decision = CardVisualDecision(
                matter_id=matter_id,
                decision_revision=revision,
                asset_id="",
                preview_token="",
                selection_mode="placeholder",
                status="missing",
                semantic_revision=semantic_revision,
                localized_alt=self._localized(
                    "No representative image is available",
                    "暂无可用的代表图片",
                ),
                localized_reason=self._localized(
                    "No current authorized visual candidate was found",
                    "没有找到当前且已授权的视觉候选",
                ),
            )
        else:
            decision = CardVisualDecision(
                matter_id=matter_id,
                decision_revision=revision,
                asset_id=selected.asset_id,
                preview_token=selected.preview_token,
                selection_mode=mode,
                status="current",
                semantic_revision=semantic_revision,
                localized_alt=dict(selected.localized_alt),
                localized_reason=dict(selected.localized_reason),
            )
        self.store.append(
            "card_visual_decision",
            matter_id,
            revision,
            asdict(decision),
        )
        return decision

    def set_override(
        self,
        *,
        matter_id: str,
        asset_id: str,
        active: bool,
        rationale: str,
    ) -> CardVisualDecision:
        asset_payload = self.store.current("visual_asset", asset_id) if asset_id else None
        if active and (
            asset_payload is None
            or not bool(asset_payload.get("current", False))
            or not bool(asset_payload.get("display_allowed", False))
        ):
            raise ValueError("cover override requires a current allowed asset")
        revision = self.store.next_revision("card_visual_override", matter_id)
        self.store.append(
            "card_visual_override",
            matter_id,
            revision,
            {
                "matter_id": matter_id,
                "asset_id": asset_id,
                "active": active,
                "rationale": rationale,
                "revision": revision,
            },
        )
        projection = self.store.current("projection", matter_id) or {}
        occurrence_ids = tuple(
            row["object_id"]
            for row in self.store.iter_current("object_coverage")
            if matter_id in row.get("matter_ids", ())
        )
        return self.decide(
            matter_id=matter_id,
            semantic_revision=str(
                projection.get("semantic_revision", f"matter:{matter_id}")
            ),
            occurrence_ids=occurrence_ids,
        )

    def resolve(self, preview_token: str, *, hero: bool = False) -> tuple[bytes, str]:
        payload = self.store.current("visual_preview_token", preview_token)
        if not payload or not bool(payload.get("current", False)):
            raise KeyError("visual preview is unavailable")
        if not bool(payload.get("display_allowed", False)):
            raise PermissionError("visual preview is not allowed for display")
        blob_ref = str(
            payload["hero_blob_ref"] if hero else payload["thumbnail_blob_ref"]
        )
        return self.blobs.get(blob_ref), str(payload["media_type"])


__all__ = [
    "ASSET_KINDS",
    "CardVisualDecision",
    "SAFE_IMAGE_MEDIA_TYPES",
    "SELECTION_MODES",
    "VisualAsset",
    "VisualAssetOwner",
]
