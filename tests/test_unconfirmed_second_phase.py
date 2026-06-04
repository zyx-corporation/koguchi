"""INV-1b 第二相: 副作用成功後に commit 記録が失敗すれば UNCONFIRMED を返す。"""
from koguchi.errors import StoreWriteError
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


class FailAfterPendingStore(SQLiteExecutionStore):
    """intent_pending の 1 件目は成功し、2 件目以降は失敗する Store。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._append_count = 0

    def append(self, event):
        self._append_count += 1
        if self._append_count == 1:
            super().append(event)  # intent_pending を書く
        else:
            raise StoreWriteError("commit record write failure")


def test_write_done_but_commit_record_failed_returns_unconfirmed(workspace):
    """INV-1b 第二相: 実行は成功したが commit record 書込みに失敗した場合、
    戻り値は SUCCESS でも FAILURE でもなく UNCONFIRMED。
    Store には intent_pending が 1 件残り、side_effect_observed は confirmed。"""
    store = FailAfterPendingStore(":memory:")
    proxy = ToolProxy(str(workspace), store)
    content = b"written content"
    envelope = make_envelope(str(workspace), content=content)

    result = proxy.write_file(envelope=envelope, content=content)

    assert result == ProxyResult.UNCONFIRMED

    # workspace にはファイルが書かれていること（副作用は成功）
    target = workspace / "out.txt"
    assert target.exists()
    assert target.read_bytes() == content

    # Store には intent_pending が 1 件残存
    pending = store.pending()
    assert len(pending) == 1
    assert pending[0].event_type == "intent_pending"
    assert pending[0].side_effect_observed == "none"  # pending 書込み時点では none
