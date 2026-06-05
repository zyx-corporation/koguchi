"""Persistent Reconciliation Result Store — durable verification history。

v0.7: JSONL ベースの append-only 保存。audit log とは別ファイル。
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koguchi.reconciliation_scheduler import ReconciliationResult

_SCHEMA_VERSION = 1


class ReconciliationStoreError(Exception):
    """reconciliation store の基底エラー。"""


class ReconciliationSerializationError(ReconciliationStoreError):
    """JSONL のシリアライズまたはデシリアライズに失敗した。"""


class ReconciliationWriteError(ReconciliationStoreError):
    """result record の書き込みに失敗した。"""


def sanitize_reconciliation_result(
    result: ReconciliationResult,
    *,
    source_event_backend: str | None = None,
) -> dict[str, Any]:
    """ReconciliationResult から保存可能なフィールドのみを allowlist 方式で抽出する。
    raw source_event, arguments, env, secrets は保存しない。
    """
    return {
        "schema_version": _SCHEMA_VERSION,
        "result_id": f"result:{result.job_id}",
        "job_id": result.job_id,
        "request_id": result.request_id,
        "status": result.status.value,
        "message": result.message,
        "error": result.error,
        "checked_at": datetime.now(UTC).isoformat(),
        "source_event_backend": source_event_backend,
    }


class JsonlReconciliationResultStore:
    """ReconciliationResult を JSONL ファイルに append-only で永続化する store。

    単一プロセス・ローカル実行を前提とする。
    audit log とは別ファイルに保存する。
    """

    def __init__(self, path: Path, *, create_parent: bool = True) -> None:
        self._path = path
        if create_parent:
            path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        result: ReconciliationResult,
        *,
        source_event_backend: str | None = None,
    ) -> None:
        """reconciliation result を 1 行の JSON として追記する。"""
        record = sanitize_reconciliation_result(
            result, source_event_backend=source_event_backend,
        )
        try:
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as e:
            raise ReconciliationSerializationError(
                f"Cannot serialize reconciliation result: {e}"
            ) from e
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.write("\n")
        except OSError as e:
            raise ReconciliationWriteError(
                f"Cannot write result to {self._path}: {e}"
            ) from e

    def read_results(self) -> list[dict[str, Any]]:
        return list(self.iter_results())

    def iter_results(self) -> Iterator[dict[str, Any]]:
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
                    raise ReconciliationSerializationError(
                        f"Broken JSONL at {self._path}:{line_num}: {e}"
                    ) from e
