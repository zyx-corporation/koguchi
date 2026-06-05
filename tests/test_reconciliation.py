"""INV-1c: 全 reconciliation 診断経路の証拠。"""
from koguchi.envelope import ActionEnvelope
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.reconcile import reconcile
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def test_reconciliation_detects_unrecorded_workspace_change(workspace, store):
    """INV-1c: Tool Proxy を通さない workspace 変更を、
    Store に対応 record がない unrecorded_external_change として検出する。"""
    sneaky = workspace / "sneaky.txt"
    sneaky.write_bytes(b"bypassed the proxy")

    findings = reconcile(str(workspace), store)

    unrecorded = [f for f in findings if f.diagnosis == "unrecorded_external_change"]
    assert len(unrecorded) == 1
    assert str(sneaky) == unrecorded[0].target
    assert unrecorded[0].confidence > 0.0


# --- pending: pending_not_executed ---

def test_reconcile_pending_not_executed(workspace):
    """intent_pending が残っているがファイルが存在しない → pending_not_executed。"""
    import json

    from koguchi.events import ExecutionEvent
    from koguchi.hashchain import compute_hash

    store = SQLiteExecutionStore(":memory:")

    # 存在しないファイルへの pending event を直接注入
    envelope = make_envelope(str(workspace), "never_written.txt", b"x")
    event = ExecutionEvent(
        event_id="ev-1",
        record_id=envelope.action_id,
        timestamp="2026-01-01T00:00:00+00:00",
        event_type="intent_pending",
        envelope=envelope,
        side_effect_observed="none",
        previous_hash="0" * 64,
        hash="",
    )
    payload_for_hash = {
        k: v
        for k, v in json.loads(event.model_dump_json()).items()
        if k != "hash"
    }
    h = compute_hash("0" * 64, payload_for_hash)
    event = event.model_copy(update={"hash": h})
    store.append(event)

    findings = reconcile(str(workspace), store)
    not_executed = [f for f in findings if f.diagnosis == "pending_not_executed"]
    assert len(not_executed) == 1


# --- pending: pending_executed_unconfirmed ---

def test_reconcile_pending_executed_unconfirmed(workspace):
    """副作用が成功したが commit 記録なし → pending_executed_unconfirmed。"""

    class FailAfterPendingStore(SQLiteExecutionStore):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._count = 0

        def append(self, event):
            self._count += 1
            if self._count == 1:
                super().append(event)  # intent_pending だけ書く
            else:
                raise RuntimeError("commit blocked")

    proxy = ToolProxy(str(workspace), FailAfterPendingStore(":memory:"))
    envelope = make_envelope(str(workspace), "orphan.txt", b"present")
    # write_file は pending 書込み後、実際にファイルを書いてから commit で失敗する
    # → UNCONFIRMED が返る
    result = proxy.write_file(envelope=envelope, content=b"present")
    assert result == ProxyResult.UNCONFIRMED

    findings = reconcile(str(workspace), proxy._store)
    unconfirmed = [
        f for f in findings if f.diagnosis == "pending_executed_unconfirmed"
    ]
    assert len(unconfirmed) == 1


# --- committed: committed_consistent ---

def test_reconcile_committed_consistent(workspace):
    """ファイルが commit 記録どおりに存在 → committed_consistent。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = make_envelope(str(workspace), "consistent.txt", b"data")
    result = proxy.write_file(envelope=envelope, content=b"data")
    assert result == ProxyResult.SUCCESS

    findings = reconcile(str(workspace), store)
    consistent = [f for f in findings if f.diagnosis == "committed_consistent"]
    assert len(consistent) == 1


# --- committed: committed_diverged (削除) ---

def test_reconcile_committed_diverged_file_deleted(workspace):
    """commit 記録があるのにファイルが削除されている → committed_diverged。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = make_envelope(str(workspace), "will_be_deleted.txt", b"temp")
    proxy.write_file(envelope=envelope, content=b"temp")

    # ファイルを削除
    (workspace / "will_be_deleted.txt").unlink()

    findings = reconcile(str(workspace), store)
    diverged = [f for f in findings if f.diagnosis == "committed_diverged"]
    assert len(diverged) == 1


# --- committed: committed_diverged (内容変更) ---

def test_reconcile_committed_diverged_content_changed(workspace):
    """commit 記録とファイル内容が食い違う → committed_diverged。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = make_envelope(str(workspace), "changed.txt", b"original")
    proxy.write_file(envelope=envelope, content=b"original")

    # 内容を書き換え（Proxy を迂回）
    (workspace / "changed.txt").write_bytes(b"modified!")

    findings = reconcile(str(workspace), store)
    diverged = [f for f in findings if f.diagnosis == "committed_diverged"]
    assert len(diverged) == 1


# --- shell pending ---

def test_reconcile_shell_pending_is_unconfirmed_with_lower_confidence(workspace):
    """shell pending はファイル存在確認不可 → pending_executed_unconfirmed, confidence 0.70。"""
    import json
    import uuid

    from koguchi.events import ExecutionEvent
    from koguchi.hashchain import compute_hash

    store = SQLiteExecutionStore(":memory:")

    envelope = ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="shell.execute",
        target=str(workspace),
        parameters_digest="abc",
        permission_scope="workspace",
        risk_class=["shell_exec"],
    )
    event = ExecutionEvent(
        event_id="ev-shell",
        record_id=envelope.action_id,
        timestamp="2026-01-01T00:00:00+00:00",
        event_type="intent_pending",
        envelope=envelope,
        side_effect_observed="none",
        previous_hash="0" * 64,
        hash="",
    )
    payload_for_hash = {
        k: v
        for k, v in json.loads(event.model_dump_json()).items()
        if k != "hash"
    }
    h = compute_hash("0" * 64, payload_for_hash)
    event = event.model_copy(update={"hash": h})
    store.append(event)

    findings = reconcile(str(workspace), store)
    unconfirmed = [
        f for f in findings if f.diagnosis == "pending_executed_unconfirmed"
    ]
    assert len(unconfirmed) == 1
    assert unconfirmed[0].confidence == 0.70


# --- network pending ---

def test_reconcile_network_pending_has_lowest_confidence(workspace):
    """network pending は完全外部 → pending_executed_unconfirmed, confidence 0.50。"""
    import json
    import uuid

    from koguchi.events import ExecutionEvent
    from koguchi.hashchain import compute_hash

    store = SQLiteExecutionStore(":memory:")

    envelope = ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="network.http_get",
        target="http://example.com",
        parameters_digest="abc",
        permission_scope="network",
        risk_class=["http_request"],
    )
    event = ExecutionEvent(
        event_id="ev-net",
        record_id=envelope.action_id,
        timestamp="2026-01-01T00:00:00+00:00",
        event_type="intent_pending",
        envelope=envelope,
        side_effect_observed="none",
        previous_hash="0" * 64,
        hash="",
    )
    payload_for_hash = {
        k: v
        for k, v in json.loads(event.model_dump_json()).items()
        if k != "hash"
    }
    h = compute_hash("0" * 64, payload_for_hash)
    event = event.model_copy(update={"hash": h})
    store.append(event)

    findings = reconcile(str(workspace), store)
    unconfirmed = [
        f for f in findings if f.diagnosis == "pending_executed_unconfirmed"
    ]
    assert len(unconfirmed) == 1
    assert unconfirmed[0].confidence == 0.50
