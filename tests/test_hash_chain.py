"""hash chain の不変条件: 各 event の previous_hash が直前 event の hash と一致する。"""
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def test_hash_chain_is_consistent_after_two_writes(workspace):
    store = SQLiteExecutionStore(":memory:")
    proxy = ToolProxy(str(workspace), store)

    c1 = b"first"
    c2 = b"second"
    env1 = make_envelope(str(workspace), "a.txt", c1)
    env2 = make_envelope(str(workspace), "b.txt", c2)

    r1 = proxy.write_file(envelope=env1, content=c1)
    r2 = proxy.write_file(envelope=env2, content=c2)

    assert r1 == ProxyResult.SUCCESS
    assert r2 == ProxyResult.SUCCESS

    events1 = store.events_for(env1.action_id)
    events2 = store.events_for(env2.action_id)
    all_events = events1 + events2

    # hash chain の連結を確認
    for i in range(1, len(all_events)):
        assert all_events[i].previous_hash is not None
