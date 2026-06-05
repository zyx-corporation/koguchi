"""Phase 2.D: filesystem.mkdir — 独立した副作用管理の証拠。"""
import uuid
from pathlib import Path

import pytest

from koguchi.envelope import ActionEnvelope
from koguchi.errors import EnvelopeRequiredError, WorkspaceBoundaryError
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore


def _make_mkdir_envelope(workspace_dir: str, subdir: str = "newdir") -> ActionEnvelope:
    return ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="filesystem.mkdir",
        target=str(Path(workspace_dir) / subdir),
        parameters_digest="unused",
        permission_scope="workspace",
        risk_class=["file_write"],
    )


# --- 成功 ---

def test_mkdir_creates_directory(workspace):
    """mkdir がディレクトリを作成し SUCCESS を返す。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = _make_mkdir_envelope(str(workspace))
    result = proxy.make_directory(envelope=envelope)

    assert result == ProxyResult.SUCCESS
    target = workspace / "newdir"
    assert target.exists()
    assert target.is_dir()

    events = store.events_for(envelope.action_id)
    assert len(events) == 2  # intent_pending + execution_committed


def test_mkdir_creates_nested_directories(workspace):
    """parents=True によりネストしたディレクトリを作成できる。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = _make_mkdir_envelope(str(workspace), "a/b/c")
    result = proxy.make_directory(envelope=envelope)

    assert result == ProxyResult.SUCCESS
    assert (workspace / "a" / "b" / "c").is_dir()


# --- 冪等 ---

def test_mkdir_existing_directory_is_success(workspace):
    """既存ディレクトリへの mkdir は SUCCESS（exist_ok=True）。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelope = _make_mkdir_envelope(str(workspace))
    proxy.make_directory(envelope=envelope)  # 1回目

    result = proxy.make_directory(envelope=envelope)  # 2回目（既存）
    assert result == ProxyResult.SUCCESS

    events = store.events_for(envelope.action_id)
    assert len(events) == 4  # 2回分の intent_pending + execution_committed


# --- INV-1a ---

def test_mkdir_requires_envelope(workspace, store):
    """envelope=None → EnvelopeRequiredError。"""
    proxy = ToolProxy(str(workspace), store)
    with pytest.raises(EnvelopeRequiredError):
        proxy.make_directory(envelope=None)


# --- 境界 ---

def test_mkdir_rejects_outside_workspace(tmp_path):
    """workspace 外への mkdir は WorkspaceBoundaryError。"""
    ws = tmp_path / "ws"
    ws.mkdir()
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(ws), store)

    envelope = _make_mkdir_envelope(str(tmp_path), "outside")
    with pytest.raises(WorkspaceBoundaryError):
        proxy.make_directory(envelope=envelope)


# --- Decision Logger 統合 ---

def test_mkdir_with_decision_logger(workspace):
    """make_directory で Decision Logger が機能する。"""
    from koguchi.decision import SQLiteDecisionStore

    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(str(workspace), exec_store, decision_store=dec_store)

    envelope = _make_mkdir_envelope(str(workspace), "intentful_dir")
    result = proxy.make_directory(
        envelope=envelope,
        intent="ログ出力用ディレクトリの作成",
    )

    assert result == ProxyResult.SUCCESS
    decision = dec_store.get(envelope.action_id)
    assert decision is not None
    assert decision.intent == "ログ出力用ディレクトリの作成"


# --- 失敗経路 ---

def test_mkdir_fails_when_file_exists_at_target(workspace):
    """target に同名のファイルが存在する場合 → FAILURE。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    # 同名のファイルを作成
    (workspace / "blocked").write_bytes(b"x")

    envelope = _make_mkdir_envelope(str(workspace), "blocked")
    result = proxy.make_directory(envelope=envelope)

    assert result == ProxyResult.FAILURE
    events = store.events_for(envelope.action_id)
    assert len(events) == 2  # intent_pending + execution_failed
