"""INV-1c: Tool Proxy を通さない workspace 変更を unrecorded_external_change として検出する。"""
from pathlib import Path

from koguchi.reconcile import reconcile
from koguchi.store import SQLiteExecutionStore


def test_reconciliation_detects_unrecorded_workspace_change(workspace, store):
    """INV-1c: Tool Proxy を通さない workspace 変更を、
    Store に対応 record がない unrecorded_external_change として検出する。"""
    # Store には何も記録せずに直接ファイルを書く（Proxy を迂回）
    sneaky = workspace / "sneaky.txt"
    sneaky.write_bytes(b"bypassed the proxy")

    findings = reconcile(str(workspace), store)

    unrecorded = [f for f in findings if f.diagnosis == "unrecorded_external_change"]
    assert len(unrecorded) == 1
    assert str(sneaky) == unrecorded[0].target
    assert unrecorded[0].confidence > 0.0
