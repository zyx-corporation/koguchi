"""Phase 3: Policy Gate — 実行前許可判定の証拠。"""
import uuid
from pathlib import Path

from koguchi.envelope import ActionEnvelope
from koguchi.events import ProxyResult
from koguchi.policy import (
    DenyShellExecution,
    ExecutionPolicyGate,
    PolicyDecision,
    PolicyResult,
)
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore


def _shell_envelope() -> ActionEnvelope:
    return ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="shell.execute",
        target="/tmp",
        parameters_digest="abc",
        permission_scope="workspace",
        risk_class=["shell_exec"],
    )


def _write_envelope(workspace_dir: str) -> ActionEnvelope:
    import hashlib

    return ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="filesystem.write",
        target=str(Path(workspace_dir) / "out.txt"),
        parameters_digest=hashlib.sha256(b"x").hexdigest(),
        expected_result_digest=hashlib.sha256(b"x").hexdigest(),
        permission_scope="workspace",
        risk_class=["file_write"],
    )


# --- DenyShellExecution ---

def test_shell_denied_by_policy(workspace):
    """DenyShellExecution ルール → shell.execute が REJECTED。"""
    store = SQLiteExecutionStore(":memory:")
    gate = ExecutionPolicyGate([DenyShellExecution()])
    proxy = ToolProxy(str(workspace), store, policy_gate=gate)

    result = proxy.execute_shell(
        envelope=_shell_envelope(), command=["echo", "x"],
    )
    assert result == ProxyResult.REJECTED


def test_write_allowed_even_with_deny_shell_rule(workspace):
    """DenyShellExecution ルールがあっても filesystem.write は ALLOW。"""
    store = SQLiteExecutionStore(":memory:")
    gate = ExecutionPolicyGate([DenyShellExecution()])
    proxy = ToolProxy(str(workspace), store, policy_gate=gate)

    result = proxy.write_file(
        envelope=_write_envelope(str(workspace)), content=b"x",
    )
    assert result == ProxyResult.SUCCESS


def test_without_policy_gate_all_tools_allowed(workspace):
    """policy_gate=None なら全ツールが通常通り動作。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    result = proxy.execute_shell(
        envelope=_shell_envelope(), command=["echo", "ok"],
    )
    assert result == ProxyResult.SUCCESS


# --- PolicyDecision ---

def test_policy_decision_values():
    assert PolicyDecision.ALLOW == "allow"
    assert PolicyDecision.DENY == "deny"
    assert PolicyDecision.REQUIRE_APPROVAL == "require_approval"


def test_policy_result():
    result = PolicyResult(
        decision=PolicyDecision.DENY,
        reason="denied by rule: DenyShellExecution",
        rule_name="DenyShellExecution",
    )
    assert result.decision == PolicyDecision.DENY
    assert "DenyShellExecution" in result.reason
