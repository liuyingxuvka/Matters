"""Canonical locale registry and complete localized-value contracts."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping


_BCP47 = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")


class UnsupportedLocale(ValueError):
    """Raised when a caller requests a locale outside the active registry."""


class LocalizationGap(ValueError):
    """Raised when a selectable locale has no non-empty value."""


@dataclass(frozen=True)
class LocaleDefinition:
    tag: str
    english_name: str
    native_name: str
    direction: str = "ltr"
    selectable: bool = True

    def __post_init__(self) -> None:
        if not _BCP47.fullmatch(self.tag):
            raise ValueError(f"invalid BCP47 locale tag: {self.tag}")
        if self.direction not in {"ltr", "rtl"}:
            raise ValueError("locale direction must be ltr or rtl")
        if not self.english_name.strip() or not self.native_name.strip():
            raise ValueError("locale names must be non-empty")

    def as_dict(self) -> dict[str, object]:
        return {
            "tag": self.tag,
            "english_name": self.english_name,
            "native_name": self.native_name,
            "direction": self.direction,
            "selectable": self.selectable,
        }


@dataclass(frozen=True)
class LocaleRegistry:
    definitions: tuple[LocaleDefinition, ...]
    default_locale: str
    revision: str = "locale-registry:1"

    def __post_init__(self) -> None:
        tags = tuple(item.tag for item in self.definitions)
        if not tags or len(tags) != len(set(tags)):
            raise ValueError("locale registry must contain unique definitions")
        if self.default_locale not in tags:
            raise ValueError("default locale must be registered")
        if not self.definition(self.default_locale).selectable:
            raise ValueError("default locale must be selectable")

    @property
    def available_locales(self) -> tuple[str, ...]:
        return tuple(item.tag for item in self.definitions if item.selectable)

    def definition(self, locale: str) -> LocaleDefinition:
        for item in self.definitions:
            if item.tag == locale:
                return item
        raise UnsupportedLocale(
            f"unsupported locale {locale!r}; available: "
            + ", ".join(self.available_locales)
        )

    def require(self, locale: str) -> str:
        definition = self.definition(locale)
        if not definition.selectable:
            raise UnsupportedLocale(f"locale {locale!r} is not selectable")
        return definition.tag

    def register(self, definition: LocaleDefinition) -> "LocaleRegistry":
        if any(item.tag == definition.tag for item in self.definitions):
            raise ValueError(f"locale already registered: {definition.tag}")
        return LocaleRegistry(
            definitions=(*self.definitions, definition),
            default_locale=self.default_locale,
            revision=f"{self.revision}+{definition.tag}",
        )

    def manifest(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "default_locale": self.default_locale,
            "available_locales": self.available_locales,
            "locales": tuple(item.as_dict() for item in self.definitions),
            "fallback_policy": "none",
        }


DEFAULT_LOCALE_REGISTRY = LocaleRegistry(
    definitions=(
        LocaleDefinition("en", "English", "English"),
        LocaleDefinition("zh-CN", "Chinese (Simplified)", "中文（简体）"),
    ),
    default_locale="en",
)


@dataclass(frozen=True)
class LocalizedText:
    values: Mapping[str, str]
    semantic_revision: str

    @classmethod
    def create(
        cls,
        values: Mapping[str, str],
        *,
        semantic_revision: str,
        registry: LocaleRegistry = DEFAULT_LOCALE_REGISTRY,
    ) -> "LocalizedText":
        if not semantic_revision.strip():
            raise LocalizationGap("localized text requires a semantic revision")
        normalized = {str(key): str(value).strip() for key, value in values.items()}
        missing = tuple(
            locale
            for locale in registry.available_locales
            if not normalized.get(locale)
        )
        if missing:
            raise LocalizationGap(
                "missing localized values for: " + ", ".join(missing)
            )
        extras = tuple(sorted(set(normalized) - set(registry.available_locales)))
        if extras:
            raise UnsupportedLocale(
                "unregistered localized values for: " + ", ".join(extras)
            )
        return cls(
            values={
                locale: normalized[locale]
                for locale in registry.available_locales
            },
            semantic_revision=semantic_revision,
        )

    def resolve(
        self,
        locale: str,
        *,
        registry: LocaleRegistry = DEFAULT_LOCALE_REGISTRY,
    ) -> str:
        registry.require(locale)
        value = self.values.get(locale, "").strip()
        if not value:
            raise LocalizationGap(f"missing localized value for {locale}")
        return value


STATE_LABELS: dict[str, tuple[str, str]] = {
    "candidate": ("Candidate", "候选事项"),
    "source_only": ("Source only", "仅来源"),
    "admitted": ("Admitted", "已接纳"),
    "planned": ("Planned", "已计划"),
    "in_progress": ("In progress", "进行中"),
    "not_started": ("Not started", "尚未开始"),
    "completed": ("Completed", "已完成"),
    "cancelled": ("Cancelled", "已取消"),
    "blocked": ("Blocked", "受阻"),
    "uncertain": ("Uncertain", "不确定"),
    "reopened": ("Reopened", "已重新打开"),
    "current": ("Current", "当前有效"),
    "unknown": ("Unknown", "尚不清楚"),
    "stale": ("Needs refresh", "需要更新"),
    "partial": ("Partially understood", "已有部分理解"),
    "sufficient": ("Sufficiently understood", "理解已足够"),
    "not_assessed": ("Not assessed", "尚未评估"),
    "tracked": ("Tracked", "已跟踪"),
    "not_tracked": ("Not tracked", "不跟踪"),
    "metadata_only": ("Metadata only", "仅登记元数据"),
    "not_read": ("Not read", "未读取"),
    "hard_excluded": ("Excluded", "已排除"),
    "active": ("Active", "已启用"),
    "unconfigured": ("Not configured", "尚未配置"),
    "not_configured": ("Not configured", "尚未配置"),
}


RATIONALE_TRANSLATIONS: dict[str, str] = {
    "source access or coverage blocked": "来源访问或覆盖范围受阻",
    "material conflict remains": "仍存在重要冲突",
    "material conflict is preserved as an uncertain Matter": "重要冲突以不确定事项保留",
    "no current goal or obligation": "目前没有明确目标或义务",
    "current evidence licenses admission": "当前证据支持接纳为事项",
    "useful source is retained as an uncertain Matter": "有用来源以不确定事项保留",
    "all explicit completion criteria have current evidence": "所有明确完成标准都有当前证据",
    "provider Done, a final file, or incomplete criteria cannot prove completion": "提供方标记完成、最终文件或不完整标准都不能单独证明事项完成",
    "completion criteria are incomplete": "完成标准尚不完整",
    "current evidence records actual work": "当前证据记录了实际工作",
    "scheduling is present without actual-start evidence": "已有排期，但没有实际开始的证据",
    "provider Done does not prove Matters completion": "提供方标记完成不能证明事项已经完成",
    "partial or unknown coverage cannot prove absence of start": "部分或未知覆盖范围不能证明尚未开始",
    "complete coverage contains no actual-start evidence": "完整覆盖范围中没有实际开始的证据",
    "dependency is open": "依赖项仍未关闭",
    "contradictory temporal evidence": "时间证据相互矛盾",
}


DISPOSITION_REASON_TRANSLATIONS: dict[str, str] = {
    "provider hard exclusion": "提供方要求强制排除",
    "credential-like occurrence": "疑似凭据内容",
    "known cache, generated, or software-state location": "已知缓存、生成内容或软件状态位置",
    "large archive is excluded from automatic extraction": "大型压缩包不进入自动解压范围",
    "source cannot be safely interpreted yet": "目前还不能安全理解该来源",
    "possible application state inside an authorized user root": "授权用户目录中可能包含应用状态",
    "supported user-owned occurrence": "受支持的用户自有内容",
    "directory_metadata_unavailable": "无法读取目录元数据",
    "metadata_unavailable": "无法读取元数据",
    "link_junction_or_reparse_not_followed": "未跟随链接、连接点或重解析点",
    "policy_excluded_software_or_cache_path": "策略已排除软件或缓存路径",
    "credential_or_secret_material": "凭据或秘密材料",
    "executable_content_not_read": "未读取可执行内容",
    "unsafe_serialized_model_not_loaded": "未加载不安全的序列化模型",
    "non_regular_file_not_read": "未读取非常规文件",
    "stable_content_unavailable": "当前没有稳定可读的内容",
    "metadata_inventory_only": "目前只登记元数据",
    "thread_metadata_inventory": "邮件会话目前只登记元数据",
    "gmail_spam_or_trash_policy": "Gmail 垃圾邮件或回收站策略已排除",
    "promotions_requires_relevance_policy": "促销邮件不进入当前建模范围",
    "mailbox_category_outside_current_inclusion": "邮件类别不在当前纳入范围内",
    "metadata_inventory_requires_tracking_decision": "当前只登记元数据，不读取内容",
    "authorized_included_mailbox_category": "已授权且属于纳入的邮件类别",
}


def localized(
    english: str,
    chinese: str,
    *,
    semantic_revision: str = "runtime-projection",
    registry: LocaleRegistry = DEFAULT_LOCALE_REGISTRY,
) -> dict[str, str]:
    return dict(
        LocalizedText.create(
            {"en": english, "zh-CN": chinese},
            semantic_revision=semantic_revision,
            registry=registry,
        ).values
    )


def state_localized(
    state: str,
    *,
    semantic_revision: str = "state-labels:1",
) -> dict[str, str]:
    labels = STATE_LABELS.get(state)
    if labels is None:
        raise LocalizationGap(f"no localized state label for {state!r}")
    return localized(*labels, semantic_revision=semantic_revision)


def rationale_localized(
    rationale: str,
    *,
    semantic_revision: str,
) -> dict[str, str]:
    chinese = RATIONALE_TRANSLATIONS.get(rationale)
    if chinese is None and rationale.startswith("new licensed obligation "):
        obligation = rationale.removeprefix("new licensed obligation ")
        chinese = f"出现新的有效义务：{obligation}"
    if chinese is None:
        raise LocalizationGap(f"no localized rationale for {rationale!r}")
    return localized(
        rationale,
        chinese,
        semantic_revision=semantic_revision,
    )


def user_text_localized(
    value: str,
    *,
    semantic_revision: str,
) -> dict[str, str]:
    """Preserve user-authored text without pretending it was translated by AI."""

    return localized(
        value,
        value,
        semantic_revision=semantic_revision,
    )


def disposition_reason_localized(
    reason: str,
    *,
    semantic_revision: str,
) -> dict[str, str]:
    chinese = DISPOSITION_REASON_TRANSLATIONS.get(reason)
    if chinese is None and reason.startswith("protected source class: "):
        source_class = reason.removeprefix("protected source class: ")
        chinese = f"受保护的来源类别：{source_class}"
    elif chinese is None and reason.startswith("user intent: "):
        intent = reason.removeprefix("user intent: ")
        chinese = f"用户选择：{intent}"
    elif chinese is None and reason.startswith("provider recommendation: "):
        recommendation = reason.removeprefix("provider recommendation: ")
        chinese = f"提供方建议：{recommendation}"
    if chinese is None:
        raise LocalizationGap(f"no localized disposition reason for {reason!r}")
    return localized(reason, chinese, semantic_revision=semantic_revision)


def zh_cn_state(state: str) -> str:
    """Compatibility-free helper for internal narrative formatting."""

    return state_localized(state)["zh-CN"]


ZH_CN_STATE = {
    state: labels[1]
    for state, labels in STATE_LABELS.items()
}


__all__ = [
    "DEFAULT_LOCALE_REGISTRY",
    "DISPOSITION_REASON_TRANSLATIONS",
    "LocaleDefinition",
    "LocaleRegistry",
    "LocalizedText",
    "LocalizationGap",
    "RATIONALE_TRANSLATIONS",
    "STATE_LABELS",
    "UnsupportedLocale",
    "ZH_CN_STATE",
    "disposition_reason_localized",
    "localized",
    "rationale_localized",
    "state_localized",
    "user_text_localized",
    "zh_cn_state",
]
