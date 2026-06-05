"""ServiceRuntime Chokepoint Backend example — v0.6。

Shows:
- RustChokepointExecutionBackend
- ServiceRuntime backend injection
- filesystem write via Rust backend
- filesystem read via Rust backend
- Unsupported tool denied
- Audit events with backend name

Requires: cargo build --manifest-path crates/koguchi-chokepoint/Cargo.toml
"""

import tempfile
from pathlib import Path

from koguchi.execution_backend import RustChokepointExecutionBackend
from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import ServiceRuntime, ServiceRuntimeRequest

BINARY = Path("crates/koguchi-chokepoint/target/debug/koguchi-chokepoint")


def main() -> None:
    if not BINARY.exists():
        print("Rust binary not found. Build it first:")
        print("  cargo build --manifest-path crates/koguchi-chokepoint/Cargo.toml")
        return

    backend = RustChokepointExecutionBackend(BINARY.resolve())
    runtime = ServiceRuntime(DefaultRuntimeBoundary(), execution_backend=backend)

    with tempfile.TemporaryDirectory() as ws:
        workspace = Path(ws)

        print("=== filesystem.write (Rust backend) ===")
        r = runtime.execute(ServiceRuntimeRequest(
            tool_name="filesystem.write",
            arguments={"path": "hello.txt", "content": "from rust backend"},
            workspace=workspace,
        ))
        print(f"  allowed={r.allowed} result={r.result}")

        print("=== filesystem.read (Rust backend) ===")
        r = runtime.execute(ServiceRuntimeRequest(
            tool_name="filesystem.read",
            arguments={"path": "hello.txt"},
            workspace=workspace,
        ))
        print(f"  allowed={r.allowed} result={r.result}")

        print("=== shell.execute (unsupported) ===")
        r = runtime.execute(ServiceRuntimeRequest(
            tool_name="shell.execute",
            arguments={"path": "test"},
            workspace=workspace,
        ))
        print(f"  allowed={r.allowed} error={r.error}")

        print("\n=== Audit Events ===")
        for event in runtime.events():
            be = event.get("execution_backend", "unknown")
            print(f"  [{event['event_type']}] {event['tool_name']}  backend={be}")

    print("\nDone.")


if __name__ == "__main__":
    main()
