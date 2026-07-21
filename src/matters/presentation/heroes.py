"""Private generated-hero runtime shared by the C11 and C12 boundaries.

C11 owns the private generation brief, runner result, immutable bytes, and
opaque token registry.  C12 consumes :class:`GeneratedHeroRecord` through
``GeneratedHeroProjectionOwner`` and remains the only publisher of the visible
hero disposition.

Generated heroes are presentation artifacts.  This module deliberately does
not import or write SourceVersion, EvidenceAnchor, visual-gallery, or canonical
Matter owners.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
import re
from secrets import token_hex
from typing import Any, Mapping, Sequence

from PIL import Image, UnidentifiedImageError

from matters.infrastructure.blobs.store import BlobStore
from matters.infrastructure.sqlite.store import SQLiteStore
from matters.presentation.localization import DEFAULT_LOCALE_REGISTRY


HERO_STATUSES = frozenset(
    {
        "generated_current",
        "generation_pending_placeholder",
        "generation_blocked_placeholder",
    }
)
HERO_INVALIDATION_REASONS = frozenset(
    {
        "identity",
        "topic",
        "theme",
        "merge",
        "split",
        "reparent",
        "permission",
        "safety",
        "policy",
        "quality",
    }
)
HERO_BLOCKING_INVALIDATIONS = frozenset({"permission", "safety", "policy"})
HERO_OBJECT_KINDS = frozenset(
    {
        "matter",
        "work_item",
        "event",
        "source",
        "source_version",
        "quick_view",
    }
)
HERO_ELIGIBILITY_DISPOSITIONS = frozenset({"eligible", "not_applicable"})
HERO_GENERATION_POLICY_REVISION = (
    "hero-generation-policy:4-photoreal-two-cue-documentary"
)
HERO_BRIEF_CONTRACT_REVISION = (
    "hero-brief:v4-photoreal-two-cue-documentary"
)
SAFE_GENERATED_MEDIA_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
MAX_GENERATED_ASSET_BYTES = 20 * 1024 * 1024
MAX_GENERATED_DIMENSION = 8192
TRANSIENT_FAILURE_KINDS = frozenset(
    {"capability_unavailable", "generation_failed", "runner_interrupted"}
)
BLOCKING_FAILURE_KINDS = frozenset(
    {
        "permission_denied",
        "policy_blocked",
        "retry_exhausted",
        "schema_invalid",
        "unsafe_output",
    }
)

_DRIVE_PATH = re.compile(r"(?i)\b[a-z]:[\\/]")
_EMAIL_ADDRESS = re.compile(
    r"(?i)\b[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-z0-9-]+(?:\.[a-z0-9-]+)+\b"
)
_URL = re.compile(r"(?i)\b(?:https?|file)://")
_PRIVATE_ID_SHAPE = re.compile(
    r"(?i)(?:\b[0-9a-f]{8}-[0-9a-f-]{27,}\b|"
    r"\b(?:id|token|account|booking|order|message)[-_:# ]*[a-z0-9_-]{4,}\b)"
)
_DIGIT = re.compile(r"\d")
_FORBIDDEN_CONCEPT_WORDS = re.compile(
    r"(?i)\b(?:"
    r"address|brand|caption|email|face|gmail|identifier|inbox|label|"
    r"lettering|logo|mailbox|message|name|path|person|portrait|"
    r"private|quote|screenshot|subject|text|trademark|word"
    r")\b"
)
_FORBIDDEN_CONCEPT_FRAGMENTS = (
    "地址",
    "标识符",
    "编号",
    "电子邮件",
    "截图",
    "姓名",
    "人名",
    "人物",
    "真人",
    "肖像",
    "路径",
    "邮件",
    "正文",
    "文字",
    "文本",
    "品牌",
    "商标",
    "标志",
)
_FORBIDDEN_ALT_STYLE_WORDS = re.compile(
    r"(?i)\b(?:"
    r"abstract|concept|conceptual|diagram|illustration|illustrative|"
    r"infographic|isometric|metaphor|poster|render|surreal|vector"
    r")\b"
)
_FORBIDDEN_ALT_STYLE_FRAGMENTS = (
    "抽象",
    "概念",
    "插画",
    "插图",
    "示意图",
    "信息图",
    "等距",
    "海报",
    "渲染图",
    "超现实",
    "矢量",
    "隐喻",
)

_PENDING_ALT = {
    "en": "A documentary-style Matter photo is being prepared",
    "zh-CN": "事项纪实风格照片正在生成",
}
_BLOCKED_ALT = {
    "en": "The documentary-style Matter photo is temporarily unavailable",
    "zh-CN": "事项纪实风格照片暂时不可用",
}


class HeroIneligibleError(ValueError):
    """Raised when any non-root-Matter object requests a hero."""


class HeroPrivacyError(ValueError):
    """Raised when a brief or generated output violates the privacy contract."""


class HeroTransitionError(ValueError):
    """Raised when a result does not match the current generation state."""


class HeroStyleError(ValueError):
    """Raised when a generated result violates the photographic style contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _fingerprint(*parts: Any) -> str:
    digest = sha256(
        "\0".join(
            item if isinstance(item, str) else _canonical_json(item)
            for item in parts
        ).encode("utf-8")
    ).hexdigest()
    return "sha256:" + digest


