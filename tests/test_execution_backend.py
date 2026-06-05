"""v0.6 Execution Backend — Python/Rust backend abstraction の証拠。"""
import tempfile
from pathlib import Path

import pytest

from koguchi.execution_backend import (
    ExecutionBackendRequest,
    PythonExecutionBackend,
    RustChokepointExecutionBackend,
)
from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import ServiceRuntime, ServiceRuntimeRequest


def test_python_backend_name():
    backend = PythonExecutionBackend()
    assert backend.name == "python"


def test_python_backend_executes():
    backend = PythonExecutionBackend()
    req = ExecutionBackendRequest(request_id="r1", tool_name="filesystem.write")
    result = backend.execute(req)
    assert result.allowed is True
    assert result.backend_name == "python"


def test_rust_backend_name():
    backend = RustChokepointExecutionBackend(Path("/nonexistent"))
    assert backend.name == "rust_chokepoint"


def test_rust_backend_unsupported_tool():
    backend = RustChokepointExecutionBackend(Path("/nonexistent"))
    req = ExecutionBackendRequest(request_id="r1", tool_name="shell.execute")
    result = backend.execute(req)
    assert result.allowed is False
    assert result.error is not None


def test_serviceruntime_defaults_to_python_backend():
    runtime = ServiceRuntime(DefaultRuntimeBoundary())
    result = runtime.execute(ServiceRuntimeRequest(tool_name="filesystem.write"))
    assert result.allowed is True
    events = runtime.events()
    assert events[0]["execution_backend"] == "python"


def test_serviceruntime_injects_rust_backend():
    """Rust backend を注入しても ServiceRuntime はクラッシュしない。"""
    backend = RustChokepointExecutionBackend(Path("/nonexistent"))
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), execution_backend=backend)
    # filesystem.write は RuntimeBoundary を通過し、Rust backend が binary 不在で deny を返す
    result = runtime.execute(ServiceRuntimeRequest(tool_name="filesystem.write"))
    assert not result.allowed
    assert result.error is not None


def test_serviceruntime_rust_backend_integration():
    """Real Rust binary integration test. Binary がない場合は skip。"""
    binary = Path(
        "crates/koguchi-chokepoint/target/debug/koguchi-chokepoint"
    ).resolve()
    if not binary.exists():
        pytest.skip("Rust binary not built")

    backend = RustChokepointExecutionBackend(binary)
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), execution_backend=backend)

    with tempfile.TemporaryDirectory() as ws:
        # filesystem.write → write_text
        result = runtime.execute(ServiceRuntimeRequest(
            tool_name="filesystem.write",
            arguments={"path": "hello.txt", "content": "world"},
            workspace=Path(ws),
        ))
        assert result.allowed is True
        events = runtime.events()
        assert events[0]["execution_backend"] == "rust_chokepoint"

        # filesystem.read → read_text
        result2 = runtime.execute(ServiceRuntimeRequest(
            tool_name="filesystem.read",
            arguments={"path": "hello.txt"},
            workspace=Path(ws),
        ))
        assert result2.allowed is True
        assert result2.result == "world"
