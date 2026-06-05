"""Execution Backend — ServiceRuntime の optional execution backend abstraction。

v0.6: Python backend が既定。Rust chokepoint backend は explicit opt-in。
"""

import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from koguchi.chokepoint_client import (
    ChokepointError,
    RustChokepointClient,
)

CHOKEPOINT_OPERATION_MAP: dict[str, str] = {
    "filesystem.write": "write_text",
    "filesystem.read": "read_text",
}


class ExecutionBackendError(Exception):
    """execution backend のエラー。"""


@dataclass(frozen=True)
class ExecutionBackendRequest:
    request_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    workspace: Path = Path("/tmp")


@dataclass(frozen=True)
class ExecutionBackendResult:
    request_id: str
    backend_name: str
    allowed: bool
    result: Any = None
    error: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None


class ExecutionBackend(Protocol):
    name: str

    def execute(self, request: ExecutionBackendRequest) -> ExecutionBackendResult: ...


class PythonExecutionBackend:
    """既定の Python in-process execution backend。"""

    name = "python"

    def execute(self, request: ExecutionBackendRequest) -> ExecutionBackendResult:
        return ExecutionBackendResult(
            request_id=request.request_id,
            backend_name=self.name,
            allowed=True,
            result={"status": "executed", "tool": request.tool_name},
        )


class RustChokepointExecutionBackend:
    """Rust chokepoint を external backend として使う experimental backend。

    filesystem.write / filesystem.read のみ対応。
    """

    name = "rust_chokepoint"

    def __init__(self, binary_path: Path) -> None:
        self._binary_path = binary_path
        self._client: RustChokepointClient | None = None
        with contextlib.suppress(ChokepointError):
            self._client = RustChokepointClient(binary_path)  # defer error to execute time

    def execute(self, request: ExecutionBackendRequest) -> ExecutionBackendResult:
        operation = CHOKEPOINT_OPERATION_MAP.get(request.tool_name)
        if operation is None:
            return ExecutionBackendResult(
                request_id=request.request_id,
                backend_name=self.name,
                allowed=False,
                error=f"unsupported tool for Rust backend: {request.tool_name}",
            )

        try:
            if self._client is None:
                return ExecutionBackendResult(
                    request_id=request.request_id,
                    backend_name=self.name,
                    allowed=False,
                    error="Rust chokepoint binary not available",
                )
            content = str(request.arguments.get("content", ""))
            path = str(request.arguments.get("path", ""))
            cr = self._client.execute(
                operation=operation,
                workspace=request.workspace,
                path=path,
                content=content,
                request_id=request.request_id,
            )
            return ExecutionBackendResult(
                request_id=cr.request_id,
                backend_name=self.name,
                allowed=cr.allowed,
                result=cr.stdout if cr.allowed else None,
                error=cr.error,
                stdout=cr.stdout,
                stderr=cr.stderr,
                exit_code=cr.exit_code,
            )
        except ChokepointError as e:
            return ExecutionBackendResult(
                request_id=request.request_id,
                backend_name=self.name,
                allowed=False,
                error=str(e),
            )
