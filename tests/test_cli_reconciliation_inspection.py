"""v0.14 CLI Inspection — read-only reconciliation CLI spike の証拠。"""

from koguchi.cli.reconciliation import inspect_reconciliation_records
from koguchi.persistence.reconciliation_records import (
    InMemoryReconciliationAuditStore,
    InMemoryReconciliationResultStore,
    ReconciliationAuditRecord,
    ReconciliationResultRecord,
)
from koguchi.reconciliation.filesystem_diff import ReconciliationStatus


def _make_stores():
    audit = InMemoryReconciliationAuditStore()
    result = InMemoryReconciliationResultStore()
    return audit, result


def _add_result(store, rid="r1", status=ReconciliationStatus.MATCHED):
    r = ReconciliationResultRecord(
        result_id=rid, request_id=f"req-{rid}",
        status=status, summary="ok",
        recommended_review_focus=["Review something"],
    )
    store.put(r)
    return r


def test_list_returns_exit_0():
    _, rs = _make_stores()
    _add_result(rs)
    r = inspect_reconciliation_records(["list"], *_make_stores())
    assert r.exit_code == 0


def test_list_empty_returns_exit_0():
    r = inspect_reconciliation_records(["list"], *_make_stores())
    assert r.exit_code == 0


def test_show_returns_exit_0_for_matched():
    audit, result = _make_stores()
    _add_result(result, "r1", ReconciliationStatus.MATCHED)
    r = inspect_reconciliation_records(["show", "r1"], audit, result)
    assert r.exit_code == 0


def test_show_returns_exit_0_for_mismatch():
    audit, result = _make_stores()
    _add_result(result, "r2", ReconciliationStatus.MISMATCH_OBSERVED)
    r = inspect_reconciliation_records(["show", "r2"], audit, result)
    assert r.exit_code == 0


def test_show_returns_exit_0_for_inconclusive():
    audit, result = _make_stores()
    _add_result(result, "r3", ReconciliationStatus.INCONCLUSIVE)
    r = inspect_reconciliation_records(["show", "r3"], audit, result)
    assert r.exit_code == 0


def test_show_unknown_returns_exit_1():
    r = inspect_reconciliation_records(["show", "nonexistent"], *_make_stores())
    assert r.exit_code == 1


def test_audit_returns_exit_0():
    audit, result = _make_stores()
    rec = ReconciliationAuditRecord(
        audit_id="a1", request_id="r1",
        route=["ToolProxy"], backend_id="fs", execution_id="e1",
        reconciliation_kind="filesystem_diff_reconciliation", mode="read_only",
    )
    audit.append(rec)
    r = inspect_reconciliation_records(["audit", "a1"], audit, result)
    assert r.exit_code == 0


def test_audit_unknown_returns_exit_1():
    r = inspect_reconciliation_records(["audit", "nonexistent"], *_make_stores())
    assert r.exit_code == 1


def test_missing_args_returns_exit_1():
    r = inspect_reconciliation_records([], *_make_stores())
    assert r.exit_code == 1


def test_forbidden_commands_return_exit_1():
    for cmd in ["retry", "repair", "approve", "reject", "deploy", "commit", "rollback", "delete"]:
        r = inspect_reconciliation_records([cmd], *_make_stores())
        assert r.exit_code == 1, f"Command '{cmd}' should be prohibited"


def test_unknown_command_returns_exit_1():
    r = inspect_reconciliation_records(["unknown"], *_make_stores())
    assert r.exit_code == 1


def test_cli_does_not_mutate_stores():
    audit, result = _make_stores()
    _add_result(result, "r1")
    rec = ReconciliationAuditRecord(
        audit_id="a1", request_id="r1",
        route=["ToolProxy"], backend_id="fs", execution_id="e1",
        reconciliation_kind="filesystem_diff_reconciliation", mode="read_only",
    )
    audit.append(rec)

    before_r = result.list_all()
    before_a = audit.list_all()

    inspect_reconciliation_records(["list"], audit, result)
    inspect_reconciliation_records(["show", "r1"], audit, result)
    inspect_reconciliation_records(["audit", "a1"], audit, result)

    assert result.list_all() == before_r
    assert audit.list_all() == before_a


def test_output_has_no_judgment_wording():
    audit, result = _make_stores()
    _add_result(result, "r1", ReconciliationStatus.MISMATCH_OBSERVED)

    r = inspect_reconciliation_records(["show", "r1"], audit, result)
    for forbidden in [
        "failed", "invalid", "unsafe", "approved", "rejected",
    ]:
        assert forbidden not in r.output.lower(), f"'{forbidden}' found in CLI output"
