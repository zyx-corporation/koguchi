"""Issue #7: 親ディレクトリが存在しない場合は REJECTED（暗黙の mkdir はしない）。"""
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def test_write_rejected_when_parent_dir_does_not_exist(tmp_path):
    """§12 スコープ: 親ディレクトリが存在しない場合は副作用なし REJECTED。
    Store にも workspace にも痕跡を残さない。"""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    # 存在しないサブディレクトリを target に指定
    envelope = make_envelope(str(workspace), "subdir/out.txt", b"x")

    result = proxy.write_file(envelope=envelope, content=b"x")

    assert result == ProxyResult.REJECTED
    # workspace にディレクトリが作られていないこと
    assert not (workspace / "subdir").exists()
    # Store には何も残っていないこと（intent_pending も書かれない）
    assert store.pending() == []
