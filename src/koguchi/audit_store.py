"""Persistent Audit Store — durable accountability layer。

ServiceRuntime が生成する AuditEvent を永続化し、後から検証可能にする。
v0.2 では JSONL ベースの append-only 保存を提供する。
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from koguchi.service_runtime import AuditEvent

_SCHEMA_VERSION = 1

_ALLOWED_FIELDS = {
    "execution_backend",
    "schema_version",
    "event_type",
    "request_id",
    "tool_name",
    "allowed",
    "reason",
    "workspace",
    "timestamp",
    "error",
}


class AuditStoreError(Exception):
    """audit store の基底エラー。"""


class AuditSerializationError(AuditStoreError):
    """JSONL のシリアライズまたはデシリアライズに失敗した。"""


class AuditWriteError(AuditStoreError):
    """audit record の書き込みに失敗した。"""


def sanitize_audit_event(event: AuditEvent) -> dict[str, Any]:
    """AuditEvent から保存可能なフィールドのみを allowlist 方式で抽出する。
    arguments や env は保存しない。
    """
    record: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "event_type": event.event_type,
        "request_id": event.request_id,
        "tool_name": event.tool_name,
        "allowed": event.allowed,
        "reason": event.reason,
        "workspace": event.workspace,
        "timestamp": event.timestamp,
        "execution_backend": event.execution_backend,
        "error": event.error,
    }
    # 将来のフィールド追加で allowlist 外のキーが混入しないよう検証
    extra = set(record.keys()) - _ALLOWED_FIELDS
    if extra:
        raise AuditSerializationError(
            f"Unexpected fields in audit record: {extra}"
        )
    return record


class JsonlAuditEventSink:
    """AuditEvent を JSONL ファイルに append-only で永続化する AuditEventSink。

    単一プロセス・ローカル実行を前提とする。
    壊れた行の読み取りは AuditSerializationError を raise する。
    """

    def __init__(self, path: Path, *, create_parent: bool = True) -> None:
        self._path = path
        if create_parent:
            path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: AuditEvent) -> None:
        """audit event を 1 行の JSON として追記する。"""
        record = sanitize_audit_event(event)
        try:
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as e:
            raise AuditSerializationError(
                f"Cannot serialize audit event: {e}"
            ) from e
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.write("\n")
        except OSError as e:
            raise AuditWriteError(
                f"Cannot write audit event to {self._path}: {e}"
            ) from e

    def read_events(self) -> list[dict[str, Any]]:
        """保存された全 audit event を読み戻す。壊れた行は AuditSerializationError。"""
        return list(self.iter_events())

    def iter_events(self) -> Iterator[dict[str, Any]]:
        """保存された audit event を 1 行ずつ yield する。"""
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    yield json.loads(stripped)
                except json.JSONDecodeError as e:
                    raise AuditSerializationError(
                        f"Broken JSONL at {self._path}:{line_num}: {e}"
                    ) from e
