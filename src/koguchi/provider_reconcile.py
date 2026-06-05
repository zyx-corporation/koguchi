"""Reconciliation v2 — 外部 API 実状態との照合フレームワーク。"""

from typing import Protocol

from koguchi.reconcile import ReconciliationFinding
from koguchi.store import ExecutionStore


class ReconciliableProvider(Protocol):
    def find_by_audit_record_id(self, record_id: str) -> dict[str, object] | None:
        """audit record_id から外部リソースを検索する。見つかれば辞書、なければ None。"""
        ...

    def exists(self, external_id: str) -> bool:
        """外部リソースが存在するか。"""
        ...


class ProviderReconciler:
    """pending event を Provider 経由で外部 API 実状態と照合する。"""

    def __init__(self, store: ExecutionStore, provider: ReconciliableProvider):
        self._store = store
        self._provider = provider

    def reconcile(self) -> list[ReconciliationFinding]:
        findings: list[ReconciliationFinding] = []

        for pending in self._store.pending():
            envelope = pending.envelope
            if envelope is None:
                continue

            # 非 filesystem ツールのみを Provider 照合の対象とする
            tool = envelope.tool
            if tool in ("filesystem.write", "filesystem.mkdir"):
                continue

            found = self._provider.find_by_audit_record_id(pending.record_id)

            if found is not None:
                findings.append(ReconciliationFinding(
                    diagnosis="pending_executed_unconfirmed",
                    record_id=pending.record_id,
                    target=envelope.target,
                    confidence=0.80,
                    detail=f"provider confirmed: {found}",
                ))
            else:
                findings.append(ReconciliationFinding(
                    diagnosis="pending_not_executed",
                    record_id=pending.record_id,
                    target=envelope.target,
                    confidence=0.60,
                    detail="provider returned no match",
                ))

        return findings
