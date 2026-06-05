"""INV-1b 第一相: intent_pending を書けない場合、副作用を起こさず REJECTED を返す。"""

from koguchi.errors import StoreWriteError
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


class BrokenStore(SQLiteExecutionStore):
    """append を常に失敗させる Store。"""

    def append(self, event):
        raise StoreWriteError("intentional failure")


def test_write_is_not_executed_when_pending_record_cannot_be_written(workspace):
    """INV-1b 第一相: 実行前の intent_pending を書けない場合、
    副作用を起こさず REJECTED を返す。Store にも workspace にも痕跡を残さない。"""
    store = BrokenStore(":memory:")
    proxy = ToolProxy(str(workspace), store)
    envelope = make_envelope(str(workspace))

    result = proxy.write_file(envelope=envelope, content=b"must not appear")

    assert result == ProxyResult.REJECTED

    # workspace に何も書かれていないこと
    target = workspace / "out.txt"
    assert not target.exists()

    # Store には pending も残らない（BrokenStore は append を拒否するため）
    assert store.pending() == []
