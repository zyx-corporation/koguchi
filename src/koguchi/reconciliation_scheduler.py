"""Reconciliation Scheduler — deferred verification from persistent audit events。

v0.3 では schema-level deferred verification に限定する。
自動修復、ロールバック、daemon、LLM judge は実装しない。
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from koguchi.reconciliation_store import JsonlReconciliationResultStore
from typing import Any, Protocol


class ReconciliationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ReconciliationJob:
    job_id: str
    request_id: str
    tool_name: str
    source_event: dict[str, Any]
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    reason: str | None = None


@dataclass
class ReconciliationResult:
    job_id: str
    request_id: str
    status: ReconciliationStatus
    message: str | None = None
    error: str | None = None


class ReconciliationJobStore(Protocol):
    def add(self, job: ReconciliationJob) -> None: ...
    def get(self, job_id: str) -> ReconciliationJob: ...
    def list(self) -> list[ReconciliationJob]: ...
    def update(self, job: ReconciliationJob) -> None: ...


class InMemoryReconciliationJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, ReconciliationJob] = {}

    def add(self, job: ReconciliationJob) -> None:
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> ReconciliationJob:
        return self._jobs[job_id]

    def list(self) -> list[ReconciliationJob]:
        return list(self._jobs.values())

    def update(self, job: ReconciliationJob) -> None:
        self._jobs[job.job_id] = job


class ReconciliationScheduler:
    """Persistent audit events から reconciliation job を plan/run する。

    v0.3: schema-level deferred verification。自動修復はしない。
    """

    def __init__(
        self,
        audit_events: list[dict[str, Any]],
        job_store: ReconciliationJobStore | None = None,
        result_store: "JsonlReconciliationResultStore | None" = None,
    ) -> None:
        self._events = audit_events
        self._store = job_store or InMemoryReconciliationJobStore()
        self._result_store = result_store

    def plan(self) -> list[ReconciliationJob]:
        """audit events から reconciliation job を生成する。
        既存 job と重複する request_id はスキップする。
        """
        existing_ids = {j.request_id for j in self._store.list()}
        jobs: list[ReconciliationJob] = []

        for event in self._events:
            rid = event.get("request_id", "")
            if not rid or rid in existing_ids:
                continue

            allowed = event.get("allowed")
            error = event.get("error")

            if allowed is True and error is None:
                job = ReconciliationJob(
                    job_id=f"reconcile:{rid}",
                    request_id=rid,
                    tool_name=str(event.get("tool_name", "unknown")),
                    source_event=event,
                )
                jobs.append(job)
            elif error is not None:
                jobs.append(
                    ReconciliationJob(
                        job_id=f"reconcile:{rid}",
                        request_id=rid,
                        tool_name=str(event.get("tool_name", "unknown")),
                        source_event=event,
                        status=ReconciliationStatus.SKIPPED,
                        reason="error event — not reconcilable",
                    )
                )
            else:
                jobs.append(
                    ReconciliationJob(
                        job_id=f"reconcile:{rid}",
                        request_id=rid,
                        tool_name=str(event.get("tool_name", "unknown")),
                        source_event=event,
                        status=ReconciliationStatus.SKIPPED,
                        reason="denied event — not reconcilable",
                    )
                )

        for job in jobs:
            self._store.add(job)

        return jobs

    def run_pending(self) -> list[ReconciliationResult]:
        """全 pending job を実行する。"""
        results: list[ReconciliationResult] = []
        for job in self._store.list():
            if job.status == ReconciliationStatus.PENDING:
                results.append(self.run_job(job.job_id))
        return results

    def run_job(self, job_id: str) -> ReconciliationResult:
        """指定 job を実行する。"""
        try:
            job = self._store.get(job_id)
        except KeyError:
            return ReconciliationResult(
                job_id=job_id,
                request_id="",
                status=ReconciliationStatus.FAILED,
                error=f"Job not found: {job_id}",
            )

        if job.status != ReconciliationStatus.PENDING:
            return ReconciliationResult(
                job_id=job.job_id,
                request_id=job.request_id,
                status=job.status,
                message="Already completed",
            )

        job.status = ReconciliationStatus.RUNNING
        self._store.update(job)

        # schema-level verification
        passed = self._verify(job)

        job.status = ReconciliationStatus.PASSED if passed else ReconciliationStatus.FAILED
        self._store.update(job)

        msg = "Schema-level verification passed" if passed else "Schema-level verification failed"
        result = ReconciliationResult(
            job_id=job.job_id,
            request_id=job.request_id,
            status=job.status,
            message=msg,
        )
        self._append_result(result, job)
        return result

    def _append_result(
        self, result: ReconciliationResult, job: ReconciliationJob,
    ) -> None:
        """result store が設定されていれば result を永続化する。"""
        if self._result_store is None:
            return
        backend = job.source_event.get("execution_backend")
        self._result_store.append(result, source_event_backend=backend)

    def _persist_results(self, results: list[ReconciliationResult]) -> None:
        """run_pending の結果を永続化する。"""
        if self._result_store is None:
            return
        for result in results:
            try:
                job = self._store.get(result.job_id)
                backend = job.source_event.get("execution_backend")
            except KeyError:
                backend = None
            self._result_store.append(result, source_event_backend=backend)

    def _verify(self, job: ReconciliationJob) -> bool:
        """v0.3: schema-level verification。request_id, tool_name, allowed を確認。"""
        event = job.source_event
        return bool(
            event.get("request_id")
            and event.get("tool_name")
            and event.get("allowed") is True
        )

    def jobs(self) -> list[ReconciliationJob]:
        return self._store.list()

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for job in self._store.list():
            key = job.status.value
            counts[key] = counts.get(key, 0) + 1
        total = sum(counts.values())
        return {"planned": total, **counts}
