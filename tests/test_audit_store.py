"""v0.2 Persistent Audit Store — JSONL 永続化の証拠。"""

import pytest

from koguchi.audit_store import (
    AuditSerializationError,
    AuditWriteError,
    JsonlAuditEventSink,
)
from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import (
    AuditEvent,
    InMemoryAuditEventSink,
    ServiceRuntime,
    ServiceRuntimeRequest,
)


def _make_event(**kwargs) -> AuditEvent:
    defaults = {
        "event_type": "allow",
        "request_id": "req-1",
        "tool_name": "filesystem.write",
        "allowed": True,
        "reason": "allowed by default",
        "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:00Z",
        "error": None,
    }
    defaults.update(kwargs)
    return AuditEvent(**defaults)


def test_jsonl_sink_is_audit_event_sink():
    """JsonlAuditEventSink が AuditEventSink 互換である。"""
    sink = InMemoryAuditEventSink()
    sink.emit(_make_event())
    assert len(sink.events()) == 1


def test_emit_writes_one_line_jsonl(tmp_path):
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditEventSink(path)
    sink.emit(_make_event())

    lines = path.read_text().strip().split("\n")
    assert len(lines) == 1


def test_multiple_events_are_appended(tmp_path):
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditEventSink(path)
    sink.emit(_make_event(request_id="r1"))
    sink.emit(_make_event(request_id="r2"))

    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2


def test_read_events_returns_saved_events(tmp_path):
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditEventSink(path)
    sink.emit(_make_event(request_id="r1"))
    sink.emit(_make_event(request_id="r2"))

    events = sink.read_events()
    assert len(events) == 2
    assert events[0]["request_id"] == "r1"
    assert events[1]["request_id"] == "r2"


def test_record_includes_schema_version(tmp_path):
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditEventSink(path)
    sink.emit(_make_event())

    events = sink.read_events()
    assert events[0]["schema_version"] == 1


def test_record_includes_request_id(tmp_path):
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditEventSink(path)
    sink.emit(_make_event(request_id="my-req"))

    events = sink.read_events()
    assert events[0]["request_id"] == "my-req"


def test_allow_deny_error_events_saved(tmp_path):
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditEventSink(path)
    sink.emit(_make_event(event_type="allow", allowed=True))
    sink.emit(_make_event(event_type="deny", allowed=False))
    sink.emit(_make_event(event_type="error", allowed=True, error="something broke"))

    events = sink.read_events()
    assert events[0]["allowed"] is True
    assert events[1]["allowed"] is False
    assert events[2]["error"] == "something broke"


def test_arguments_not_saved(tmp_path):
    """sanitize_audit_event の allowlist により arguments 相当の key は保存されない。"""
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditEventSink(path)
    sink.emit(_make_event())

    events = sink.read_events()
    assert "arguments" not in events[0]


def test_creates_parent_directory(tmp_path):
    path = tmp_path / "deep" / "nested" / "audit.jsonl"
    sink = JsonlAuditEventSink(path, create_parent=True)
    sink.emit(_make_event())
    assert path.exists()


def test_create_parent_false_raises_on_emit(tmp_path):
    path = tmp_path / "nonexistent" / "audit.jsonl"
    sink = JsonlAuditEventSink(path, create_parent=False)
    with pytest.raises((OSError, AuditWriteError)):
        sink.emit(_make_event())


def test_broken_jsonl_raises_on_read(tmp_path):
    path = tmp_path / "audit.jsonl"
    path.write_text("this is not json\n", encoding="utf-8")
    sink = JsonlAuditEventSink(path, create_parent=False)
    with pytest.raises(AuditSerializationError):
        sink.read_events()


def test_service_runtime_with_jsonl_sink(tmp_path):
    """ServiceRuntime に JsonlAuditEventSink を渡すと実行イベントが永続化される。"""
    path = tmp_path / "audit.jsonl"
    sink = JsonlAuditEventSink(path)
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)

    runtime.execute(ServiceRuntimeRequest(tool_name="filesystem.write"))
    runtime.execute(ServiceRuntimeRequest(tool_name="shell.execute"))

    events = JsonlAuditEventSink(path, create_parent=False).read_events()
    assert len(events) >= 2
    types = {e["event_type"] for e in events}
    assert "allow" in types
    assert "deny" in types
