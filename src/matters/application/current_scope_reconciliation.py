"""C1/C2 Gmail current-scope reconciliation without provider refetch.

This owner repairs a narrow durable-state mismatch: the current coverage row
still points at a metadata-only Gmail scope while the same occurrence is
already tracked by one newer, current inventory scope.  It never calls a Gmail
adapter and never reads source bytes; it can only reuse current durable C1/C2
authorities and an already-recorded body/content-disposition receipt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, TYPE_CHECKING

from matters.application.coverage_ledger import (
    STAGE_ORDER,
    bounded_stage_output_set_ref,
)

if TYPE_CHECKING:
    from matters.infrastructure.sqlite.store import SQLiteStore


RECONCILIATION_RECEIPT_OWNER = "gmail_current_scope_reconciliation"
RECONCILIATION_CONTRACT = "gmail-current-scope-reconciliation:v1"
CONTENT_RECEIPT_REBASE_CONTRACT = "gmail-content-receipt-rebase:v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _pointer(
    stage_id: str,
    status: str,
    owner_id: str,
    input_fingerprint: str,
    *,
    output_ref: str = "",
    failure_class: str = "",
) -> dict[str, Any]:
    return {
        "stage_id": stage_id,
        "status": status,
        "owner_id": owner_id,
        "input_fingerprint": input_fingerprint,
        "output_ref": output_ref,
        "failure_class": failure_class,
        "updated_at": _utc_now(),
    }


@dataclass(frozen=True)
class CurrentScopeReconciliationPage:
    status: str
    inspected_count: int
    switched_count: int
    pending_count: int
    blocked_count: int
    stale_count: int
    next_after_object_id: str = ""


@dataclass(frozen=True)
class GmailContentReceiptRebasePage:
    status: str
    inspected_count: int
    rebased_count: int
    current_count: int
    blocked_count: int
    next_after_object_id: str = ""


@dataclass(frozen=True)
class _Decision:
    status: str
    failure_class: str
    receipt: dict[str, Any]
    coverage: dict[str, Any] | None = None


class GmailCurrentScopeReconciliationOwner:
    """Rebind exact current Gmail coverage using only durable local state."""

    def __init__(self, store: "SQLiteStore") -> None:
        self.store = store

    def rebase_content_receipts_page(
        self,
        *,
        after_object_id: str = "",
        limit: int = 100,
    ) -> GmailContentReceiptRebasePage:
        """Reconstruct exact body receipts from current durable source proofs.

        This direct rebase performs no provider read and never materializes a
        body.  It is permitted only when the registry-current Gmail source has
        an exact body digest/length and current evidence anchors for that same
        revision.
        """

        records, next_after = self.store.gmail_current_scope_reconciliation_page(
            after_object_id=after_object_id,
            limit=limit,
        )
        rebased = current = blocked = 0
        for record in records:
            sources = tuple(record.get("sources", ()))
            if len(sources) != 1:
                blocked += 1
                continue
            source = dict(sources[0].get("payload", {}))
            content = dict(source.get("content", {}))
            source_id = str(source.get("source_id", ""))
            source_version = int(source.get("version", 0) or 0)
            source_ref = f"{source_id}:v{source_version}"
            body_digest = str(
                content.get("body_text_fingerprint", "")
            )
            body_byte_count = int(
                content.get("body_text_byte_length", 0) or 0
            )
            anchors = tuple(
                item
                for item in self.store.evidence_anchors_for_source_version(
                    source_id=source_id,
                    source_version=source_version,
                )
                if bool(item.get("current", True))
            )
            evidence_ids = tuple(
                str(item.get("evidence_id", ""))
                for item in anchors
                if str(item.get("evidence_id", ""))
            )
            if (
                str(source.get("provider", "")) != "gmail"
                or bool(source.get("tombstone", False))
                or not body_digest.startswith("sha256:")
                or body_byte_count < 1
                or not evidence_ids
            ):
                blocked += 1
                continue
            desired = {
                "artifact_type": "gmail_message_body",
                "source_id": source_id,
                "source_version_ref": source_ref,
                "manifest_identity": (
                    f"gmail-content-receipt-rebase:{source_ref}"
                ),
                "manifest_sha256": _fingerprint(
                    {
                        "contract": CONTENT_RECEIPT_REBASE_CONTRACT,
                        "source_ref": source_ref,
                        "body_digest": body_digest,
                        "body_byte_count": body_byte_count,
                        "evidence_ids": evidence_ids,
                    }
                ),
                "batch_number": 0,
                "source_page_identity_digest": _fingerprint(
                    str(record["object_id"])
                ),
                "body_digest": body_digest,
                "body_byte_count": body_byte_count,
                "content_status": "available",
                "evidence_set_ref": bounded_stage_output_set_ref(
                    "evidence_anchor",
                    source_ref,
                    evidence_ids,
                ),
                "provider_read_performed": False,
                "rebase_contract": CONTENT_RECEIPT_REBASE_CONTRACT,
                "proof_basis": (
                    "registry_current_digest_length_and_current_evidence"
                ),
            }
            write = self.store.compare_current_and_append(
                "gmail_message_body",
                source_id,
                is_equivalent=lambda observed, expected=desired: (
                    observed == expected
                ),
                payload_factory=lambda _revision, _current, expected=desired: (
                    expected
                ),
            )
            if str(write["status"]) == "appended":
                rebased += 1
            else:
                current += 1
        status = (
            "blocked"
            if blocked
            else "partial"
            if next_after
            else "current"
        )
        return GmailContentReceiptRebasePage(
            status=status,
            inspected_count=len(records),
            rebased_count=rebased,
            current_count=current,
            blocked_count=blocked,
            next_after_object_id=next_after,
        )

    @staticmethod
    def _bound_occurrence_is_exact(
        record: Mapping[str, Any],
    ) -> bool:
        coverage = dict(record["coverage"]["payload"])
        inventory_record = record.get("bound_inventory")
        if not isinstance(inventory_record, Mapping):
            return False
        inventory = dict(inventory_record.get("payload", {}))
        if (
            str(inventory.get("scope_id", ""))
            != str(coverage.get("scope_id", ""))
            or int(inventory.get("revision", 0) or 0)
            != int(coverage.get("inventory_revision", 0) or 0)
        ):
            return False
        object_id = str(record["object_id"])
        occurrences = tuple(
            item
            for item in inventory.get("occurrences", ())
            if str(item.get("occurrence_id", "")) == object_id
            and str(item.get("provider", "")) == "gmail"
            and str(item.get("object_type", "")) == "message"
        )
        dispositions = tuple(
            item
            for item in inventory.get("dispositions", ())
            if str(item.get("occurrence_id", "")) == object_id
            and str(item.get("status", "")) == "metadata_only"
        )
        return len(occurrences) == 1 and len(dispositions) == 1

    @staticmethod
    def _receipt(
        record: Mapping[str, Any],
        *,
        status: str,
        decision: str,
        failure_class: str = "",
        target: Mapping[str, Any] | None = None,
        source_ref: str = "",
        content_status: str = "",
        replacement_fingerprint: str = "",
    ) -> dict[str, Any]:
        coverage = dict(record["coverage"]["payload"])
        policy_record = record.get("tracking_policy")
        policy_payload = (
            dict(policy_record.get("payload", {}))
            if isinstance(policy_record, Mapping)
            else {}
        )
        return {
            "artifact_type": "gmail_current_scope_reconciliation_receipt",
            "contract": RECONCILIATION_CONTRACT,
            "owner_id": "C1_authorization_coverage",
            "object_ref": _fingerprint(str(record["object_id"])),
            "status": status,
            "decision": decision,
            "failure_class": failure_class,
            "input_fingerprint": str(record["context_fingerprint"]),
            "prior_scope_ref": _fingerprint(
                str(coverage.get("scope_id", ""))
            ),
            "prior_inventory_revision": int(
                coverage.get("inventory_revision", 0) or 0
            ),
            "target_scope_ref": (
                _fingerprint(str(target.get("scope_id", "")))
                if target is not None
                else ""
            ),
            "target_inventory_revision": (
                int(target.get("inventory_revision", 0) or 0)
                if target is not None
                else 0
            ),
            "tracking_policy_revision": int(
                policy_payload.get("revision", 0) or 0
            ),
            "source_ref": source_ref,
            "content_status": content_status,
            "replacement_fingerprint": replacement_fingerprint,
            "provider_read_performed": False,
        }

    def _target(self, record: Mapping[str, Any]) -> _Decision | Mapping[str, Any]:
        candidates = tuple(record.get("tracked_candidates", ()))
        if len(candidates) != 1:
            failure = (
                "tracked_scope_ambiguous"
                if len(candidates) > 1
                else "newer_tracked_scope_absent"
            )
            status = "blocked" if len(candidates) > 1 else "pending"
            return _Decision(
                status,
                failure,
                self._receipt(
                    record,
                    status=status,
                    decision="coverage_unchanged",
                    failure_class=failure,
                ),
            )
        candidate = dict(candidates[0])
        coverage = dict(record["coverage"]["payload"])
        bound_scope_record = record.get("bound_scope")
        target_scope_record = candidate.get("scope")
        target_inventory_record = candidate.get("inventory")
        policy_record = record.get("tracking_policy")
        if not all(
            isinstance(item, Mapping)
            for item in (
                bound_scope_record,
                target_scope_record,
                target_inventory_record,
                policy_record,
            )
        ):
            failure = "current_authority_missing"
            return _Decision(
                "blocked",
                failure,
                self._receipt(
                    record,
                    status="blocked",
                    decision="coverage_unchanged",
                    failure_class=failure,
                    target=candidate,
                ),
            )

        bound_scope = dict(bound_scope_record["payload"])
        target_scope = dict(target_scope_record["payload"])
        target_inventory = dict(target_inventory_record["payload"])
        policy = dict(policy_record["payload"])
        bound_inventory = dict(record["bound_inventory"]["payload"])
        same_account = (
            str(bound_scope.get("provider", "")) == "gmail"
            and str(target_scope.get("provider", "")) == "gmail"
            and str(bound_scope.get("root_locator", "")).startswith("sha256:")
            and str(bound_scope.get("root_locator", ""))
            == str(target_scope.get("root_locator", ""))
        )
        target_scope_current = (
            bool(target_scope.get("active", True))
            and int(target_scope.get("revision", 0) or 0)
            == int(target_scope_record.get("revision", 0) or 0)
            and "message" in tuple(target_scope.get("object_types", ()))
        )
        target_inventory_current = (
            str(candidate.get("provider", "")) == "gmail"
            and str(candidate.get("object_type", "")) == "message"
            and str(candidate.get("disposition", "")) == "tracked"
            and str(candidate.get("scope_id", ""))
            == str(target_inventory.get("scope_id", ""))
            and int(candidate.get("inventory_revision", 0) or 0)
            == int(target_inventory.get("revision", 0) or 0)
            == int(target_inventory_record.get("revision", 0) or 0)
            and str(
                dict(candidate.get("occurrence", {})).get(
                    "occurrence_id",
                    "",
                )
            )
            == str(record["object_id"])
        )
        policy_revision = int(policy.get("revision", 0) or 0)
        policy_current = (
            str(policy.get("policy_id", "")) == "tracking-policy:default"
            and policy_revision > 0
            and policy_revision
            == int(policy_record.get("revision", 0) or 0)
            == int(bound_inventory.get("policy_revision", 0) or 0)
            == int(target_inventory.get("policy_revision", 0) or 0)
        )
        bound_time = _parse_time(record["bound_inventory"].get("created_at"))
        target_time = _parse_time(target_inventory_record.get("created_at"))
        target_is_newer = (
            bound_time is not None
            and target_time is not None
            and target_time > bound_time
            and (
                str(candidate.get("scope_id", ""))
                != str(coverage.get("scope_id", ""))
                or int(candidate.get("inventory_revision", 0) or 0)
                != int(coverage.get("inventory_revision", 0) or 0)
            )
        )
        target_is_content_successor = (
            str(coverage.get("disposition", "")) == "metadata_only"
            and str(candidate.get("disposition", "")) == "tracked"
            and (
                str(candidate.get("scope_id", ""))
                != str(coverage.get("scope_id", ""))
                or int(candidate.get("inventory_revision", 0) or 0)
                != int(coverage.get("inventory_revision", 0) or 0)
            )
        )

        if not same_account or not target_scope_current:
            failure = "authorization_scope_conflict"
        elif not target_inventory_current:
            failure = "tracked_inventory_authority_conflict"
        elif not policy_current:
            failure = "tracking_policy_conflict"
        elif not (target_is_newer or target_is_content_successor):
            failure = "tracked_scope_not_newer"
        else:
            return candidate
        return _Decision(
            "blocked",
            failure,
            self._receipt(
                record,
                status="blocked",
                decision="coverage_unchanged",
                failure_class=failure,
                target=candidate,
            ),
        )

    @staticmethod
    def _source_content(
        record: Mapping[str, Any],
    ) -> tuple[str, str, Mapping[str, Any]] | _Decision:
        sources = tuple(record.get("sources", ()))
        if len(sources) != 1:
            failure = (
                "gmail_source_ambiguous"
                if len(sources) > 1
                else "gmail_source_missing"
            )
            status = "blocked" if len(sources) > 1 else "pending"
            return _Decision(
                status,
                failure,
                GmailCurrentScopeReconciliationOwner._receipt(
                    record,
                    status=status,
                    decision="coverage_unchanged",
                    failure_class=failure,
                ),
            )
        source_record = dict(sources[0])
        source = dict(source_record.get("payload", {}))
        reference = dict(source.get("external_reference", {}))
        content = dict(source.get("content", {}))
        if (
            bool(source.get("tombstone", False))
            or str(source.get("provider", "")) != "gmail"
            or str(reference.get("provider", "")) != "gmail"
            or str(reference.get("object_type", "")) != "gmail_message"
            or str(reference.get("external_id", ""))
            != str(record["object_id"])
            or int(source.get("version", 0) or 0) < 1
        ):
            failure = "gmail_source_not_current"
            return _Decision(
                "blocked",
                failure,
                GmailCurrentScopeReconciliationOwner._receipt(
                    record,
                    status="blocked",
                    decision="coverage_unchanged",
                    failure_class=failure,
                ),
            )
        source_ref = f"{source['source_id']}:v{source['version']}"
        body_fingerprint = str(content.get("body_text_fingerprint", ""))
        body_length = int(content.get("body_text_byte_length", 0) or 0)
        body_record = source_record.get("body_receipt")
        body = (
            dict(body_record.get("payload", {}))
            if isinstance(body_record, Mapping)
            else {}
        )
        body_current = (
            body_fingerprint.startswith("sha256:")
            and body_length > 0
            and str(body.get("source_id", "")) == str(source["source_id"])
            and str(body.get("source_version_ref", "")) == source_ref
            and str(body.get("content_status", "")) == "available"
            and str(body.get("body_digest", "")) == body_fingerprint
            and int(body.get("body_byte_count", 0) or 0) == body_length
        )
        no_text_record = source_record.get("no_text_disposition")
        no_text = (
            dict(no_text_record.get("payload", {}))
            if isinstance(no_text_record, Mapping)
            else {}
        )
        no_text_current = (
            not body_fingerprint
            and body_length == 0
            and str(no_text.get("source_id", "")) == str(source["source_id"])
            and str(no_text.get("source_version_ref", "")) == source_ref
            and str(no_text.get("content_status", "")) == "no_text_body"
            and no_text.get("body_present") is False
            and bool(str(no_text.get("raw_recovery_proof_identity", "")))
        )
        if body_current and no_text_current:
            failure = "gmail_content_disposition_conflict"
            return _Decision(
                "blocked",
                failure,
                GmailCurrentScopeReconciliationOwner._receipt(
                    record,
                    status="blocked",
                    decision="coverage_unchanged",
                    failure_class=failure,
                ),
            )
        if body_current:
            return source_ref, "available", body
        if no_text_current:
            return source_ref, "no_text_body", no_text
        failure = "gmail_body_not_current"
        return _Decision(
            "pending",
            failure,
            GmailCurrentScopeReconciliationOwner._receipt(
                record,
                status="pending",
                decision="coverage_unchanged",
                failure_class=failure,
                source_ref=source_ref,
            ),
        )

    @staticmethod
    def _coverage_replacement(
        record: Mapping[str, Any],
        target: Mapping[str, Any],
        *,
        source_ref: str,
        content_status: str,
        content_receipt: Mapping[str, Any],
    ) -> dict[str, Any]:
        prior = dict(record["coverage"]["payload"])
        authority_fingerprint = _fingerprint(
            {
                "contract": RECONCILIATION_CONTRACT,
                "scope_id": target["scope_id"],
                "inventory_revision": target["inventory_revision"],
                "occurrence": target["occurrence"],
                "policy_revision": dict(
                    record["tracking_policy"]["payload"]
                ).get("revision"),
            }
        )
        stages: dict[str, Any] = {
            "authorization": _pointer(
                "authorization",
                "current",
                "C1_authorization_coverage",
                authority_fingerprint,
                output_ref=f"scope:{target['scope_id']}",
            ),
            "inventory": _pointer(
                "inventory",
                "current",
                "C1_authorization_coverage",
                authority_fingerprint,
                output_ref=(
                    f"inventory:{target['scope_id']}:"
                    f"{target['inventory_revision']}"
                ),
            ),
        }
        prior_stages = {
            str(stage_id): dict(pointer)
            for stage_id, pointer in dict(prior.get("stages", {})).items()
        }
        source_pointer = prior_stages.get("source_version", {})
        if (
            source_pointer.get("status") == "current"
            and source_pointer.get("output_ref") == source_ref
            and not source_pointer.get("failure_class")
        ):
            stages["source_version"] = source_pointer
        else:
            stages["source_version"] = _pointer(
                "source_version",
                "current",
                "C2_source_registry",
                _fingerprint(
                    {
                        "contract": RECONCILIATION_CONTRACT,
                        "source_ref": source_ref,
                        "content_receipt": content_receipt,
                    }
                ),
                output_ref=source_ref,
            )

        if content_status == "available":
            evidence_ref = str(content_receipt.get("evidence_set_ref", ""))
            for stage_id in ("extraction", "evidence", "analysis"):
                pointer = prior_stages.get(stage_id, {})
                valid = (
                    not pointer.get("failure_class")
                    and pointer.get("status")
                    in (
                        {"current"}
                        if stage_id in {"extraction", "evidence"}
                        else {"current", "pending"}
                    )
                )
                if stage_id == "evidence":
                    valid = valid and pointer.get("output_ref") == evidence_ref
                if valid:
                    stages[stage_id] = pointer
        else:
            disposition_ref = (
                "gmail_message_content_disposition:"
                f"{content_receipt['source_id']}:no_text_body"
            )
            no_text_fingerprint = _fingerprint(
                {
                    "contract": RECONCILIATION_CONTRACT,
                    "source_ref": source_ref,
                    "content_disposition": content_receipt,
                }
            )
            for stage_id, owner_id in (
                ("extraction", "C3_evidence_qualification"),
                ("evidence", "C3_evidence_qualification"),
                ("analysis", "C11_guard_prediction"),
            ):
                stages[stage_id] = _pointer(
                    stage_id,
                    "not_applicable",
                    owner_id,
                    no_text_fingerprint,
                    output_ref=disposition_ref,
                )

        return {
            "object_id": str(record["object_id"]),
            "provider": "gmail",
            "object_type": "message",
            "scope_id": str(target["scope_id"]),
            "inventory_revision": int(target["inventory_revision"]),
            "disposition": "tracked",
            "required_stages": STAGE_ORDER,
            "stages": stages,
            "active": True,
            "matter_ids": tuple(prior.get("matter_ids", ())),
            "revision": int(prior.get("revision", 0) or 0) + 1,
            "retry_count": int(prior.get("retry_count", 0) or 0),
            "next_retry_at": str(prior.get("next_retry_at", "")),
            "updated_at": _utc_now(),
        }

    def _decide(self, record: Mapping[str, Any]) -> _Decision:
        if not self._bound_occurrence_is_exact(record):
            failure = "bound_metadata_inventory_not_exact"
            return _Decision(
                "blocked",
                failure,
                self._receipt(
                    record,
                    status="blocked",
                    decision="coverage_unchanged",
                    failure_class=failure,
                ),
            )
        target = self._target(record)
        if isinstance(target, _Decision):
            return target
        source_content = self._source_content(record)
        if isinstance(source_content, _Decision):
            source_content.receipt["target_scope_ref"] = _fingerprint(
                str(target["scope_id"])
            )
            source_content.receipt["target_inventory_revision"] = int(
                target["inventory_revision"]
            )
            return source_content
        source_ref, content_status, content_receipt = source_content
        replacement = self._coverage_replacement(
            record,
            target,
            source_ref=source_ref,
            content_status=content_status,
            content_receipt=content_receipt,
        )
        replacement_fingerprint = _fingerprint(
            {
                key: value
                for key, value in replacement.items()
                if key not in {"revision", "updated_at"}
            }
        )
        receipt = self._receipt(
            record,
            status="current",
            decision="switched_to_newer_tracked_scope",
            target=target,
            source_ref=source_ref,
            content_status=content_status,
            replacement_fingerprint=replacement_fingerprint,
        )
        return _Decision("current", "", receipt, replacement)

    def reconcile_page(
        self,
        *,
        after_object_id: str = "",
        limit: int = 200,
    ) -> CurrentScopeReconciliationPage:
        """Reconcile one bounded page; callers may resume with the returned key."""

        records, next_after = self.store.gmail_current_scope_reconciliation_page(
            after_object_id=after_object_id,
            limit=limit,
        )
        switched = pending = blocked = stale = 0
        for record in records:
            decision = self._decide(record)
            committed = self.store.commit_gmail_current_scope_reconciliation(
                object_id=str(record["object_id"]),
                expected_context_fingerprint=str(record["context_fingerprint"]),
                receipt_payload=decision.receipt,
                coverage_payload=decision.coverage,
            )
            if committed["status"] == "stale":
                stale += 1
            elif decision.status == "current":
                switched += 1
            elif decision.status == "blocked":
                blocked += 1
            else:
                pending += 1
        if not records:
            status = "no_delta"
        elif next_after or stale:
            status = "partial"
        elif pending or blocked:
            status = "complete_with_gaps"
        else:
            status = "complete"
        return CurrentScopeReconciliationPage(
            status=status,
            inspected_count=len(records),
            switched_count=switched,
            pending_count=pending,
            blocked_count=blocked,
            stale_count=stale,
            next_after_object_id=next_after,
        )


__all__ = [
    "CONTENT_RECEIPT_REBASE_CONTRACT",
    "CurrentScopeReconciliationPage",
    "GmailContentReceiptRebasePage",
    "GmailCurrentScopeReconciliationOwner",
    "RECONCILIATION_CONTRACT",
    "RECONCILIATION_RECEIPT_OWNER",
]
