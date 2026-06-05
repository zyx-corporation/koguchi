"""Reconciliation Scheduler example — v0.3。

Shows:
- Persisting audit events to JSONL
- Reading back events
- Planning reconciliation jobs
- Running pending jobs
- Summary output
"""

from pathlib import Path

from koguchi.audit_store import JsonlAuditEventSink
from koguchi.reconciliation_scheduler import ReconciliationScheduler
from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import ServiceRuntime, ServiceRuntimeRequest


def main() -> None:
    # 1. Generate audit events
    path = Path("/tmp/koguchi-reconcile-example.jsonl")
    sink = JsonlAuditEventSink(path)
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)
    runtime.execute(ServiceRuntimeRequest(tool_name="filesystem.write"))
    runtime.execute(ServiceRuntimeRequest(tool_name="shell.execute"))

    # 2. Read back
    events = JsonlAuditEventSink(path, create_parent=False).read_events()

    # 3. Plan reconciliation jobs
    scheduler = ReconciliationScheduler(events)
    jobs = scheduler.plan()

    # 4. Show plan
    print("=== Reconciliation Jobs ===")
    for job in jobs:
        print(f"  [{job.status.value}] {job.job_id}  tool={job.tool_name}")

    # 5. Run pending
    results = scheduler.run_pending()
    print("\n=== Results ===")
    for r in results:
        print(f"  [{r.status.value}] {r.job_id}: {r.message}")

    # 6. Summary
    print("\n=== Summary ===")
    for key, val in scheduler.summary().items():
        print(f"  {key}: {val}")

    path.unlink(missing_ok=True)
    print("\nDone.")


if __name__ == "__main__":
    main()
