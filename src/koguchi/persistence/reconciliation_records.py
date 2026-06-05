"""Reconciliation Persistence — in-memory stores for observation records。

v0.13 read-only persistence spike。production persistence ではない。
"""

from dataclasses import dataclass, field

from koguchi.reconciliation.filesystem_diff import (
    FilesystemDifference,
    ReconciliationStatus,
)


@dataclass(frozen=True)
class ReconciliationAuditRecord:
    audit_id: str
    request_id: str
    route: list[str]
    backend_id: str
    execution_id: str
    reconciliation_kind: str
    mode: str
    result_ref: str | None = None
    boundary: dict[str, bool] = field(default_factory=lambda: {
        "read_only": True,
        "no_repair": True,
        "no_retry": True,
        "no_control_decision": True,
    })


@dataclass(frozen=True)
class ReconciliationResultRecord:
    result_id: str
    request_id: str
    status: ReconciliationStatus
    summary: str
    observed_differences: list[FilesystemDifference] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    stale_artifacts: list[str] = field(default_factory=list)
    audit_gaps: list[str] = field(default_factory=list)
    recommended_review_focus: list[str] = field(default_factory=list)
    boundary: dict[str, bool] = field(default_factory=lambda: {
        "review_focus_only": True,
        "correctness_decision": False,
        "enforcement": False,
        "approval": False,
        "rejection": False,
    })


class InMemoryReconciliationAuditStore:
    """in-memory audit store。observation metadata を保存する。correctness decision ではない。"""

    def __init__(self) -> None:
        self._records: dict[str, ReconciliationAuditRecord] = {}

    def append(self, record: ReconciliationAuditRecord) -> None:
        if record.audit_id in self._records:
            raise ValueError(f"Duplicate audit_id: {record.audit_id}")
        self._records[record.audit_id] = record

    def get(self, audit_id: str) -> ReconciliationAuditRecord | None:
        return self._records.get(audit_id)

    def list_all(self) -> list[ReconciliationAuditRecord]:
        return list(self._records.values())


class InMemoryReconciliationResultStore:
    """in-memory result store。reconciliation output を保存する。
    correctness decision ではない。approval/rejection ではない。
    """

    def __init__(self) -> None:
        self._records: dict[str, ReconciliationResultRecord] = {}

    def put(self, record: ReconciliationResultRecord) -> None:
        if record.result_id in self._records:
            raise ValueError(f"Duplicate result_id: {record.result_id}")
        self._records[record.result_id] = record

    def get(self, result_id: str) -> ReconciliationResultRecord | None:
        return self._records.get(result_id)

    def list_all(self) -> list[ReconciliationResultRecord]:
        return list(self._records.values())
