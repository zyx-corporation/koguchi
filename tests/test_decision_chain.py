"""DecisionStore hash chain — verify_chain の証拠。"""
from koguchi.decision import SQLiteDecisionStore
from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def _write_two_decisions(workspace):
    """Decision 付きで2回 write_file するヘルパー。"""
    db = ":memory:"
    exec_store = SQLiteExecutionStore(db)
    dec_store = SQLiteDecisionStore(db)
    proxy = ToolProxy(str(workspace), exec_store, decision_store=dec_store)

    for fname, content, intent in [
        ("a.txt", b"alpha", "最初の書込み"),
        ("b.txt", b"beta", "二回目の書込み"),
    ]:
        envelope = make_envelope(str(workspace), fname, content)
        result = proxy.write_file(envelope=envelope, content=content, intent=intent)
        assert result == ProxyResult.SUCCESS

    return dec_store


def test_decision_chain_is_clean(workspace):
    """正常な Decision chain は空リストを返す。"""
    dec_store = _write_two_decisions(workspace)
    findings = dec_store.verify_chain()
    assert findings == []


def test_decision_chain_detects_previous_hash_mismatch(workspace):
    """previous_hash を書き換えると検出される。"""
    dec_store = _write_two_decisions(workspace)

    row = dec_store._conn.execute(
        "SELECT rowid, previous_hash FROM decisions ORDER BY rowid LIMIT 1 OFFSET 1"
    ).fetchone()
    dec_store._conn.execute(
        "UPDATE decisions SET previous_hash = ? WHERE rowid = ?",
        ("deadbeef" * 8, row[0]),
    )
    dec_store._conn.commit()

    findings = dec_store.verify_chain()
    assert any(f.diagnosis == "previous_hash_mismatch" for f in findings)