def _localized(
    values: Mapping[str, str],
    *,
    field_name: str,
) -> dict[str, str]:
    available = DEFAULT_LOCALE_REGISTRY.available_locales
    normalized = {
        str(locale): " ".join(str(value).split())
        for locale, value in values.items()
        if str(locale)
    }
    if set(normalized) != set(available):
        raise ValueError(
            f"{field_name} requires exactly " + ", ".join(available)
        )
    if any(not normalized[locale] for locale in available):
        raise ValueError(f"{field_name} values must be non-empty")
    return {locale: normalized[locale] for locale in available}


def _privacy_problem(value: str, *, allow_digits: bool = False) -> str:
    if not value.strip():
        return "empty"
    if "\\" in value or "/" in value or _DRIVE_PATH.search(value):
        return "path"
    if "@" in value or _EMAIL_ADDRESS.search(value):
        return "email"
    if _URL.search(value):
        return "url"
    if _PRIVATE_ID_SHAPE.search(value):
        return "private_identifier"
    if not allow_digits and _DIGIT.search(value):
        return "literal_identifier"
    if _FORBIDDEN_CONCEPT_WORDS.search(value):
        return "forbidden_literal"
    if any(fragment in value for fragment in _FORBIDDEN_CONCEPT_FRAGMENTS):
        return "forbidden_literal"
    return ""


def _alt_style_problem(value: str) -> str:
    if _FORBIDDEN_ALT_STYLE_WORDS.search(value):
        return "non-photographic style language"
    if any(fragment in value for fragment in _FORBIDDEN_ALT_STYLE_FRAGMENTS):
        return "non-photographic style language"
    return ""


def _concepts(
    values: Sequence[str],
    *,
    field_name: str,
) -> tuple[str, ...]:
    normalized = tuple(
        dict.fromkeys(" ".join(str(value).strip().split()).casefold() for value in values)
    )
    if not normalized or len(normalized) > 8:
        raise HeroPrivacyError(
            f"{field_name} requires between one and eight abstract concepts"
        )
    for value in normalized:
        if len(value) > 48:
            raise HeroPrivacyError(f"{field_name} concept is too detailed")
        problem = _privacy_problem(value)
        if problem:
            raise HeroPrivacyError(
                f"{field_name} contains prohibited {problem} content"
            )
    return normalized


def _normalized_image(content: bytes, media_type: str) -> bytes:
    if not content or len(content) > MAX_GENERATED_ASSET_BYTES:
        raise ValueError("generated hero image size is invalid")
    if media_type not in SAFE_GENERATED_MEDIA_TYPES:
        raise ValueError("generated hero requires a browser-safe image type")
    expected_formats = {
        "image/jpeg": {"JPEG"},
        "image/png": {"PNG"},
        "image/webp": {"WEBP"},
    }
    try:
        with Image.open(BytesIO(content)) as opened:
            opened.verify()
        with Image.open(BytesIO(content)) as opened:
            width, height = opened.size
            if (
                min(width, height) < 1
                or max(width, height) > MAX_GENERATED_DIMENSION
            ):
                raise ValueError("generated hero dimensions are invalid")
            if str(opened.format or "").upper() not in expected_formats[media_type]:
                raise ValueError("generated hero media type does not match its bytes")
            normalized = opened.convert(
                "RGBA" if media_type in {"image/png", "image/webp"} else "RGB"
            )
            output = BytesIO()
            if media_type == "image/jpeg":
                normalized.save(output, format="JPEG", quality=90, optimize=True)
            elif media_type == "image/webp":
                normalized.save(output, format="WEBP", quality=90, method=6)
            else:
                normalized.save(output, format="PNG", optimize=True)
            return output.getvalue()
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("generated hero bytes are not a decodable image") from exc


