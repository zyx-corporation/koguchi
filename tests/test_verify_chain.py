"""Issue #10: verify_chain() — hash chain の正常・改竄・previous_hash 不整合を検出する。"""
import json

from koguchi.events import ProxyResult
from koguchi.proxy import ToolProxy
from koguchi.store import SQLiteExecutionStore
from tests.conftest import make_envelope


def _write_two(workspace, store):
    proxy = ToolProxy(str(workspace), store)
    c1, c2 = b"alpha", b"beta"
    r1 = proxy.write_file(envelope=make_envelope(str(workspace), "a.txt", c1), content=c1)
    r2 = proxy.write_file(envelope=make_envelope(str(workspace), "b.txt", c2), content=c2)
    assert r1 == ProxyResult.SUCCESS
    assert r2 == ProxyResult.SUCCESS


def test_verify_chain_clean(workspace):
    """正常な chain は空リストを返す。"""
    store = SQLiteExecutionStore(":memory:")
    _write_two(workspace, store)

    findings = store.verify_chain()

    assert findings == [], f"unexpected findings: {findings}"


def test_verify_chain_detects_payload_tampering(workspace):
    """payload を直接書き換えると hash_mismatch が検出される。"""
    store = SQLiteExecutionStore(":memory:")
    _write_two(workspace, store)

    # 最初の event の payload を改竄する
    row = store._conn.execute(
        "SELECT rowid, payload FROM execution_events ORDER BY rowid LIMIT 1"
    ).fetchone()
    rowid, payload_str = row
    payload = json.loads(payload_str)
    payload["record_id"] = "tampered-record-id"
    store._conn.execute(
        "UPDATE execution_events SET payload = ? WHERE rowid = ?",
        (json.dumps(payload, sort_keys=True), rowid),
    )
    store._conn.commit()

    findings = store.verify_chain()

    hash_mismatches = [f for f in findings if f.diagnosis == "hash_mismatch"]
    assert len(hash_mismatches) >= 1


def test_verify_chain_detects_previous_hash_mismatch(workspace):
    """previous_hash を書き換えると previous_hash_mismatch が検出される。"""
    store = SQLiteExecutionStore(":memory:")
    _write_two(workspace, store)

    # 2 番目の event の previous_hash を壊す
    row = store._conn.execute(
        "SELECT rowid, payload FROM execution_events ORDER BY rowid LIMIT 1 OFFSET 1"
    ).fetchone()
    rowid, payload_str = row
    payload = json.loads(payload_str)
    payload["previous_hash"] = "deadbeef" * 8  # 偽の previous_hash
    store._conn.execute(
        "UPDATE execution_events SET payload = ? WHERE rowid = ?",
        (json.dumps(payload, sort_keys=True), rowid),
    )
    store._conn.commit()

    findings = store.verify_chain()

    prev_mismatches = [f for f in findings if f.diagnosis == "previous_hash_mismatch"]
    assert len(prev_mismatches) >= 1
