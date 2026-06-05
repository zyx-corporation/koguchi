"""統合テスト — 複数ツール連鎖とエンドツーエンドシナリオの証拠。"""
import uuid
from pathlib import Path

from koguchi.envelope import ActionEnvelope
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore


def _write_envelope(ws: str, filename: str) -> ActionEnvelope:
    import hashlib

    target = str(Path(ws) / filename)
    return ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="filesystem.write",
        target=target,
        parameters_digest=hashlib.sha256(b"data").hexdigest(),
        expected_result_digest=hashlib.sha256(b"data").hexdigest(),
        permission_scope="workspace",
        risk_class=["file_write"],
    )


def _mkdir_envelope(ws: str, subdir: str) -> ActionEnvelope:
    return ActionEnvelope(
        action_id=str(uuid.uuid4()),
        tool="filesystem.mkdir",
        target=str(Path(ws) / subdir),
        parameters_digest="unused",
        permission_scope="workspace",
        risk_class=["file_write"],
    )


def test_mkdir_then_write_file(workspace):
    """mkdir → write_file の連鎖が正常に動作する。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    # 1. ディレクトリ作成
    mkdir_env = _mkdir_envelope(str(workspace), "sub")
    assert proxy.make_directory(envelope=mkdir_env) == ProxyResult.SUCCESS
    assert (workspace / "sub").is_dir()

    # 2. ファイル書込み
    write_env = _write_envelope(str(workspace), "sub/file.txt")
    assert proxy.write_file(envelope=write_env, content=b"data") == ProxyResult.SUCCESS
    assert (workspace / "sub" / "file.txt").read_bytes() == b"data"

    # 3. 両方の event が記録されている
    assert len(store.events_for(mkdir_env.action_id)) == 2
    assert len(store.events_for(write_env.action_id)) == 2


def test_multiple_writes_independent_records(workspace):
    """複数回の write_file が独立した record_id で記録される。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    envelopes = []
    for i in range(3):
        env = _write_envelope(str(workspace), f"file_{i}.txt")
        assert proxy.write_file(envelope=env, content=b"data") == ProxyResult.SUCCESS
        envelopes.append(env)

    # 各 record が独立
    for env in envelopes:
        events = store.events_for(env.action_id)
        assert len(events) == 2
        types = {e.event_type for e in events}
        assert types == {"intent_pending", "execution_committed"}


def test_hash_chain_remains_valid_after_mixed_operations(workspace):
    """write + mkdir + shell の混合後も hash chain が破綻しない。"""
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    # write
    proxy.write_file(envelope=_write_envelope(str(workspace), "a.txt"), content=b"x")
    # mkdir
    proxy.make_directory(envelope=_mkdir_envelope(str(workspace), "d"))
    # write
    proxy.write_file(envelope=_write_envelope(str(workspace), "b.txt"), content=b"y")

    findings = store.verify_chain()
    assert findings == []
