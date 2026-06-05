"""Phase 3: Context Resolver — コンテキスト自動キャプチャの証拠。"""
from koguchi.context import SystemContextResolver
from koguchi.decision import SQLiteDecisionStore
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def test_context_resolver_auto_captures(workspace):
    """context_resolver 注入時、明示的 context なしで自動キャプチャされる。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(
        str(workspace), exec_store,
        decision_store=dec_store,
        context_resolver=SystemContextResolver(),
    )

    envelope = make_envelope(str(workspace), content=b"auto")
    result = proxy.write_file(
        envelope=envelope, content=b"auto",
        intent="自動コンテキストテスト",
    )

    assert result == ProxyResult.SUCCESS

    decision = dec_store.get(envelope.action_id)
    assert decision is not None
    assert decision.context_snapshot is not None
    ctx = decision.context_snapshot
    assert "timestamp" in ctx
    assert "python_version" in ctx
    assert "platform" in ctx
    assert "pid" in ctx

    # context_ref も埋まっている
    events = exec_store.events_for(envelope.action_id)
    assert events[0].context_ref is not None


def test_explicit_context_overrides_auto_capture(workspace):
    """明示的に context を渡した場合、自動キャプチャは行われない。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(
        str(workspace), exec_store,
        decision_store=dec_store,
        context_resolver=SystemContextResolver(),
    )

    envelope = make_envelope(str(workspace), content=b"explicit")
    custom_ctx = {"custom_key": "custom_value"}
    proxy.write_file(
        envelope=envelope, content=b"explicit",
        intent="明示的コンテキストテスト",
        context=custom_ctx,
    )

    decision = dec_store.get(envelope.action_id)
    assert decision.context_snapshot == custom_ctx


def test_no_context_resolver_no_capture(workspace):
    """context_resolver 未注入なら context は None のまま（後方互換）。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(str(workspace), exec_store, decision_store=dec_store)

    envelope = make_envelope(str(workspace), content=b"no resolver")
    proxy.write_file(
        envelope=envelope, content=b"no resolver",
        intent="コンテキストなし",
    )

    decision = dec_store.get(envelope.action_id)
    assert decision.context_snapshot is None
