"""INV-1 / INV-1a: Envelope を伴わない管理対象 write は REJECTED を返す。"""
import pytest

from koguchi.errors import EnvelopeRequiredError
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore


def test_managed_write_requires_proxy_and_envelope(workspace, store):
    """INV-1 / INV-1a: Envelope を伴わない、または Proxy を経由しない
    管理対象 write は実行されず REJECTED を返す。"""
    proxy = ToolProxy(str(workspace), store)

    with pytest.raises(EnvelopeRequiredError):
        proxy.write_file(envelope=None, content=b"should not be written")

    # workspace に何も書かれていないこと
    assert list(workspace.iterdir()) == []
    # Store にも何も残っていないこと
    assert store.pending() == []
