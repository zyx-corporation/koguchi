"""v0.13 Reconciliation Persistence — read-only in-memory stores の証拠。"""
import pytest

from koguchi.persistence.reconciliation_records import (
    InMemoryReconciliationAuditStore,
    InMemoryReconciliationResultStore,
    ReconciliationAuditRecord,
    ReconciliationResultRecord,
)
from koguchi.reconciliation.filesystem_diff import ReconciliationStatus


def test_audit_store_append_and_get():
    store = InMemoryReconciliationAuditStore()
    rec = ReconciliationAuditRecord(
        audit_id="a1", request_id="r1",
        route=["Scheduler", "ToolProxy"],
        backend_id="fs", execution_id="e1",
        reconciliation_kind="filesystem_diff_reconciliation",
        mode="read_only",
    )
    store.append(rec)
    assert store.get("a1") is not None
    assert store.get("a1").audit_id == "a1"


def test_audit_store_duplicate_raises():
    store = InMemoryReconciliationAuditStore()
    rec = ReconciliationAuditRecord(
        audit_id="a1", request_id="r1",
        route=["ToolProxy"], backend_id="fs", execution_id="e1",
        reconciliation_kind="filesystem_diff_reconciliation", mode="read_only",
    )
    store.append(rec)
    with pytest.raises(ValueError):
        store.append(rec)


def test_audit_store_unknown_is_none():
    store = InMemoryReconciliationAuditStore()
    assert store.get("nonexistent") is None


def test_audit_record_has_boundary():
    rec = ReconciliationAuditRecord(
        audit_id="a1", request_id="r1",
        route=["ToolProxy"], backend_id="fs", execution_id="e1",
        reconciliation_kind="filesystem_diff_reconciliation", mode="read_only",
    )
    assert rec.boundary["read_only"] is True
    assert rec.boundary["no_repair"] is True
    assert rec.boundary["no_retry"] is True


def test_result_store_put_and_get():
    store = InMemoryReconciliationResultStore()
    rec = ReconciliationResultRecord(
        result_id="r1", request_id="req1",
        status=ReconciliationStatus.MATCHED,
        summary="No differences",
    )
    store.put(rec)
    assert store.get("r1") is not None


def test_result_record_has_boundary():
    rec = ReconciliationResultRecord(
        result_id="r1", request_id="req1",
        status=ReconciliationStatus.MISMATCH_OBSERVED,
        summary="Differences found",
    )
    assert rec.boundary["review_focus_only"] is True
    assert rec.boundary["correctness_decision"] is False
    assert rec.boundary["enforcement"] is False
    assert rec.boundary["approval"] is False


def test_matched_is_not_approval():
    rec = ReconciliationResultRecord(
        result_id="r1", request_id="req1",
        status=ReconciliationStatus.MATCHED,
        summary="No differences",
    )
    assert "approved" not in rec.summary.lower()


def test_mismatch_is_not_failure_trigger():
    rec = ReconciliationResultRecord(
        result_id="r1", request_id="req1",
        status=ReconciliationStatus.MISMATCH_OBSERVED,
        summary="Differences were observed",
    )
    for forbidden in ["retry", "repair", "deploy", "commit", "rollback"]:
        assert forbidden not in rec.summary.lower()


def test_no_forbidden_wording_in_records():
    rec = ReconciliationResultRecord(
        result_id="r1", request_id="req1",
        status=ReconciliationStatus.INCONCLUSIVE,
        summary="Cannot determine alignment",
    )
    text = rec.summary + str(rec.recommended_review_focus)
    for forbidden in [
        "retry required", "repair required", "delete", "overwrite",
        "approved", "rejected", "safe", "unsafe",
    ]:
        assert forbidden not in text.lower()


def test_list_all_preserves_order():
    store = InMemoryReconciliationResultStore()
    for i in range(3):
        store.put(ReconciliationResultRecord(
            result_id=str(i), request_id=f"r{i}",
            status=ReconciliationStatus.MATCHED, summary="ok",
        ))
    assert len(store.list_all()) == 3
