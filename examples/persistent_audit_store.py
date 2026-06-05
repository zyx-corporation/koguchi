"""Persistent audit store example — v0.2。

Shows:
- JsonlAuditEventSink with temporary JSONL path
- allow event saved
- deny event saved
- reading back saved events
- request_id present
- arguments / env NOT saved (sanitized via allowlist)
"""

from pathlib import Path

from koguchi.audit_store import JsonlAuditEventSink
from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import ServiceRuntime, ServiceRuntimeRequest


def main() -> None:
    path = Path("/tmp/koguchi-audit.jsonl")
    sink = JsonlAuditEventSink(path)
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)

    # ALLOW
    runtime.execute(ServiceRuntimeRequest(tool_name="filesystem.write"))

    # DENY
    runtime.execute(ServiceRuntimeRequest(tool_name="shell.execute"))

    # Read back
    print("=== Persistent Audit Events ===")
    reader = JsonlAuditEventSink(path, create_parent=False)
    for event in reader.read_events():
        status = "ALLOW" if event["allowed"] else "DENY"
        print(f"  [{status}] {event['tool_name']}  request_id={event['request_id']}")
        # arguments / env / secrets は保存されない（sanitize_audit_event の allowlist による）
        assert "arguments" not in event

    # Cleanup
    path.unlink(missing_ok=True)
    print("Done.")


if __name__ == "__main__":
    main()
