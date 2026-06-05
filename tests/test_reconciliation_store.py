"""v0.7 Reconciliation Store — persistent result の証拠。"""
import pytest

from koguchi.reconciliation_scheduler import (
    ReconciliationResult,
    ReconciliationScheduler,
    ReconciliationStatus,
)
from koguchi.reconciliation_store import (
    JsonlReconciliationResultStore,
    ReconciliationSerializationError,
)


def _allow_event(rid="req-1") -> dict:
    return {
        "schema_version": 1,
        "request_id": rid,
        "tool_name": "filesystem.write",
        "allowed": True,
        "reason": "allowed",
        "workspace": "/tmp",
        "timestamp": "2026-06-05T00:00:00Z",
        "error": None,
        "execution_backend": "rust_chokepoint",
    }


def test_store_appends_result(tmp_path):
    path = tmp_path / "results.jsonl"
    store = JsonlReconciliationResultStore(path)
    result = ReconciliationResult("j1", "r1", ReconciliationStatus.PASSED,
                                   message="ok")
    store.append(result, source_event_backend="rust_chokepoint")
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 1


def test_store_reads_results(tmp_path):
    path = tmp_path / "results.jsonl"
    store = JsonlReconciliationResultStore(path)
    store.append(ReconciliationResult("j1", "r1", ReconciliationStatus.PASSED,
                                       message="ok"))
    results = store.read_results()
    assert len(results) == 1
    assert results[0]["status"] == "passed"


def test_store_includes_schema_version(tmp_path):
    path = tmp_path / "results.jsonl"
    store = JsonlReconciliationResultStore(path)
    store.append(ReconciliationResult("j1", "r1", ReconciliationStatus.PASSED))
    assert store.read_results()[0]["schema_version"] == 1


def test_store_includes_source_backend(tmp_path):
    path = tmp_path / "results.jsonl"
    store = JsonlReconciliationResultStore(path)
    store.append(ReconciliationResult("j1", "r1", ReconciliationStatus.PASSED),
                 source_event_backend="rust_chokepoint")
    assert store.read_results()[0]["source_event_backend"] == "rust_chokepoint"


def test_scheduler_persists_results(tmp_path):
    path = tmp_path / "results.jsonl"
    result_store = JsonlReconciliationResultStore(path)
    scheduler = ReconciliationScheduler(
        [_allow_event("r1")], result_store=result_store,
    )
    scheduler.plan()
    scheduler.run_pending()
    results = result_store.read_results()
    assert len(results) == 1
    assert results[0]["status"] == "passed"


def test_scheduler_captures_backend(tmp_path):
    path = tmp_path / "results.jsonl"
    result_store = JsonlReconciliationResultStore(path)
    scheduler = ReconciliationScheduler(
        [_allow_event("r-backend")], result_store=result_store,
    )
    scheduler.plan()
    scheduler.run_pending()
    assert result_store.read_results()[0]["source_event_backend"] == "rust_chokepoint"


def test_broken_jsonl_raises(tmp_path):
    path = tmp_path / "results.jsonl"
    path.write_text("not json\n", encoding="utf-8")
    store = JsonlReconciliationResultStore(path, create_parent=False)
    with pytest.raises(ReconciliationSerializationError):
        store.read_results()