@dataclass(frozen=True)
class HeroSubject:
    """C6/C12-owned eligibility and stability inputs for one object."""

    object_id: str
    object_kind: str
    semantic_identity_id: str
    topic_concepts: tuple[str, ...]
    theme_concepts: tuple[str, ...]
    hierarchy_revision: str
    is_root: bool = False
    independently_openable: bool = False
    identity_current: bool = True
    hierarchy_current: bool = True
    merge_disposition_current: bool = True
    permission_disposition: str = "allowed"
    safety_disposition: str = "allowed"
    generation_policy_revision: str = HERO_GENERATION_POLICY_REVISION
    contains_source_excerpt: bool = False
    contains_literal_text: bool = False
    contains_logo_or_brand: bool = False
    contains_private_identifier: bool = False
    contains_path: bool = False
    contains_email_body: bool = False
    contains_identifiable_real_people: bool = False

    def __post_init__(self) -> None:
        if not self.object_id or self.object_kind not in HERO_OBJECT_KINDS:
            raise ValueError("hero subject identity and supported object kind are required")
        if not self.semantic_identity_id or not self.hierarchy_revision:
            raise ValueError("semantic identity and hierarchy revision are required")
        if self.permission_disposition not in {"allowed", "blocked"}:
            raise ValueError("unsupported hero permission disposition")
        if self.safety_disposition not in {"allowed", "blocked"}:
            raise ValueError("unsupported hero safety disposition")
        if not self.generation_policy_revision:
            raise ValueError("hero generation policy revision is required")
        if self.generation_policy_revision != HERO_GENERATION_POLICY_REVISION:
            raise ValueError(
                "unsupported stale hero generation policy revision"
            )
        object.__setattr__(
            self,
            "topic_concepts",
            _concepts(self.topic_concepts, field_name="topic"),
        )
        object.__setattr__(
            self,
            "theme_concepts",
            _concepts(self.theme_concepts, field_name="theme"),
        )
        forbidden_flags = {
            "source_excerpt": self.contains_source_excerpt,
            "literal_text": self.contains_literal_text,
            "logo_or_brand": self.contains_logo_or_brand,
            "private_identifier": self.contains_private_identifier,
            "path": self.contains_path,
            "email_body": self.contains_email_body,
            "identifiable_real_people": self.contains_identifiable_real_people,
        }
        present = tuple(name for name, active in forbidden_flags.items() if active)
        if present:
            raise HeroPrivacyError(
                "hero brief input contains prohibited private content: "
                + ", ".join(present)
            )

    @property
    def eligibility_disposition(self) -> str:
        disposition = (
            "eligible"
            if self.object_kind == "matter" and self.is_root
            else "not_applicable"
        )
        if disposition not in HERO_ELIGIBILITY_DISPOSITIONS:
            raise AssertionError("unsupported hero eligibility disposition")
        return disposition

    @property
    def eligible(self) -> bool:
        return self.eligibility_disposition == "eligible"

    @property
    def ready(self) -> bool:
        return (
            self.eligible
            and self.identity_current
            and self.hierarchy_current
            and self.merge_disposition_current
            and self.permission_disposition == "allowed"
            and self.safety_disposition == "allowed"
        )


@dataclass(frozen=True)
class HeroGenerationBrief:
    """The only minimized payload that may be sent to an image generator."""

    topic_concepts: tuple[str, ...]
    theme_concepts: tuple[str, ...]
    style: str
    negative_constraints: tuple[str, ...]
    brief_fingerprint: str

    def provider_payload(self) -> dict[str, object]:
        return {
            "topic_concepts": list(self.topic_concepts),
            "theme_concepts": list(self.theme_concepts),
            "style": self.style,
            "negative_constraints": list(self.negative_constraints),
        }


