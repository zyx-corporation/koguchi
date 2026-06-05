"""v0.5 Dashboard Observation Plane — read-only snapshot の証拠。"""
import json
import tempfile
from pathlib import Path

from koguchi.dashboard import (
    DashboardBuilder,
    render_text,
)


def _allow_event(rid="req-1", tool="filesystem.write") -> dict:
    return {
        "schema_version": 1,
        "event_type": "allow",
        "request_id": rid,
        "tool_name": tool,
        "allowed": True,
        "reason": "allowed",
        "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:00Z",
        "error": None,
    }


def _deny_event(rid="req-2") -> dict:
    return {
        "schema_version": 1,
        "event_type": "deny",
        "request_id": rid,
        "tool_name": "shell.execute",
        "allowed": False,
        "reason": "denied",
        "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:01Z",
        "error": None,
    }


def test_empty_input_snapshot():
    builder = DashboardBuilder()
    snapshot = builder.build()
    assert snapshot.audit.total_events == 0
    assert snapshot.reconciliation.total_jobs == 0
    assert snapshot.chokepoint.configured is False


def test_snapshot_is_json_serializable():
    builder = DashboardBuilder()
    snapshot = builder.build()
    json.dumps(snapshot.to_dict())


def test_audit_counts_allowed_denied():
    builder = DashboardBuilder(audit_events=[_allow_event(), _deny_event()])
    snapshot = builder.build()
    assert snapshot.audit.total_events == 2
    assert snapshot.audit.allowed_events == 1
    assert snapshot.audit.denied_events == 1


def test_audit_counts_tools():
    builder = DashboardBuilder(audit_events=[
        _allow_event(tool="filesystem.write"),
        _allow_event(tool="filesystem.write"),
        _allow_event(tool="todo.create"),
    ])
    snapshot = builder.build()
    assert snapshot.audit.tools == {
        "filesystem.write": 2, "todo.create": 1,
    }


def test_audit_recent_request_ids():
    builder = DashboardBuilder(audit_events=[
        _allow_event("r1"), _allow_event("r2"), _allow_event("r3"),
    ])
    snapshot = builder.build()
    assert "r1" in snapshot.audit.recent_request_ids


def test_malformed_event_does_not_crash():
    builder = DashboardBuilder(audit_events=[
        _allow_event(),
        "not a dict",  # malformed
    ])
    snapshot = builder.build()
    assert snapshot.audit.total_events == 2
    assert snapshot.audit.malformed_events == 1


def test_reconciliation_summary():
    from koguchi.reconciliation_scheduler import (
        ReconciliationJob,
        ReconciliationStatus,
    )
    jobs = [
        ReconciliationJob("j1", "r1", "t1", {},
                          status=ReconciliationStatus.PASSED),
        ReconciliationJob("j2", "r2", "t2", {},
                          status=ReconciliationStatus.SKIPPED),
        ReconciliationJob("j3", "r3", "t3", {},
                          status=ReconciliationStatus.PENDING),
    ]
    builder = DashboardBuilder(reconciliation_jobs=jobs)
    summary = builder.build().reconciliation
    assert summary.total_jobs == 3
    assert summary.passed == 1
    assert summary.skipped == 1
    assert summary.pending == 1


def test_chokepoint_not_configured():
    builder = DashboardBuilder()
    cs = builder.build().chokepoint
    assert cs.configured is False
    assert cs.available is False


def test_chokepoint_configured_not_available():
    builder = DashboardBuilder(
        chokepoint_binary=Path("/nonexistent/chokepoint"),
    )
    cs = builder.build().chokepoint
    assert cs.configured is True
    assert cs.available is False


def test_chokepoint_available():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = Path(f.name)
    try:
        builder = DashboardBuilder(chokepoint_binary=path)
        cs = builder.build().chokepoint
        assert cs.available is True
    finally:
        path.unlink()


def test_snapshot_no_arguments_or_env():
    builder = DashboardBuilder(audit_events=[_allow_event()])
    d = builder.build().to_dict()
    assert "arguments" not in d
    assert "env" not in d


def test_text_report_includes_sections():
    builder = DashboardBuilder(audit_events=[_allow_event()])
    snapshot = builder.build()
    text = render_text(snapshot)
    assert "=== Dashboard Snapshot ===" in text
    assert "Audit:" in text
    assert "Reconciliation:" in text
    assert "Chokepoint:" in text
