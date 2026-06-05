"""Dashboard Static HTML Report example — v0.8。

Generates a read-only static HTML report from audit + reconciliation + chokepoint state.
"""

from pathlib import Path

from koguchi.audit_store import JsonlAuditEventSink
from koguchi.dashboard import DashboardBuilder
from koguchi.dashboard_report import render_html_report
from koguchi.reconciliation_scheduler import ReconciliationScheduler
from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import ServiceRuntime, ServiceRuntimeRequest

BINARY = Path("crates/koguchi-chokepoint/target/debug/koguchi-chokepoint")


def main() -> None:
    # Generate sample audit events
    audit_path = Path("/tmp/koguchi-html-audit.jsonl")
    sink = JsonlAuditEventSink(audit_path)
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)
    runtime.execute(ServiceRuntimeRequest(tool_name="filesystem.write"))
    runtime.execute(ServiceRuntimeRequest(tool_name="shell.execute"))
    runtime.execute(ServiceRuntimeRequest(tool_name="todo.create"))

    # Read audit + plan reconciliation
    events = JsonlAuditEventSink(audit_path, create_parent=False).read_events()
    scheduler = ReconciliationScheduler(events)
    scheduler.plan()
    scheduler.run_pending()

    # Build dashboard + render HTML
    builder = DashboardBuilder(
        audit_events=events,
        reconciliation_jobs=scheduler.jobs(),
        chokepoint_binary=BINARY.resolve() if BINARY.exists() else None,
    )
    snapshot = builder.build()
    html_str = render_html_report(snapshot)

    report_path = Path("/tmp/koguchi-dashboard-report.html")
    report_path.write_text(html_str, encoding="utf-8")
    print(f"Wrote static dashboard report: {report_path}")

    audit_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
