"""Phase 2.B: shell.execute — 非 atomic ツールの side_effect_observed 経路の証拠。"""
import hashlib
import uuid
from pathlib import Path

import pytest

from koguchi.decision import SQLiteDecisionStore
from koguchi.envelope import ActionEnvelope
from koguchi.errors import EnvelopeRequiredError
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore


def _make_shell_envelope(workspace_dir: str) -> ActionEnvelope:
    return ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="shell.execute",
        target=str(Path(workspace_dir).resolve()),
        parameters_digest=hashlib.sha256(b"echo hello").hexdigest(),
        permission_scope="workspace",
        risk_class=["shell_exec"],
    )


# --- 正常完了 ---

def test_shell_execute_success(workspace):
    """shell.execute が正常完了 → SUCCESS, side_effect_observed = confirmed。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = _make_shell_envelope(str(workspace))
    result = proxy.execute_shell(envelope=envelope, command=["echo", "hello"])

    assert result == ProxyResult.SUCCESS

    events = store.events_for(envelope.action_id)
    assert len(events) == 2  # intent_pending + execution_committed
    committed = [e for e in events if e.event_type == "execution_committed"][0]
    assert committed.side_effect_observed == "confirmed"
    assert committed.result_digest is not None


def test_shell_result_digest_captures_output(workspace):
    """stdout / stderr / exit_code が result_digest に反映される。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = _make_shell_envelope(str(workspace))
    proxy.execute_shell(envelope=envelope, command=["echo", "captured"])

    events = store.events_for(envelope.action_id)
    committed = [e for e in events if e.event_type == "execution_committed"][0]

    # stdout "captured\n" + stderr "" + "0" が digest に含まれている
    expected = hashlib.sha256(b"captured\n" + b"" + b"0").hexdigest()
    assert committed.result_digest == expected


def test_shell_non_zero_exit_is_still_confirmed(workspace):
    """非ゼロ exit でもプロセス完了は confirmed。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = _make_shell_envelope(str(workspace))
    result = proxy.execute_shell(
        envelope=envelope,
        command=["sh", "-c", "echo error >&2; exit 1"],
    )

    assert result == ProxyResult.SUCCESS
    events = store.events_for(envelope.action_id)
    committed = [e for e in events if e.event_type == "execution_committed"][0]
    assert committed.side_effect_observed == "confirmed"


# --- タイムアウト → unknown ---

def test_shell_timeout_produces_unknown(workspace):
    """タイムアウト → FAILURE, side_effect_observed = unknown。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = _make_shell_envelope(str(workspace))
    result = proxy.execute_shell(
        envelope=envelope,
        command=["sleep", "10"],
        timeout=0.1,
    )

    assert result == ProxyResult.FAILURE
    events = store.events_for(envelope.action_id)
    assert len(events) == 2  # intent_pending + execution_failed
    failed = [e for e in events if e.event_type == "execution_failed"][0]
    assert failed.side_effect_observed == "unknown"


# --- INV-1a ---

def test_shell_execute_requires_envelope(workspace, store):
    """envelope=None → EnvelopeRequiredError。"""
    proxy = ToolProxy(str(workspace), store)

    with pytest.raises(EnvelopeRequiredError):
        proxy.execute_shell(envelope=None, command=["echo", "x"])


# --- Decision Logger 統合 ---

def test_shell_execute_with_decision_logger(workspace):
    """shell.execute で Decision Logger が機能する。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(str(workspace), exec_store, decision_store=dec_store)

    envelope = _make_shell_envelope(str(workspace))
    result = proxy.execute_shell(
        envelope=envelope,
        command=["echo", "intentful"],
        intent="テスト用のシェル実行",
    )

    assert result == ProxyResult.SUCCESS

    decision = dec_store.get(envelope.action_id)
    assert decision is not None
    assert decision.intent == "テスト用のシェル実行"

    events = exec_store.events_for(envelope.action_id)
    for ev in events:
        assert ev.intent == "テスト用のシェル実行"
        assert ev.decision_ref is not None
