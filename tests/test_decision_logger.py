"""Phase 2: Decision Logger — 縮退防止フック (intent / decision_ref / context_ref) の証拠。"""
import hashlib
import json

from koguchi.decision import SQLiteDecisionStore
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope

# --- Decision 記録 + フック伝播 ---

def test_decision_hooks_are_filled_when_decision_store_is_used(workspace):
    """decision_store 注入 + intent 指定時、ExecutionEvent の intent / decision_ref
    / context_ref が埋まる。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(str(workspace), exec_store, decision_store=dec_store)

    content = b"meaningful write"
    envelope = make_envelope(str(workspace), content=content)
    ctx = {"phase": "2", "caller": "test"}

    result = proxy.write_file(
        envelope=envelope, content=content,
        intent="重要な設定ファイルの書き換え", context=ctx,
    )
    assert result == ProxyResult.SUCCESS

    # Store の intent_pending event にフックが伝播している
    events = exec_store.events_for(envelope.action_id)
    for ev in events:
        assert ev.intent == "重要な設定ファイルの書き換え"
        assert ev.decision_ref is not None
        assert ev.context_ref is not None

    # context_ref は context 辞書の SHA-256 digest
    expected_ctx_ref = hashlib.sha256(
        json.dumps(ctx, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    assert events[0].context_ref == expected_ctx_ref


def test_decision_is_retrievable_after_write(workspace):
    """DecisionStore.get() で記録された Decision を取得できる。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(str(workspace), exec_store, decision_store=dec_store)

    envelope = make_envelope(str(workspace), content=b"retrievable")
    result = proxy.write_file(
        envelope=envelope, content=b"retrievable",
        intent="検索可能性のテスト",
    )
    assert result == ProxyResult.SUCCESS

    decision = dec_store.get(envelope.action_id)
    assert decision is not None
    assert decision.action_id == envelope.action_id
    assert decision.intent == "検索可能性のテスト"
    assert decision.context_snapshot is None


# --- Decision 記録失敗 → REJECTED ---

def test_write_rejected_when_decision_record_fails(workspace):
    """Decision 記録に失敗した場合、副作用を起こさず REJECTED。"""
    exec_store = SQLiteExecutionStore(":memory:")

    class BrokenDecisionStore:
        def record(self, decision):
            raise RuntimeError("decision store down")

        def get(self, action_id):
            return None

        def last_hash(self):
            return "0" * 64

    proxy = ToolProxy(str(workspace), exec_store, decision_store=BrokenDecisionStore())
    envelope = make_envelope(str(workspace), content=b"should not appear")

    result = proxy.write_file(
        envelope=envelope, content=b"should not appear",
        intent="失敗する意思決定",
    )
    assert result == ProxyResult.REJECTED
    assert not (workspace / "out.txt").exists()
    assert exec_store.pending() == []


# --- 後方互換性 ---

def test_backward_compatible_without_decision_store(workspace):
    """decision_store=None の場合、フックは None のまま。"""
    exec_store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), exec_store)

    envelope = make_envelope(str(workspace), content=b"old school")
    result = proxy.write_file(envelope=envelope, content=b"old school")
    assert result == ProxyResult.SUCCESS

    events = exec_store.events_for(envelope.action_id)
    for ev in events:
        assert ev.intent is None
        assert ev.decision_ref is None
        assert ev.context_ref is None


def test_decision_store_present_but_no_intent_passed(workspace):
    """decision_store が注入されていても intent=None なら Decision は作らずフックも None。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(str(workspace), exec_store, decision_store=dec_store)

    envelope = make_envelope(str(workspace), content=b"no intent")
    result = proxy.write_file(envelope=envelope, content=b"no intent")
    assert result == ProxyResult.SUCCESS

    events = exec_store.events_for(envelope.action_id)
    for ev in events:
        assert ev.intent is None
        assert ev.decision_ref is None
        assert ev.context_ref is None

    # DecisionStore にも何も残っていない
    assert dec_store.get(envelope.action_id) is None


# --- intent_pending / execution_failed / execution_committed すべてに伝播 ---

def test_intent_propagates_to_all_events_in_same_record(workspace):
    """同一 record 内の intent_pending / execution_failed / execution_committed の
    すべてに intent が伝播する。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(str(workspace), exec_store, decision_store=dec_store)

    envelope = make_envelope(str(workspace), "propagate.txt", b"x")
    result = proxy.write_file(
        envelope=envelope, content=b"x",
        intent="全イベント伝播テスト",
    )
    assert result == ProxyResult.SUCCESS

    events = exec_store.events_for(envelope.action_id)
    assert len(events) == 2  # intent_pending + execution_committed
    event_types = {ev.event_type for ev in events}
    assert event_types == {"intent_pending", "execution_committed"}
    for ev in events:
        assert ev.intent == "全イベント伝播テスト"
        assert ev.decision_ref is not None
