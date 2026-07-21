"""Private source-image derivatives for the Images evidence gallery."""

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


class VisualAssetOwner:
    """Persist path-free derivatives of authorized source images."""

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
        # The authorized source image remains at its provider.  Only
        # presentation derivatives are stored in MATTERS_HOME.
        original_ref = (
            "external-original:sha256:" + sha256(content).hexdigest()
        )
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
                "Related source image",
                "相关来源图片",
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
        """Render an internal document derivative without admitting it as a photo."""

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
            display_allowed=False,
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

    def retire_document_previews_from_gallery(self) -> int:
        """Remove legacy text/document screenshots from the Images projection."""

        retired = 0
        for payload in self.store.iter_current("visual_asset"):
            if (
                str(payload.get("kind", "")) != "document_preview"
                or not bool(payload.get("display_allowed", False))
            ):
                continue
            asset_id = str(payload.get("asset_id", ""))
            token = str(payload.get("preview_token", ""))
            if not asset_id:
                continue
            next_asset = dict(payload)
            next_asset["display_allowed"] = False
            self.store.append(
                "visual_asset",
                asset_id,
                self.store.next_revision("visual_asset", asset_id),
                next_asset,
            )
            if token:
                token_payload = self.store.current("visual_preview_token", token)
                if token_payload:
                    next_token = dict(token_payload)
                    next_token["display_allowed"] = False
                    self.store.append(
                        "visual_preview_token",
                        token,
                        self.store.next_revision("visual_preview_token", token),
                        next_token,
                    )
            retired += 1
        return retired

    def assets_for_occurrence(self, occurrence_id: str) -> tuple[VisualAsset, ...]:
        assets = []
        for payload in self.store.iter_current("visual_asset"):
            if str(payload.get("occurrence_id")) != occurrence_id:
                continue
            asset = VisualAsset(**dict(payload))
            if asset.current and asset.display_allowed:
                assets.append(asset)
        return tuple(sorted(assets, key=lambda item: item.asset_id))

    def retire_legacy_card_visual_authority(self) -> int:
        """Deactivate legacy card-visual rows during direct replacement."""

        retired = 0
        for payload in self.store.list_current("card_visual_override"):
            if not bool(payload.get("active", False)):
                continue
            matter_id = str(payload.get("matter_id", ""))
            if not matter_id:
                continue
            revision = self.store.next_revision(
                "card_visual_override",
                matter_id,
            )
            self.store.append(
                "card_visual_override",
                matter_id,
                revision,
                {
                    "matter_id": matter_id,
                    "asset_id": "",
                    "active": False,
                    "rationale": "ordinary_change_cover_path_retired",
                    "revision": revision,
                },
            )
            retired += 1
        for payload in self.store.list_current("card_visual_decision"):
            if str(payload.get("status", "")) == "retired":
                continue
            matter_id = str(payload.get("matter_id", ""))
            if not matter_id:
                continue
            revision = self.store.next_revision(
                "card_visual_decision",
                matter_id,
            )
            self.store.append(
                "card_visual_decision",
                matter_id,
                revision,
                {
                    "matter_id": matter_id,
                    "status": "retired",
                    "revision": revision,
                    "rationale": "generated_hero_direct_replacement",
                },
            )
            retired += 1
        return retired

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
    "SAFE_IMAGE_MEDIA_TYPES",
    "VisualAsset",
    "VisualAssetOwner",
]
