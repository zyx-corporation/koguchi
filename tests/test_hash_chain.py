"""hash chain の不変条件: 各 event の previous_hash が直前 event の hash と一致する。"""
import json

from koguchi.events import ProxyResult
from koguchi.hashchain import GENESIS_HASH
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def test_hash_chain_is_consistent_after_two_writes(workspace):
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)
    c1, c2 = b"first", b"second"
    env1 = make_envelope(str(workspace), "a.txt", c1)
    env2 = make_envelope(str(workspace), "b.txt", c2)

    assert proxy.write_file(envelope=env1, content=c1) == ProxyResult.SUCCESS
    assert proxy.write_file(envelope=env2, content=c2) == ProxyResult.SUCCESS

    # グローバル挿入順(rowid)で previous_hash == 直前 hash を突く
    rows = store._conn.execute(
        "SELECT payload, hash FROM execution_events ORDER BY rowid"
    ).fetchall()
    assert len(rows) == 4  # pending+committed が 2 回

    prev = GENESIS_HASH
    for payload, h in rows:
        ev = json.loads(payload)
        assert ev["previous_hash"] == prev
        prev = h


def test_canonical_serialize_raises_on_non_serializable(workspace):
    """シリアライズ不能なオブジェクトで TypeError が発生する。"""
    import pytest

    from koguchi.hashchain import canonical_serialize

    with pytest.raises(TypeError):
        canonical_serialize({"bad": object()})
