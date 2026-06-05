"""Dashboard Observation Plane — read-only operational awareness。

v0.5: JSON serializable snapshot。control plane ではない。
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koguchi.reconciliation_scheduler import ReconciliationJob


@dataclass(frozen=True)
class AuditSummary:
    total_events: int = 0
    allowed_events: int = 0
    denied_events: int = 0
    error_events: int = 0
    malformed_events: int = 0
    tools: dict[str, int] = field(default_factory=dict)
    recent_request_ids: list[str] = field(default_factory=list)
    first_timestamp: str | None = None
    last_timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_events": self.total_events,
            "allowed_events": self.allowed_events,
            "denied_events": self.denied_events,
            "error_events": self.error_events,
            "malformed_events": self.malformed_events,
            "tools": self.tools,
            "recent_request_ids": self.recent_request_ids,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
        }


@dataclass(frozen=True)
class ReconciliationSummary:
    total_jobs: int = 0
    pending: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_jobs": self.total_jobs,
            "pending": self.pending,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
        }


@dataclass(frozen=True)
class ChokepointSummary:
    configured: bool = False
    available: bool = False
    binary_path: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "available": self.available,
            "binary_path": self.binary_path,
            "note": self.note,
        }


@dataclass(frozen=True)
class DashboardSnapshot:
    schema_version: int = 1
    generated_at: str = ""
    audit: AuditSummary = field(default_factory=AuditSummary)
    reconciliation: ReconciliationSummary = field(default_factory=ReconciliationSummary)
    chokepoint: ChokepointSummary = field(default_factory=ChokepointSummary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "audit": self.audit.to_dict(),
            "reconciliation": self.reconciliation.to_dict(),
            "chokepoint": self.chokepoint.to_dict(),
        }


class DashboardBuilder:
    """audit events, reconciliation jobs, chokepoint binary から
    read-only snapshot を生成する。"""

    def __init__(
        self,
        *,
        audit_events: list[dict[str, Any]] | None = None,
        reconciliation_jobs: list[ReconciliationJob] | None = None,
        chokepoint_binary: Path | None = None,
    ) -> None:
        self._audit_events = audit_events or []
        self._reconciliation_jobs = reconciliation_jobs or []
        self._chokepoint_binary = chokepoint_binary

    def build(self) -> DashboardSnapshot:
        return DashboardSnapshot(
            schema_version=1,
            generated_at=datetime.now(UTC).isoformat(),
            audit=self._build_audit(),
            reconciliation=self._build_reconciliation(),
            chokepoint=self._build_chokepoint(),
        )

    def _build_audit(self) -> AuditSummary:
        total = 0
        allowed = 0
        denied = 0
        errors = 0
        malformed = 0
        tools: dict[str, int] = {}
        recent: list[str] = []
        first_ts: str | None = None
        last_ts: str | None = None

        for event in self._audit_events:
            total += 1
            try:
                is_allowed = event.get("allowed")
                tool = str(event.get("tool_name", "unknown"))
                ts = event.get("timestamp")

                if is_allowed is True:
                    allowed += 1
                elif is_allowed is False:
                    denied += 1
                if event.get("error") is not None:
                    errors += 1

                tools[tool] = tools.get(tool, 0) + 1
                rid = event.get("request_id")
                if rid and len(recent) < 5:
                    recent.append(str(rid))

                if ts:
                    if first_ts is None:
                        first_ts = str(ts)
                    last_ts = str(ts)
            except Exception:
                malformed += 1

        return AuditSummary(
            total_events=total,
            allowed_events=allowed,
            denied_events=denied,
            error_events=errors,
            malformed_events=malformed,
            tools=tools,
            recent_request_ids=recent,
            first_timestamp=first_ts,
            last_timestamp=last_ts,
        )

    def _build_reconciliation(self) -> ReconciliationSummary:
        pending = passed = failed = skipped = 0
        for job in self._reconciliation_jobs:
            status = job.status.value
            if status == "pending":
                pending += 1
            elif status == "passed":
                passed += 1
            elif status == "failed":
                failed += 1
            elif status == "skipped":
                skipped += 1
        return ReconciliationSummary(
            total_jobs=len(self._reconciliation_jobs),
            pending=pending,
            passed=passed,
            failed=failed,
            skipped=skipped,
        )

    def _build_chokepoint(self) -> ChokepointSummary:
        if self._chokepoint_binary is None:
            return ChokepointSummary(
                configured=False,
                available=False,
                note="chokepoint binary not configured",
            )
        if self._chokepoint_binary.exists():
            return ChokepointSummary(
                configured=True,
                available=True,
                binary_path=str(self._chokepoint_binary),
            )
        return ChokepointSummary(
            configured=True,
            available=False,
            binary_path=str(self._chokepoint_binary),
            note="binary not found at path",
        )


def render_text(snapshot: DashboardSnapshot) -> str:
    """DashboardSnapshot を人間が読めるテキストに変換する。"""
    lines = [
        "=== Dashboard Snapshot ===",
        f"generated_at: {snapshot.generated_at}",
        "",
        "Audit:",
        f"  total_events: {snapshot.audit.total_events}",
        f"  allowed_events: {snapshot.audit.allowed_events}",
        f"  denied_events: {snapshot.audit.denied_events}",
        f"  error_events: {snapshot.audit.error_events}",
        f"  malformed_events: {snapshot.audit.malformed_events}",
    ]
    if snapshot.audit.tools:
        lines.append(f"  tools: {snapshot.audit.tools}")
    lines += [
        "",
        "Reconciliation:",
        f"  total_jobs: {snapshot.reconciliation.total_jobs}",
        f"  pending: {snapshot.reconciliation.pending}",
        f"  passed: {snapshot.reconciliation.passed}",
        f"  failed: {snapshot.reconciliation.failed}",
        f"  skipped: {snapshot.reconciliation.skipped}",
        "",
        "Chokepoint:",
        f"  configured: {snapshot.chokepoint.configured}",
        f"  available: {snapshot.chokepoint.available}",
    ]
    if snapshot.chokepoint.binary_path:
        lines.append(f"  binary_path: {snapshot.chokepoint.binary_path}")
    if snapshot.chokepoint.note:
        lines.append(f"  note: {snapshot.chokepoint.note}")
    return "\n".join(lines)
