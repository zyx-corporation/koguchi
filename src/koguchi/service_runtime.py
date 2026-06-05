"""Service Runtime — accountable execution surface。

Tool Proxy の execution backend として機能し、RuntimeBoundary 判定、
tool execution、audit emission を一貫して扱う。

Service Runtime は権限主体ではなく、観測可能な実行面である。
security sandbox ではない。
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from koguchi.runtime import RuntimeBoundary


@dataclass
class ServiceRuntimeRequest:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    workspace: Path = Path("/tmp")
    env: dict[str, str] | None = None
    request_id: str | None = None


@dataclass
class ServiceRuntimeResult:
    allowed: bool
    reason: str | None = None
    result: Any = None
    error: str | None = None
    request_id: str = ""


@dataclass
class AuditEvent:
    event_type: str  # "allow", "deny", "error"
    request_id: str
    tool_name: str
    allowed: bool
    reason: str | None
    workspace: str
    timestamp: str
    error: str | None = None


class AuditEventSink(Protocol):
    def emit(self, event: AuditEvent) -> None:
        """audit event を永続化または転送する。"""
        ...


class InMemoryAuditEventSink:
    """テスト・観測用の in-memory audit event sink。"""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def emit(self, event: AuditEvent) -> None:
        self._events.append(event)

    def events(self) -> list[AuditEvent]:
        return list(self._events)


class ServiceRuntime:
    """Tool Proxy の execution backend。

    PolicyGate を置き換えない。RuntimeBoundary を置き換えない。
    実行経路の観測可能化を責務とする。
    """

    def __init__(
        self,
        runtime_boundary: RuntimeBoundary,
        event_sink: AuditEventSink | None = None,
    ) -> None:
        self._boundary = runtime_boundary
        self._sink = event_sink or InMemoryAuditEventSink()
        self._started_at = datetime.now(UTC).isoformat()

    def execute(self, request: ServiceRuntimeRequest) -> ServiceRuntimeResult:
        request_id = request.request_id or str(uuid.uuid4())
        tool = request.tool_name

        decision = self._boundary.evaluate_tool(tool)

        if not decision.allowed:
            event = AuditEvent(
                event_type="deny",
                request_id=request_id,
                tool_name=tool,
                allowed=False,
                reason=decision.reason,
                workspace=str(request.workspace),
                timestamp=datetime.now(UTC).isoformat(),
            )
            self._sink.emit(event)
            return ServiceRuntimeResult(
                allowed=False,
                reason=decision.reason,
                request_id=request_id,
            )

        # tool execution — Phase 10 では stub
        try:
            result_data = self._execute_tool(tool, request.arguments)
        except Exception as e:
            event = AuditEvent(
                event_type="error",
                request_id=request_id,
                tool_name=tool,
                allowed=True,
                reason=decision.reason,
                workspace=str(request.workspace),
                timestamp=datetime.now(UTC).isoformat(),
                error=str(e),
            )
            self._sink.emit(event)
            return ServiceRuntimeResult(
                allowed=True,
                reason=decision.reason,
                error=str(e),
                request_id=request_id,
            )

        event = AuditEvent(
            event_type="allow",
            request_id=request_id,
            tool_name=tool,
            allowed=True,
            reason=decision.reason,
            workspace=str(request.workspace),
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._sink.emit(event)
        return ServiceRuntimeResult(
            allowed=True,
            reason=decision.reason,
            result=result_data,
            request_id=request_id,
        )

    def _execute_tool(self, tool: str, arguments: dict[str, Any]) -> Any:
        """tool execution backend。Phase 10 では stub。"""
        return {"tool": tool, "arguments": arguments, "status": "executed"}

    def status(self) -> dict[str, Any]:
        """runtime status — observation plane のみ。"""
        sink = self._sink
        event_count = len(sink.events()) if isinstance(sink, InMemoryAuditEventSink) else 0
        return {
            "started_at": self._started_at,
            "event_count": event_count,
            "uptime_seconds": time.time(),
        }

    def events(self) -> list[dict[str, Any]]:
        """audit events を JSON serializable なリストとして返す。"""
        sink = self._sink
        if isinstance(sink, InMemoryAuditEventSink):
            return [
                {
                    "event_type": e.event_type,
                    "request_id": e.request_id,
                    "tool_name": e.tool_name,
                    "allowed": e.allowed,
                    "reason": e.reason,
                    "workspace": e.workspace,
                    "timestamp": e.timestamp,
                    "error": e.error,
                }
                for e in sink.events()
            ]
        return []
