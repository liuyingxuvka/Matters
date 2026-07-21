"""Durable bounded filesystem inventory partitions.

This coordinator is intentionally private-runtime only.  It shallow-partitions
an authorized root, then scans each child subtree within the per-scope budget
and partitions that child only when the bounded scan exhausts the budget.  A
completed manifest proves inventory traversal only; it never claims that
tracked content has been fully extracted or semantically modeled.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import stat as stat_module
import time
from typing import Any, Mapping
from uuid import uuid4

from matters.application.orchestrator import MatterService
from matters.application.source_workflows import SourceWorkflow
from matters.inventory.owners import CURRENT_TRACKING_POLICY_REVISION
from matters.providers.filesystem import (
    FilesystemReadOnlyAdapter,
    FilesystemResourceLimit,
)


MANIFEST_SCHEMA = "matters.private-filesystem-partitions.v1"
MANIFEST_CHECKPOINT_NODES = 25
SUMMARY_CHECKPOINT_NODES = 25


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: str) -> str:
    return "sha256:" + sha256(value.encode("utf-8")).hexdigest()


def _node_id(relative_path: str) -> str:
    return "partition:" + sha256(relative_path.encode("utf-8")).hexdigest()[:24]


def _summary_payload(summary: Any) -> dict[str, Any]:
    payload = asdict(summary)
    payload.pop("scope_id", None)
    return payload


class PartitionManifestError(RuntimeError):
    """Raised when a private partition manifest cannot be trusted."""


class PartitionedFilesystemRunner:
    """Run or resume one durable, resource-bounded filesystem inventory."""

    def __init__(
        self,
        service: MatterService,
        *,
        manifest_path: Path,
        max_entries: int = 25_000,
        content_limit: int = 0,
    ) -> None:
        if max_entries < 1 or content_limit < 0:
            raise ValueError("partition resource limits are invalid")
        if service.store is None or service.config.private_root is None:
            raise ValueError("active private runtime is required")
        private_root = Path(
            os.path.abspath(service.config.private_root)
        )
        candidate = Path(os.path.abspath(manifest_path))
        try:
            candidate.relative_to(private_root)
        except ValueError as exc:
            raise ValueError(
                "partition manifest must remain inside MATTERS_HOME"
            ) from exc
        self.service = service
        self.manifest_path = candidate
        self.max_entries = max_entries
        self.content_limit = content_limit
        self.workflow = SourceWorkflow(service)

    @staticmethod
    def default_manifest_path(private_root: Path, root: Path) -> Path:
        root_identity = sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:24]
        return (
            Path(os.path.abspath(private_root))
            / "runs"
            / "filesystem-partitions"
            / f"{root_identity}.json"
        )

    @staticmethod
    def _is_reparse(metadata: os.stat_result) -> bool:
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        reparse_flag = int(
            getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
        return bool(attributes & reparse_flag)

    def _safe_node_path(self, root: Path, relative_path: str) -> Path:
        normalized = PurePosixPath(relative_path)
        if relative_path == ".":
            return root
        if (
            normalized.is_absolute()
            or any(part in {"", ".", ".."} for part in normalized.parts)
        ):
            raise PartitionManifestError("partition_relative_path_invalid")
        current = root
        for part in normalized.parts:
            current = current / part
            metadata = os.stat(current, follow_symlinks=False)
            if stat_module.S_ISLNK(metadata.st_mode) or self._is_reparse(metadata):
                raise PartitionManifestError(
                    "partition_link_junction_or_reparse_forbidden"
                )
        resolved = current.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise PartitionManifestError("partition_scope_escape") from exc
        if not resolved.is_dir():
            raise PartitionManifestError("partition_directory_required")
        return resolved

    def _new_manifest(
        self,
        root: Path,
        *,
        superseded: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()
        former_paths = {
            str(node.get("relative_path", ""))
            for node in dict((superseded or {}).get("nodes", {})).values()
            if str(node.get("relative_path", "")) not in {"", "."}
        }
        former_paths.update(
            str(item)
            for item in (superseded or {}).get(
                "retirement_relative_paths",
                (),
            )
            if str(item) not in {"", "."}
        )
        superseded_identity = ""
        superseded_policy_revision = 0
        if superseded:
            superseded_identity = _digest(
                json.dumps(
                    superseded,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str,
                )
            )
            superseded_policy_revision = int(
                superseded.get("policy_revision", 0)
            )
        return {
            "schema": MANIFEST_SCHEMA,
            "manifest_revision": 1,
            "root_identity": _digest(str(root)),
            "authorized_root": str(root),
            "policy_revision": CURRENT_TRACKING_POLICY_REVISION,
            "max_entries": self.max_entries,
            "last_content_limit": 0,
            "inventory_status": "partial",
            "terminal_coverage": "not_claimed",
            "superseded_manifest_identity": superseded_identity,
            "superseded_policy_revision": superseded_policy_revision,
            "retirement_relative_paths": sorted(former_paths),
            "created_at": now,
            "updated_at": now,
            "nodes": {
                _node_id("."): {
                    "node_id": _node_id("."),
                    "relative_path": ".",
                    "parent_node_id": "",
                    "status": "pending",
                    "attempt_count": 0,
                    "child_node_ids": [],
                    "summary": {},
                    "error_code": "",
                }
            },
        }

    def _load(self, root: Path) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return self._new_manifest(root)
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PartitionManifestError(
                "partition_manifest_unreadable"
            ) from exc
        if payload.get("schema") != MANIFEST_SCHEMA:
            raise PartitionManifestError("partition_manifest_schema_mismatch")
        if payload.get("authorized_root") != str(root):
            raise PartitionManifestError("partition_manifest_root_mismatch")
        if payload.get("root_identity") != _digest(str(root)):
            raise PartitionManifestError("partition_manifest_identity_mismatch")
        if payload.get("max_entries") != self.max_entries:
            raise PartitionManifestError("partition_manifest_budget_mismatch")
        if payload.get("policy_revision") != CURRENT_TRACKING_POLICY_REVISION:
            return self._new_manifest(root, superseded=payload)
        nodes = payload.get("nodes")
        if not isinstance(nodes, dict) or _node_id(".") not in nodes:
            raise PartitionManifestError("partition_manifest_nodes_invalid")
        return payload

    def _save(self, manifest: Mapping[str, Any]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.manifest_path.with_name(
            self.manifest_path.name
            + f".{os.getpid()}.{uuid4().hex}.tmp"
        )
        serialized = (
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            for attempt in range(20):
                try:
                    os.replace(temporary, self.manifest_path)
                    return
                except PermissionError:
                    if attempt == 19:
                        raise
                    # Windows indexers and virus scanners can briefly retain a
                    # read handle on the destination.  Keep the same complete
                    # temp file and retry the atomic replacement.
                    time.sleep(min(0.02 * (attempt + 1), 0.25))
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _scan(
        self,
        path: Path,
        *,
        max_depth: int | None = None,
        content_limit: int = 0,
        policy_path_prefix: tuple[str, ...] = (),
    ):
        return self.workflow.run_filesystem(
            FilesystemReadOnlyAdapter(
                path,
                page_size=self.max_entries,
                max_entries=self.max_entries,
                max_depth=max_depth,
                policy_path_prefix=policy_path_prefix,
            ),
            content_limit=content_limit,
            refresh_coverage_summary=False,
        )

    def _partition_node(
        self,
        manifest: dict[str, Any],
        *,
        root: Path,
        node: dict[str, Any],
        path: Path,
    ) -> tuple[str, ...]:
        shallow_adapter = FilesystemReadOnlyAdapter(
            path,
            page_size=self.max_entries,
            max_entries=self.max_entries,
            max_depth=0,
            policy_path_prefix=(
                ()
                if node["relative_path"] == "."
                else PurePosixPath(str(node["relative_path"])).parts
            ),
        )
        result = self.workflow.run_filesystem(
            shallow_adapter,
            content_limit=0,
            refresh_coverage_summary=False,
        )
        children = shallow_adapter.partition_children()
        if not children:
            raise FilesystemResourceLimit(
                "filesystem_partition_has_no_safe_child_boundary"
            )
        child_ids: list[str] = []
        for child in children:
            relative = child.relative_to(root).as_posix()
            child_id = _node_id(relative)
            child_ids.append(child_id)
            manifest["nodes"].setdefault(
                child_id,
                {
                    "node_id": child_id,
                    "relative_path": relative,
                    "parent_node_id": node["node_id"],
                    "status": "pending",
                    "attempt_count": 0,
                    "child_node_ids": [],
                    "summary": {},
                    "error_code": "",
                },
            )
        node.update(
            {
                "status": "partitioned",
                "child_node_ids": sorted(child_ids),
                "summary": _summary_payload(result.summary),
                "error_code": "",
            }
        )
        return tuple(sorted(child_ids))

    def _has_safe_child_boundary(
        self,
        *,
        node: Mapping[str, Any],
        path: Path,
    ) -> bool:
        """Detect an immediate safe split without recursively walking the root."""

        adapter = FilesystemReadOnlyAdapter(
            path,
            page_size=self.max_entries,
            max_entries=self.max_entries,
            max_depth=0,
            policy_path_prefix=(
                ()
                if node["relative_path"] == "."
                else PurePosixPath(str(node["relative_path"])).parts
            ),
        )
        return bool(adapter.partition_children())

    def run(
        self,
        root: Path,
        *,
        refresh: bool = False,
    ) -> Mapping[str, Any]:
        root = Path(root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("authorized filesystem root must be a directory")
        manifest = self._load(root)
        if refresh:
            manifest = self._new_manifest(root, superseded=manifest)
        nodes: dict[str, dict[str, Any]] = manifest["nodes"]
        if not refresh:
            for node in nodes.values():
                if node["status"] in {"running", "failed"}:
                    node["status"] = "pending"
                    node["error_code"] = ""
        manifest["inventory_status"] = "partial"
        manifest["manifest_revision"] = int(manifest["manifest_revision"]) + 1
        manifest["updated_at"] = _utc_now()
        self._save(manifest)
        pending_ids = [
            node_id
            for node_id, node in sorted(nodes.items())
            if node["status"] == "pending"
        ]
        queued_ids = set(pending_ids)
        pending_index = 0
        nodes_since_manifest_checkpoint = 0
        nodes_since_summary = 0

        while pending_index < len(pending_ids):
            pending_id = pending_ids[pending_index]
            pending_index += 1
            pending = nodes[pending_id]
            if pending["status"] != "pending":
                continue
            pending["status"] = "running"
            pending["attempt_count"] = int(pending["attempt_count"]) + 1
            pending["error_code"] = ""
            try:
                path = self._safe_node_path(
                    root,
                    str(pending["relative_path"]),
                )
                try:
                    requires_prepartition = (
                        pending["relative_path"] == "."
                        or bool(pending["child_node_ids"])
                    )
                    if (
                        requires_prepartition
                        and self._has_safe_child_boundary(
                            node=pending,
                            path=path,
                        )
                    ):
                        child_ids = self._partition_node(
                            manifest,
                            root=root,
                            node=pending,
                            path=path,
                        )
                        for child_id in child_ids:
                            if (
                                child_id not in queued_ids
                                and nodes[child_id]["status"] == "pending"
                            ):
                                pending_ids.append(child_id)
                                queued_ids.add(child_id)
                        result = None
                    else:
                        prefix = (
                            ()
                            if pending["relative_path"] == "."
                            else PurePosixPath(
                                str(pending["relative_path"])
                            ).parts
                        )
                        result = self._scan(
                            path,
                            policy_path_prefix=prefix,
                        )
                except (FilesystemResourceLimit, MemoryError):
                    child_ids = self._partition_node(
                        manifest,
                        root=root,
                        node=pending,
                        path=path,
                    )
                    for child_id in child_ids:
                        if (
                            child_id not in queued_ids
                            and nodes[child_id]["status"] == "pending"
                        ):
                            pending_ids.append(child_id)
                            queued_ids.add(child_id)
                else:
                    if result is not None:
                        pending.update(
                            {
                                "status": "complete",
                                "summary": _summary_payload(result.summary),
                                "error_code": "",
                            }
                        )
            except Exception as exc:
                pending["status"] = "failed"
                pending["error_code"] = type(exc).__name__
            manifest["updated_at"] = _utc_now()
            nodes_since_manifest_checkpoint += 1
            nodes_since_summary += 1
            if (
                nodes_since_manifest_checkpoint
                >= MANIFEST_CHECKPOINT_NODES
                or pending["status"] == "failed"
            ):
                self._save(manifest)
                nodes_since_manifest_checkpoint = 0
            if (
                nodes_since_summary >= SUMMARY_CHECKPOINT_NODES
                and self.service.coverage_ledger is not None
            ):
                self.service.coverage_ledger.refresh_summary()
                nodes_since_summary = 0

        if nodes_since_manifest_checkpoint and self.content_limit:
            manifest["updated_at"] = _utc_now()
            self._save(manifest)
            nodes_since_manifest_checkpoint = 0
        statuses = [str(node["status"]) for node in nodes.values()]
        ok = bool(statuses) and all(
            status in {"complete", "partitioned"} for status in statuses
        )
        extraction_attempted = 0
        content_ingested = 0
        if ok and self.content_limit:
            remaining = self.content_limit
            eligible_nodes = sorted(
                (
                    (
                        int(node.get("summary", {}).get("discovered", 0)),
                        int(node.get("summary", {}).get("tracked", 0)),
                        node_id,
                        node,
                    )
                    for node_id, node in nodes.items()
                    if (
                        node["status"] == "complete"
                        and int(node.get("summary", {}).get("tracked", 0)) > 0
                    )
                ),
                key=lambda row: (
                    0 if row[1] >= self.content_limit else 1,
                    row[0] if row[1] >= self.content_limit else -row[1],
                    row[0],
                    row[2],
                ),
            )
            for _discovered, _tracked, _node_id_value, node in eligible_nodes:
                if remaining <= 0:
                    break
                path = self._safe_node_path(
                    root,
                    str(node["relative_path"]),
                )
                result = self._scan(
                    path,
                    content_limit=remaining,
                    policy_path_prefix=(
                        ()
                        if node["relative_path"] == "."
                        else PurePosixPath(
                            str(node["relative_path"])
                        ).parts
                    ),
                )
                attempted = min(int(result.summary.tracked), remaining)
                extraction_attempted += attempted
                content_ingested += int(result.summary.content_ingested)
                remaining -= attempted
        manifest["inventory_status"] = "complete" if ok else "blocked"
        manifest["terminal_coverage"] = "not_claimed"
        manifest["last_content_limit"] = self.content_limit
        manifest["last_extraction"] = {
            "attempted": extraction_attempted,
            "content_ingested": content_ingested,
        }
        retirement = {
            "retired_scope_count": 0,
            "retired_object_count": 0,
        }
        if ok:
            active_relative_paths = {
                str(node.get("relative_path", ""))
                for node in nodes.values()
            }
            retirement_candidates = tuple(
                str(item)
                for item in manifest.get(
                    "retirement_relative_paths",
                    (),
                )
                if str(item) not in active_relative_paths
            )
            retirement = dict(
                self.workflow.retire_filesystem_scopes(
                    root=root,
                    relative_paths=retirement_candidates,
                )
            )
            manifest["retirement_relative_paths"] = []
        manifest["last_scope_retirement"] = retirement
        manifest["updated_at"] = _utc_now()
        self._save(manifest)
        if self.service.coverage_ledger is not None:
            self.service.coverage_ledger.refresh_summary()
        return {
            "ok": ok,
            "inventory_status": manifest["inventory_status"],
            "terminal_coverage": manifest["terminal_coverage"],
            "manifest_revision": manifest["manifest_revision"],
            "partition_count": len(nodes),
            "complete_partition_count": statuses.count("complete"),
            "delegating_partition_count": statuses.count("partitioned"),
            "failed_partition_count": statuses.count("failed"),
            "pending_partition_count": statuses.count("pending")
            + statuses.count("running"),
            "content_attempted": extraction_attempted,
            "content_ingested": content_ingested,
            "retired_scope_count": int(retirement["retired_scope_count"]),
            "retired_object_count": int(retirement["retired_object_count"]),
        }


__all__ = [
    "MANIFEST_SCHEMA",
    "PartitionManifestError",
    "PartitionedFilesystemRunner",
]
