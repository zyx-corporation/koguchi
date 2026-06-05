"""Phase 4: AuditGate — アプリケーション抽象化層の証拠。"""
import hashlib

from koguchi.audit import AuditResult, KoguchiAuditGate
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore


def test_audit_gate_wraps_write_file(workspace):
    """KoguchiAuditGate 経由で filesystem.write が実行できる。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)
    gate = KoguchiAuditGate(proxy)

    target = str(workspace / "audited.txt")
    result = gate.audit(
        tool="filesystem.write",
        target=target,
        params_digest=hashlib.sha256(b"audited").hexdigest(),
        permission_scope="workspace",
        risk_class=["file_write"],
        intent="監査テスト",
        data=b"audited",
    )

    assert result.result == ProxyResult.SUCCESS
    assert result.action_id != ""
    assert result.side_effect_observed is not None
    assert (workspace / "audited.txt").read_bytes() == b"audited"


def test_audit_gate_result_is_auditresult():
    """audit() の戻り値が AuditResult である。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy("/tmp", store)
    gate = KoguchiAuditGate(proxy)

    result = gate.audit(
        tool="filesystem.write",
        target="/tmp/test.txt",
        params_digest="abc",
        permission_scope="workspace",
        risk_class=["file_write"],
        data=b"test",
    )

    assert isinstance(result, AuditResult)
    assert result.result == ProxyResult.SUCCESS
    assert result.action_id != ""
