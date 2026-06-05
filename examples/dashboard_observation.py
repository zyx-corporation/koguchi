"""Dashboard Observation Plane example — v0.5。

Shows:
- Audit events from JSONL
- Reconciliation jobs from scheduler
- Chokepoint availability check
- Dashboard snapshot generation
- Text report output
"""

from pathlib import Path

from koguchi.audit_store import JsonlAuditEventSink
from koguchi.dashboard import DashboardBuilder, render_text
from koguchi.reconciliation_scheduler import ReconciliationScheduler
from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import ServiceRuntime, ServiceRuntimeRequest

BINARY = Path("crates/koguchi-chokepoint/target/debug/koguchi-chokepoint")


def main() -> None:
    # 1. Generate audit events
    audit_path = Path("/tmp/koguchi-dashboard-audit.jsonl")
    sink = JsonlAuditEventSink(audit_path)
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)
    runtime.execute(ServiceRuntimeRequest(tool_name="filesystem.write"))
    runtime.execute(ServiceRuntimeRequest(tool_name="shell.execute"))
    runtime.execute(ServiceRuntimeRequest(tool_name="todo.create"))

    # 2. Read audit + plan reconciliation
    events = JsonlAuditEventSink(audit_path, create_parent=False).read_events()
    scheduler = ReconciliationScheduler(events)
    scheduler.plan()
    scheduler.run_pending()

    # 3. Build dashboard
    builder = DashboardBuilder(
        audit_events=events,
        reconciliation_jobs=scheduler.jobs(),
        chokepoint_binary=BINARY.resolve() if BINARY.exists() else None,
    )
    snapshot = builder.build()

    # 4. Show
    print(render_text(snapshot))

    audit_path.unlink(missing_ok=True)
    print("\nDone.")


if __name__ == "__main__":
    main()