@dataclass(frozen=True)
class GeneratedHeroRecord:
    """Private C11 generation state; never a Source or evidence value."""

    matter_id: str
    generation_revision: int
    status: str
    semantic_identity_fingerprint: str
    topic_fingerprint: str
    theme_fingerprint: str
    hierarchy_fingerprint: str
    permission_fingerprint: str
    safety_fingerprint: str
    policy_fingerprint: str
    brief_fingerprint: str
    brief_payload: Mapping[str, Any]
    runner_contract_id: str
    execution_identity: str
    private_asset_token: str
    private_blob_ref: str
    media_type: str
    localized_alt: Mapping[str, str]
    safety_disposition: str
    attempt: int = 0
    max_attempts: int = 3
    retryable: bool = True
    failure_kind: str = ""
    invalidated_by: str = ""

    def __post_init__(self) -> None:
        if not self.matter_id or self.generation_revision < 1:
            raise ValueError("hero record identity and revision are required")
        if self.status not in HERO_STATUSES:
            raise ValueError("unsupported generated hero status")
        if self.attempt < 0 or self.max_attempts < 1 or self.attempt > self.max_attempts:
            raise ValueError("generated hero attempt bounds are invalid")
        if self.invalidated_by and self.invalidated_by not in HERO_INVALIDATION_REASONS:
            raise ValueError("unsupported generated hero invalidation reason")
        localized_alt = _localized(self.localized_alt, field_name="localized_alt")
        object.__setattr__(self, "localized_alt", localized_alt)
        object.__setattr__(self, "brief_payload", dict(self.brief_payload))
        if self.status == "generated_current":
            required = (
                self.brief_fingerprint,
                self.runner_contract_id,
                self.execution_identity,
                self.private_asset_token,
                self.private_blob_ref,
                self.media_type,
            )
            if any(not value for value in required):
                raise ValueError("current generated hero is missing private asset identity")
            if self.media_type not in SAFE_GENERATED_MEDIA_TYPES:
                raise ValueError("unsupported generated hero media type")
            if self.safety_disposition != "allowed":
                raise ValueError("current generated hero requires allowed safety")
        elif self.private_asset_token or self.private_blob_ref:
            raise ValueError("temporary hero placeholders cannot expose an asset")


@dataclass(frozen=True)
class GeneratedHeroProjection:
    """C12-safe display projection with no runner or private blob details."""

    status: str
    private_asset_token: str
    localized_alt: Mapping[str, str]
    generation_revision: int

    def __post_init__(self) -> None:
        if self.status not in HERO_STATUSES:
            raise ValueError("unsupported generated hero projection status")
        object.__setattr__(
            self,
            "localized_alt",
            _localized(self.localized_alt, field_name="localized_alt"),
        )
        if self.status == "generated_current" and not self.private_asset_token:
            raise ValueError("current generated hero projection requires an asset token")
        if self.status != "generated_current" and self.private_asset_token:
            raise ValueError("placeholder projection cannot expose an asset token")


