"""Phase 10: Service Runtime — accountable execution surface の証拠。"""
import json

from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import (
    InMemoryAuditEventSink,
    ServiceRuntime,
    ServiceRuntimeRequest,
)


def test_service_runtime_generates_request_id():
    runtime = ServiceRuntime(DefaultRuntimeBoundary())
    req = ServiceRuntimeRequest(tool_name="filesystem.write")
    result = runtime.execute(req)
    assert result.request_id != ""
    assert result.allowed is True


def test_service_runtime_denies_shell_by_default():
    runtime = ServiceRuntime(DefaultRuntimeBoundary())
    req = ServiceRuntimeRequest(tool_name="shell.execute")
    result = runtime.execute(req)
    assert result.allowed is False
    assert result.reason is not None


def test_allow_result_has_no_error():
    runtime = ServiceRuntime(DefaultRuntimeBoundary())
    req = ServiceRuntimeRequest(tool_name="filesystem.write")
    result = runtime.execute(req)
    assert result.error is None


def test_deny_emits_audit_event():
    sink = InMemoryAuditEventSink()
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)
    req = ServiceRuntimeRequest(tool_name="shell.execute")
    runtime.execute(req)

    events = sink.events()
    assert len(events) == 1
    assert events[0].event_type == "deny"
    assert events[0].allowed is False


def test_allow_emits_audit_event():
    sink = InMemoryAuditEventSink()
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)
    req = ServiceRuntimeRequest(tool_name="filesystem.write")
    runtime.execute(req)

    events = sink.events()
    assert len(events) == 1
    assert events[0].event_type == "allow"
    assert events[0].allowed is True


def test_runtime_status_is_json_serializable():
    runtime = ServiceRuntime(DefaultRuntimeBoundary())
    runtime.execute(ServiceRuntimeRequest(tool_name="filesystem.write"))
    status = runtime.status()
    json.dumps(status)  # raises if not serializable


def test_runtime_events_are_json_serializable():
    sink = InMemoryAuditEventSink()
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)
    runtime.execute(ServiceRuntimeRequest(tool_name="todo.create"))
    runtime.execute(ServiceRuntimeRequest(tool_name="shell.execute"))

    events = runtime.events()
    json.dumps(events)  # raises if not serializable
    assert len(events) == 2


def test_unknown_tool_is_denied_with_audit():
    sink = InMemoryAuditEventSink()
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), event_sink=sink)
    req = ServiceRuntimeRequest(tool_name="dangerous.unsafe_tool")
    result = runtime.execute(req)

    assert result.allowed is False
    events = sink.events()
    assert len(events) == 1
    assert events[0].event_type == "deny"
