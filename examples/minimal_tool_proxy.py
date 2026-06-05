"""Minimal Koguchi example — v0.1 Developer Preview.

Demonstrates:
- ToolProxy as side-effect chokepoint
- PolicyGate evaluation
- allow / deny paths
- audit event emission

Koguchi is not a security sandbox.
The current Python implementation provides best-effort runtime constraint checks.
"""

from koguchi import (
    ActionEnvelope,
    DenyShellExecution,
    ExecutionPolicyGate,
    SQLiteExecutionStore,
    ToolProxy,
)
from koguchi.runtime import DefaultRuntimeBoundary
from koguchi.service_runtime import ServiceRuntime, ServiceRuntimeRequest


def main() -> None:
    # --- Setup ---
    store = SQLiteExecutionStore(":memory:")
    policy_gate = ExecutionPolicyGate([DenyShellExecution()])
    proxy = ToolProxy("./workspace", store, policy_gate=policy_gate)

    # ServiceRuntime as accountable execution surface
    boundary = DefaultRuntimeBoundary()
    runtime = ServiceRuntime(boundary)

    # --- ALLOW: filesystem.write ---
    print("=== ALLOW: filesystem.write ===")
    envelope = ActionEnvelope(
        action_id="example-1",
        tool="filesystem.write",
        target="./workspace/out.txt",
        parameters_digest="abc123",
        permission_scope="workspace",
        risk_class=["file_write"],
    )
    result = proxy.write_file(envelope=envelope, content=b"Hello, Koguchi")
    print(f"  result: {result}")

    # ServiceRuntime check
    req = ServiceRuntimeRequest(tool_name="filesystem.write")
    sr_result = runtime.execute(req)
    print(f"  runtime: allowed={sr_result.allowed}, id={sr_result.request_id}")

    # --- DENY: shell.execute ---
    print("=== DENY: shell.execute ===")
    req = ServiceRuntimeRequest(tool_name="shell.execute")
    sr_result = runtime.execute(req)
    print(f"  runtime: allowed={sr_result.allowed}, reason={sr_result.reason}")

    # --- Audit events ---
    print("=== Audit Events ===")
    for event in runtime.events():
        print(f"  [{event['event_type']}] {event['tool_name']}: allowed={event['allowed']}")


if __name__ == "__main__":
    main()