class GeneratedHeroOwner:
    """C11 owner for private generation work and result registration."""

    record_owner = "generated_hero_record"
    token_owner = "generated_hero_token"

    def __init__(
        self,
        *,
        store: SQLiteStore,
        blob_store: BlobStore,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1 or max_attempts > 10:
            raise ValueError("generated hero max attempts must be between 1 and 10")
        self.store = store
        self.blobs = blob_store
        self.max_attempts = max_attempts

    @staticmethod
    def _brief(subject: HeroSubject) -> HeroGenerationBrief:
        payload = {
            "topic_concepts": list(subject.topic_concepts),
            "theme_concepts": list(subject.theme_concepts),
            "style": (
                "photorealistic candid documentary and editorial photography; "
                "natural available light; plausible real-world environment; "
                "ordinary camera perspective; scene-defining physical setting, "
                "objects, and activity specific to the Matter must dominate so "
                "the topic is recognizable without a caption; at least two "
                "independently recognizable Matter-specific physical cues must "
                "dominate the visible frame; vary composition "
                "and prefer an object-led or place-led scene when a person at a "
                "computer would be interchangeable; privacy-safe generic "
                "fictional non-identifiable people only when useful, shown "
                "without face emphasis; the scene is a presentation-only "
                "reconstruction and does not claim that the depicted event happened"
            ),
            "negative_constraints": [
                "no abstract or conceptual illustration",
                "no vector art, icon art, 3D render, or isometric render",
                "no infographic, collage, diagram, or poster",
                "no surreal, fantasy, symbolic, or metaphorical composition",
                "no generic person working at a desk or computer when the same "
                "scene could represent an unrelated Matter",
                "no single person, face, pose, or generic work activity as the "
                "only distinguishing cue",
                "no interchangeable office scene without topic-specific place, "
                "equipment, objects, or activity",
                "no screenshot, email, message, document preview, source image, "
                "or legible device-screen content",
                "no literal text or lettering",
                "no logos, brands, or trademarks",
                "no private identifiers, addresses, paths, or source excerpts",
                "no email or message content",
                "no identifiable or recognizable real people; any depicted "
                "person must be fictional, generic, and non-identifiable",
            ],
        }
        return HeroGenerationBrief(
            topic_concepts=subject.topic_concepts,
            theme_concepts=subject.theme_concepts,
            style=str(payload["style"]),
            negative_constraints=tuple(payload["negative_constraints"]),
            brief_fingerprint=_fingerprint(
                HERO_BRIEF_CONTRACT_REVISION,
                payload,
            ),
        )

    @staticmethod
    def _specificity_problem(subject: HeroSubject) -> str:
        normalized_themes = {
            " ".join(str(item).casefold().split())
            for item in subject.theme_concepts
        }
        generic_themes = {
            "progress",
            "journey preparation",
            "participant working at a computer",
            "developer working in a studio",
            "developer at hackathon workstation",
            "personal administration at home",
            "workflow review meeting",
        }
        if normalized_themes & generic_themes:
            return "insufficient_matter_specificity"
        if not any(len(theme.split()) >= 4 for theme in normalized_themes):
            return "insufficient_matter_specificity"
        return ""

    @staticmethod
    def _subject_fingerprints(subject: HeroSubject) -> dict[str, str]:
        return {
            "semantic_identity_fingerprint": _fingerprint(
                "hero-identity:v1",
                subject.semantic_identity_id,
            ),
            "topic_fingerprint": _fingerprint(
                "hero-topic:v1",
                subject.topic_concepts,
            ),
            "theme_fingerprint": _fingerprint(
                "hero-theme:v1",
                subject.theme_concepts,
            ),
            "hierarchy_fingerprint": _fingerprint(
                "hero-hierarchy:v1",
                subject.hierarchy_revision,
            ),
            "permission_fingerprint": _fingerprint(
                "hero-permission:v1",
                subject.permission_disposition,
            ),
            "safety_fingerprint": _fingerprint(
                "hero-safety:v1",
                subject.safety_disposition,
            ),
            "policy_fingerprint": _fingerprint(
                "hero-policy:v1",
                subject.generation_policy_revision,
            ),
        }

    def current(self, matter_id: str) -> GeneratedHeroRecord | None:
        payload = self.store.current(self.record_owner, matter_id)
        return GeneratedHeroRecord(**dict(payload)) if payload else None

    def prepare(self, subject: HeroSubject) -> GeneratedHeroRecord:
        """Create or reuse one pending/blocked/current generation record."""

        with self.store.immediate_transaction():
            return self._prepare_locked(subject)

    def _prepare_locked(self, subject: HeroSubject) -> GeneratedHeroRecord:
        """Prepare while holding the generated-hero write-owner transaction."""

        if not subject.eligible:
            raise HeroIneligibleError(
                "hero generation is not applicable; only root Matters receive heroes"
            )
        fingerprints = self._subject_fingerprints(subject)
        current = self.current(subject.object_id)
        invalidation = self._changed_dependency(current, fingerprints)
        if current is not None and not invalidation:
            if current.status == "generated_current":
                return current
            if (
                current.status == "generation_pending_placeholder"
                and current.brief_fingerprint
                and subject.ready
            ):
                return current
            if (
                current.status == "generation_blocked_placeholder"
                and (
                    subject.permission_disposition == "blocked"
                    or subject.safety_disposition == "blocked"
                )
            ):
                return current

        if current is not None and current.private_asset_token:
            self._retire_token(current.private_asset_token)

        if subject.permission_disposition == "blocked":
            return self._append_placeholder(
                subject=subject,
                fingerprints=fingerprints,
                status="generation_blocked_placeholder",
                failure_kind="permission_denied",
                invalidated_by=invalidation or "permission",
            )
        if subject.safety_disposition == "blocked":
            return self._append_placeholder(
                subject=subject,
                fingerprints=fingerprints,
                status="generation_blocked_placeholder",
                failure_kind="unsafe_output",
                invalidated_by=invalidation or "safety",
            )
        if not (
            subject.identity_current
            and subject.hierarchy_current
            and subject.merge_disposition_current
        ):
            return self._append_placeholder(
                subject=subject,
                fingerprints=fingerprints,
                status="generation_pending_placeholder",
                failure_kind="dependencies_not_current",
                invalidated_by=invalidation,
            )
        specificity_problem = self._specificity_problem(subject)
        if specificity_problem:
            return self._append_placeholder(
                subject=subject,
                fingerprints=fingerprints,
                status="generation_pending_placeholder",
                failure_kind=specificity_problem,
                invalidated_by=invalidation,
            )

        brief = self._brief(subject)
        return self._append(
            GeneratedHeroRecord(
                matter_id=subject.object_id,
                generation_revision=self.store.next_revision(
                    self.record_owner,
                    subject.object_id,
                ),
                status="generation_pending_placeholder",
                **fingerprints,
                brief_fingerprint=brief.brief_fingerprint,
                brief_payload=brief.provider_payload(),
                runner_contract_id="",
                execution_identity="",
                private_asset_token="",
                private_blob_ref="",
                media_type="",
                localized_alt=_PENDING_ALT,
                safety_disposition="pending",
                attempt=0,
                max_attempts=self.max_attempts,
                retryable=True,
                failure_kind="",
                invalidated_by=invalidation,
            )
        )

    @staticmethod
    def _changed_dependency(
        current: GeneratedHeroRecord | None,
        fingerprints: Mapping[str, str],
    ) -> str:
        if current is None:
            return ""
        comparisons = (
            ("identity", "semantic_identity_fingerprint"),
            ("topic", "topic_fingerprint"),
            ("theme", "theme_fingerprint"),
            ("permission", "permission_fingerprint"),
            ("safety", "safety_fingerprint"),
            ("policy", "policy_fingerprint"),
        )
        for reason, field_name in comparisons:
            if getattr(current, field_name) != fingerprints[field_name]:
                return reason
        return ""

    def register_generated(
        self,
        *,
        matter_id: str,
        brief_fingerprint: str,
        content: bytes,
        media_type: str,
        localized_alt: Mapping[str, str],
        runner_contract_id: str,
        execution_identity: str,
        safety_disposition: str = "allowed",
        contains_literal_text: bool = False,
        contains_logo_or_brand: bool = False,
        contains_identifiable_real_people: bool = False,
    ) -> GeneratedHeroRecord:
        """Accept one safety-reviewed private generated asset."""

        with self.store.immediate_transaction():
            return self._register_generated_locked(
                matter_id=matter_id,
                brief_fingerprint=brief_fingerprint,
                content=content,
                media_type=media_type,
                localized_alt=localized_alt,
                runner_contract_id=runner_contract_id,
                execution_identity=execution_identity,
                safety_disposition=safety_disposition,
                contains_literal_text=contains_literal_text,
                contains_logo_or_brand=contains_logo_or_brand,
                contains_identifiable_real_people=contains_identifiable_real_people,
            )

    def _register_generated_locked(
        self,
        *,
        matter_id: str,
        brief_fingerprint: str,
        content: bytes,
        media_type: str,
        localized_alt: Mapping[str, str],
        runner_contract_id: str,
        execution_identity: str,
        safety_disposition: str,
        contains_literal_text: bool,
        contains_logo_or_brand: bool,
        contains_identifiable_real_people: bool,
    ) -> GeneratedHeroRecord:
        """Register while holding the generated-hero write-owner transaction."""

        current = self.current(matter_id)
        if current is None:
            raise HeroTransitionError("hero generation was not prepared")
        normalized_content = _normalized_image(content, media_type)
        expected_blob_ref = "sha256:" + sha256(normalized_content).hexdigest()
        if current.status == "generated_current":
            if (
                current.brief_fingerprint == brief_fingerprint
                and current.private_blob_ref == expected_blob_ref
                and current.runner_contract_id == runner_contract_id
                and current.execution_identity == execution_identity
            ):
                return current
            raise HeroTransitionError("a different current hero is already registered")
        if current.status != "generation_pending_placeholder":
            raise HeroTransitionError("blocked hero generation cannot accept an asset")
        if not current.brief_fingerprint or current.brief_fingerprint != brief_fingerprint:
            raise HeroTransitionError("generated result does not match the current brief")
        if not runner_contract_id or not execution_identity:
            raise ValueError("generated hero runner and execution identities are required")
        if safety_disposition != "allowed":
            raise HeroPrivacyError("generated hero safety disposition is not allowed")
        output_hazards = {
            "literal_text": contains_literal_text,
            "logo_or_brand": contains_logo_or_brand,
            "identifiable_real_people": contains_identifiable_real_people,
        }
        present = tuple(name for name, active in output_hazards.items() if active)
        if present:
            raise HeroPrivacyError(
                "generated hero output contains prohibited content: "
                + ", ".join(present)
            )
        safe_alt = _localized(localized_alt, field_name="localized_alt")
        for locale, value in safe_alt.items():
            problem = _privacy_problem(value, allow_digits=False)
            if problem:
                raise HeroPrivacyError(
                    f"localized_alt[{locale}] contains prohibited {problem} content"
                )
            style_problem = _alt_style_problem(value)
            if style_problem:
                raise HeroStyleError(
                    f"localized_alt[{locale}] contains prohibited "
                    f"{style_problem}"
                )
        blob_ref = self.blobs.put(normalized_content)
        token = "hero:" + token_hex(24)
        record = GeneratedHeroRecord(
            matter_id=matter_id,
            generation_revision=self.store.next_revision(
                self.record_owner,
                matter_id,
            ),
            status="generated_current",
            semantic_identity_fingerprint=current.semantic_identity_fingerprint,
            topic_fingerprint=current.topic_fingerprint,
            theme_fingerprint=current.theme_fingerprint,
            hierarchy_fingerprint=current.hierarchy_fingerprint,
            permission_fingerprint=current.permission_fingerprint,
            safety_fingerprint=current.safety_fingerprint,
            policy_fingerprint=current.policy_fingerprint,
            brief_fingerprint=current.brief_fingerprint,
            brief_payload=current.brief_payload,
            runner_contract_id=runner_contract_id,
            execution_identity=execution_identity,
            private_asset_token=token,
            private_blob_ref=blob_ref,
            media_type=media_type,
            localized_alt=safe_alt,
            safety_disposition="allowed",
            attempt=current.attempt,
            max_attempts=current.max_attempts,
            retryable=False,
            failure_kind="",
            invalidated_by="",
        )
        self.store.append(
            self.token_owner,
            token,
            self.store.next_revision(self.token_owner, token),
            {
                "private_asset_token": token,
                "private_blob_ref": blob_ref,
                "media_type": media_type,
                "current": True,
                "display_allowed": True,
            },
        )
        return self._append(record)

    def record_failure(
        self,
        *,
        matter_id: str,
        failure_kind: str,
    ) -> GeneratedHeroRecord:
        """Record a bounded retry or a typed blocked placeholder."""

        with self.store.immediate_transaction():
            return self._record_failure_locked(
                matter_id=matter_id,
                failure_kind=failure_kind,
            )

    def _record_failure_locked(
        self,
        *,
        matter_id: str,
        failure_kind: str,
    ) -> GeneratedHeroRecord:
        """Record failure while holding the generated-hero owner transaction."""

        if failure_kind not in TRANSIENT_FAILURE_KINDS | BLOCKING_FAILURE_KINDS:
            raise ValueError("unsupported generated hero failure kind")
        current = self.current(matter_id)
        if current is None or current.status != "generation_pending_placeholder":
            raise HeroTransitionError("only pending hero generation can fail")
        attempt = current.attempt + 1
        transient = failure_kind in TRANSIENT_FAILURE_KINDS
        retryable = transient and attempt < current.max_attempts
        status = (
            "generation_pending_placeholder"
            if retryable
            else "generation_blocked_placeholder"
        )
        terminal_failure = (
            failure_kind
            if not transient or retryable
            else "retry_exhausted"
        )
        return self._append(
            GeneratedHeroRecord(
                matter_id=matter_id,
                generation_revision=self.store.next_revision(
                    self.record_owner,
                    matter_id,
                ),
                status=status,
                semantic_identity_fingerprint=current.semantic_identity_fingerprint,
                topic_fingerprint=current.topic_fingerprint,
                theme_fingerprint=current.theme_fingerprint,
                hierarchy_fingerprint=current.hierarchy_fingerprint,
                permission_fingerprint=current.permission_fingerprint,
                safety_fingerprint=current.safety_fingerprint,
                policy_fingerprint=current.policy_fingerprint,
                brief_fingerprint=current.brief_fingerprint,
                brief_payload=current.brief_payload,
                runner_contract_id="",
                execution_identity="",
                private_asset_token="",
                private_blob_ref="",
                media_type="",
                localized_alt=_PENDING_ALT if retryable else _BLOCKED_ALT,
                safety_disposition="pending" if retryable else "blocked",
                attempt=attempt,
                max_attempts=current.max_attempts,
                retryable=retryable,
                failure_kind=terminal_failure,
                invalidated_by="",
            )
        )

    def apply_change(
        self,
        *,
        matter_id: str,
        change_kind: str,
    ) -> GeneratedHeroRecord:
        """Invalidate only the exact OpenSpec-authorized dependency classes.

        Unknown or ordinary clue/summary/localization/processing changes retain
        the current record byte-for-byte and do not append a revision.
        """

        with self.store.immediate_transaction():
            return self._apply_change_locked(
                matter_id=matter_id,
                change_kind=change_kind,
            )

    def _apply_change_locked(
        self,
        *,
        matter_id: str,
        change_kind: str,
    ) -> GeneratedHeroRecord:
        """Apply invalidation under the generated-hero owner transaction."""

        current = self.current(matter_id)
        if current is None:
            raise HeroTransitionError("generated hero does not exist")
        if change_kind not in HERO_INVALIDATION_REASONS:
            return current
        if current.private_asset_token:
            self._retire_token(current.private_asset_token)
        blocked = change_kind in HERO_BLOCKING_INVALIDATIONS
        return self._append(
            GeneratedHeroRecord(
                matter_id=matter_id,
                generation_revision=self.store.next_revision(
                    self.record_owner,
                    matter_id,
                ),
                status=(
                    "generation_blocked_placeholder"
                    if blocked
                    else "generation_pending_placeholder"
                ),
                semantic_identity_fingerprint=current.semantic_identity_fingerprint,
                topic_fingerprint=current.topic_fingerprint,
                theme_fingerprint=current.theme_fingerprint,
                hierarchy_fingerprint=current.hierarchy_fingerprint,
                permission_fingerprint=current.permission_fingerprint,
                safety_fingerprint=current.safety_fingerprint,
                policy_fingerprint=current.policy_fingerprint,
                brief_fingerprint="",
                brief_payload={},
                runner_contract_id="",
                execution_identity="",
                private_asset_token="",
                private_blob_ref="",
                media_type="",
                localized_alt=_BLOCKED_ALT if blocked else _PENDING_ALT,
                safety_disposition="blocked" if blocked else "pending",
                attempt=0,
                max_attempts=current.max_attempts,
                retryable=not blocked,
                failure_kind=f"{change_kind}_invalidated",
                invalidated_by=change_kind,
            )
        )

    def resolve(self, private_asset_token: str) -> tuple[bytes, str]:
        payload = self.store.current(self.token_owner, private_asset_token)
        if not payload or not bool(payload.get("current", False)):
            raise KeyError("generated hero is unavailable")
        if not bool(payload.get("display_allowed", False)):
            raise PermissionError("generated hero is not allowed for display")
        return (
            self.blobs.get(str(payload["private_blob_ref"])),
            str(payload["media_type"]),
        )

    def _append_placeholder(
        self,
        *,
        subject: HeroSubject,
        fingerprints: Mapping[str, str],
        status: str,
        failure_kind: str,
        invalidated_by: str,
    ) -> GeneratedHeroRecord:
        blocked = status == "generation_blocked_placeholder"
        return self._append(
            GeneratedHeroRecord(
                matter_id=subject.object_id,
                generation_revision=self.store.next_revision(
                    self.record_owner,
                    subject.object_id,
                ),
                status=status,
                **fingerprints,
                brief_fingerprint="",
                brief_payload={},
                runner_contract_id="",
                execution_identity="",
                private_asset_token="",
                private_blob_ref="",
                media_type="",
                localized_alt=_BLOCKED_ALT if blocked else _PENDING_ALT,
                safety_disposition="blocked" if blocked else "pending",
                attempt=0,
                max_attempts=self.max_attempts,
                retryable=not blocked,
                failure_kind=failure_kind,
                invalidated_by=invalidated_by,
            )
        )

    def _append(self, record: GeneratedHeroRecord) -> GeneratedHeroRecord:
        self.store.append(
            self.record_owner,
            record.matter_id,
            record.generation_revision,
            asdict(record),
        )
        return record

    def _retire_token(self, private_asset_token: str) -> None:
        payload = self.store.current(self.token_owner, private_asset_token)
        if not payload or not bool(payload.get("current", False)):
            return
        retired = dict(payload)
        retired["current"] = False
        retired["display_allowed"] = False
        self.store.append(
            self.token_owner,
            private_asset_token,
            self.store.next_revision(self.token_owner, private_asset_token),
            retired,
        )


class GeneratedHeroProjectionOwner:
    """C12 adapter from private generation state to one safe display value."""

    @staticmethod
    def project(record: GeneratedHeroRecord) -> GeneratedHeroProjection:
        return GeneratedHeroProjection(
            status=record.status,
            private_asset_token=(
                record.private_asset_token
                if record.status == "generated_current"
                else ""
            ),
            localized_alt=record.localized_alt,
            generation_revision=record.generation_revision,
        )


__all__ = [
    "BLOCKING_FAILURE_KINDS",
    "GeneratedHeroOwner",
    "GeneratedHeroProjection",
    "GeneratedHeroProjectionOwner",
    "GeneratedHeroRecord",
    "HERO_BRIEF_CONTRACT_REVISION",
    "HERO_BLOCKING_INVALIDATIONS",
    "HERO_ELIGIBILITY_DISPOSITIONS",
    "HERO_GENERATION_POLICY_REVISION",
    "HERO_INVALIDATION_REASONS",
    "HERO_OBJECT_KINDS",
    "HERO_STATUSES",
    "HeroGenerationBrief",
    "HeroIneligibleError",
    "HeroPrivacyError",
    "HeroStyleError",
    "HeroSubject",
    "HeroTransitionError",
    "MAX_GENERATED_ASSET_BYTES",
    "MAX_GENERATED_DIMENSION",
    "SAFE_GENERATED_MEDIA_TYPES",
    "TRANSIENT_FAILURE_KINDS",
]
